# app/services/ai_router.py
from __future__ import annotations

"""
AI-Enhanced Router with minimal AI intervention.
- Keyword expansion for better coverage
- Vector retrieval for semantic matching
- No AI decision-making for question selection (deterministic)
"""

import json
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from app.config import get_settings
from app.services.lexicon_router import LexiconRouter
from app.services.question_bank import QuestionBank
from app.services.session import SessionState
from app.vendors.ibm_cloud import RAGQueryClient, LLMClient
from app.utils.rerank import hybrid_fusion
from app.services.enhanced_semantic_router import EnhancedSemanticRouter


@dataclass
class RoutingResult:
    """Routing result with confidence and metadata"""
    pnm: str
    term: str
    confidence: float
    method: str  # 'exact' | 'semantic' | 'ai_enhanced'
    keywords: List[str] = None


class AIEnhancedRouter:
    """
    Enhanced router with keyword expansion and vector retrieval.
    Falls back gracefully to deterministic routing when AI unavailable.
    """
    
    def __init__(
        self,
        lexicon_router: LexiconRouter,
        question_bank: QuestionBank,
        enable_ai: bool = True
    ):
        self.cfg = get_settings()
        self.lexicon = lexicon_router
        self.qb = question_bank
        self.enable_ai = enable_ai and self._check_ai_available()
        
        # Initialize enhanced semantic router (always available)
        self.semantic_router = EnhancedSemanticRouter()
        
        # Initialize AI components if enabled
        if self.enable_ai:
            self.llm = LLMClient(
                model_id=getattr(self.cfg, "AI_MODEL_ID", "meta-llama/llama-3-3-70b-instruct"),
                params={"max_new_tokens": 500, "temperature": 0.1}
            )
            self.rag = RAGQueryClient()
        else:
            self.llm = None
            self.rag = None
            
    def _check_ai_available(self) -> bool:
        """Check if AI services are configured and available"""
        try:
            return bool(self.cfg.WATSONX_APIKEY and self.cfg.SPACE_ID)
        except:
            return False
    
    def route(
        self,
        user_text: str,
        session: SessionState,
        use_ai: Optional[bool] = None
    ) -> Optional[RoutingResult]:
        """
        Main routing method with AI-first approach.
        Priority: AI-enhanced semantic > exact match > basic semantic
        """
        if not user_text:
            return None
            
        # 1. FIRST try AI-enhanced routing for best semantic understanding
        if (use_ai if use_ai is not None else self.enable_ai):
            enhanced_result = self._try_ai_enhanced_routing(user_text, session)
            if enhanced_result and enhanced_result.confidence > 0.5:  # Lower threshold for AI
                return enhanced_result
                
        # 2. Fallback to exact lexicon match (for specific medical terms)
        exact_result = self._try_exact_match(user_text)
        if exact_result:
            # Reduce confidence for lexicon matches to prefer AI
            exact_result.confidence = min(exact_result.confidence * 0.8, 0.7)
            return exact_result
                
        # 3. Last resort: basic semantic search
        return self._try_semantic_fallback(user_text)
    
    def _try_exact_match(self, user_text: str) -> Optional[RoutingResult]:
        """Try exact lexicon matching (deterministic)"""
        hits = self.lexicon._ac_hits(user_text)
        if hits:
            term, pnm = hits[0]
            return RoutingResult(
                pnm=pnm,
                term=term,
                confidence=1.0,
                method='exact'
            )
        return None
    
    def _try_ai_enhanced_routing(
        self,
        user_text: str,
        session: SessionState
    ) -> Optional[RoutingResult]:
        """
        AI-enhanced routing with keyword expansion and vector retrieval.
        Falls back to enhanced semantic routing if AI unavailable.
        """
        # First try enhanced semantic routing (always available)
        semantic_result = self.semantic_router.route_semantic(user_text)
        if semantic_result:
            pnm, term, confidence, keywords = semantic_result
            # If we have high confidence semantic match, use it directly
            if confidence > 0.7:
                return RoutingResult(
                    pnm=pnm,
                    term=term,
                    confidence=confidence,
                    method='enhanced_semantic',
                    keywords=keywords
                )
        
        # If AI is available, try AI-enhanced routing
        if self.llm and self.llm.healthy():
            try:
                # 1. Expand keywords using AI
                keywords = self._expand_keywords(user_text, session)
                if not keywords:
                    keywords = self.semantic_router.extract_keywords(user_text)  # Use semantic fallback
                    
                # 2. Build enhanced query
                enhanced_query = self._build_search_query(user_text, keywords)
                
                # 3. Vector search in question bank
                question_candidates = self._search_questions(enhanced_query)
                
                # 4. Deterministic selection (no AI) - pick best scoring
                if question_candidates:
                    best = self._select_best_deterministic(
                        question_candidates,
                        user_text,
                        keywords
                    )
                    if best:
                        return RoutingResult(
                            pnm=best['pnm'],
                            term=best['term'],
                            confidence=best['score'],
                            method='ai_enhanced',
                            keywords=keywords
                        )
            except Exception:
                pass  # Fall through to semantic result
        
        # Return semantic result if available (even with lower confidence)
        if semantic_result:
            pnm, term, confidence, keywords = semantic_result
            return RoutingResult(
                pnm=pnm,
                term=term,
                confidence=confidence,
                method='enhanced_semantic',
                keywords=keywords
            )
            
        return None
    
    def _expand_keywords(
        self,
        user_text: str,
        session: SessionState
    ) -> List[str]:
        """
        Enhanced keyword expansion using LLM with ALS-specific domain knowledge.
        Returns comprehensive list of medical and symptom-related keywords.
        """
        if not self.llm or not self.llm.healthy():
            return self._fallback_keyword_expansion(user_text)
            
        # Get recent context for better expansion
        context = self._get_session_context(session, last_n=3)
        
        prompt = f"""You are an ALS/MND medical assistant. Extract and expand keywords from this patient statement.

Patient statement: "{user_text}"

Recent context: {json.dumps(context, ensure_ascii=False) if context else "None"}

Focus on these ALS symptom domains:
- Breathing: respiratory, breathless, dyspnea, orthopnea, ventilation
- Speech: voice, dysarthria, speaking, articulation, communication  
- Swallowing: dysphagia, choking, aspiration, eating, drinking
- Mobility: walking, weakness, gait, movement, transfer
- Hand function: grip, dexterity, fine motor, writing
- Other: fatigue, pain, cramps, saliva, nutrition

Extract ALL relevant keywords (both explicit and implied symptoms):
- Direct symptoms mentioned
- Related medical terms
- Body parts affected  
- Activities impacted
- Equipment/aids mentioned
- Timing/context clues

Output format: comma-separated list, 10-15 keywords maximum
Include both simple and medical terms when relevant.

Patient statement: "{user_text}"
Keywords:"""

        try:
            response = self.llm.generate_text(prompt)
            if response:
                # Enhanced cleaning and validation
                keywords = []
                # Split by comma or space and clean
                raw_words = response.replace('\n', ' ').replace('.', '').split(',')
                for word_group in raw_words:
                    # Handle multi-word terms and single words
                    for word in word_group.split():
                        word = word.strip().lower()
                        # Accept both single words and important multi-word medical terms
                        if word and (word.replace(' ', '').isalpha() or word in ['sob', 'peg', 'niv', 'cpap', 'bipap', 'aac']):
                            if len(word) > 1 and word not in keywords:
                                keywords.append(word)
                                if len(keywords) >= 15:
                                    break
                    if len(keywords) >= 15:
                        break
                return keywords
        except:
            pass
            
        return self._fallback_keyword_expansion(user_text)
    
    def _fallback_keyword_expansion(self, user_text: str) -> List[str]:
        """Fallback keyword expansion using rule-based approach"""
        keywords = []
        text_lower = user_text.lower()
        
        # Rule-based keyword mapping for common ALS symptoms
        keyword_maps = {
            'breathing': ['breathing', 'respiratory', 'breathless', 'dyspnea', 'ventilation', 'airway'],
            'breathless': ['breathless', 'breathing', 'respiratory', 'sob', 'dyspnea'],
            'voice': ['voice', 'speech', 'speaking', 'talking', 'communication', 'dysarthria'],
            'speak': ['speaking', 'speech', 'voice', 'talking', 'communication', 'articulation'],
            'talk': ['talking', 'speech', 'voice', 'speaking', 'communication', 'verbal'],
            'swallow': ['swallowing', 'dysphagia', 'eating', 'drinking', 'choking', 'aspiration'],
            'choke': ['choking', 'swallowing', 'dysphagia', 'aspiration', 'eating', 'drinking'],
            'eat': ['eating', 'swallowing', 'nutrition', 'food', 'chewing', 'appetite'],
            'weak': ['weakness', 'strength', 'muscle', 'mobility', 'fatigue', 'tired'],
            'tired': ['fatigue', 'tired', 'exhausted', 'energy', 'weakness', 'sleepy'],
            'walk': ['walking', 'mobility', 'gait', 'legs', 'movement', 'balance'],
            'hand': ['hands', 'grip', 'dexterity', 'fingers', 'motor', 'coordination']
        }
        
        # Extract base keywords from text
        base_words = text_lower.split()
        for word in base_words:
            word = word.strip('.,!?();:')
            if len(word) > 2:
                keywords.append(word)
                # Add related terms
                for key, related in keyword_maps.items():
                    if key in word or word in key:
                        keywords.extend(related[:3])  # Add top 3 related terms
        
        # Remove duplicates while preserving order
        seen = set()
        unique_keywords = []
        for kw in keywords:
            if kw not in seen and len(kw) > 1:
                seen.add(kw)
                unique_keywords.append(kw)
                if len(unique_keywords) >= 12:
                    break
                    
        return unique_keywords
            
        return []
    
    def _build_search_query(
        self,
        original_text: str,
        keywords: List[str]
    ) -> str:
        """Build optimized search query from original text and keywords"""
        # Combine original with keywords, avoid duplication
        parts = [original_text]
        
        # Add keywords not already in original text
        original_lower = original_text.lower()
        for kw in keywords:
            if kw.lower() not in original_lower:
                parts.append(kw)
                
        return ' '.join(parts[:10])  # limit length
    
    def _search_questions(self, query: str) -> List[Dict[str, Any]]:
        """
        Search question bank using vector retrieval.
        Returns list of candidates with scores.
        """
        if not self.rag or not self.rag.healthy():
            return []
            
        try:
            # Search in question vector index
            results = self.rag.search(
                query=query,
                top_k=10,
                index_kind='question'  # using question index
            )
            
            # Parse and structure results
            candidates = []
            for doc in results:
                meta = doc.get('metadata', {})
                if meta.get('pnm') and meta.get('term'):
                    candidates.append({
                        'pnm': meta['pnm'],
                        'term': meta['term'],
                        'score': float(doc.get('score', 0)),
                        'text': doc.get('text', ''),
                        'question_id': meta.get('id')
                    })
                    
            return candidates
            
        except:
            return []
    
    def _select_best_deterministic(
        self,
        candidates: List[Dict[str, Any]],
        user_text: str,
        keywords: List[str]
    ) -> Optional[Dict[str, Any]]:
        """
        Deterministic selection of best candidate.
        No AI involvement - pure scoring based on relevance.
        """
        if not candidates:
            return None
            
        # Score each candidate
        scored = []
        user_words = set(user_text.lower().split())
        keyword_set = set(k.lower() for k in keywords)
        
        for cand in candidates:
            # Base score from vector search
            score = cand['score']
            
            # Boost if term appears in user text
            term_lower = cand['term'].lower()
            if term_lower in user_text.lower():
                score += 0.2
                
            # Boost for keyword matches
            cand_text = (cand.get('text', '') + ' ' + cand['term']).lower()
            matched_keywords = sum(1 for kw in keyword_set if kw in cand_text)
            score += matched_keywords * 0.1
            
            # Penalize if already asked (would need session history)
            # This would require passing asked_qids
            
            scored.append({
                **cand,
                'final_score': min(score, 1.0)
            })
            
        # Sort by score and return best
        scored.sort(key=lambda x: x['final_score'], reverse=True)
        
        # Only return if confidence is reasonable
        if scored[0]['final_score'] > 0.5:
            return {
                'pnm': scored[0]['pnm'],
                'term': scored[0]['term'],
                'score': scored[0]['final_score'],
                'question_id': scored[0].get('question_id')
            }
            
        return None
    
    def _try_semantic_fallback(self, user_text: str) -> Optional[RoutingResult]:
        """Enhanced semantic search fallback with improved question matching"""
        if not getattr(self.cfg, "ENABLE_SEMANTIC_BACKOFF", False):
            return None
            
        # First try lexicon router's built-in semantic search
        fallback_keywords = self._fallback_keyword_expansion(user_text)
        hits = self.lexicon.locate(user_text, keyword_pool=fallback_keywords)
        
        if hits:
            term, pnm = hits[0]
            # Validate match strength
            confidence = self._calculate_semantic_confidence(user_text, term, pnm)
            if confidence > 0.5:
                return RoutingResult(
                    pnm=pnm,
                    term=term,
                    confidence=confidence,
                    method='semantic'
                )
        
        # Enhanced fallback with question bank search
        if self.rag and self.rag.healthy():
            try:
                # Multi-query semantic search for better coverage
                queries = [
                    user_text,
                    self._extract_symptom_keywords(user_text),
                    self._build_medical_query(user_text)
                ]
                
                all_candidates = []
                for query in queries:
                    if not query.strip():
                        continue
                        
                    # Search in question bank using vector similarity
                    question_docs = self.rag.search(query, top_k=8, index_kind="question")
                    for doc in question_docs:
                        meta = doc.get("metadata", {})
                        if meta.get("pnm") and meta.get("term"):
                            score = doc.get("score", 0.0) or 0.0
                            # Boost score if text contains strong symptom indicators
                            if self._has_strong_symptom_indicators(user_text, meta.get("term", "")):
                                score += 0.3
                            
                            all_candidates.append({
                                "pnm": meta["pnm"],
                                "term": meta["term"], 
                                "score": score,
                                "text": doc.get("text", ""),
                                "query": query
                            })
                
                # Select best candidate with confidence threshold
                if all_candidates:
                    # Sort by score and select best
                    all_candidates.sort(key=lambda x: x["score"], reverse=True)
                    best = all_candidates[0]
                    
                    # Apply confidence threshold
                    confidence = min(best["score"], 0.8)  # Cap at 0.8 for semantic fallback
                    if confidence > 0.4:  # Lower threshold for fallback
                        return RoutingResult(
                            pnm=best["pnm"],
                            term=best["term"],
                            confidence=confidence,
                            method="semantic_fallback"
                        )
            except Exception:
                pass
                
        return None
    
    def _calculate_semantic_confidence(self, user_text: str, term: str, pnm: str) -> float:
        """Calculate confidence score for semantic match"""
        text_lower = user_text.lower()
        term_lower = term.lower()
        
        base_confidence = 0.6
        
        # Boost if term appears in text
        if term_lower in text_lower or any(word in text_lower for word in term_lower.split()):
            base_confidence += 0.2
            
        # Boost for strong symptom indicators
        if self._has_strong_symptom_indicators(user_text, term):
            base_confidence += 0.1
            
        return min(base_confidence, 0.8)
    
    def _extract_symptom_keywords(self, text: str) -> str:
        """Extract key symptom-related words from text"""
        text_lower = text.lower()
        symptom_words = []
        
        # Common ALS symptom keywords
        symptom_patterns = [
            'breath', 'breathing', 'breathless', 'respiratory',
            'voice', 'speak', 'speech', 'talk', 'talking', 
            'swallow', 'choke', 'choking', 'eating', 'drinking',
            'weak', 'weakness', 'tired', 'fatigue',
            'walk', 'walking', 'mobility', 'movement',
            'hand', 'grip', 'finger', 'writing'
        ]
        
        for word in text_lower.split():
            word = word.strip('.,!?();:')
            if any(pattern in word for pattern in symptom_patterns):
                symptom_words.append(word)
        
        return ' '.join(symptom_words[:5])  # Top 5 symptom words
    
    def _build_medical_query(self, text: str) -> str:
        """Build medical-focused query from user text"""
        text_lower = text.lower()
        
        # Map common phrases to medical terms
        medical_mappings = {
            'trouble breathing': 'dyspnea respiratory breathing',
            'short of breath': 'dyspnea breathlessness respiratory', 
            'voice weak': 'dysarthria speech voice weakness',
            'trouble talking': 'dysarthria speech communication',
            'choke when': 'dysphagia swallowing aspiration',
            'trouble swallowing': 'dysphagia swallowing eating',
            'difficulty eating': 'dysphagia nutrition swallowing'
        }
        
        query_parts = []
        for phrase, medical_terms in medical_mappings.items():
            if phrase in text_lower:
                query_parts.append(medical_terms)
        
        if not query_parts:
            # Extract key words and add medical context
            words = text_lower.split()
            key_words = [w for w in words if len(w) > 3 and w.isalpha()][:3]
            query_parts.append(' '.join(key_words))
        
        return ' '.join(query_parts)
    
    def _has_strong_symptom_indicators(self, user_text: str, term: str) -> bool:
        """Check if user text has strong indicators for the given term"""
        text_lower = user_text.lower()
        term_lower = term.lower()
        
        strong_indicators = {
            'breathing': ['breath', 'respiratory', 'breathless', 'dyspnea', 'orthopnea'],
            'speech': ['voice', 'speak', 'talk', 'dysarthria', 'articulation'],
            'swallowing': ['swallow', 'choke', 'dysphagia', 'eating', 'drinking'],
            'mobility': ['walk', 'movement', 'gait', 'mobility', 'transfer'],
            'hand function': ['hand', 'grip', 'finger', 'dexterity', 'motor']
        }
        
        indicators = strong_indicators.get(term_lower, [])
        return any(indicator in text_lower for indicator in indicators)
    
    def _get_session_context(
        self,
        session: SessionState,
        last_n: int = 3
    ) -> List[Dict[str, str]]:
        """Get recent Q&A context from session for better keyword expansion"""
        context = []
        
        # Add current PNM/term if exists
        if session.current_pnm and session.current_term:
            context.append({
                'type': 'current_focus',
                'pnm': session.current_pnm,
                'term': session.current_term
            })
            
        # Add recently asked questions
        if session.asked_qids:
            recent_qids = session.asked_qids[-last_n:]
            for qid in recent_qids:
                # Extract main question ID (remove followup suffix)
                main_qid = qid.split('#')[0] if '#' in qid else qid
                context.append({
                    'type': 'recent_question',
                    'qid': main_qid
                })
                
        return context
    
    def get_expanded_keywords(
        self,
        user_text: str,
        session: SessionState
    ) -> List[str]:
        """
        Public method to just get expanded keywords without routing.
        Useful for debugging or display in UI.
        """
        if self.enable_ai:
            return self._expand_keywords(user_text, session)
        return []


def create_ai_router(
    lexicon_router: LexiconRouter,
    question_bank: QuestionBank,
    force_enable: bool = False
) -> AIEnhancedRouter:
    """
    Factory function to create AI router with proper configuration.
    """
    cfg = get_settings()
    enable_ai = force_enable or getattr(cfg, 'ENABLE_AI_ENHANCEMENT', False)
    
    return AIEnhancedRouter(
        lexicon_router=lexicon_router,
        question_bank=question_bank,
        enable_ai=enable_ai
    )