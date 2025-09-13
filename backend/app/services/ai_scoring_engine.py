# app/services/ai_scoring_engine.py
from __future__ import annotations
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import json
import logging
import re
from app.services.pnm_scoring import PNMScore, PNMScoringEngine

@dataclass
class AIScoreResult:
    """Result of AI-powered scoring"""
    score: float                    # 0-7 scale matching question options
    confidence: float              # 0-1 confidence in scoring
    reasoning: str                 # Explanation of scoring rationale
    quality_of_life_impact: str   # Impact description
    extracted_insights: List[str] # Key insights from response

class AIFreeTextScorer:
    """
    AI-powered scoring for free-text user responses.
    Converts unstructured responses to structured scores matching question bank format.
    """
    
    def __init__(self, ai_router=None):
        self.ai_router = ai_router
        self.log = logging.getLogger(__name__)
        
        # Scoring criteria mapping (aligned with question bank 0-7 scale)
        self.score_mapping = {
            0: {"qol": "No impact on quality of life", "level": "Fully prepared/optimal"},
            1: {"qol": "90% quality of life", "level": "Excellent management"},
            2: {"qol": "75% quality of life", "level": "Good management"},
            3: {"qol": "65% quality of life", "level": "Moderate management"},
            4: {"qol": "50% quality of life", "level": "Some challenges"},
            5: {"qol": "35% quality of life", "level": "Significant challenges"},
            6: {"qol": "25% quality of life", "level": "Major difficulties"},
            7: {"qol": "<10% quality of life", "level": "Extreme impact"}
        }
    
    async def score_free_text_response(
        self, 
        user_response: str, 
        question_context: Dict[str, Any],
        pnm_domain: str,
        conversation_history: List[Dict] = None
    ) -> AIScoreResult:
        """
        Score free-text response using AI analysis
        """
        try:
            # Prepare scoring prompt
            scoring_prompt = self._build_scoring_prompt(
                user_response, 
                question_context, 
                pnm_domain,
                conversation_history
            )
            
            # Get AI analysis
            if self.ai_router:
                analysis = await self.ai_router.analyze_text(scoring_prompt)
            else:
                # Fallback to rule-based scoring
                analysis = self._fallback_rule_based_scoring(user_response, pnm_domain)
            
            # Extract structured score from AI response
            score_result = self._parse_ai_scoring_response(analysis, user_response)
            
            self.log.info(f"AI scoring completed: score={score_result.score}, confidence={score_result.confidence}")
            
            return score_result
            
        except Exception as e:
            self.log.error(f"AI scoring failed: {e}")
            # Fallback to rule-based scoring
            return self._fallback_rule_based_scoring(user_response, pnm_domain)
    
    def _build_scoring_prompt(
        self, 
        user_response: str, 
        question_context: Dict[str, Any],
        pnm_domain: str,
        conversation_history: List[Dict] = None
    ) -> str:
        """Build comprehensive scoring prompt for AI"""
        
        prompt = f"""
You are an expert in ALS (Amyotrophic Lateral Sclerosis) patient assessment. Score this patient response on a 0-7 scale.

SCORING SCALE (0=best, 7=worst):
0: No impact on quality of life - Fully prepared/optimal management
1: 90% quality of life - Excellent management  
2: 75% quality of life - Good management
3: 65% quality of life - Moderate management
4: 50% quality of life - Some challenges
5: 35% quality of life - Significant challenges
6: 25% quality of life - Major difficulties
7: <10% quality of life - Extreme impact/no preparation

CONTEXT:
- PNM Domain: {pnm_domain}
- Question Context: {question_context.get('question', {}).get('text', 'N/A')}

PATIENT RESPONSE:
"{user_response}"

ANALYSIS REQUIREMENTS:
1. Assess preparedness, awareness, and coping level
2. Consider ALS-specific challenges and progression
3. Evaluate quality of life impact
4. Extract key insights about patient state

Respond in JSON format:
{{
    "score": <0-7 integer>,
    "confidence": <0-1 float>,
    "reasoning": "<detailed explanation>",
    "quality_of_life_impact": "<impact description>",
    "extracted_insights": ["<insight1>", "<insight2>"]
}}
"""
        
        # Add conversation history context if available
        if conversation_history:
            recent_context = conversation_history[-3:] if len(conversation_history) > 3 else conversation_history
            context_summary = "\n".join([f"- {msg.get('content', '')}" for msg in recent_context])
            prompt += f"\n\nRECENT CONVERSATION CONTEXT:\n{context_summary}"
        
        return prompt
    
    def _parse_ai_scoring_response(self, ai_response: str, original_response: str) -> AIScoreResult:
        """Parse AI response into structured score result"""
        try:
            # Try to extract JSON from AI response
            json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            if json_match:
                result_data = json.loads(json_match.group())
                
                score = int(result_data.get('score', 4))  # Default to moderate
                score = max(0, min(7, score))  # Ensure valid range
                
                confidence = float(result_data.get('confidence', 0.7))
                confidence = max(0.0, min(1.0, confidence))  # Ensure valid range
                
                return AIScoreResult(
                    score=float(score),
                    confidence=confidence,
                    reasoning=result_data.get('reasoning', 'AI analysis completed'),
                    quality_of_life_impact=self.score_mapping[score]['qol'],
                    extracted_insights=result_data.get('extracted_insights', [])
                )
            else:
                # Fallback parsing if no JSON found
                return self._extract_score_from_text(ai_response, original_response)
                
        except Exception as e:
            self.log.warning(f"Failed to parse AI scoring response: {e}")
            return self._fallback_rule_based_scoring(original_response, "general")
    
    def _extract_score_from_text(self, ai_response: str, original_response: str) -> AIScoreResult:
        """Extract score from unstructured AI text response"""
        # Look for numerical scores in text
        score_patterns = [
            r'score[:\s]*(\d)',
            r'rating[:\s]*(\d)',
            r'(\d)/7',
            r'level[:\s]*(\d)'
        ]
        
        extracted_score = 4  # Default moderate score
        for pattern in score_patterns:
            match = re.search(pattern, ai_response.lower())
            if match:
                extracted_score = int(match.group(1))
                break
        
        # Determine confidence based on response quality
        confidence = 0.6 if len(ai_response) > 100 else 0.4
        
        return AIScoreResult(
            score=float(max(0, min(7, extracted_score))),
            confidence=confidence,
            reasoning=ai_response[:200] + "..." if len(ai_response) > 200 else ai_response,
            quality_of_life_impact=self.score_mapping[extracted_score]['qol'],
            extracted_insights=[]
        )
    
    def _fallback_rule_based_scoring(self, user_response: str, pnm_domain: str) -> AIScoreResult:
        """Rule-based fallback when AI scoring fails"""
        response_lower = user_response.lower()
        
        # Positive indicators (lower scores)
        positive_keywords = [
            "prepared", "ready", "plan", "strategy", "team", "support",
            "managing well", "under control", "confident", "equipped"
        ]
        
        # Negative indicators (higher scores)  
        negative_keywords = [
            "not prepared", "no plan", "worried", "scared", "don't know",
            "struggling", "difficult", "overwhelming", "unprepared"
        ]
        
        # Scoring logic
        positive_count = sum(1 for keyword in positive_keywords if keyword in response_lower)
        negative_count = sum(1 for keyword in negative_keywords if keyword in response_lower)
        response_length = len(user_response)
        
        if positive_count >= 2 and negative_count == 0:
            score = 1  # Excellent
        elif positive_count > negative_count:
            score = 2  # Good
        elif negative_count > positive_count:
            score = 6  # Major difficulties
        elif response_length < 20:
            score = 5  # Minimal engagement suggests challenges
        else:
            score = 4  # Moderate default
        
        confidence = 0.5  # Lower confidence for rule-based
        
        return AIScoreResult(
            score=float(score),
            confidence=confidence,
            reasoning=f"Rule-based analysis: {positive_count} positive, {negative_count} negative indicators",
            quality_of_life_impact=self.score_mapping[score]['qol'],
            extracted_insights=[f"Response length: {response_length} characters"]
        )


