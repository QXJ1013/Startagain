# app/services/pnm_scoring.py
from __future__ import annotations
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import re

class AwarenessLevel(Enum):
    """Patient self-awareness levels for each PNM domain"""
    UNAWARE = 0          # No recognition of this need/impact
    VAGUE = 1            # Some vague awareness but unclear
    AWARE = 2            # Clear recognition of the issue
    UNDERSTANDING = 3    # Deep understanding of ALS impact
    MANAGING = 4         # Actively managing/addressing the need

@dataclass
class PNMScore:
    """Score for a specific PNM domain"""
    pnm_level: str
    domain: str
    awareness_score: int
    understanding_score: int
    coping_score: int
    action_score: int
    
    @property
    def total_score(self) -> int:
        return self.awareness_score + self.understanding_score + self.coping_score + self.action_score
    
    @property
    def max_score(self) -> int:
        return 16  # 4 dimensions × 4 max points each
    
    @property
    def percentage(self) -> float:
        return (self.total_score / self.max_score) * 100
    
    def to_dict(self) -> dict:
        """Convert PNMScore to dictionary for JSON serialization"""
        return {
            'pnm_level': self.pnm_level,
            'domain': self.domain,
            'awareness_score': self.awareness_score,
            'understanding_score': self.understanding_score,
            'coping_score': self.coping_score,
            'action_score': self.action_score,
            'total_score': self.total_score,
            'max_score': self.max_score,
            'percentage': self.percentage
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'PNMScore':
        """Create PNMScore from dictionary"""
        return cls(
            pnm_level=data['pnm_level'],
            domain=data['domain'],
            awareness_score=data['awareness_score'],
            understanding_score=data['understanding_score'],
            coping_score=data['coping_score'],
            action_score=data['action_score']
        )

class PNMScoringEngine:
    """
    Evaluates patient self-awareness and knowledge about ALS impact on their needs.
    
    The scoring focuses on:
    1. Awareness: Does patient recognize this need area is affected?
    2. Understanding: How well do they understand ALS impact?
    3. Coping: Do they know management strategies?
    4. Action: Are they taking steps to address it?
    """
    
    def __init__(self):
        self.pnm_hierarchy = [
            "Physiological",      # Basic survival needs
            "Safety",             # Security and protection
            "Love & Belonging",   # Social and emotional connection
            "Esteem",             # Self-worth and achievement
            "Self-Actualisation", # Personal growth and fulfillment
            "Cognitive",          # Knowledge and understanding
            "Aesthetic",          # Environmental quality
            "Transcendence"       # Spiritual meaning and purpose
        ]
        
        # Keywords indicating different awareness levels
        self.awareness_indicators = {
            AwarenessLevel.UNAWARE: [
                "not worried", "fine right now", "no problem", "not affected", 
                "no issues", "haven't thought", "not relevant", "no change",
                "don't know", "not aware"
            ],
            AwarenessLevel.VAGUE: [
                "might", "maybe", "not sure", "think so", "unclear", 
                "sometimes notice", "a little", "occasionally", "heard"
            ],
            AwarenessLevel.AWARE: [
                "i know", "aware that", "understand that", "realize",
                "recognize", "notice", "see changes", "experiencing"
            ],
            AwarenessLevel.UNDERSTANDING: [
                "als will", "disease progression", "muscle weakness causes",
                "understand how", "know this happens", "familiar with",
                "learned about", "als affects"
            ],
            AwarenessLevel.MANAGING: [
                "have discussed", "already planned", "working with team",
                "have strategies", "implemented", "using", "prepared for"
            ]
        }
    
    def score_response(self, user_response: str, pnm_level: str, domain: str) -> PNMScore:
        """Score a user response for PNM self-awareness"""
        response_lower = user_response.lower()
        
        # Score each dimension
        awareness = self._score_awareness(response_lower)
        understanding = self._score_understanding(response_lower)
        coping = self._score_coping(response_lower)
        action = self._score_action(response_lower)
        
        return PNMScore(
            pnm_level=pnm_level,
            domain=domain,
            awareness_score=awareness,
            understanding_score=understanding,
            coping_score=coping,
            action_score=action
        )
    
    def _score_awareness(self, response: str) -> int:
        """Score patient's awareness of the need area being affected"""
        scores = []
        
        # Enhanced scoring with more indicators
        # High awareness indicators
        high_awareness = ["i know", "i understand", "i realize", "aware that", "recognize", 
                         "experiencing", "notice", "see changes", "dealing with", "struggling with"]
        
        # Managing indicators
        managing = ["using", "working with", "have team", "therapist", "discussed with doctor", 
                   "already implemented", "have strategies", "prepared", "plan in place"]
        
        # Unaware indicators  
        unaware = ["not worried", "fine", "no problem", "haven't thought", "not affected", 
                  "don't know", "not sure", "no issues", "not relevant"]
        
        # Check for positive awareness
        if any(phrase in response for phrase in managing):
            scores.append(4)
        elif any(phrase in response for phrase in high_awareness):
            scores.append(3)
        elif len(response) > 50 and any(word in response for word in ["yes", "i", "my", "have"]):
            scores.append(2)  # Detailed positive response
        elif any(phrase in response for phrase in unaware):
            scores.append(0)
        else:
            scores.append(2)  # Default moderate awareness for engagement
        
        return max(scores) if scores else 2
    
    def _score_understanding(self, response: str) -> int:
        """Score patient's understanding of how ALS affects this need"""
        # Disease knowledge indicators
        disease_words = ["als", "mnd", "disease", "condition", "muscle weakness", 
                        "motor neuron", "neurological", "degenerative", "progression"]
        
        # Causal understanding
        causal_words = ["because", "due to", "caused by", "affects", "impacts", 
                       "weakens", "progressive", "gets worse", "will get"]
        
        # Practical understanding  
        practical_words = ["need help", "harder", "difficult", "challenging", 
                          "assistance", "adaptive", "modified", "backup"]
        
        score = 1  # Default base understanding
        
        if any(word in response for word in disease_words):
            score += 1
        if any(word in response for word in causal_words):
            score += 1  
        if any(word in response for word in practical_words):
            score += 1
            
        return min(score, 4)  # Cap at 4
    
    def _score_coping(self, response: str) -> int:
        """Score patient's knowledge of coping strategies"""
        # Equipment and tools
        equipment = ["equipment", "device", "machine", "bipap", "wheelchair", "walker", 
                    "computer", "tablet", "app", "communication device"]
        
        # Professional support
        professional = ["therapist", "doctor", "nurse", "team", "specialist", 
                       "respiratory", "physical", "occupational", "speech"]
        
        # Strategies and methods
        strategies = ["strategy", "technique", "method", "approach", "way", 
                     "routine", "schedule", "plan", "system"]
        
        score = 0
        if any(word in response for word in equipment):
            score += 2
        if any(word in response for word in professional):
            score += 1
        if any(word in response for word in strategies):
            score += 1
            
        return min(score, 4)  # Cap at 4
    
    def _score_action(self, response: str) -> int:
        """Score whether patient is taking active steps"""
        # Current active management
        active = ["using", "working with", "have", "regularly", "daily", "weekly", 
                 "established", "implemented", "currently", "already", "practice"]
        
        # Planning and future action
        planning = ["will", "plan to", "going to", "scheduled", "appointment", 
                   "considering", "looking into", "next step", "discussing"]
        
        # No action indicators
        no_action = ["haven't", "not", "don't", "no plan", "not considered", 
                    "not sure", "maybe", "might"]
        
        if any(word in response for word in active):
            return 4  # Active management
        elif any(word in response for word in planning):
            return 2  # Planning action
        elif any(word in response for word in no_action):
            return 0  # No action
        else:
            return 2  # Default moderate action for engagement
    
    def calculate_overall_pnm_profile(self, scores: List[PNMScore]) -> Dict[str, Any]:
        """Calculate overall PNM awareness profile"""
        if not scores:
            return {}
        
        profile = {}
        pnm_totals = {}
        
        # Group scores by PNM level
        for score in scores:
            level = score.pnm_level
            if level not in pnm_totals:
                pnm_totals[level] = []
            pnm_totals[level].append(score)
        
        # Calculate averages for each PNM level
        for level, level_scores in pnm_totals.items():
            total_score = sum(s.total_score for s in level_scores)
            total_possible = sum(s.max_score for s in level_scores)
            avg_percentage = (total_score / total_possible) * 100
            
            profile[level] = {
                'score': total_score,
                'possible': total_possible,
                'percentage': avg_percentage,
                'level': self._categorize_awareness_level(avg_percentage),
                'domains_assessed': len(level_scores)
            }
        
        # Calculate overall profile
        overall_score = sum(s.total_score for s in scores)
        overall_possible = sum(s.max_score for s in scores)
        overall_percentage = (overall_score / overall_possible) * 100
        
        profile['overall'] = {
            'score': overall_score,
            'possible': overall_possible,
            'percentage': overall_percentage,
            'level': self._categorize_awareness_level(overall_percentage),
            'domains_assessed': len(scores)
        }
        
        return profile
    
    def _categorize_awareness_level(self, percentage: float) -> str:
        """Categorize overall awareness level"""
        if percentage >= 80:
            return "Highly Aware & Managing"
        elif percentage >= 60:
            return "Good Awareness & Understanding"
        elif percentage >= 40:
            return "Moderate Awareness"
        elif percentage >= 20:
            return "Limited Awareness"
        else:
            return "Minimal Awareness"
    
    def generate_improvement_suggestions(self, profile: Dict[str, Any]) -> List[str]:
        """Generate suggestions for improving PNM awareness"""
        suggestions = []
        
        for level, data in profile.items():
            if level == 'overall':
                continue
                
            percentage = data['percentage']
            
            if percentage < 40:
                suggestions.append(f"Focus on building awareness of {level} needs and how ALS affects them")
            elif percentage < 60:
                suggestions.append(f"Develop deeper understanding of ALS impact on {level} needs")
            elif percentage < 80:
                suggestions.append(f"Learn and implement strategies for managing {level} needs")
        
        if profile.get('overall', {}).get('percentage', 0) < 60:
            suggestions.append("Consider working with ALS care team to develop comprehensive awareness plan")
        
        return suggestions


# Backward compatibility alias
PNMScorer = PNMScoringEngine