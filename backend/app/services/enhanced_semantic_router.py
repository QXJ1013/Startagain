"""
Enhanced Semantic Router with intelligent fallback patterns.
Provides better semantic understanding even without AI services.
"""

import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

@dataclass
class SemanticPattern:
    """Semantic pattern for intelligent routing"""
    patterns: List[str]  # Regex patterns to match
    keywords: List[str]  # Keywords to expand from this pattern
    pnm: str  # Target PNM dimension
    term: str  # Target term
    confidence: float  # Base confidence for this pattern


class EnhancedSemanticRouter:
    """
    Intelligent semantic routing without requiring AI services.
    Uses comprehensive pattern matching and semantic understanding.
    """
    
    def __init__(self):
        # Define comprehensive semantic patterns for ALS/MND symptoms
        self.semantic_patterns = [
            # BREATHING patterns
            SemanticPattern(
                patterns=[
                    r'\b(breath|breathe|breathing|breathless|dyspnea|respiratory)\b',
                    r'\b(short.*breath|out.*breath|catch.*breath)\b',
                    r'\b(oxygen|O2|sats|saturation)\b',
                    r'\b(bipap|cpap|ventilat|NIV|non.?invasive)\b',
                    r'\b(lung|respiratory|pulmonary)\b',
                    r'\b(suffocating|gasping|air hunger)\b'
                ],
                keywords=['breathing', 'respiratory', 'oxygen', 'bipap', 'ventilation', 'dyspnea', 'lung'],
                pnm='Physiological',
                term='Breathing',
                confidence=0.9
            ),
            
            # EATING/SWALLOWING patterns
            SemanticPattern(
                patterns=[
                    r'\b(eat|eating|swallow|swallowing|dysphagia)\b',
                    r'\b(chok|choking|aspirat|aspiration)\b',
                    r'\b(feeding|tube|PEG|gastrostomy|nutrition)\b',
                    r'\b(meal|food|drink|liquid|thicken)\b',
                    r'\b(weight.*loss|malnutrition|calorie)\b',
                    r'\b(drool|saliva|secretions)\b'
                ],
                keywords=['eating', 'swallowing', 'nutrition', 'feeding', 'dysphagia', 'PEG', 'food'],
                pnm='Physiological',
                term='Nutrition',
                confidence=0.9
            ),
            
            # SPEECH/COMMUNICATION patterns
            SemanticPattern(
                patterns=[
                    r'\b(speak|speech|voice|talk|talking)\b',
                    r'\b(dysarthria|slur|articulation|pronunciation)\b',
                    r'\b(AAC|communication.*device|augmentative)\b',
                    r'\b(understood|understand.*me|hear.*me)\b',
                    r'\b(vocal|verbal|express|communicate)\b',
                    r'\b(whisper|weak.*voice|lose.*voice)\b'
                ],
                keywords=['speech', 'voice', 'communication', 'AAC', 'dysarthria', 'talking', 'verbal'],
                pnm='Esteem',
                term='Communication',
                confidence=0.85
            ),
            
            # MOBILITY patterns
            SemanticPattern(
                patterns=[
                    r'\b(walk|walking|ambulation|gait)\b',
                    r'\b(wheel.*chair|scooter|walker|cane)\b',
                    r'\b(fall|falling|balance|unsteady)\b',
                    r'\b(transfer|bed|chair|toilet|car)\b',
                    r'\b(leg.*weak|foot.*drop|trip|stumble)\b',
                    r'\b(stairs|climb|stand|sit)\b'
                ],
                keywords=['mobility', 'walking', 'wheelchair', 'transfer', 'balance', 'gait', 'movement'],
                pnm='Physiological',
                term='Mobility',
                confidence=0.85
            ),
            
            # HAND/ARM FUNCTION patterns
            SemanticPattern(
                patterns=[
                    r'\b(hand|hands|finger|grip|grasp)\b',
                    r'\b(arm|shoulder|elbow|wrist)\b',
                    r'\b(button|zip|dress|writing|typing)\b',
                    r'\b(fine.*motor|dexterity|coordination)\b',
                    r'\b(drop|dropping|hold|holding)\b',
                    r'\b(weak.*hand|weak.*arm|clumsy)\b'
                ],
                keywords=['hand', 'grip', 'dexterity', 'fine motor', 'arm', 'writing', 'coordination'],
                pnm='Physiological',
                term='Hand Function',
                confidence=0.85
            ),
            
            # FATIGUE patterns
            SemanticPattern(
                patterns=[
                    r'\b(fatigue|tired|exhausted|energy)\b',
                    r'\b(weak|weakness|strength)\b',
                    r'\b(rest|sleep|insomnia)\b',
                    r'\b(motivation|effort|stamina)\b'
                ],
                keywords=['fatigue', 'tired', 'energy', 'weakness', 'rest', 'stamina'],
                pnm='Physiological',
                term='Energy Management',
                confidence=0.8
            ),
            
            # EMOTIONAL/PSYCHOLOGICAL patterns
            SemanticPattern(
                patterns=[
                    r'\b(depress|anxiety|anxious|worry|worried)\b',
                    r'\b(mood|emotion|feeling|cope|coping)\b',
                    r'\b(stress|overwhelm|burden|struggle)\b',
                    r'\b(hope|hopeless|despair|fear)\b',
                    r'\b(mental.*health|psychological|therapy)\b'
                ],
                keywords=['emotional', 'depression', 'anxiety', 'coping', 'mental health', 'mood'],
                pnm='Self-Actualisation',
                term='Emotional Wellbeing',
                confidence=0.8
            ),
            
            # SOCIAL patterns
            SemanticPattern(
                patterns=[
                    r'\b(family|friend|social|relationship)\b',
                    r'\b(isolat|alone|lonely|connect)\b',
                    r'\b(support|help|care|carer|caregiver)\b',
                    r'\b(visit|meeting|gathering|activity)\b'
                ],
                keywords=['social', 'family', 'friends', 'support', 'relationships', 'connection'],
                pnm='Love & Belonging',
                term='Social Connections',
                confidence=0.8
            ),
            
            # SAFETY patterns
            SemanticPattern(
                patterns=[
                    r'\b(safe|safety|emergency|alarm|alert)\b',
                    r'\b(risk|danger|hazard|accident)\b',
                    r'\b(home.*modification|accessible|adapt)\b',
                    r'\b(emergency.*plan|backup|contingency)\b'
                ],
                keywords=['safety', 'emergency', 'risk', 'accessible', 'adaptation', 'plan'],
                pnm='Safety',
                term='Safety Planning',
                confidence=0.8
            )
        ]
        
        # Build optimized pattern index
        self._build_pattern_index()
    
    def _build_pattern_index(self):
        """Build optimized index for pattern matching"""
        self.compiled_patterns = []
        for sp in self.semantic_patterns:
            compiled = []
            for pattern in sp.patterns:
                try:
                    compiled.append(re.compile(pattern, re.IGNORECASE))
                except:
                    pass  # Skip invalid patterns
            self.compiled_patterns.append((sp, compiled))
    
    def route_semantic(self, text: str) -> Optional[Tuple[str, str, float, List[str]]]:
        """
        Route text based on semantic understanding.
        Returns: (pnm, term, confidence, keywords) or None
        """
        if not text:
            return None
        
        text_lower = text.lower()
        best_match = None
        best_score = 0
        best_keywords = []
        
        # Check each semantic pattern
        for semantic_pattern, compiled_patterns in self.compiled_patterns:
            matches = 0
            total_patterns = len(compiled_patterns)
            
            # Count how many patterns match
            for pattern in compiled_patterns:
                if pattern.search(text):
                    matches += 1
            
            if matches > 0:
                # Calculate match score
                match_ratio = matches / total_patterns
                score = semantic_pattern.confidence * (0.5 + 0.5 * match_ratio)
                
                # Boost score if multiple keywords present
                keyword_matches = sum(1 for kw in semantic_pattern.keywords if kw in text_lower)
                if keyword_matches > 1:
                    score *= (1 + 0.1 * keyword_matches)
                
                if score > best_score:
                    best_score = score
                    best_match = semantic_pattern
                    best_keywords = semantic_pattern.keywords[:5]  # Top 5 keywords
        
        if best_match and best_score > 0.4:
            return (
                best_match.pnm,
                best_match.term,
                min(best_score, 0.95),  # Cap confidence at 0.95
                best_keywords
            )
        
        return None
    
    def extract_keywords(self, text: str) -> List[str]:
        """
        Extract relevant keywords from text using semantic understanding.
        """
        if not text:
            return []
        
        keywords = set()
        text_lower = text.lower()
        
        # Check all patterns and collect keywords
        for semantic_pattern, compiled_patterns in self.compiled_patterns:
            for pattern in compiled_patterns:
                if pattern.search(text):
                    # Add relevant keywords from this pattern
                    keywords.update(semantic_pattern.keywords[:3])
                    break  # One match per semantic pattern is enough
        
        # Also extract explicit medical terms from text
        medical_terms = [
            'bipap', 'cpap', 'peg', 'aac', 'wheelchair', 'walker',
            'oxygen', 'ventilator', 'feeding tube', 'nebulizer'
        ]
        
        for term in medical_terms:
            if term in text_lower:
                keywords.add(term)
        
        # Extract symptom descriptors
        symptom_words = re.findall(r'\b(weak|difficult|hard|problem|issue|trouble|can\'t|cannot|unable)\b', text_lower)
        keywords.update(symptom_words[:2])  # Add top 2 symptom descriptors
        
        return list(keywords)[:10]  # Return max 10 keywords
    
    def confidence_from_match_quality(self, text: str, keywords: List[str]) -> float:
        """
        Calculate confidence score based on match quality.
        """
        if not text or not keywords:
            return 0.3
        
        text_lower = text.lower()
        matches = sum(1 for kw in keywords if kw in text_lower)
        
        # Base confidence from keyword matches
        confidence = 0.4 + (0.1 * min(matches, 5))
        
        # Boost for medical terminology
        medical_boost = 0
        medical_terms = ['bipap', 'cpap', 'peg', 'dysphagia', 'dysarthria', 'als', 'mnd']
        for term in medical_terms:
            if term in text_lower:
                medical_boost += 0.05
        
        confidence += min(medical_boost, 0.2)
        
        # Boost for clear symptom description
        if re.search(r'\b(i have|i am|my \w+ is|experiencing|suffering)\b', text_lower):
            confidence += 0.1
        
        return min(confidence, 0.95)