class EnhancedPNMScorer(PNMScoringEngine):
    """
    Enhanced PNM scoring with missing value handling and AI integration
    """
    
    def __init__(self):
        super().__init__()
        self.ai_scorer = AIFreeTextScorer()
        self.log = logging.getLogger(__name__)
    
    def calculate_pnm_scores_with_missing_values(
        self, 
        responses: Dict[str, Any], 
        conversation_scores: List[PNMScore] = None
    ) -> Dict[str, Any]:
        """
        Calculate PNM scores handling missing values through intelligent averaging
        """
        try:
            # Group available scores by PNM domain
            domain_scores = {}
            total_responses = 0
            
            # Process existing conversation scores
            if conversation_scores:
                for score in conversation_scores:
                    domain = score.pnm_level
                    if domain not in domain_scores:
                        domain_scores[domain] = []
                    domain_scores[domain].append({
                        'total_score': score.total_score,
                        'max_score': score.max_score,
                        'percentage': score.percentage
                    })
                    total_responses += 1
            
            # Calculate averages and handle missing domains
            pnm_profile = {}
            overall_scores = []
            
            for pnm_level in self.pnm_hierarchy:
                if pnm_level in domain_scores:
                    # Calculate average for domains with data
                    scores = domain_scores[pnm_level]
                    avg_total = sum(s['total_score'] for s in scores) / len(scores)
                    avg_max = sum(s['max_score'] for s in scores) / len(scores)
                    avg_percentage = (avg_total / avg_max) * 100
                    
                    pnm_profile[pnm_level] = {
                        'score': avg_total,
                        'possible': avg_max,
                        'percentage': avg_percentage,
                        'level': self._categorize_awareness_level(avg_percentage),
                        'domains_assessed': len(scores),
                        'has_data': True
                    }
                    overall_scores.append(avg_total)
                else:
                    # Handle missing domains with intelligent estimation
                    estimated_score = self._estimate_missing_domain_score(
                        pnm_level, domain_scores, responses
                    )
                    
                    pnm_profile[pnm_level] = {
                        'score': estimated_score['total'],
                        'possible': 16.0,  # Standard max score
                        'percentage': estimated_score['percentage'],
                        'level': self._categorize_awareness_level(estimated_score['percentage']),
                        'domains_assessed': 0,
                        'has_data': False,
                        'estimation_method': estimated_score['method']
                    }
                    overall_scores.append(estimated_score['total'])
            
            # Calculate overall profile
            if overall_scores:
                overall_total = sum(overall_scores)
                overall_possible = len(overall_scores) * 16.0
                overall_percentage = (overall_total / overall_possible) * 100
                
                pnm_profile['overall'] = {
                    'score': overall_total,
                    'possible': overall_possible,
                    'percentage': overall_percentage,
                    'level': self._categorize_awareness_level(overall_percentage),
                    'domains_assessed': len([d for d in pnm_profile.values() if isinstance(d, dict) and d.get('has_data', False)]),
                    'estimated_domains': len([d for d in pnm_profile.values() if isinstance(d, dict) and not d.get('has_data', True)])
                }
            
            self.log.info(f"PNM scoring completed: {len(domain_scores)} domains with data, {total_responses} total responses")
            
            return pnm_profile
            
        except Exception as e:
            self.log.error(f"PNM scoring calculation failed: {e}")
            return {}
    
    def _estimate_missing_domain_score(
        self, 
        missing_domain: str, 
        available_scores: Dict[str, List], 
        responses: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Intelligently estimate score for missing PNM domain
        """
        if not available_scores:
            # No data available, use conservative middle estimate
            return {
                'total': 8.0,  # Middle of 0-16 range
                'percentage': 50.0,
                'method': 'conservative_default'
            }
        
        # Calculate average from available domains
        all_percentages = []
        for domain_scores in available_scores.values():
            domain_avg = sum(s['percentage'] for s in domain_scores) / len(domain_scores)
            all_percentages.append(domain_avg)
        
        if all_percentages:
            # Weight by domain hierarchy (basic needs often more impacted in ALS)
            domain_index = self.pnm_hierarchy.index(missing_domain) if missing_domain in self.pnm_hierarchy else 4
            hierarchy_weight = 1.0 + (domain_index * 0.1)  # Earlier domains slightly weighted higher
            
            estimated_percentage = (sum(all_percentages) / len(all_percentages)) * hierarchy_weight
            estimated_percentage = min(100.0, max(0.0, estimated_percentage))
            estimated_total = (estimated_percentage / 100.0) * 16.0
            
            return {
                'total': estimated_total,
                'percentage': estimated_percentage,
                'method': f'weighted_average_{len(available_scores)}_domains'
            }
        
        # Final fallback
        return {
            'total': 8.0,
            'percentage': 50.0,
            'method': 'fallback_estimate'
        }


class StageScorer:
    """
    Stage-based scoring system using simple averages
    """
    
    def __init__(self):
        self.log = logging.getLogger(__name__)
        
        # ALS progression stages
        self.stages = [
            "Early", "Moderate", "Advanced", "Late"
        ]
    
    def calculate_stage_scores(
        self, 
        pnm_scores: Dict[str, Any], 
        conversation_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Calculate stage-based scores using simple averaging
        """
        try:
            stage_profile = {}
            
            # Map PNM domains to stages based on impact patterns
            stage_mapping = self._map_pnm_to_stages(pnm_scores)
            
            # Calculate stage averages
            for stage in self.stages:
                if stage in stage_mapping:
                    domain_scores = stage_mapping[stage]
                    if domain_scores:
                        avg_percentage = sum(domain_scores) / len(domain_scores)
                        stage_profile[stage] = {
                            'percentage': avg_percentage,
                            'level': self._categorize_stage_level(avg_percentage),
                            'domains_count': len(domain_scores),
                            'impact_areas': self._identify_impact_areas(avg_percentage)
                        }
                    else:
                        stage_profile[stage] = {
                            'percentage': 50.0,  # Default moderate
                            'level': 'Moderate Impact',
                            'domains_count': 0,
                            'impact_areas': []
                        }
            
            # Overall stage assessment
            if stage_profile:
                overall_avg = sum(s['percentage'] for s in stage_profile.values()) / len(stage_profile)
                stage_profile['overall_stage_assessment'] = {
                    'average_percentage': overall_avg,
                    'primary_stage': self._determine_primary_stage(stage_profile),
                    'progression_indicators': self._analyze_progression(stage_profile)
                }
            
            self.log.info(f"Stage scoring completed for {len(stage_profile)} stages")
            
            return stage_profile
            
        except Exception as e:
            self.log.error(f"Stage scoring failed: {e}")
            return {}
    
    def _map_pnm_to_stages(self, pnm_scores: Dict[str, Any]) -> Dict[str, List[float]]:
        """Map PNM domain scores to ALS progression stages"""
        stage_mapping = {
            "Early": [],      # Cognitive, Aesthetic 
            "Moderate": [],   # Safety, Esteem
            "Advanced": [],   # Love & Belonging, Self-Actualisation
            "Late": []        # Physiological, Transcendence
        }
        
        # PNM to stage mapping based on typical ALS progression
        pnm_stage_map = {
            "Cognitive": "Early",
            "Aesthetic": "Early", 
            "Safety": "Moderate",
            "Esteem": "Moderate",
            "Love & Belonging": "Advanced",
            "Self-Actualisation": "Advanced",
            "Physiological": "Late",
            "Transcendence": "Late"
        }
        
        for pnm_domain, score_data in pnm_scores.items():
            if pnm_domain != 'overall' and isinstance(score_data, dict):
                percentage = score_data.get('percentage', 50.0)
                stage = pnm_stage_map.get(pnm_domain, "Moderate")
                stage_mapping[stage].append(percentage)
        
        return stage_mapping
    
    def _categorize_stage_level(self, percentage: float) -> str:
        """Categorize stage impact level"""
        if percentage >= 80:
            return "Minimal Impact"
        elif percentage >= 60:
            return "Mild Impact"
        elif percentage >= 40:
            return "Moderate Impact"
        elif percentage >= 20:
            return "Significant Impact"
        else:
            return "Severe Impact"
    
    def _identify_impact_areas(self, percentage: float) -> List[str]:
        """Identify key impact areas based on score"""
        areas = []
        if percentage < 60:
            areas.append("Daily Living")
        if percentage < 50:
            areas.append("Independence")
        if percentage < 40:
            areas.append("Communication")
        if percentage < 30:
            areas.append("Mobility")
        if percentage < 20:
            areas.append("Care Needs")
        return areas
    
    def _determine_primary_stage(self, stage_profile: Dict[str, Any]) -> str:
        """Determine primary ALS stage based on scores"""
        stage_scores = {
            stage: data['percentage'] 
            for stage, data in stage_profile.items() 
            if stage != 'overall_stage_assessment'
        }
        
        if not stage_scores:
            return "Moderate"
        
        # Find stage with lowest percentage (highest impact)
        primary_stage = min(stage_scores, key=stage_scores.get)
        return primary_stage
    
    def _analyze_progression(self, stage_profile: Dict[str, Any]) -> List[str]:
        """Analyze progression indicators"""
        indicators = []
        
        # Extract percentage scores for analysis
        scores = {
            stage: data['percentage'] 
            for stage, data in stage_profile.items() 
            if stage != 'overall_stage_assessment'
        }
        
        if "Late" in scores and scores["Late"] < 40:
            indicators.append("Advanced progression indicators present")
        if "Early" in scores and "Late" in scores:
            if scores["Late"] - scores["Early"] > 30:
                indicators.append("Significant progression from early to late stages")
        if all(score < 50 for score in scores.values()):
            indicators.append("Multi-stage impact identified")
        
        return indicators