# app/services/option_scorer.py
"""
Flexible option-based scoring system for predefined answer choices.
Maps question options to scores using semantic understanding rather than hardcoded values.
"""

from typing import Dict, List, Optional, Any, Tuple
import re
from dataclasses import dataclass

@dataclass
class OptionScore:
    """Score derived from option selection"""
    option_value: str
    option_label: str
    score_0_7: float
    confidence: float
    method: str  # 'semantic_match' | 'pattern_analysis' | 'position_based'
    rationale: str


class OptionScorer:
    """
    Intelligent option scoring that avoids hardcoded mappings.
    Uses semantic analysis and pattern recognition to derive scores.
    """
    
    def __init__(self):
        # Semantic indicators for different proficiency levels
        # These are patterns, not fixed scores
        self.proficiency_indicators = {
            'expert_level': {
                'patterns': [
                    r'\b(expert|master|teach|coach|mentor|guide|proficient|fluent)\b',
                    r'\b(complete|full|total|perfect)\s+(understanding|control|mastery)\b',
                    r'\b(help|train|instruct|show)\s+others\b'
                ],
                'score_range': (6.0, 7.0),
                'confidence_boost': 0.2
            },
            'high_competence': {
                'patterns': [
                    r'\b(confident|capable|comfortable|good|strong|effective)\b',
                    r'\b(well|easily|successfully|independently)\b',
                    r'\b(managing|handling|doing)\s+well\b'
                ],
                'score_range': (5.0, 6.5),
                'confidence_boost': 0.15
            },
            'moderate_ability': {
                'patterns': [
                    r'\b(managing|coping|okay|adequate|fair|moderate)\b',
                    r'\b(some|partial|occasional)\s+(help|support|assistance)\b',
                    r'\b(getting by|making do|working on)\b'
                ],
                'score_range': (3.0, 5.0),
                'confidence_boost': 0.1
            },
            'struggling': {
                'patterns': [
                    r'\b(difficult|hard|challenging|struggle|trouble|problem)\b',
                    r'\b(need|require|depend)\s+(help|support|assistance)\b',
                    r'\b(limited|reduced|impaired|restricted)\b'
                ],
                'score_range': (1.5, 3.0),
                'confidence_boost': 0.1
            },
            'minimal_ability': {
                'patterns': [
                    r'\b(unable|cannot|impossible|can\'t|no longer)\b',
                    r'\b(severe|extreme|complete)\s+(difficulty|impairment)\b',
                    r'\b(fully|totally|completely)\s+dependent\b'
                ],
                'score_range': (0.0, 1.5),
                'confidence_boost': 0.15
            }
        }
        
        # Percentage-based patterns (flexible interpretation)
        self.percentage_patterns = [
            (r'\b100\s*%|hundred\s+percent\b', 7.0, 0.9),
            (r'\b90\s*%|ninety\s+percent\b', 6.3, 0.9),
            (r'\b75\s*%|three.quarters\b', 5.25, 0.9),
            (r'\b50\s*%|half|fifty\s+percent\b', 3.5, 0.85),
            (r'\b25\s*%|quarter|twenty.five\b', 1.75, 0.85),
            (r'\b10\s*%|ten\s+percent\b', 0.7, 0.9),
            (r'\b0\s*%|zero|none\b', 0.0, 0.9)
        ]
        
        # Frequency indicators
        self.frequency_patterns = [
            (r'\b(always|constantly|continuously)\b', 6.5, 7.0),
            (r'\b(usually|regularly|often|frequently)\b', 5.0, 6.0),
            (r'\b(sometimes|occasionally|periodically)\b', 3.0, 4.5),
            (r'\b(rarely|seldom|infrequently)\b', 1.5, 2.5),
            (r'\b(never|not at all)\b', 0.0, 1.0)
        ]
    
    def score_option(
        self, 
        option_value: str,
        option_label: str,
        all_options: Optional[List[Dict[str, str]]] = None
    ) -> OptionScore:
        """
        Score an option based on semantic analysis and relative position.
        
        Args:
            option_value: The value identifier of the selected option
            option_label: The display text of the selected option
            all_options: All available options for context (helps with relative scoring)
        
        Returns:
            OptionScore with derived score and confidence
        """
        # Clean inputs
        value_lower = option_value.lower().strip()
        label_lower = option_label.lower().strip()
        
        # Try multiple scoring methods and combine results
        semantic_score = self._semantic_analysis(value_lower, label_lower)
        pattern_score = self._pattern_matching(label_lower)
        
        # If we have all options, use relative positioning
        position_score = None
        if all_options:
            position_score = self._relative_position_scoring(
                option_value, option_label, all_options
            )
        
        # Combine scores intelligently
        final_score = self._combine_scores(
            semantic_score, pattern_score, position_score
        )
        
        return final_score
    
    def _semantic_analysis(self, value: str, label: str) -> Optional[Tuple[float, float, str]]:
        """
        Analyze semantic meaning of option text.
        Returns: (score, confidence, method) or None
        """
        combined_text = f"{value} {label}".lower()
        
        for level_name, level_config in self.proficiency_indicators.items():
            for pattern in level_config['patterns']:
                if re.search(pattern, combined_text, re.IGNORECASE):
                    # Calculate score within the range based on match strength
                    min_score, max_score = level_config['score_range']
                    
                    # Check multiple patterns for stronger confidence
                    matches = sum(1 for p in level_config['patterns'] 
                                if re.search(p, combined_text, re.IGNORECASE))
                    
                    if matches > 1:
                        score = max_score
                        confidence = 0.8 + level_config['confidence_boost']
                    else:
                        score = (min_score + max_score) / 2
                        confidence = 0.6 + level_config['confidence_boost']
                    
                    return (score, confidence, f'semantic_{level_name}')
        
        return None
    
    def _pattern_matching(self, label: str) -> Optional[Tuple[float, float, str]]:
        """
        Match against percentage and frequency patterns.
        Returns: (score, confidence, method) or None
        """
        # Check percentage patterns
        for pattern, score, confidence in self.percentage_patterns:
            if re.search(pattern, label, re.IGNORECASE):
                return (score, confidence, 'percentage_match')
        
        # Check frequency patterns
        for pattern, min_score, max_score in self.frequency_patterns:
            if re.search(pattern, label, re.IGNORECASE):
                score = (min_score + max_score) / 2
                return (score, 0.75, 'frequency_match')
        
        return None
    
    def _relative_position_scoring(
        self,
        selected_value: str,
        selected_label: str,
        all_options: List[Dict[str, str]]
    ) -> Tuple[float, float, str]:
        """
        Score based on relative position among all options.
        Assumes options are ordered from best to worst.
        """
        if not all_options:
            return None
        
        # Find position of selected option
        position = -1
        for i, opt in enumerate(all_options):
            if opt.get('value') == selected_value:
                position = i
                break
        
        if position == -1:
            # Option not found in list, check by label
            for i, opt in enumerate(all_options):
                if opt.get('label', '').lower() == selected_label.lower():
                    position = i
                    break
        
        if position == -1:
            return None
        
        # Calculate score based on position
        # This creates an even distribution across the 0-7 scale
        n_options = len(all_options)
        if n_options == 1:
            return (3.5, 0.3, 'single_option')
        
        # Linear interpolation from 7 to 0
        score = 7.0 * (1 - position / (n_options - 1))
        
        # Confidence based on number of options (more options = higher confidence)
        confidence = min(0.5 + (n_options - 2) * 0.1, 0.8)
        
        return (score, confidence, 'position_based')
    
    def _combine_scores(
        self,
        semantic: Optional[Tuple[float, float, str]],
        pattern: Optional[Tuple[float, float, str]],
        position: Optional[Tuple[float, float, str]]
    ) -> OptionScore:
        """
        Intelligently combine multiple scoring methods.
        """
        scores = []
        weights = []
        methods = []
        
        if semantic:
            scores.append(semantic[0])
            weights.append(semantic[1])
            methods.append(semantic[2])
        
        if pattern:
            scores.append(pattern[0])
            weights.append(pattern[1])
            methods.append(pattern[2])
        
        if position:
            scores.append(position[0])
            weights.append(position[1] * 0.7)  # Position scoring gets lower weight
            methods.append(position[2])
        
        if not scores:
            # No scoring method worked, return neutral score
            return OptionScore(
                option_value="unknown",
                option_label="unknown",
                score_0_7=3.5,
                confidence=0.2,
                method="fallback",
                rationale="Could not determine score from option"
            )
        
        # Weighted average
        total_weight = sum(weights)
        final_score = sum(s * w for s, w in zip(scores, weights)) / total_weight
        final_confidence = total_weight / len(scores)
        
        # Generate rationale
        rationale = f"Scored using {', '.join(methods)}. "
        if semantic:
            rationale += f"Semantic analysis suggests {semantic[2].replace('_', ' ')}. "
        if pattern:
            rationale += f"Pattern matching found {pattern[2].replace('_', ' ')}. "
        if position:
            rationale += f"Relative position indicates {position[2].replace('_', ' ')}."
        
        return OptionScore(
            option_value="",
            option_label="",
            score_0_7=round(final_score, 2),
            confidence=round(final_confidence, 2),
            method='+'.join(methods),
            rationale=rationale.strip()
        )
    
    def analyze_option_distribution(
        self,
        options: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Analyze the distribution and nature of available options.
        Helps AI understand the scale being used.
        """
        if not options:
            return {}
        
        analysis = {
            'n_options': len(options),
            'option_types': [],
            'scale_type': 'unknown',
            'suggested_scoring': []
        }
        
        # Analyze each option
        for i, opt in enumerate(options):
            label = opt.get('label', '').lower()
            value = opt.get('value', '').lower()
            
            # Determine option type
            if any(re.search(p, label) for p, _, _ in self.percentage_patterns):
                analysis['option_types'].append('percentage')
            elif any(re.search(p[0], label) for p in self.frequency_patterns):
                analysis['option_types'].append('frequency')
            elif any(re.search(p, label) for level in self.proficiency_indicators.values() 
                   for p in level['patterns']):
                analysis['option_types'].append('proficiency')
            else:
                analysis['option_types'].append('descriptive')
        
        # Determine scale type
        if 'percentage' in analysis['option_types']:
            analysis['scale_type'] = 'percentage_scale'
        elif 'frequency' in analysis['option_types']:
            analysis['scale_type'] = 'frequency_scale'
        elif 'proficiency' in analysis['option_types']:
            analysis['scale_type'] = 'proficiency_scale'
        else:
            analysis['scale_type'] = 'ordinal_scale'
        
        # Generate suggested scoring for each option
        for i, opt in enumerate(options):
            score_info = self.score_option(
                opt.get('value', ''),
                opt.get('label', ''),
                options
            )
            analysis['suggested_scoring'].append({
                'value': opt.get('value'),
                'label': opt.get('label'),
                'suggested_score': score_info.score_0_7,
                'confidence': score_info.confidence
            })
        
        return analysis


def score_from_option(
    option_value: str,
    option_label: str,
    all_options: Optional[List[Dict[str, str]]] = None
) -> Dict[str, Any]:
    """
    Convenience function for scoring a single option.
    """
    scorer = OptionScorer()
    result = scorer.score_option(option_value, option_label, all_options)
    
    return {
        'score_0_7': result.score_0_7,
        'confidence': result.confidence,
        'method': result.method,
        'rationale': result.rationale
    }