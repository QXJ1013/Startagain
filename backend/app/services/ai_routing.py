# app/services/ai_routing.py
"""
AI-powered routing service for intelligent question selection.
Simplified from bot.ipynb to work with current framework.
"""

import json
import os
import re
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass
from app.core.config_manager import config

log = logging.getLogger(__name__)

@dataclass
class RoutingResult:
    """Result from AI routing"""
    pnm: str
    term: str
    keywords: List[str]
    confidence: float
    method: str = "ai_keywords"

class AIRouter:
    """
    Simplified AI routing using keyword expansion and smart matching.
    This is a middle ground between full AI selection and simple keyword matching.
    """
    
    _symptom_keywords = None
    _dimension_terms = None
    
    @classmethod
    def _load_pnm_lexicon(cls) -> Dict:
        """Load PNM lexicon from JSON file"""
        if cls._symptom_keywords is None:
            try:
                lexicon_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'pnm_lexicon.json')
                with open(lexicon_path, 'r', encoding='utf-8') as f:
                    lexicon_data = json.load(f)
                
                # Transform lexicon data - PRESERVE ALL TERMS
                cls._symptom_keywords = {}
                
                for pnm, pnm_data in lexicon_data.items():
                    terms = pnm_data.get('terms', {})
                    for term_name, keywords in terms.items():
                        # Create unique key for each term
                        key = f"{pnm.lower()}_{term_name.lower().replace(' ', '_').replace('&', 'and')}"
                        
                        # Store ALL keywords for better matching
                        cls._symptom_keywords[key] = {
                            'keywords': keywords,  # All keywords together
                            'pnm': pnm,
                            'term': term_name,
                            'priority': len(keywords)  # More keywords = higher priority
                        }
                
                print(f"Loaded {len(cls._symptom_keywords)} routing entries from PNM lexicon")
                                
            except Exception as e:
                print(f"Error loading PNM lexicon: {e}")
                # Minimal fallback
                cls._symptom_keywords = {
                    'physiological_breathing': {
                        'keywords': ['breath', 'breathing', 'respiratory', 'dyspnea'],
                        'pnm': 'Physiological',
                        'term': 'Breathing',
                        'priority': 4
                    }
                }
                
        return cls._symptom_keywords
    
    @classmethod
    def _load_dimension_terms(cls) -> Dict:
        """Load dimension terms dynamically from question bank structure"""
        if cls._dimension_terms is None:
            try:
                # Try to load from question bank data structure
                from app.services.question_bank import QuestionBank
                qb = QuestionBank()
                
                # Extract unique PNM->Term mappings from actual questions
                dimension_terms = {}
                questions = getattr(qb, 'questions', [])
                
                for q in questions:
                    pnm = q.get('Primary_Need_Model', '')
                    term = q.get('Term', '')
                    if pnm and term and pnm not in dimension_terms:
                        dimension_terms[pnm] = term
                
                cls._dimension_terms = dimension_terms if dimension_terms else {
                    'Physiological': 'Breathing',
                    'Safety': 'Falls risk',
                    'Love & Belonging': 'Social support',
                    'Esteem': 'Independence',
                    'Self-Actualisation': 'Hobbies & goals',
                    'Cognitive': 'Memory & attention',
                    'Aesthetic': 'Personal appearance',
                    'Transcendence': 'Meaning & purpose'
                }
                
            except Exception:
                # Fallback dimension terms
                cls._dimension_terms = {
                    'Physiological': 'Breathing',
                    'Safety': 'Falls risk',
                    'Love & Belonging': 'Social support',
                    'Esteem': 'Independence',
                    'Self-Actualisation': 'Hobbies & goals',
                    'Cognitive': 'Memory & attention',
                    'Aesthetic': 'Personal appearance',
                    'Transcendence': 'Meaning & purpose'
                }
                
        return cls._dimension_terms
    
    @classmethod
    def get_symptom_keywords(cls) -> Dict:
        """Get symptom keywords (loads dynamically if needed)"""
        return cls._load_pnm_lexicon()
    
    @classmethod
    def get_dimension_terms(cls) -> Dict:
        """Get dimension terms (loads dynamically if needed)"""
        return cls._load_dimension_terms()
    
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
        symptom_keywords = cls.get_symptom_keywords()
        for symptom_area, mapping in symptom_keywords.items():
            # Get keywords from the new data structure
            route_keywords = mapping.get('keywords', [])
            # Check if any keywords match
            if any(kw in input_lower for kw in route_keywords):
                # Add some related keywords
                expanded.update(route_keywords[:3])  # Add top keywords
        
        return list(expanded)[:8]  # Limit to 8 keywords
    
    @classmethod
    def _calculate_semantic_similarity(cls, input_text: str, input_words: set, keywords: List[str]) -> float:
        """
        UPGRADED: TF-IDF based semantic similarity calculation with medical term awareness
        Replaces simple string matching with intelligent vector-based scoring
        """
        if not keywords:
            return 0.0
        
        # Build TF-IDF vectors for input and keywords
        input_vector = cls._build_tfidf_vector(input_text)
        keyword_vectors = [cls._build_tfidf_vector(kw) for kw in keywords]
        
        # Calculate cosine similarity for each keyword
        similarities = []
        for i, kw_vector in enumerate(keyword_vectors):
            cosine_sim = cls._cosine_similarity(input_vector, kw_vector)
            
            # Apply medical term boosting
            medical_boost = cls._calculate_medical_term_boost(input_text, keywords[i])
            boosted_similarity = min(1.0, cosine_sim + medical_boost)
            
            similarities.append(boosted_similarity)
        
        if not similarities:
            return 0.0
        
        # Multi-layer scoring: best match + coverage + consistency
        max_sim = max(similarities)
        avg_sim = sum(similarities) / len(similarities)
        coverage_score = len([s for s in similarities if s > 0.1]) / len(similarities)
        
        # Dynamic weighting based on match quality
        if max_sim > 0.8:  # High-confidence match
            final_score = 0.8 * max_sim + 0.15 * avg_sim + 0.05 * coverage_score
        elif max_sim > 0.5:  # Medium-confidence match  
            final_score = 0.6 * max_sim + 0.25 * avg_sim + 0.15 * coverage_score
        else:  # Low-confidence match
            final_score = 0.4 * max_sim + 0.35 * avg_sim + 0.25 * coverage_score
            
        return min(1.0, final_score)
    
    @classmethod
    def _build_tfidf_vector(cls, text: str) -> dict:
        """Build TF-IDF vector for medical text with domain-specific term weighting"""
        if not hasattr(cls, '_medical_idf_cache'):
            cls._medical_idf_cache = cls._build_medical_idf_cache()
        
        words = re.findall(r'\\b\\w{2,}\\b', text.lower())  # Extract words 2+ chars
        word_count = len(words)
        
        # Calculate TF (Term Frequency)
        tf_dict = {}
        for word in words:
            tf_dict[word] = tf_dict.get(word, 0) + 1
        
        # Convert to TF-IDF vector
        tfidf_vector = {}
        for word, tf in tf_dict.items():
            tf_normalized = tf / word_count  # Normalize by document length
            idf = cls._medical_idf_cache.get(word, 1.0)  # Default IDF for unknown words
            tfidf_vector[word] = tf_normalized * idf
        
        return tfidf_vector
    
    @classmethod 
    def _build_medical_idf_cache(cls) -> dict:
        """Build IDF cache with medical domain knowledge"""
        # Medical terms get higher IDF (more important)
        medical_terms = {
            # High importance medical terms
            'breathing': 3.0, 'breath': 3.0, 'respiratory': 3.0, 'dyspnea': 3.5,
            'swallow': 3.0, 'swallowing': 3.0, 'dysphagia': 3.5, 'aspiration': 3.5,
            'mobility': 3.0, 'walking': 2.8, 'gait': 3.2, 'wheelchair': 3.0,
            'speech': 3.0, 'voice': 2.8, 'dysarthria': 3.5, 'communication': 2.5,
            'weakness': 2.8, 'weak': 2.8, 'fatigue': 3.0, 'tired': 2.5,
            'independence': 2.8, 'independent': 2.8, 'autonomy': 3.2,
            'isolation': 3.0, 'isolated': 3.0, 'lonely': 2.5,
            
            # Medical equipment and aids  
            'cpap': 3.5, 'bipap': 3.5, 'ventilator': 3.5, 'peg': 3.5,
            'aids': 2.2, 'equipment': 2.0, 'device': 2.0, 'support': 2.0,
            
            # Symptom descriptors
            'severe': 2.5, 'mild': 2.2, 'moderate': 2.3, 'worse': 2.3,
            'difficulty': 2.5, 'trouble': 2.3, 'problem': 2.0, 'issue': 1.8
        }
        
        # Common words get lower IDF (less important)
        common_words = {
            'the': 0.1, 'and': 0.1, 'or': 0.2, 'but': 0.3, 'with': 0.4,
            'have': 0.5, 'has': 0.5, 'had': 0.5, 'get': 0.5, 'got': 0.5,
            'feel': 0.8, 'feels': 0.8, 'feeling': 0.8, 'about': 0.6,
            'what': 0.7, 'how': 0.8, 'when': 0.7, 'where': 0.6, 'why': 0.8,
            'can': 0.6, 'could': 0.6, 'would': 0.5, 'should': 0.7
        }
        
        # Combine dictionaries  
        idf_cache = {**common_words, **medical_terms}
        
        return idf_cache
    
    @classmethod
    def _cosine_similarity(cls, vec1: dict, vec2: dict) -> float:
        """Calculate cosine similarity between two TF-IDF vectors"""
        if not vec1 or not vec2:
            return 0.0
        
        # Calculate dot product
        dot_product = 0.0
        common_words = set(vec1.keys()) & set(vec2.keys())
        for word in common_words:
            dot_product += vec1[word] * vec2[word]
        
        # Calculate magnitudes
        mag1 = sum(val ** 2 for val in vec1.values()) ** 0.5
        mag2 = sum(val ** 2 for val in vec2.values()) ** 0.5
        
        if mag1 == 0 or mag2 == 0:
            return 0.0
        
        return dot_product / (mag1 * mag2)
    
    @classmethod
    def _calculate_medical_term_boost(cls, input_text: str, keyword: str) -> float:
        """
        ENHANCED: Advanced medical terminology matching with comprehensive synonym mapping
        Handles word variations, medical synonyms, and concept relationships
        """
        input_lower = input_text.lower()
        keyword_lower = keyword.lower()
        
        # Exact medical term match gets strong boost
        if keyword_lower in input_lower:
            return 0.3
        
        # Medical synonym dictionary with comprehensive mappings
        medical_synonyms = {
            # Hand/Grip related terms
            'hand': ['hands', 'finger', 'fingers', 'grip', 'gripping', 'grasp', 'grasping', 'dexterity', 'fine motor', 'manual'],
            'weakness': ['weak', 'weaker', 'weakening', 'weakened', 'frail', 'feeble', 'strength loss'],
            'grip': ['gripping', 'grasp', 'grasping', 'hold', 'holding', 'clutch', 'pinch'],
            
            # Mobility related terms  
            'mobility': ['walk', 'walking', 'move', 'moving', 'movement', 'ambulatory', 'locomotion', 'getting around', 'transfers', 'transfer'],
            'walking': ['walk', 'gait', 'step', 'stepping', 'ambulation', 'mobility', 'difficult', 'becoming difficult', 'getting harder', 'trouble walking'],
            'transfers': ['transfer', 'transfers', 'moving', 'getting up', 'sitting down', 'bed mobility', 'chair transfers'],
            'wheelchair': ['chair', 'mobility aid', 'mobility device'],
            'aids': ['aid', 'help', 'assist', 'assistance', 'support', 'equipment', 'device', 'devices'],
            
            # Breathing related terms
            'breathing': ['breath', 'respiratory', 'respiration', 'air', 'oxygen', 'lung', 'pulmonary'],
            'shortness': ['short', 'difficulty', 'trouble', 'problem', 'hard'],
            'breathless': ['breathlessness', 'winded', 'out of breath'],
            
            # Speech related terms
            'speech': ['speak', 'speaking', 'talk', 'talking', 'voice', 'vocal', 'communication', 'articulation'],
            'voice': ['vocal', 'speak', 'speaking', 'talk', 'talking', 'speech'],
            
            # Swallowing related terms  
            'swallow': ['swallowing', 'eat', 'eating', 'drink', 'drinking', 'food', 'liquid'],
            'choke': ['choking', 'cough', 'coughing', 'aspiration'],
            
            # Independence related terms
            'independence': ['independent', 'autonomous', 'autonomy', 'self', 'own', 'myself'],
            'independent': ['independence', 'autonomous', 'autonomy', 'self-reliant'],
            'maintain': ['keep', 'preserve', 'sustain', 'continue'],
            
            # General symptom terms
            'difficulty': ['trouble', 'problem', 'hard', 'challenging', 'struggle'],
            'trouble': ['difficulty', 'problem', 'issue', 'challenge', 'struggle'],
            'tired': ['fatigue', 'exhausted', 'weary', 'worn out', 'energy'],
            'fatigue': ['tired', 'exhausted', 'weary', 'low energy'],
            
            # Question words and information seeking
            'what': ['how', 'which', 'where'],
            'available': ['options', 'choices', 'possible', 'exist', 'there'],
            'help': ['assist', 'support', 'aid', 'beneficial', 'useful'],
            'about': ['regarding', 'concerning', 'related to'],
            'information': ['info', 'details', 'facts', 'knowledge'],
            'tell': ['explain', 'describe', 'share', 'inform'],
            'explain': ['tell', 'describe', 'clarify', 'elaborate']
        }
        
        boost = 0.0
        input_words = input_lower.split()
        keyword_words = keyword_lower.split()
        
        # Check for synonym matches with context prioritization
        domain_specific_boost = 0.0
        generic_boost = 0.0
        
        # Define domain-specific terms that should get priority
        domain_specific_terms = {
            'hand', 'hands', 'finger', 'fingers', 'grip', 'gripping', 'grasp', 'grasping',
            'walk', 'walking', 'mobility', 'gait', 'ambulatory', 'transfer', 'transfers',
            'breath', 'breathing', 'respiratory', 'lung', 'oxygen', 'air',
            'swallow', 'swallowing', 'eat', 'eating', 'choke', 'choking',
            'speech', 'speak', 'speaking', 'voice', 'talk', 'talking'
        }
        
        generic_terms = {'difficulty', 'trouble', 'problem', 'hard', 'challenging', 'struggle'}
        
        for input_word in input_words:
            for keyword_word in keyword_words:
                # Direct synonym lookup
                if keyword_word in medical_synonyms:
                    if input_word in medical_synonyms[keyword_word] or input_word == keyword_word:
                        # Prioritize domain-specific matches
                        if input_word in domain_specific_terms or keyword_word in domain_specific_terms:
                            domain_specific_boost += 0.35  # Higher boost for domain-specific
                        elif input_word in generic_terms or keyword_word in generic_terms:
                            generic_boost += 0.15  # Lower boost for generic terms
                        else:
                            boost += 0.25  # Normal boost for other terms
                        
                # Reverse synonym lookup with same prioritization
                if input_word in medical_synonyms:
                    if keyword_word in medical_synonyms[input_word] or keyword_word == input_word:
                        if input_word in domain_specific_terms or keyword_word in domain_specific_terms:
                            domain_specific_boost += 0.35
                        elif input_word in generic_terms or keyword_word in generic_terms:
                            generic_boost += 0.15
                        else:
                            boost += 0.25
                        
                # Word root similarity (for medical terms)
                if len(input_word) > 4 and len(keyword_word) > 4:
                    if (input_word[:4] == keyword_word[:4] or  # Same prefix
                        input_word[-3:] == keyword_word[-3:]):  # Same suffix
                        boost += 0.15
                        
                # PHASE 1.4: Advanced Levenshtein distance for spell correction
                levenshtein_boost = cls._calculate_levenshtein_boost(input_word, keyword_word)
                boost += levenshtein_boost
        
        # Medical concept relationships (broader categories)
        concept_relationships = {
            'hand function': ['hand', 'finger', 'grip', 'weak', 'strength', 'dexterity', 'motor'],
            'mobility': ['walk', 'move', 'mobility', 'aid', 'wheelchair', 'leg', 'ambulatory'],  
            'breathing': ['breath', 'air', 'respiratory', 'lung', 'oxygen', 'shortness'],
            'independence': ['independent', 'autonomous', 'self', 'maintain', 'own']
        }
        
        # Check concept relationships
        for concept, related_words in concept_relationships.items():
            if any(word in keyword_lower for word in related_words):
                if any(word in input_lower for word in related_words):
                    boost += 0.2
                    
        # Prioritize domain-specific boosts over generic ones
        final_boost = boost + domain_specific_boost
        if final_boost < 0.2 and generic_boost > 0:  # Only use generic boost if no domain-specific match
            final_boost += generic_boost * 0.5  # Reduced weight for generic matches
            
        return min(0.5, final_boost)  # Increased cap to 0.5 for better synonym matching
    
    @classmethod
    def _calculate_levenshtein_boost(cls, word1: str, word2: str) -> float:
        """
        PHASE 1.4: Advanced Levenshtein distance calculation for spell correction
        Provides intelligent fuzzy matching with medical term awareness
        """
        if len(word1) < 3 or len(word2) < 3:
            return 0.0
            
        # Calculate Levenshtein distance
        distance = cls._levenshtein_distance(word1, word2)
        max_len = max(len(word1), len(word2))
        
        # Don't match words that are too different
        if distance > max_len * 0.4:  # More than 40% different
            return 0.0
            
        # Calculate similarity ratio
        similarity_ratio = 1.0 - (distance / max_len)
        
        # Medical terms get higher tolerance for spelling errors
        medical_terms = {
            'dysphagia', 'dyspnea', 'dysarthria', 'aspiration', 'orthopnea',
            'sialorrhea', 'spasticity', 'fasciculation', 'atrophy', 'weakness',
            'fatigue', 'respiratory', 'pulmonary', 'swallowing', 'breathing',
            'mobility', 'dexterity', 'independence', 'autonomy'
        }
        
        is_medical_term = any(term in word1.lower() or term in word2.lower() 
                             for term in medical_terms)
        
        # Boost calculation based on similarity and context
        if similarity_ratio > 0.8:  # High similarity (1-2 char difference)
            boost = 0.2 if is_medical_term else 0.15
        elif similarity_ratio > 0.6:  # Medium similarity 
            boost = 0.15 if is_medical_term else 0.1
        elif similarity_ratio > 0.4:  # Lower similarity but still useful
            boost = 0.1 if is_medical_term else 0.05
        else:
            boost = 0.0
            
        # Additional boost for common medical misspellings
        common_misspellings = {
            ('breathe', 'breath'): 0.25,
            ('breath', 'breathe'): 0.25, 
            ('swallo', 'swallow'): 0.3,
            ('speach', 'speech'): 0.3,
            ('weaknes', 'weakness'): 0.25,
            ('fatige', 'fatigue'): 0.3,
            ('mobily', 'mobility'): 0.3,
            ('indepen', 'independent'): 0.2
        }
        
        for (misspell, correct), bonus in common_misspellings.items():
            if (word1.lower().startswith(misspell) and word2.lower().startswith(correct)) or \
               (word2.lower().startswith(misspell) and word1.lower().startswith(correct)):
                boost += bonus
                break
        
        return min(0.25, boost)  # Cap at 0.25 to prevent over-boosting
    
    @classmethod
    def _levenshtein_distance(cls, s1: str, s2: str) -> int:
        """
        Calculate Levenshtein distance between two strings
        Optimized implementation for spell checking
        """
        if len(s1) == 0:
            return len(s2)
        if len(s2) == 0:
            return len(s1)
            
        # Create matrix
        rows = len(s1) + 1
        cols = len(s2) + 1
        matrix = [[0] * cols for _ in range(rows)]
        
        # Initialize first row and column
        for i in range(rows):
            matrix[i][0] = i
        for j in range(cols):
            matrix[0][j] = j
            
        # Fill matrix
        for i in range(1, rows):
            for j in range(1, cols):
                cost = 0 if s1[i-1] == s2[j-1] else 1
                matrix[i][j] = min(
                    matrix[i-1][j] + 1,      # deletion
                    matrix[i][j-1] + 1,      # insertion
                    matrix[i-1][j-1] + cost  # substitution
                )
        
        return matrix[rows-1][cols-1]
    
    @classmethod
    def _check_semantic_relation(cls, input_text: str, keyword: str) -> bool:
        """Check for semantic relationships between input and keywords"""
        # Medical concept mappings
        concept_relations = {
            'breath': ['air', 'lung', 'oxygen', 'chest', 'suffocate'],
            'speech': ['voice', 'talk', 'communicate', 'speak', 'word'],
            'swallow': ['eat', 'drink', 'throat', 'choke', 'food'],
            'mobility': ['walk', 'move', 'leg', 'foot', 'balance'],
            'hand': ['grip', 'finger', 'arm', 'hold', 'grasp'],
            'fatigue': ['tired', 'energy', 'exhaust', 'weak', 'rest'],
            'pain': ['hurt', 'ache', 'sore', 'discomfort', 'suffer']
        }
        
        for concept, relations in concept_relations.items():
            if concept in keyword and any(rel in input_text for rel in relations):
                return True
        
        return False
    
    @classmethod
    def _calculate_context_boost(cls, input_text: str, route_data: Dict) -> float:
        """Calculate contextual boost based on medical context patterns"""
        boost = 0.0
        
        # Urgency indicators
        urgency_patterns = ['severe', 'worse', 'cannot', "can't", 'unable', 'emergency']
        if any(pattern in input_text for pattern in urgency_patterns):
            boost += 0.1
        
        # Time context
        time_patterns = ['night', 'morning', 'day', 'evening', 'lately', 'recently']
        if any(pattern in input_text for pattern in time_patterns):
            boost += 0.05
        
        # Emotional context for psychological PNMs
        emotion_patterns = ['worry', 'scared', 'anxious', 'depressed', 'isolated']
        if route_data['pnm'] in ['Love & Belonging', 'Transcendence'] and \
           any(pattern in input_text for pattern in emotion_patterns):
            boost += 0.15
        
        return boost
    
    @classmethod
    def _calculate_routing_confidence(cls, matches: List[Dict], best_score: float) -> float:
        """Calculate routing confidence based on score distribution"""
        if not matches or best_score <= 0:
            return 0.1
        
        # High confidence if best score is significantly higher than second best
        if len(matches) >= 2:
            second_score = matches[1]['score']
            score_gap = best_score - second_score
            
            if score_gap > 0.3:
                confidence = min(0.95, 0.6 + score_gap)
            elif score_gap > 0.15:
                confidence = min(0.85, 0.5 + score_gap)
            else:
                confidence = min(0.7, 0.4 + score_gap)
        else:
            # Single match - confidence based on absolute score
            confidence = min(0.9, best_score + 0.2)
        
        return max(0.1, confidence)
    
    @classmethod
    def _intelligent_fallback(cls, input_text: str, dimension_focus: Optional[str]) -> RoutingResult:
        """Intelligent fallback with context awareness instead of always defaulting to Physiological"""
        
        # Analyze input for PNM hints even without exact matches
        pnm_hints = {
            'Physiological': ['breath', 'speak', 'swallow', 'walk', 'move', 'tired', 'pain', 'weak'],
            'Safety': ['fall', 'danger', 'safe', 'risk', 'accident', 'afraid'],
            'Love & Belonging': ['family', 'friend', 'lonely', 'social', 'isolated', 'support'],
            'Esteem': ['work', 'job', 'independent', 'confidence', 'self', 'ability'],
            'Cognitive': ['understand', 'confus', 'remember', 'think', 'decision', 'plan'],
            'Transcendence': ['meaning', 'purpose', 'faith', 'spiritual', 'legacy']
        }
        
        best_pnm = 'Physiological'
        best_term = 'General health'
        confidence = 0.2
        
        if input_text:
            for pnm, hints in pnm_hints.items():
                hint_matches = sum(1 for hint in hints if hint in input_text.lower())
                if hint_matches > 0:
                    best_pnm = pnm
                    confidence = min(0.4, 0.2 + hint_matches * 0.1)
                    break
        
        # Use dimension focus if available
        if dimension_focus:
            best_pnm = dimension_focus
            confidence = 0.5
        
        dimension_terms = cls.get_dimension_terms()
        best_term = dimension_terms.get(best_pnm, 'General assessment')
        
        return RoutingResult(
            pnm=best_pnm,
            term=best_term,
            keywords=cls.expand_keywords_simple(input_text) if input_text else [],
            confidence=confidence,
            method="intelligent_fallback"
        )
    
    @classmethod
    def route_query(cls, user_input: str, dimension_focus: Optional[str] = None) -> RoutingResult:
        """
        COMPLETELY REWRITTEN: Intelligent semantic routing with high accuracy.
        No more simple string matching - uses advanced similarity and context.
        """
        
        # Direct dimension focus (highest priority)
        dimension_terms = cls.get_dimension_terms()
        if dimension_focus and dimension_focus in dimension_terms:
            return RoutingResult(
                pnm=dimension_focus,
                term=dimension_terms[dimension_focus],
                keywords=[dimension_focus.lower()],
                confidence=1.0,
                method="dimension_direct"
            )
        
        if not user_input or len(user_input.strip()) < 3:
            return cls._intelligent_fallback(user_input or "", dimension_focus)
        
        input_lower = user_input.lower().strip()
        input_words = set(re.findall(r'\b\w+\b', input_lower))
        
        # PHASE 2.1: RAG Semantic Enhancement
        rag_boost = cls._calculate_rag_semantic_boost(user_input)
        
        # Get all routing entries
        symptom_keywords = cls.get_symptom_keywords()
        
        # Calculate semantic similarity scores
        best_matches = []
        
        for route_key, route_data in symptom_keywords.items():
            keywords = route_data.get('keywords', route_data.get('primary', []))
            
            # Multi-level matching algorithm
            similarity_score = cls._calculate_semantic_similarity(
                input_lower, input_words, keywords
            )
            
            if similarity_score > 0:
                # Context boost based on medical patterns
                context_boost = cls._calculate_context_boost(input_lower, route_data)
                
                # Priority boost for more comprehensive terms
                priority_boost = min(0.1, route_data.get('priority', 0) / 100)
                
                # PHASE 2.1: Apply RAG semantic boost
                rag_domain_boost = rag_boost.get(route_data.get('term', ''), 0.0)
                
                final_score = similarity_score + context_boost + priority_boost + rag_domain_boost
                
                best_matches.append({
                    'route_key': route_key,
                    'score': final_score,
                    'similarity': similarity_score,
                    'route_data': route_data
                })
        
        # Sort by score and get best match
        best_matches.sort(key=lambda x: x['score'], reverse=True)
        
        if best_matches and best_matches[0]['score'] > 0.3:
            best = best_matches[0]
            route_data = best['route_data']
            
            # Calculate confidence based on score distribution
            confidence = cls._calculate_routing_confidence(best_matches, best['score'])
            
            return RoutingResult(
                pnm=route_data['pnm'],
                term=route_data['term'],
                keywords=cls.expand_keywords_simple(user_input),
                confidence=confidence,
                method="semantic_routing"
            )
        
        # Intelligent fallback with context awareness
        return cls._intelligent_fallback(input_lower, dimension_focus)
    
    @classmethod
    def find_matching_questions(cls, pnm: str, term: str, question_bank: List[Dict]) -> List[Dict]:
        """
        Find questions that match the given PNM and term.
        More flexible matching than exact string comparison.
        """
        matches = []
        
        # Load matching configuration
        matching_config = config.get('question_selection.selection.matching', {})
        min_word_overlap = matching_config.get('minimum_word_overlap', 2)
        fuzzy_match = matching_config.get('fuzzy_match_enabled', True)
        substring_match = matching_config.get('substring_match_enabled', True)
        pnm_word_match = matching_config.get('pnm_word_match', True)
        
        # Normalize search terms
        pnm_lower = pnm.lower() if pnm else ""
        term_lower = term.lower() if term else ""
        
        for question in question_bank:
            q_pnm = question.get('Primary_Need_Model', '').lower()
            q_term = question.get('Term', '').lower()
            
            # Check for PNM match (flexible)
            pnm_match = False
            if substring_match:
                pnm_match = pnm_lower in q_pnm or q_pnm in pnm_lower
            
            if not pnm_match and pnm_word_match and fuzzy_match:
                pnm_match = (pnm_lower and q_pnm and any(w in q_pnm for w in pnm_lower.split()))
            
            # Check for term match (very flexible)
            term_match = False
            if term_lower and q_term:
                # Direct substring match
                if substring_match:
                    term_match = (term_lower in q_term or q_term in term_lower)
                
                # Word overlap match
                if not term_match and fuzzy_match:
                    term_words = set(term_lower.split())
                    q_term_words = set(q_term.split())
                    overlap = term_words & q_term_words
                    term_match = len(overlap) >= min(min_word_overlap, len(term_words), len(q_term_words))
            
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
        
        # Load scoring weights from config
        weights = config.get('question_selection.selection.scoring.weights', {})
        exact_match_weight = weights.get('keyword_exact_match', 2.0)
        term_match_weight = weights.get('keyword_term_match', 1.0)
        overlap_factor = weights.get('word_overlap_factor', 0.5)
        
        # Get question text
        q_main = question.get('Prompt_Main', '').lower()
        q_term = question.get('Term', '').lower()
        
        # Check keyword matches in question
        for keyword in keywords:
            if keyword in q_main:
                score += exact_match_weight
            if keyword in q_term:
                score += term_match_weight
        
        # Check if question addresses the user's concern
        user_words = set(user_input.lower().split())
        q_words = set(q_main.split())
        overlap = len(user_words & q_words)
        score += overlap * overlap_factor
        
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
    
    @classmethod
    def _calculate_rag_semantic_boost(cls, user_input: str) -> Dict[str, float]:
        """
        PHASE 2.1: RAG Semantic Enhancement
        Use medical terminology index to enhance term matching accuracy
        """
        try:
            # Load medical terminology index
            terminology_path = os.path.join(
                os.path.dirname(__file__), 
                '../data/medical_terminology_index.json'
            )
            
            if not os.path.exists(terminology_path):
                return {}
                
            with open(terminology_path, 'r', encoding='utf-8') as f:
                terminology_data = json.load(f)
            
            medical_index = terminology_data.get('medical_terminology_index', {})
            input_lower = user_input.lower()
            domain_boosts = {}
            
            # Check mobility expressions
            for expr_data in medical_index.get('mobility_expressions', []):
                if cls._check_expression_match(input_lower, expr_data):
                    domain_boosts['Mobility'] = 0.35  # Increased from 0.25
                    # Apply competing category suppression
                    domain_boosts['Swallowing'] = -0.25  # Increased suppression from -0.15
            
            # Check hand function expressions  
            for expr_data in medical_index.get('hand_function_expressions', []):
                if cls._check_expression_match(input_lower, expr_data):
                    domain_boosts['Hand function'] = 0.35  # Increased from 0.25
                    domain_boosts['Swallowing'] = -0.25  # Increased suppression
            
            # Check breathing expressions
            for expr_data in medical_index.get('breathing_expressions', []):
                if cls._check_expression_match(input_lower, expr_data):
                    domain_boosts['Breathing'] = 0.35  # Increased from 0.25
            
            # Check swallowing expressions
            for expr_data in medical_index.get('swallowing_expressions', []):
                if cls._check_expression_match(input_lower, expr_data):
                    domain_boosts['Swallowing'] = 0.35  # Increased from 0.25
            
            # Check independence expressions
            for expr_data in medical_index.get('independence_expressions', []):
                if cls._check_expression_match(input_lower, expr_data):
                    domain_boosts['Independence'] = 0.35  # Increased from 0.25
                    
            # Check cognitive/emotional expressions
            for expr_data in medical_index.get('cognitive_emotional_expressions', []):
                if cls._check_expression_match(input_lower, expr_data):
                    domain = expr_data.get('domain', '')
                    if domain in ['Cognitive', 'Esteem', 'Love & Belonging']:
                        domain_boosts[domain] = 0.65  # Significantly increased boost
                        # Apply stronger competing suppression for conflicting domains
                        domain_boosts['Swallowing'] = -0.45
                        if domain == 'Cognitive':
                            domain_boosts['Esteem'] = -0.2  # Stronger suppression between related domains  
                        elif domain == 'Esteem':
                            domain_boosts['Cognitive'] = -0.2
                    
            # Check pain/comfort expressions  
            for expr_data in medical_index.get('pain_comfort_expressions', []):
                if cls._check_expression_match(input_lower, expr_data):
                    domain = expr_data.get('domain', '')
                    if domain in ['Pain', 'Comfort']:
                        domain_boosts[domain] = 0.35  # Increased from 0.25
                        domain_boosts['Swallowing'] = -0.25  # Increased suppression
                    
            return domain_boosts
            
        except Exception as e:
            log.warning(f"RAG semantic boost calculation failed: {e}")
            return {}
    
    @classmethod
    def _check_expression_match(cls, input_text: str, expr_data: Dict) -> bool:
        """
        Check if input matches a medical expression pattern
        """
        keywords = expr_data.get('keywords', [])
        expression = expr_data.get('expression', '').lower()
        
        # Direct expression match
        if expression in input_text:
            return True
            
        # Keyword overlap threshold (at least 60% of keywords present)
        if keywords:
            matches = sum(1 for kw in keywords if kw.lower() in input_text)
            overlap_ratio = matches / len(keywords)
            return overlap_ratio >= 0.6
            
        return False