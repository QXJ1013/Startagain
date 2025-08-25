# app/services/ai_scorer.py
"""
AI-based PNM scoring system as a fallback/alternative to rule-based scoring.
Uses simple pattern matching and heuristics to ensure scoring always works.
"""

from typing import Dict, Any, List, Optional
from app.services.pnm_scoring import PNMScore
import re

class AIScorer:
    """
    Simple AI-like scorer that uses pattern matching and heuristics
    to ensure we always generate reasonable PNM scores.
    """
    
    def __init__(self):
        self.response_patterns = {
            'high_confidence': [
                r'\b(expert|teach|help others|share experience|confident|very good at)\b',
                r'\b(have mastered|completely understand|fully prepared)\b',
                r'\b(coach|mentor|guide|lead)\b'
            ],
            'moderate_positive': [
                r'\b(use|using|work with|have|regularly|daily|manage)\b',
                r'\b(understand|know|aware|realize|recognize)\b',
                r'\b(good|well|effective|successful|working)\b'
            ],
            'struggling': [
                r'\b(difficult|hard|challenging|struggle|problem|issue)\b',
                r'\b(can\'t|cannot|unable|don\'t know|not sure)\b',
                r'\b(confused|overwhelmed|lost|stuck)\b'
            ],
            'minimal': [
                r'\b(maybe|might|sometimes|occasionally|a little)\b',
                r'\b(not really|not much|barely|hardly)\b'
            ]
        }
        
        self.domain_keywords = {
            'Physiological': ['breath', 'bipap', 'oxygen', 'mobility', 'walk', 'move', 'eat', 'swallow'],
            'Safety': ['safe', 'emergency', 'plan', 'backup', 'accessible', 'fall', 'risk'],
            'Love & Belonging': ['family', 'friends', 'communicate', 'social', 'support', 'lonely'],
            'Esteem': ['confident', 'independent', 'capable', 'self-worth', 'dignity'],
            'Self-Actualisation': ['goals', 'dreams', 'purpose', 'meaning', 'fulfillment'],
            'Cognitive': ['understand', 'learn', 'knowledge', 'information', 'decision'],
            'Aesthetic': ['environment', 'comfortable', 'pleasant', 'beauty', 'quality'],
            'Transcendence': ['spiritual', 'faith', 'legacy', 'beyond', 'transcend']
        }
    
    def score_response(self, user_response: str, pnm_level: str, domain: str) -> PNMScore:
        """
        Generate a PNM score using AI-like pattern matching and heuristics.
        Always returns a reasonable score based on response analysis.
        """
        response_lower = user_response.lower()
        response_length = len(user_response)
        
        # Base scoring using pattern matching
        awareness_score = self._calculate_awareness_score(response_lower, response_length)
        understanding_score = self._calculate_understanding_score(response_lower, pnm_level)
        coping_score = self._calculate_coping_score(response_lower)
        action_score = self._calculate_action_score(response_lower)
        
        return PNMScore(
            pnm_level=pnm_level,
            domain=domain,
            awareness_score=awareness_score,
            understanding_score=understanding_score,
            coping_score=coping_score,
            action_score=action_score
        )
    
    def _calculate_awareness_score(self, response: str, length: int) -> int:
        """Calculate awareness score based on response patterns and length"""
        score = 1  # Base score
        
        # Length-based scoring (longer responses often indicate more awareness)
        if length > 100:
            score += 1
        if length > 200:
            score += 1
            
        # Pattern-based scoring
        for pattern in self.response_patterns['high_confidence']:
            if re.search(pattern, response, re.IGNORECASE):
                return 4  # Maximum awareness
                
        for pattern in self.response_patterns['moderate_positive']:
            if re.search(pattern, response, re.IGNORECASE):
                score = max(score, 3)
                
        for pattern in self.response_patterns['struggling']:
            if re.search(pattern, response, re.IGNORECASE):
                score = max(score, 2)  # At least aware of the struggle
                
        for pattern in self.response_patterns['minimal']:
            if re.search(pattern, response, re.IGNORECASE):
                score = max(score, 1)
        
        return min(score, 4)
    
    def _calculate_understanding_score(self, response: str, pnm_level: str) -> int:
        """Calculate understanding score based on domain-relevant keywords"""
        score = 1  # Base understanding
        
        # Check for domain-relevant keywords
        domain_words = self.domain_keywords.get(pnm_level, [])
        matches = sum(1 for word in domain_words if word in response)
        
        if matches >= 3:
            score = 4
        elif matches >= 2:
            score = 3
        elif matches >= 1:
            score = 2
            
        # Check for ALS/disease understanding
        disease_terms = ['als', 'mnd', 'disease', 'condition', 'motor neuron', 'progressive']
        if any(term in response for term in disease_terms):
            score = min(score + 1, 4)
            
        return score
    
    def _calculate_coping_score(self, response: str) -> int:
        """Calculate coping score based on mentions of tools, strategies, support"""
        score = 0
        
        # Equipment and tools
        equipment_words = ['equipment', 'device', 'machine', 'tool', 'aid', 'technology']
        if any(word in response for word in equipment_words):
            score += 2
            
        # Professional support
        support_words = ['therapist', 'doctor', 'nurse', 'team', 'specialist', 'caregiver']
        if any(word in response for word in support_words):
            score += 1
            
        # Strategies and methods
        strategy_words = ['strategy', 'method', 'technique', 'approach', 'plan', 'routine']
        if any(word in response for word in strategy_words):
            score += 1
            
        return min(score, 4)
    
    def _calculate_action_score(self, response: str) -> int:
        """Calculate action score based on current/planned actions"""
        # Current actions
        current_actions = ['using', 'doing', 'have', 'currently', 'regularly', 'already']
        if any(word in response for word in current_actions):
            return 4
            
        # Planned actions
        planned_actions = ['will', 'plan', 'going to', 'scheduled', 'considering']
        if any(word in response for word in planned_actions):
            return 2
            
        # Positive engagement (at least thinking about it)
        if len(response) > 50 and any(word in response for word in ['yes', 'i', 'my']):
            return 2
            
        return 1  # Minimal action for engagement

def create_ai_fallback_score(user_response: str, pnm_level: str, domain: str) -> PNMScore:
    """
    Create a fallback score using AI-like analysis.
    This ensures we always have a reasonable score.
    """
    scorer = AIScorer()
    return scorer.score_response(user_response, pnm_level, domain)