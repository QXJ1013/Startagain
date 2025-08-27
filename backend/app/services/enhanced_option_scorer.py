# app/services/enhanced_option_scorer.py
"""
Enhanced option scoring with better contextual understanding and randomness handling.
Uses question-specific calibration and context-aware scoring.
"""

from typing import Dict, List, Optional, Any, Tuple
import re
import json
import hashlib
from dataclasses import dataclass
from app.services.option_scorer import OptionScorer

@dataclass
class EnhancedOptionScore:
    """Enhanced score with context awareness"""
    option_value: str
    option_label: str
    score_0_7: float
    confidence: float
    method: str
    rationale: str
    context_factors: Dict[str, Any]
    question_context: Optional[str] = None


class EnhancedOptionScorer:
    """
    Advanced option scoring that understands question context and handles randomness.
    Uses question-specific calibration instead of generic patterns.
    """
    
    def __init__(self):
        self.base_scorer = OptionScorer()  # Use base as fallback
        
        # Question-specific scoring calibration
        # Maps question patterns to scoring strategies
        self.question_calibrations = {
            'aac_device': {
                'question_pattern': r'AAC|communication device|speech device',
                'scoring_curve': 'expertise',  # Higher weight on independence
                'context_weight': 0.8,
                'option_mappings': {
                    'expert': (6.5, 7.0),
                    'confident': (5.5, 6.5),
                    'managing': (3.5, 4.5),
                    'struggling': (1.5, 2.5),
                    'unable': (0.0, 1.0)
                }
            },
            'breathing': {
                'question_pattern': r'breath|respiratory|oxygen|ventilat',
                'scoring_curve': 'safety_critical',  # More conservative scoring
                'context_weight': 0.9,
                'option_mappings': {
                    'no_issues': (6.0, 7.0),
                    'mild': (4.5, 5.5),
                    'moderate': (3.0, 4.0),
                    'severe': (1.0, 2.0),
                    'critical': (0.0, 0.5)
                }
            },
            'mobility': {
                'question_pattern': r'walk|mobil|movement|transfer|balance',
                'scoring_curve': 'functional',
                'context_weight': 0.7,
                'option_mappings': {
                    'independent': (6.5, 7.0),
                    'minimal_help': (5.0, 6.0),
                    'moderate_help': (3.0, 4.0),
                    'significant_help': (1.5, 2.5),
                    'dependent': (0.0, 1.0)
                }
            },
            'emotional': {
                'question_pattern': r'mood|emotion|depress|anxiety|cope',
                'scoring_curve': 'psychological',
                'context_weight': 0.6,
                'option_mappings': {
                    'excellent': (6.5, 7.0),
                    'good': (5.0, 6.0),
                    'fair': (3.5, 4.5),
                    'poor': (2.0, 3.0),
                    'very_poor': (0.0, 1.5)
                }
            }
        }
        
        # Context modifiers that affect scoring
        self.context_modifiers = {
            'uncertainty': {
                'patterns': [r'\bmight\b', r'\bmaybe\b', r'\bprobably\b', r'\bthink\b', r'\bguess\b'],
                'confidence_penalty': 0.2,
                'score_adjustment': -0.5
            },
            'qualification': {
                'patterns': [r'but', r'however', r'except', r'unless', r'depends'],
                'confidence_penalty': 0.15,
                'score_adjustment': -0.3
            },
            'emphasis': {
                'patterns': [r'\breally\b', r'\bvery\b', r'\bdefinitely\b', r'\babsolutely\b'],
                'confidence_boost': 0.1,
                'score_adjustment': 0.2
            },
            'temporal': {
                'patterns': [r'sometimes', r'usually', r'always', r'never', r'often'],
                'confidence_boost': 0.05,
                'score_adjustment': 0.0  # Already handled by frequency
            }
        }
        
        # Response noise filters
        self.noise_patterns = {
            'filler': r'\b(um|uh|er|well|you know|I mean)\b',
            'hedging': r'\b(sort of|kind of|like|basically)\b',
            'tangential': r'(by the way|anyway|also|oh and)',
        }
    
    def score_with_context(
        self,
        option_value: str,
        option_label: str,
        all_options: List[Dict[str, str]],
        question_text: Optional[str] = None,
        question_id: Optional[str] = None,
        user_response: Optional[str] = None
    ) -> EnhancedOptionScore:
        """
        Score with full context awareness.
        
        Args:
            option_value: Selected option value
            option_label: Display label of option
            all_options: All available options
            question_text: The actual question asked
            question_id: Question identifier
            user_response: Full user response (may differ from option_label)
        """
        
        # Determine question type and calibration
        calibration = self._get_question_calibration(question_text, question_id)
        
        # Clean and analyze response
        cleaned_response = self._clean_response(user_response or option_label)
        context_factors = self._analyze_context(cleaned_response)
        
        # Calculate base score using option position and calibration
        base_score = self._calculate_calibrated_score(
            option_value, option_label, all_options, calibration
        )
        
        # Apply context modifiers
        adjusted_score = self._apply_context_modifiers(
            base_score, context_factors, calibration
        )
        
        # Calculate confidence based on multiple factors
        confidence = self._calculate_confidence(
            context_factors, calibration, option_value, all_options
        )
        
        # Generate detailed rationale
        rationale = self._generate_rationale(
            option_label, adjusted_score, context_factors, calibration
        )
        
        return EnhancedOptionScore(
            option_value=option_value,
            option_label=option_label,
            score_0_7=round(adjusted_score, 2),
            confidence=round(confidence, 2),
            method=f"enhanced_{calibration.get('scoring_curve', 'adaptive')}",
            rationale=rationale,
            context_factors=context_factors,
            question_context=question_text
        )
    
    def _get_question_calibration(
        self, 
        question_text: Optional[str],
        question_id: Optional[str]
    ) -> Dict[str, Any]:
        """Get question-specific calibration settings"""
        
        if not question_text:
            return self._default_calibration()
        
        question_lower = question_text.lower()
        
        # Check for specific question types
        for cal_name, calibration in self.question_calibrations.items():
            if re.search(calibration['question_pattern'], question_lower):
                return {**calibration, 'type': cal_name}
        
        # Analyze question for dynamic calibration
        if 'how often' in question_lower or 'frequency' in question_lower:
            return self._frequency_calibration()
        elif 'how well' in question_lower or 'ability' in question_lower:
            return self._ability_calibration()
        elif 'how much' in question_lower or 'severity' in question_lower:
            return self._severity_calibration()
        
        return self._default_calibration()
    
    def _default_calibration(self) -> Dict[str, Any]:
        """Default calibration for unknown question types"""
        return {
            'scoring_curve': 'linear',
            'context_weight': 0.5,
            'type': 'default',
            'option_mappings': {}
        }
    
    def _frequency_calibration(self) -> Dict[str, Any]:
        """Calibration for frequency-based questions"""
        return {
            'scoring_curve': 'frequency',
            'context_weight': 0.6,
            'type': 'frequency',
            'option_mappings': {
                'always': (6.5, 7.0),
                'usually': (5.0, 6.0),
                'sometimes': (3.0, 4.0),
                'rarely': (1.5, 2.5),
                'never': (0.0, 0.5)
            }
        }
    
    def _ability_calibration(self) -> Dict[str, Any]:
        """Calibration for ability/proficiency questions"""
        return {
            'scoring_curve': 'expertise',
            'context_weight': 0.7,
            'type': 'ability',
            'option_mappings': {
                'expert': (6.5, 7.0),
                'proficient': (5.5, 6.5),
                'competent': (4.0, 5.0),
                'developing': (2.0, 3.5),
                'novice': (0.0, 1.5)
            }
        }
    
    def _severity_calibration(self) -> Dict[str, Any]:
        """Calibration for severity/impact questions"""
        return {
            'scoring_curve': 'inverse_severity',
            'context_weight': 0.8,
            'type': 'severity',
            'option_mappings': {
                'none': (6.5, 7.0),
                'minimal': (5.0, 6.0),
                'moderate': (3.0, 4.0),
                'significant': (1.5, 2.5),
                'severe': (0.0, 1.0)
            }
        }
    
    def _clean_response(self, response: str) -> str:
        """Remove noise while preserving meaning"""
        cleaned = response.lower()
        
        # Remove filler words
        for noise_type, pattern in self.noise_patterns.items():
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        # Normalize whitespace
        cleaned = ' '.join(cleaned.split())
        
        return cleaned.strip()
    
    def _analyze_context(self, response: str) -> Dict[str, Any]:
        """Analyze response context for scoring adjustments"""
        context = {
            'has_uncertainty': False,
            'has_qualification': False,
            'has_emphasis': False,
            'has_temporal': False,
            'response_length': len(response),
            'modifiers_found': []
        }
        
        for modifier_type, modifier_info in self.context_modifiers.items():
            for pattern in modifier_info['patterns']:
                if re.search(pattern, response, re.IGNORECASE):
                    context[f'has_{modifier_type}'] = True
                    context['modifiers_found'].append(modifier_type)
                    break
        
        # Analyze response complexity
        context['complexity'] = self._assess_complexity(response)
        
        return context
    
    def _assess_complexity(self, response: str) -> str:
        """Assess response complexity"""
        word_count = len(response.split())
        
        if word_count <= 3:
            return 'simple'
        elif word_count <= 10:
            return 'moderate'
        else:
            return 'complex'
    
    def _calculate_calibrated_score(
        self,
        option_value: str,
        option_label: str,
        all_options: List[Dict[str, str]],
        calibration: Dict[str, Any]
    ) -> float:
        """Calculate score using calibration settings"""
        
        # Check for direct mapping in calibration
        option_mappings = calibration.get('option_mappings', {})
        
        # Try to match option to calibrated ranges
        for mapping_key, score_range in option_mappings.items():
            if mapping_key in option_value.lower() or mapping_key in option_label.lower():
                # Return midpoint of calibrated range
                return (score_range[0] + score_range[1]) / 2
        
        # Fallback to position-based scoring with curve adjustment
        if all_options:
            position = self._find_option_position(option_value, option_label, all_options)
            if position >= 0:
                return self._apply_scoring_curve(
                    position, len(all_options), calibration['scoring_curve']
                )
        
        # Last resort: use base scorer
        base_result = self.base_scorer.score_option(option_value, option_label, all_options)
        return base_result.score_0_7
    
    def _find_option_position(
        self,
        value: str,
        label: str,
        options: List[Dict[str, str]]
    ) -> int:
        """Find position of option in list"""
        for i, opt in enumerate(options):
            if opt.get('value') == value or opt.get('label') == label:
                return i
        return -1
    
    def _apply_scoring_curve(
        self,
        position: int,
        total_options: int,
        curve_type: str
    ) -> float:
        """Apply different scoring curves based on question type"""
        
        if total_options <= 1:
            return 3.5  # Neutral for single option
        
        # Normalized position (0 to 1, where 0 is best)
        norm_pos = position / (total_options - 1)
        
        if curve_type == 'linear':
            # Simple linear mapping
            return 7.0 * (1 - norm_pos)
        
        elif curve_type == 'expertise':
            # Steeper curve for expertise questions (bigger gaps at top)
            if norm_pos < 0.2:
                return 7.0 - (norm_pos * 5)  # 7.0 to 6.0
            elif norm_pos < 0.4:
                return 6.0 - ((norm_pos - 0.2) * 10)  # 6.0 to 4.0
            elif norm_pos < 0.6:
                return 4.0 - ((norm_pos - 0.4) * 7.5)  # 4.0 to 2.5
            elif norm_pos < 0.8:
                return 2.5 - ((norm_pos - 0.6) * 6.25)  # 2.5 to 1.25
            else:
                return 1.25 - ((norm_pos - 0.8) * 6.25)  # 1.25 to 0.0
        
        elif curve_type == 'safety_critical':
            # Conservative scoring for safety-critical questions
            if norm_pos < 0.3:
                return 7.0 - (norm_pos * 3.33)  # 7.0 to 6.0
            elif norm_pos < 0.5:
                return 6.0 - ((norm_pos - 0.3) * 10)  # 6.0 to 4.0
            elif norm_pos < 0.7:
                return 4.0 - ((norm_pos - 0.5) * 10)  # 4.0 to 2.0
            else:
                return 2.0 - ((norm_pos - 0.7) * 6.67)  # 2.0 to 0.0
        
        elif curve_type == 'functional':
            # Balanced curve for functional assessments
            return 7.0 * (1 - norm_pos ** 1.5)
        
        elif curve_type == 'inverse_severity':
            # Inverted for severity (lower severity = higher score)
            return 7.0 * (1 - norm_pos ** 0.8)
        
        else:
            # Default linear
            return 7.0 * (1 - norm_pos)
    
    def _apply_context_modifiers(
        self,
        base_score: float,
        context_factors: Dict[str, Any],
        calibration: Dict[str, Any]
    ) -> float:
        """Apply contextual adjustments to base score"""
        
        adjusted = base_score
        context_weight = calibration.get('context_weight', 0.5)
        
        # Apply modifiers based on context
        total_adjustment = 0.0
        
        if context_factors['has_uncertainty']:
            modifier = self.context_modifiers['uncertainty']
            total_adjustment += modifier['score_adjustment']
        
        if context_factors['has_qualification']:
            modifier = self.context_modifiers['qualification']
            total_adjustment += modifier['score_adjustment']
        
        if context_factors['has_emphasis']:
            modifier = self.context_modifiers['emphasis']
            total_adjustment += modifier['score_adjustment']
        
        # Apply weighted adjustment
        adjusted += total_adjustment * context_weight
        
        # Consider response complexity
        if context_factors['complexity'] == 'complex':
            # Complex responses might indicate nuanced understanding
            adjusted += 0.2 * context_weight
        elif context_factors['complexity'] == 'simple':
            # Very simple responses might lack depth
            adjusted -= 0.1 * context_weight
        
        # Ensure within bounds
        return max(0.0, min(7.0, adjusted))
    
    def _calculate_confidence(
        self,
        context_factors: Dict[str, Any],
        calibration: Dict[str, Any],
        option_value: str,
        all_options: List[Dict[str, str]]
    ) -> float:
        """Calculate confidence score based on multiple factors"""
        
        base_confidence = 0.7  # Start with moderate confidence
        
        # Adjust based on calibration match
        if calibration['type'] != 'default':
            base_confidence += 0.1
        
        # Adjust based on context modifiers
        if context_factors['has_uncertainty']:
            base_confidence -= self.context_modifiers['uncertainty']['confidence_penalty']
        
        if context_factors['has_qualification']:
            base_confidence -= self.context_modifiers['qualification']['confidence_penalty']
        
        if context_factors['has_emphasis']:
            base_confidence += self.context_modifiers['emphasis']['confidence_boost']
        
        # Adjust based on option clarity
        if option_value and all_options:
            # Clear option selection increases confidence
            base_confidence += 0.1
        
        # Response complexity affects confidence
        if context_factors['complexity'] == 'complex':
            base_confidence -= 0.05
        elif context_factors['complexity'] == 'simple':
            base_confidence += 0.05
        
        return max(0.2, min(0.95, base_confidence))
    
    def _generate_rationale(
        self,
        option_label: str,
        score: float,
        context_factors: Dict[str, Any],
        calibration: Dict[str, Any]
    ) -> str:
        """Generate detailed scoring rationale"""
        
        parts = []
        
        # Base scoring method
        parts.append(f"Scored using {calibration['scoring_curve']} curve")
        
        # Context modifiers applied
        if context_factors['modifiers_found']:
            modifiers = ', '.join(context_factors['modifiers_found'])
            parts.append(f"with {modifiers} adjustments")
        
        # Score interpretation
        if score >= 6.0:
            parts.append("indicating high proficiency")
        elif score >= 4.0:
            parts.append("indicating moderate ability")
        elif score >= 2.0:
            parts.append("indicating some difficulty")
        else:
            parts.append("indicating significant challenges")
        
        # Confidence factors
        if context_factors['has_uncertainty']:
            parts.append("(uncertainty detected)")
        
        return '. '.join(parts) + '.'


def create_enhanced_scorer() -> EnhancedOptionScorer:
    """Factory function for enhanced scorer"""
    return EnhancedOptionScorer()