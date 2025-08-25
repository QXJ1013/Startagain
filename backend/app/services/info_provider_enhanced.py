# app/services/info_provider_enhanced.py
from __future__ import annotations

"""
Enhanced Information Provider with intelligent RAG.
- Context-aware retrieval from knowledge base
- Smart content extraction and summarization
- Personalized card generation based on session state
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import json

from app.config import get_settings
from app.vendors.ibm_cloud import RAGQueryClient, LLMClient
from app.vendors.bm25 import BM25Client
from app.utils.rerank import hybrid_fusion
from app.utils.text import normalize_text, split_sentences, truncate_words


@dataclass
class InfoContext:
    """Context for information retrieval"""
    current_pnm: str
    current_term: str
    last_answer: str
    question_history: List[str]
    severity_indicators: List[str]
    
    
class EnhancedInfoProvider:
    """
    Intelligent information card provider with RAG.
    - Retrieves from knowledge base with context awareness
    - Generates personalized, actionable information
    - Adapts to patient's current state and needs
    """
    
    def __init__(self):
        self.cfg = get_settings()
        self.enabled = getattr(self.cfg, "INFO_PROVIDER_ENABLED", True)
        
        # RAG components
        self.rag = RAGQueryClient()
        self.bm25 = BM25Client(
            bg_index_dir=self.cfg.BM25_BG_INDEX_DIR,
            q_index_dir=self.cfg.BM25_Q_INDEX_DIR
        )
        
        # LLM for intelligent extraction with optimized parameters
        if self.enabled:
            self.llm = LLMClient(
                model_id=getattr(self.cfg, "INFO_MODEL_ID", "meta-llama/llama-3-3-70b-instruct"),
                params={
                    "max_new_tokens": 2000,  # Increased for more detailed responses
                    "temperature": 0.2,      # Lower temperature for more consistent output
                    "top_p": 0.9,           # Slightly restrict vocabulary for quality
                    "repetition_penalty": 1.1  # Avoid repetitive content
                }
            )
        else:
            self.llm = None
            
        # Configuration
        self.top_k = int(getattr(self.cfg, "INFO_TOP_K", 6))
        self.max_cards = int(getattr(self.cfg, "INFO_MAX_CARDS", 2))
        self.bullets_per_card = int(getattr(self.cfg, "INFO_BULLETS_PER_CARD", 3))
        self.alpha = float(getattr(self.cfg, "HYBRID_ALPHA", 0.6))
        
    def maybe_provide_info(
        self,
        *,
        session,
        last_answer: str,
        current_pnm: Optional[str],
        current_term: Optional[str],
        storage=None
    ) -> List[Dict[str, Any]]:
        """
        Main entry point - provides contextual information cards.
        Enhanced with intelligent retrieval and generation.
        """
        if not self.enabled:
            return []
            
        # Check throttling
        min_gap = int(getattr(self.cfg, "INFO_MIN_TURNS_INTERVAL", 2))
        if hasattr(session, "last_info_turn"):
            if (session.turn_index - int(session.last_info_turn or -999)) < min_gap:
                return []
                
        # Build enhanced context
        context = self._build_context(session, last_answer, current_pnm, current_term, storage)
        if not context:
            return []
            
        # Retrieve relevant knowledge
        documents = self._retrieve_knowledge(context)
        if not documents:
            return []
            
        # Generate information cards
        cards = self._generate_cards(documents, context)
        
        # Update throttle state
        if cards:
            session.last_info_turn = session.turn_index
            if storage:
                self._update_session_throttle(session, storage)
                
        return cards
    
    def _build_context(
        self,
        session,
        last_answer: str,
        current_pnm: Optional[str],
        current_term: Optional[str],
        storage=None
    ) -> Optional[InfoContext]:
        """Build rich context for retrieval with enhanced personalization"""
        if not current_pnm or not current_term:
            return None
            
        # Extract severity indicators from answer
        severity_indicators = self._extract_severity_indicators(last_answer)
        
        # Get recent question history and user responses for better personalization
        question_history = []
        user_responses = []
        if storage and session.session_id:
            turns = storage.list_turns(session.session_id)
            # Get conversation context
            for turn in turns[-10:]:  # Look at more history for better context
                if turn.get('role') == 'assistant':
                    content = turn.get('content', '')
                    if content and '?' in content:
                        question_history.append(content)
                elif turn.get('role') == 'user':
                    content = turn.get('content', '')
                    if content and len(content) > 10:  # Meaningful responses only
                        user_responses.append(content)
        
        # Enhanced context with user response patterns
        enhanced_context = InfoContext(
            current_pnm=current_pnm,
            current_term=current_term,
            last_answer=last_answer,
            question_history=question_history[-3:],
            severity_indicators=severity_indicators
        )
        
        # Add personalization data
        enhanced_context.user_responses = user_responses[-5:]  # Last 5 responses for pattern analysis
        enhanced_context.session_stage = self._determine_session_stage(session, storage)
        enhanced_context.specific_mentions = self._extract_specific_mentions(last_answer)
        
        return enhanced_context
    
    def _determine_session_stage(self, session, storage) -> str:
        """Determine what stage of the conversation we're in for better personalization"""
        if not storage or not session.session_id:
            return "initial"
            
        try:
            turns = storage.list_turns(session.session_id)
            turn_count = len([t for t in turns if t.get('role') == 'user'])
            
            if turn_count <= 2:
                return "initial"
            elif turn_count <= 5:
                return "exploring"
            elif turn_count <= 10:
                return "detailed"
            else:
                return "comprehensive"
        except:
            return "initial"
    
    def _extract_specific_mentions(self, text: str) -> List[str]:
        """Extract specific details mentioned by the user for personalization"""
        import re
        
        specific_mentions = []
        text_lower = text.lower()
        
        # Equipment and aids
        equipment_patterns = [
            r'\b(?:two|three|four|\d+)\s+pillows?\b',
            r'\bwheelchair\b', r'\bwalker\b', r'\bcane\b', r'\brollator\b',
            r'\bcpap\b', r'\bbipap\b', r'\bventilator\b',
            r'\bfeeding tube\b', r'\bpeg\b'
        ]
        
        # Time and frequency indicators  
        time_patterns = [
            r'\bat night\b', r'\bin the morning\b', r'\bevery day\b', r'\bmost days\b',
            r'\bseveral times\b', r'\bonce a week\b', r'\bfrequently\b'
        ]
        
        # Specific symptoms or situations
        situation_patterns = [
            r'\bwhen eating\b', r'\bwhen drinking\b', r'\bwhen walking\b',
            r'\bgoing upstairs\b', r'\bin bed\b', r'\bwaking up\b',
            r'\bthin liquids\b', r'\bthick liquids\b', r'\bsolid food\b'
        ]
        
        all_patterns = equipment_patterns + time_patterns + situation_patterns
        
        for pattern in all_patterns:
            matches = re.findall(pattern, text_lower)
            specific_mentions.extend(matches)
        
        return list(set(specific_mentions))  # Remove duplicates
    
    def _extract_severity_indicators(self, text: str) -> List[str]:
        """Extract severity/urgency indicators from user's answer"""
        indicators = []
        text_lower = text.lower()
        
        # High severity keywords
        high_severity = ['emergency', 'severe', 'cannot', 'unable', 'fallen', 'choke', 'breathless']
        medium_severity = ['difficult', 'trouble', 'sometimes', 'help', 'struggle']
        low_severity = ['minor', 'slight', 'occasional', 'manageable']
        
        for word in high_severity:
            if word in text_lower:
                indicators.append(f"high:{word}")
                
        for word in medium_severity:
            if word in text_lower:
                indicators.append(f"medium:{word}")
                
        for word in low_severity:
            if word in text_lower:
                indicators.append(f"low:{word}")
                
        return indicators
    
    def _retrieve_knowledge(self, context: InfoContext) -> List[Dict[str, Any]]:
        """
        Enhanced knowledge retrieval with context awareness.
        Combines multiple retrieval strategies.
        """
        # Build multi-faceted query
        queries = self._build_retrieval_queries(context)
        
        all_docs = []
        seen_ids = set()
        
        for query in queries:
            # BM25 retrieval
            bm_docs = self.bm25.search_background(query, top_k=self.top_k)
            
            # Vector retrieval
            vx_docs = self.rag.search(query, top_k=self.top_k, index_kind="background")
            
            # Fusion with vector-optimized weights for better semantic matching
            # Lower alpha (0.4) gives more weight to vector search for semantic queries
            fused = hybrid_fusion(
                lexical_run=bm_docs,
                vector_run=vx_docs,
                alpha=0.4,  # 60% vector, 40% lexical for better semantic coverage
                normalize=True,
                topn=self.top_k
            )
            
            # Deduplicate
            for doc in fused:
                doc_id = doc.get('id', str(hash(doc.get('text', ''))))
                if doc_id not in seen_ids:
                    seen_ids.add(doc_id)
                    all_docs.append(doc)
                    
        # Re-rank by relevance to context
        ranked_docs = self._rerank_by_context(all_docs, context)
        
        return ranked_docs[:self.top_k]
    
    def _build_retrieval_queries(self, context: InfoContext) -> List[str]:
        """Build multiple queries for comprehensive retrieval"""
        queries = []
        
        # Query 1: Direct combination
        q1 = f"{context.current_pnm} {context.current_term} {context.last_answer}"
        queries.append(normalize_text(q1))
        
        # Query 2: Term-focused with severity
        if context.severity_indicators:
            severity = context.severity_indicators[0].split(':')[0]
            q2 = f"{context.current_term} {severity} severity ALS management"
            queries.append(normalize_text(q2))
            
        # Query 3: Solution-focused
        q3 = f"how to manage {context.current_term} solutions aids equipment"
        queries.append(normalize_text(q3))
        
        # Query 4: Based on question history
        if context.question_history:
            recent_q = context.question_history[-1]
            q4 = f"{context.current_term} {recent_q}"
            queries.append(normalize_text(q4))
            
        return queries[:3]  # Limit to avoid too many searches
    
    def _rerank_by_context(
        self,
        docs: List[Dict[str, Any]],
        context: InfoContext
    ) -> List[Dict[str, Any]]:
        """Re-rank documents based on contextual relevance"""
        scored_docs = []
        
        for doc in docs:
            score = doc.get('score', 0.0) or doc.get('fused_score', 0.0)
            text = doc.get('text', '')
            meta = doc.get('metadata', {})
            
            # Boost if matches current PNM/term
            if meta.get('pnm', '').lower() == context.current_pnm.lower():
                score += 0.2
            if meta.get('term', '').lower() == context.current_term.lower():
                score += 0.3
                
            # Boost if contains severity-appropriate content
            if context.severity_indicators:
                if 'high:' in context.severity_indicators[0]:
                    if any(w in text.lower() for w in ['immediate', 'urgent', 'emergency']):
                        score += 0.2
                elif 'low:' in context.severity_indicators[0]:
                    if any(w in text.lower() for w in ['maintain', 'prevent', 'early']):
                        score += 0.1
                        
            # Boost if actionable
            if any(w in text.lower() for w in ['how to', 'steps', 'guide', 'tips']):
                score += 0.15
                
            scored_docs.append({
                **doc,
                'context_score': score
            })
            
        # Sort by context score
        scored_docs.sort(key=lambda x: x['context_score'], reverse=True)
        return scored_docs
    
    def _generate_cards(
        self,
        documents: List[Dict[str, Any]],
        context: InfoContext
    ) -> List[Dict[str, Any]]:
        """
        Generate information cards from retrieved documents.
        Uses LLM for intelligent extraction if available.
        """
        cards = []
        
        for doc in documents[:self.max_cards]:
            if self.llm and self.llm.healthy():
                card = self._generate_card_with_llm(doc, context)
            else:
                card = self._generate_card_simple(doc, context)
                
            if card:
                cards.append(card)
                
        return cards
    
    def _generate_card_with_llm(
        self,
        doc: Dict[str, Any],
        context: InfoContext
    ) -> Optional[Dict[str, Any]]:
        """Generate card using LLM for intelligent extraction"""
        text = doc.get('text', '')
        meta = doc.get('metadata', {})
        
        # Build personalized prompt with enhanced context
        specific_mentions = getattr(context, 'specific_mentions', [])
        session_stage = getattr(context, 'session_stage', 'initial')
        
        personalization_notes = []
        if specific_mentions:
            personalization_notes.append(f"Patient mentioned: {', '.join(specific_mentions[:3])}")
        if session_stage in ['detailed', 'comprehensive']:
            personalization_notes.append("This is an ongoing conversation - build on previous topics")
        
        prompt = f"""You are a compassionate ALS/MND specialist nurse creating personalized, high-quality care information cards for patients and caregivers.

PATIENT CONTEXT:
- Current area of concern: {context.current_term} ({context.current_pnm})
- Patient's recent response: "{context.last_answer}"
- Severity indicators: {', '.join(context.severity_indicators[:2]) if context.severity_indicators else 'moderate concern'}
- Conversation depth: {session_stage}
- Specific patient mentions: {', '.join(specific_mentions[:4]) if specific_mentions else 'general concerns'}

EXPERT KNOWLEDGE SOURCE:
{text[:2000]}

PERSONALIZATION CONTEXT:
{chr(10).join(f"• {note}" for note in personalization_notes) if personalization_notes else "• Provide comprehensive but accessible guidance"}

TASK: Create a comprehensive, practical information card that directly addresses this patient's specific situation and provides immediate value.

TITLE REQUIREMENTS:
- 10-18 words that speak directly to their situation
- Include specific patient details when mentioned (e.g., "at night", "when swallowing", "using walker")
- Use encouraging, person-centered language (avoid clinical jargon)
- Make it feel like personalized guidance, not generic advice
- Examples: "Improving Nighttime Breathing Comfort with Positioning and Equipment"
- Examples: "Safe Swallowing Strategies for Thin Liquids and Meal Planning"

INFORMATION BULLETS (exactly 4 comprehensive points):
- Each bullet: 25-40 words, providing substantial actionable guidance
- Start with encouraging, warm language ("You might find...", "A helpful approach is...", "Consider trying...")
- Include specific steps, timeframes, or measurements when appropriate
- Address both immediate relief and longer-term management
- Reference specific patient details naturally when relevant
- Provide clear "why this helps" context to build understanding
- Balance being thorough with being reassuring and non-overwhelming

QUALITY STANDARDS:
- Each bullet must be genuinely helpful and actionable TODAY
- Include practical details (timing, positioning, equipment, techniques)
- Address both symptom management AND emotional support aspects
- Use natural, conversational language that feels personal
- Ensure content is ALS/MND-specific and evidence-based

OUTPUT FORMAT (JSON only, no explanations or markdown):
{{"title": "Comprehensive title addressing their specific situation", "bullets": ["You might find that [detailed actionable strategy with specific steps and reasoning for their situation]...", "A helpful approach is [comprehensive technique with timing/method details that addresses their specific concerns]...", "Consider trying [practical intervention with clear instructions that builds on their mentioned details]...", "Many families discover [supportive strategy with both practical and emotional benefits for their specific circumstances]..."]}}"""

        try:
            response = self.llm.generate_json(prompt)
            if response and 'title' in response and 'bullets' in response:
                bullets = response['bullets'][:self.bullets_per_card]
                
                # Clean and validate bullets with enhanced post-processing
                clean_bullets = []
                for bullet in bullets:
                    if bullet and len(bullet.strip()) > 10:
                        # Post-process each bullet for quality
                        cleaned_bullet = self._clean_bullet_text(bullet)
                        if self._validate_bullet_quality(cleaned_bullet):
                            clean_bullets.append(cleaned_bullet)
                        
                if clean_bullets:
                    return {
                        "title": self._clean_title_text(response['title']),
                        "bullets": clean_bullets,
                        "url": meta.get('url'),
                        "source": meta.get('source', 'ALS/MND Knowledge Base'),
                        "pnm": context.current_pnm,
                        "term": context.current_term,
                        "score": float(doc.get('context_score', 0.8)),
                        "disclaimer": "This advice is based on your responses and knowledge resources. It does not constitute medical diagnosis."
                    }
        except:
            pass
            
        # Fallback to simple extraction
        return self._generate_card_simple(doc, context)
    
    def _generate_card_simple(
        self,
        doc: Dict[str, Any],
        context: InfoContext
    ) -> Dict[str, Any]:
        """Enhanced simple card generation without LLM - creates higher quality fallback cards"""
        meta = doc.get('metadata', {})
        text = doc.get('text', '')
        
        # Generate more engaging, specific title
        title = self._create_engaging_title(meta, context)
        
        # Extract enhanced bullet points
        sentences = split_sentences(text)
        bullets = self._extract_quality_bullets(sentences, context)
        
        # Ensure minimum quality
        if len(bullets) < 2:
            bullets = self._generate_fallback_bullets(context)
            
        return {
            "title": title,
            "bullets": bullets[:self.bullets_per_card],
            "url": meta.get('url'),
            "source": meta.get('source', 'ALS/MND Knowledge Base'),
            "pnm": context.current_pnm,
            "term": context.current_term,
            "score": float(doc.get('context_score', 0.6)),
            "generated_by": "enhanced_fallback"
        }
    
    def _create_engaging_title(self, meta: Dict[str, Any], context: InfoContext) -> str:
        """Create an engaging, personalized title even without LLM"""
        base_title = (
            meta.get('title') or 
            meta.get('heading') or 
            f"Managing {context.current_term}"
        )
        
        # Add context-specific improvements
        if context.severity_indicators:
            severity = context.severity_indicators[0].split(':')[0]
            if severity == 'high':
                prefix = "Immediate Support for"
            elif severity == 'low':  
                prefix = "Maintaining Comfort with"
            else:
                prefix = "Managing"
        else:
            prefix = "Practical Guidance for"
            
        # Incorporate specific mentions
        specific_mentions = getattr(context, 'specific_mentions', [])
        if specific_mentions and len(specific_mentions) > 0:
            mention = specific_mentions[0]
            title = f"{prefix} {context.current_term} - {mention.title()} Considerations"
        else:
            title = f"{prefix} {context.current_term} in Daily Life"
            
        return title[:70]  # Keep reasonable length
    
    def _extract_quality_bullets(self, sentences: List[str], context: InfoContext) -> List[str]:
        """Extract higher quality bullet points from text"""
        bullets = []
        
        # Priority patterns for actionable content
        priority_patterns = [
            'you can', 'try to', 'consider', 'ask your', 'speak with',
            'use', 'avoid', 'ensure', 'maintain', 'practice',
            'helpful', 'effective', 'important', 'recommended'
        ]
        
        # First pass: prioritize actionable sentences
        for sent in sentences:
            if len(bullets) >= self.bullets_per_card:
                break
                
            sent = sent.strip()
            if len(sent) < 15 or len(sent) > 200:  # Skip too short/long
                continue
                
            # Check for priority patterns
            if any(pattern in sent.lower() for pattern in priority_patterns):
                # Clean and enhance the sentence
                enhanced_bullet = self._enhance_bullet_text(sent, context)
                if enhanced_bullet and self._validate_bullet_quality(enhanced_bullet):
                    bullets.append(enhanced_bullet)
                    
        # Second pass: fill remaining slots with informative content
        if len(bullets) < self.bullets_per_card:
            for sent in sentences:
                if len(bullets) >= self.bullets_per_card:
                    break
                    
                sent = sent.strip()
                if sent and len(sent) >= 20 and sent not in bullets:
                    enhanced_bullet = self._enhance_bullet_text(sent, context)
                    if enhanced_bullet and len(enhanced_bullet) >= 20:
                        bullets.append(enhanced_bullet)
                        
        return bullets
    
    def _enhance_bullet_text(self, text: str, context: InfoContext) -> str:
        """Enhance a bullet point to be more supportive and actionable"""
        # Clean the text
        text = text.strip()
        if not text:
            return ""
            
        # Add supportive language if not present
        supportive_starters = ['you might find', 'consider', 'many people', 'a helpful approach']
        if not any(starter in text.lower() for starter in supportive_starters):
            if text.lower().startswith(('use', 'try', 'avoid', 'ensure')):
                text = f"You might find it helpful to {text.lower()}"
            elif text.lower().startswith(('ask', 'speak', 'contact')):
                text = f"Consider working with your care team to {text.lower()}"
            else:
                text = f"Many people find that {text.lower()}"
                
        # Ensure proper sentence structure
        if not text.endswith('.'):
            text += '.'
            
        # Capitalize first letter
        if text:
            text = text[0].upper() + text[1:]
            
        return text
    
    def _generate_fallback_bullets(self, context: InfoContext) -> List[str]:
        """Generate fallback bullets when no good content is found"""
        term = context.current_term.lower()
        
        # Template-based fallback content based on common ALS concerns
        fallback_templates = {
            'breathing': [
                "Consider discussing breathing support options with your respiratory therapist.",
                "Many people find that positioning with extra pillows helps improve comfort during sleep.",
                "Regular monitoring of breathing patterns can help your care team adjust treatments.",
                "Gentle breathing exercises may help maintain respiratory muscle strength when appropriate."
            ],
            'swallowing': [
                "Work with a speech-language pathologist to assess safe swallowing strategies.",
                "Consider modifying food textures and liquid consistency based on professional guidance.", 
                "Many families find meal planning and preparation techniques help ensure proper nutrition.",
                "Regular swallowing evaluations can help adjust strategies as needs change."
            ],
            'mobility': [
                "Physical therapy can help maintain strength and develop adaptive movement strategies.",
                "Consider mobility aids and equipment that can support independence and safety.",
                "Many people find that pacing activities throughout the day helps manage energy.",
                "Home modifications may improve accessibility and reduce fall risk."
            ]
        }
        
        # Find matching template or use generic
        for key, templates in fallback_templates.items():
            if key in term:
                return templates[:self.bullets_per_card]
                
        # Generic fallbacks
        return [
            f"Consider discussing {context.current_term} management with your ALS care team.",
            f"Many people find that working with specialists helps develop effective strategies for {context.current_term}.",
            f"Regular monitoring and adjustment of approaches can help optimize {context.current_term} management.",
            f"Support groups and resources may provide valuable insights for managing {context.current_term}."
        ][:self.bullets_per_card]
    
    def _clean_bullet_text(self, bullet: str) -> str:
        """Clean bullet text by removing formatting issues and improving quality"""
        import re
        
        if not bullet or not isinstance(bullet, str):
            return ""
            
        # Remove leading numbers, bullets, and formatting characters
        cleaned = re.sub(r'^[\d\s•\-\*\.\)]+', '', bullet.strip())
        
        # Remove trailing ellipsis and incomplete sentences
        cleaned = re.sub(r'\.{2,}$|…$', '.', cleaned)
        
        # Ensure proper sentence structure
        cleaned = cleaned.strip()
        if cleaned and not cleaned.endswith(('.', '!', '?')):
            cleaned += '.'
            
        # Capitalize first letter
        if cleaned:
            cleaned = cleaned[0].upper() + cleaned[1:] if len(cleaned) > 1 else cleaned.upper()
            
        return cleaned
    
    def _validate_bullet_quality(self, bullet: str) -> bool:
        """Validate that a bullet point meets enhanced quality standards"""
        if not bullet or len(bullet.strip()) < 20:  # Increased minimum length
            return False
            
        # Check for incomplete sentences or formatting issues
        if bullet.count('•') > 0 or bullet.startswith(tuple('0123456789')):
            return False
            
        # Ensure appropriate length for comprehensive advice
        words = bullet.split()
        if len(words) < 8 or len(words) > 45:  # Increased range for comprehensive bullets
            return False
            
        # Enhanced action-oriented content check
        action_words = ['try', 'consider', 'use', 'practice', 'ask', 'discuss', 'avoid', 'ensure', 
                       'maintain', 'adjust', 'find', 'discover', 'approach', 'helpful', 'might']
        supportive_words = ['many people', 'you might', 'consider', 'helpful approach', 'try']
        
        has_action = any(word in bullet.lower() for word in action_words)
        has_supportive = any(phrase in bullet.lower() for phrase in supportive_words)
        
        if not (has_action or has_supportive):
            return False
            
        # Check for ALS/MND relevance
        als_related = ['breathing', 'swallow', 'mobility', 'speech', 'hand', 'walk', 'eat', 
                      'position', 'device', 'equipment', 'therapy', 'care', 'support']
        if not any(word in bullet.lower() for word in als_related):
            # Allow if it's a comprehensive sentence with practical advice
            if len(words) < 12:
                return False
                
        return True
    
    def _clean_title_text(self, title: str) -> str:
        """Clean and improve title text"""
        if not title or not isinstance(title, str):
            return "Helpful Tips for ALS Management"
            
        # Remove unnecessary formatting
        cleaned = title.strip().replace('[', '').replace(']', '')
        
        # Ensure proper capitalization
        words = cleaned.split()
        if words:
            # Capitalize important words
            important_words = ['als', 'mnd', 'breathing', 'speech', 'swallowing', 'mobility', 'daily', 'living']
            cleaned_words = []
            for word in words:
                if word.lower() in important_words or len(word) > 3:
                    cleaned_words.append(word.capitalize())
                else:
                    cleaned_words.append(word.lower())
            
            # Always capitalize first word
            if cleaned_words:
                cleaned_words[0] = cleaned_words[0].capitalize()
            
            cleaned = ' '.join(cleaned_words)
        
        # Limit length
        if len(cleaned) > 60:
            cleaned = cleaned[:57] + '...'
            
        return cleaned or "Tips for Managing ALS Symptoms"

    def _update_session_throttle(self, session, storage) -> None:
        """Update session with last info turn"""
        try:
            storage.upsert_session(
                session_id=session.session_id,
                user_id=session.user_id,
                status=session.status,
                fsm_state=session.fsm_state,
                current_pnm=session.current_pnm,
                current_term=session.current_term,
                current_qid=session.current_qid,
                asked_qids=session.asked_qids,
                followup_ptr=session.followup_ptr,
                lock_until_turn=session.lock_until_turn,
                turn_index=session.turn_index,
                last_info_turn=session.last_info_turn,
            )
        except:
            pass  # Non-critical