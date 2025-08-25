# app/services/ai_routing.py
"""
AI-powered routing service for intelligent question selection.
Simplified from bot.ipynb to work with current framework.
"""

import json
import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

@dataclass
class RoutingResult:
    """Result from AI routing"""
    pnm: str
    term: str
    keywords: List[str]
    confidence: float
    method: str = "ai_keywords"

class AIRoutingService:
    """
    Simplified AI routing using keyword expansion and smart matching.
    This is a middle ground between full AI selection and simple keyword matching.
    """
    
    # Comprehensive keyword mappings for each symptom area
    SYMPTOM_KEYWORDS = {
        'breathing': {
            'primary': ['breath', 'breathing', 'breathless', 'breathlessness', 'respiratory', 'lungs', 'air', 'oxygen'],
            'related': ['wheeze', 'gasp', 'pant', 'suffocate', 'dyspnea', 'inhale', 'exhale', 'ventilation'],
            'pnm': 'Physiological',
            'term': 'Breathing exercises'
        },
        'speaking': {
            'primary': ['speak', 'speech', 'speaking', 'talk', 'talking', 'voice', 'vocal', 'communicate', 'communication'],
            'related': ['articulate', 'pronunciation', 'clarity', 'dysarthria', 'verbal', 'express', 'conversation'],
            'pnm': 'Love & Belonging',
            'term': 'Communication with support network'
        },
        'swallowing': {
            'primary': ['swallow', 'swallowing', 'eating', 'drinking', 'choking', 'dysphagia', 'throat', 'food'],
            'related': ['nutrition', 'diet', 'meals', 'aspiration', 'feeding', 'liquids', 'solids', 'texture'],
            'pnm': 'Physiological',
            'term': 'Nutrition management'
        },
        'mobility': {
            'primary': ['walk', 'walking', 'mobility', 'movement', 'move', 'ambulation', 'gait', 'balance'],
            'related': ['fall', 'falling', 'stumble', 'trip', 'weakness', 'paralysis', 'wheelchair', 'transfer'],
            'pnm': 'Physiological',
            'term': 'Mobility and transfers'
        },
        'fatigue': {
            'primary': ['tired', 'fatigue', 'exhausted', 'exhaustion', 'energy', 'weakness', 'weak'],
            'related': ['rest', 'sleep', 'stamina', 'endurance', 'lethargy', 'drowsy', 'weary'],
            'pnm': 'Physiological',
            'term': 'Energy conservation'
        },
        'emotional': {
            'primary': ['sad', 'depressed', 'depression', 'anxiety', 'anxious', 'worry', 'scared', 'fear'],
            'related': ['mood', 'emotion', 'feeling', 'stress', 'cope', 'coping', 'mental', 'psychological'],
            'pnm': 'Esteem',
            'term': 'Emotional wellbeing'
        }
    }
    
    # Dimension-specific terms from actual question bank
    DIMENSION_TERMS = {
        'Physiological': 'Breathing exercises',
        'Safety': 'Equipment readiness and proficiency', 
        'Love & Belonging': 'Communication with support network',
        'Esteem': 'Home adaptations implementation',
        'Self-Actualisation': 'Gaming with adaptive devices',  # Using Aesthetic term as fallback
        'Cognitive': 'Emergency preparedness',
        'Aesthetic': 'Gaming with adaptive devices',
        'Transcendence': 'Communication with support network'  # Using Love & Belonging term as fallback
    }
    
    @classmethod
    def expand_keywords_simple(cls, user_input: str) -> List[str]:
        """
        Simplified keyword expansion without AI.
        Extracts relevant keywords from user input using pattern matching.
        """
        if not user_input:
            return []
            
        # Convert to lowercase for matching
        input_lower = user_input.lower()
        
        # Remove common stop words
        stop_words = {'i', 'me', 'my', 'am', 'is', 'are', 'was', 'were', 'have', 'has', 'had',
                     'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might',
                     'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                     'of', 'with', 'by', 'from', 'about', 'into', 'through', 'during',
                     'before', 'after', 'above', 'below', 'between', 'under', 'feel', 'feeling'}
        
        # Extract words
        words = re.findall(r'\b[a-z]+\b', input_lower)
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        
        # Add related keywords based on symptom areas
        expanded = set(keywords)
        for symptom_area, mapping in cls.SYMPTOM_KEYWORDS.items():
            # Check if any primary keywords match
            if any(kw in input_lower for kw in mapping['primary']):
                # Add some related keywords
                expanded.update(mapping['primary'][:3])  # Add top primary keywords
                expanded.update(mapping['related'][:2])  # Add some related keywords
        
        return list(expanded)[:8]  # Limit to 8 keywords like in bot.ipynb
    
    @classmethod
    def route_query(cls, user_input: str, dimension_focus: Optional[str] = None) -> RoutingResult:
        """
        Route user query to appropriate PNM dimension and term.
        Uses intelligent keyword matching without requiring AI API.
        """
        
        # If dimension focus is specified, use it directly
        if dimension_focus and dimension_focus in cls.DIMENSION_TERMS:
            return RoutingResult(
                pnm=dimension_focus,
                term=cls.DIMENSION_TERMS[dimension_focus],
                keywords=[dimension_focus.lower()],
                confidence=1.0,
                method="dimension_direct"
            )
        
        if not user_input:
            # Default fallback
            return RoutingResult(
                pnm='Physiological',
                term='General health',
                keywords=[],
                confidence=0.1,
                method="fallback"
            )
        
        input_lower = user_input.lower()
        
        # Extract keywords
        keywords = cls.expand_keywords_simple(user_input)
        
        # Score each symptom area based on keyword matches
        best_match = None
        best_score = 0
        
        for symptom_area, mapping in cls.SYMPTOM_KEYWORDS.items():
            score = 0
            
            # Check primary keywords (higher weight)
            for kw in mapping['primary']:
                if kw in input_lower:
                    score += 3
                elif any(kw in word for word in keywords):
                    score += 2
            
            # Check related keywords (lower weight)
            for kw in mapping['related']:
                if kw in input_lower:
                    score += 1
                elif any(kw in word for word in keywords):
                    score += 0.5
            
            if score > best_score:
                best_score = score
                best_match = symptom_area
        
        # Return the best match
        if best_match and best_score > 0:
            mapping = cls.SYMPTOM_KEYWORDS[best_match]
            confidence = min(1.0, best_score / 10.0)  # Normalize confidence
            
            return RoutingResult(
                pnm=mapping['pnm'],
                term=mapping['term'],
                keywords=keywords,
                confidence=confidence,
                method="keyword_match"
            )
        
        # Fallback to Physiological if no clear match
        return RoutingResult(
            pnm='Physiological',
            term='General health',
            keywords=keywords,
            confidence=0.3,
            method="fallback"
        )
    
    @classmethod
    def find_matching_questions(cls, pnm: str, term: str, question_bank: List[Dict]) -> List[Dict]:
        """
        Find questions that match the given PNM and term.
        More flexible matching than exact string comparison.
        """
        matches = []
        
        # Normalize search terms
        pnm_lower = pnm.lower() if pnm else ""
        term_lower = term.lower() if term else ""
        
        for question in question_bank:
            q_pnm = question.get('Primary_Need_Model', '').lower()
            q_term = question.get('Term', '').lower()
            
            # Check for PNM match (flexible)
            pnm_match = (
                pnm_lower in q_pnm or 
                q_pnm in pnm_lower or
                (pnm_lower and q_pnm and any(w in q_pnm for w in pnm_lower.split()))
            )
            
            # Check for term match (very flexible)
            term_match = False
            if term_lower and q_term:
                # Direct substring match
                term_match = (term_lower in q_term or q_term in term_lower)
                
                # Word overlap match
                if not term_match:
                    term_words = set(term_lower.split())
                    q_term_words = set(q_term.split())
                    overlap = term_words & q_term_words
                    term_match = len(overlap) >= min(2, len(term_words), len(q_term_words))
            
            # Add to matches if both match or if PNM matches strongly
            if pnm_match and term_match:
                matches.append(question)
            elif pnm_match and not term:  # If no term specified, PNM match is enough
                matches.append(question)
        
        return matches
    
    @classmethod
    def score_question_relevance(cls, question: Dict, keywords: List[str], user_input: str) -> float:
        """
        Score how relevant a question is to the user input and keywords.
        """
        score = 0.0
        
        # Get question text
        q_main = question.get('Prompt_Main', '').lower()
        q_term = question.get('Term', '').lower()
        
        # Check keyword matches in question
        for keyword in keywords:
            if keyword in q_main:
                score += 2.0
            if keyword in q_term:
                score += 1.0
        
        # Check if question addresses the user's concern
        user_words = set(user_input.lower().split())
        q_words = set(q_main.split())
        overlap = len(user_words & q_words)
        score += overlap * 0.5
        
        return score
    
    @classmethod
    def select_best_question(cls, 
                           questions: List[Dict], 
                           keywords: List[str], 
                           user_input: str,
                           asked_qids: List[str]) -> Optional[Dict]:
        """
        Select the best question from candidates based on relevance scoring.
        """
        if not questions:
            return None
        
        # Filter out already asked questions
        available = [q for q in questions if str(q.get('id')) not in asked_qids]
        
        if not available:
            return None
        
        # Score each question
        scored = []
        for q in available:
            score = cls.score_question_relevance(q, keywords, user_input)
            scored.append((score, q))
        
        # Sort by score and return the best
        scored.sort(key=lambda x: x[0], reverse=True)
        
        return scored[0][1] if scored else None