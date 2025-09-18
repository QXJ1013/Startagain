# app/services/info_provider_enhanced.py
from __future__ import annotations

"""
Enhanced Information Provider with intelligent RAG.
- Context-aware retrieval from knowledge base
- Smart content extraction and summarization
- Personalized card generation based on session state
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import json

from app.config import get_settings
from app.vendors.ibm_cloud import RAGQueryClient, LLMClient
from app.vendors.bm25 import BM25Client
from app.utils.rerank import hybrid_fusion
from app.utils.text import normalize_text, split_sentences, truncate_words
from app.services.nlg_service import NaturalLanguageGenerator, enhance_info_card
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class InfoContext:
    """Enhanced context for intelligent information retrieval and personalization"""
    # Basic context fields (backward compatible)
    current_pnm: str
    current_term: str
    last_answer: str
    question_history: List[str]
    severity_indicators: List[str]
    
    # Enhanced intelligence fields
    emotional_state: str = 'neutral'
    user_responses: List[str] = field(default_factory=list)
    specific_mentions: List[str] = field(default_factory=list)
    session_stage: str = 'initial'
    pnm_scores: Dict[str, float] = field(default_factory=dict)
    cultural_context: str = 'general'
    
    # Advanced personalization fields
    major_concerns: List[str] = field(default_factory=list)
    is_detailed_responder: bool = False
    symptom_changes: List[Dict[str, Any]] = field(default_factory=list)
    total_interactions: int = 0
    
    
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
        
        # Initialize NLG service for enhanced content quality
        self.nlg = NaturalLanguageGenerator()
        
    def maybe_provide_info(
        self,
        *,
        conversation,
        last_answer: str,
        current_pnm: Optional[str],
        current_term: Optional[str],
        storage=None
    ) -> List[Dict[str, Any]]:
        """
        Main entry point - provides contextual information cards.
        Enhanced with intelligent retrieval and generation.
        """
        import logging
        log = logging.getLogger(__name__)
        log.info(f"maybe_provide_info called: enabled={self.enabled}, pnm={current_pnm}, term={current_term}")
        
        if not self.enabled:
            log.info("Info provider disabled")
            return []
            
        # Check throttling - document-based architecture
        if not conversation or not conversation.messages:
            log.info("No conversation or messages available")
            return []
            
        message_count = len(conversation.messages)
        min_interval = int(getattr(self.cfg, "INFO_MIN_TURNS_INTERVAL", 2))
        
        # Simple throttling: provide info every 3 messages after minimum interval
        if message_count < min_interval or message_count % 3 != 0:
            log.info(f"Throttled: message_count={message_count}, min_interval={min_interval}")
            return []
                
        # Build enhanced context using conversation document
        context = self._build_context(conversation, last_answer, current_pnm, current_term, storage)
        log.info(f"Context built: {bool(context)}")
        if not context:
            log.info("No context built")
            return []
            
        # Retrieve relevant knowledge
        documents = self._retrieve_knowledge(context)
        log.info(f"Retrieved {len(documents) if documents else 0} documents")
        
        # Generate information cards (with fallback if no documents)
        cards = self._generate_cards(documents or [], context)
        
        # No throttle state update needed in document-based architecture
        return cards
    
    def _build_context(
        self,
        conversation,
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
        
        # Get comprehensive conversation history for better personalization
        question_history = []
        user_responses = []
        repeated_concerns = {}  # Track recurring themes
        symptom_progression = []  # Track how symptoms change
        messages = []  # Initialize messages list
        
        if conversation and conversation.messages:
            # Use conversation messages for analysis
            messages = conversation.messages
            
            # Analyze ALL messages for patterns, not just recent ones
            for idx, message in enumerate(messages):
                if message.role == 'assistant':
                    content = message.content
                    if content and '?' in content:
                        question_history.append(content)
                elif message.role == 'user':
                    content = message.content.lower()
                    if content and len(content) > 10:  # Meaningful responses only
                        user_responses.append(content)
                        
                        # Track recurring concerns
                        concern_keywords = ['breathing', 'swallow', 'walk', 'sleep', 'talk', 
                                          'fatigue', 'pain', 'anxiety', 'fall', 'choke']
                        for keyword in concern_keywords:
                            if keyword in content:
                                if keyword not in repeated_concerns:
                                    repeated_concerns[keyword] = []
                                repeated_concerns[keyword].append(idx)
                        
                        # Track symptom progression words
                        if any(word in content for word in ['worse', 'better', 'improving', 'declining']):
                            symptom_progression.append({
                                'turn': idx,
                                'content': content[:100]
                            })
        
        # Identify most concerning issues (mentioned 3+ times)
        major_concerns = [k for k, v in repeated_concerns.items() if len(v) >= 3]
        
        # Determine conversation patterns
        response_length_avg = sum(len(r) for r in user_responses) / max(len(user_responses), 1)
        is_detailed_responder = response_length_avg > 50  # User gives detailed answers
        
        # Enhanced context with user response patterns
        enhanced_context = InfoContext(
            current_pnm=current_pnm,
            current_term=current_term,
            last_answer=last_answer,
            question_history=question_history[-5:],  # Keep more history
            severity_indicators=severity_indicators
        )
        
        # Add comprehensive personalization data
        enhanced_context.user_responses = user_responses[-10:]  # More responses for better patterns
        enhanced_context.session_stage = self._determine_session_stage(conversation, storage)
        enhanced_context.specific_mentions = self._extract_specific_mentions(last_answer)
        enhanced_context.major_concerns = major_concerns  # New: recurring themes
        enhanced_context.is_detailed_responder = is_detailed_responder  # New: response style
        enhanced_context.symptom_changes = symptom_progression[-3:]  # New: progression tracking
        enhanced_context.total_interactions = len(messages) if messages else 0  # New: conversation depth
        
        # Add intelligence fields
        enhanced_context.emotional_state = self._detect_emotional_state(last_answer)
        
        # Extract PNM scores from conversation assessment_state
        if hasattr(conversation, 'assessment_state') and conversation.assessment_state:
            enhanced_context.pnm_scores = conversation.assessment_state.get('scores', {})
        
        # Determine cultural context (simple implementation)
        enhanced_context.cultural_context = 'general'  # Could be enhanced with user profile data
        
        return enhanced_context
    
    def _determine_session_stage(self, conversation, storage) -> str:
        """Determine what stage of the conversation we're in for better personalization"""
        if not conversation or not conversation.messages:
            return "initial"
            
        try:
            messages = conversation.messages
            user_message_count = len([m for m in messages if m.role == 'user'])
            
            if user_message_count <= 2:
                return "initial"
            elif user_message_count <= 5:
                return "exploring"
            elif user_message_count <= 10:
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
        Generate enhanced information cards from retrieved documents with fallback support.
        Uses NLG service to improve RAG content quality and personalization.
        """
        cards = []
        
        # If we have documents, generate from them
        if documents:
            for doc in documents[:self.max_cards]:
                # First generate card content (existing logic)
                if self.llm and self.llm.healthy():
                    raw_card = self._generate_card_with_llm(doc, context)
                else:
                    raw_card = self._generate_card_simple(doc, context)
                
                # Then enhance with NLG for better quality and personalization
                if raw_card:
                    enhanced_card = self._enhance_card_with_nlg(raw_card, context)
                    cards.append(enhanced_card)
        else:
            # Fallback: generate template-based card when no documents available
            fallback_card = self._generate_fallback_card(context)
            if fallback_card:
                enhanced_card = self._enhance_card_with_nlg(fallback_card, context)
                cards.append(enhanced_card)
                
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
        
        # Enhanced prompt with better structure and specificity
        
        # Analyze conversation history for patterns
        user_responses = getattr(context, 'user_responses', [])
        frequency_words = ['always', 'often', 'sometimes', 'rarely', 'never']
        user_frequency = 'not specified'
        for word in frequency_words:
            if word in context.last_answer.lower():
                user_frequency = word
                break
        
        # Determine stage based on severity indicators
        severity_level = 'moderate'
        if context.severity_indicators:
            high_count = sum(1 for s in context.severity_indicators if s.startswith('high:'))
            if high_count >= 2:
                severity_level = 'high'
            elif any(s.startswith('low:') for s in context.severity_indicators):
                severity_level = 'low'
        
        # Extract specific challenges from answer
        challenges = []
        if 'difficult' in context.last_answer.lower():
            challenges.append('experiencing difficulty')
        if 'can\'t' in context.last_answer.lower() or 'cannot' in context.last_answer.lower():
            challenges.append('unable to perform')
        if 'help' in context.last_answer.lower():
            challenges.append('needs assistance')
        
        prompt = f"""You are an experienced ALS/MND specialist creating a personalized information card. Your goal is to provide IMMEDIATELY ACTIONABLE guidance that the patient can use TODAY.

PATIENT PROFILE:
- Topic: {context.current_term} ({context.current_pnm} needs)
- Their exact words: "{context.last_answer[:150]}"
- Frequency/Pattern: {user_frequency}
- Severity: {severity_level} priority
- Key challenges: {', '.join(challenges) if challenges else 'managing symptoms'}
- Specific mentions: {', '.join(specific_mentions[:3]) if specific_mentions else 'none'}

CONVERSATION HISTORY INSIGHTS:
- Session stage: {session_stage} (adjust detail level accordingly)
- Previous questions: {len(context.question_history)} asked
{f"- Recurring themes: {', '.join([q[:30] for q in context.question_history[-2:]])}" if context.question_history else ""}

KNOWLEDGE BASE CONTENT:
 {text[:1500]}

CRITICAL INSTRUCTIONS:

1. TITLE (15-20 words):
   - Must include their SPECIFIC situation (e.g., if they said "at night", include "nighttime")
   - Use their language level (simple if answers are brief, detailed if elaborate)
   - Focus on the BENEFIT, not the problem
   - Good: "Managing Breathing Comfort When Lying Down at Night"
   - Bad: "Breathing Difficulties Information"

2. FOUR BULLETS (each 30-40 words, MUST be different approaches):
   
   Bullet 1 - IMMEDIATE RELIEF (what to do RIGHT NOW):
   - Start with action verb (Try, Position, Use)
   - Include specific measurements/angles/times
   - Explain WHY it helps in simple terms
   
   Bullet 2 - DAILY ROUTINE INTEGRATION:
   - Connect to their mentioned daily patterns
   - Provide a structured approach (morning/evening/before meals)
   - Include frequency and duration
   
   Bullet 3 - EQUIPMENT/TECHNIQUE OPTIMIZATION:
   - Suggest specific tools or adaptations
   - Include both no-cost and equipment options
   - Mention how to obtain or alternatives
   
   Bullet 4 - MONITORING & PROGRESSION:
   - How to track if it's working
   - When to adjust the approach
   - Include caregiver involvement if severity is high

3. LANGUAGE RULES:
   - Use "you" directly, be conversational
   - Avoid medical jargon unless they used it first
   - Include emotional reassurance naturally
   - Acknowledge their specific situation

4. BASED ON SEVERITY:
   - Low: Focus on prevention and optimization
   - Moderate: Balance management with adaptation
   - High: Prioritize comfort and caregiver support

OUTPUT FORMAT (JSON only):
{{
  "title": "[Specific, encouraging title with their context]",
  "bullets": [
    "[Action verb] [specific technique with measurement] because [simple explanation of benefit]",
    "[Time-based routine] with [specific duration/frequency] to [clear outcome]",
    "[Equipment/technique] using [specific item/method] which [practical benefit]",
    "[Monitoring approach] by [specific indicator] and [adjustment strategy]"
  ]
}}"""

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
    
    def _enhance_card_with_nlg(self, card: Dict[str, Any], context: InfoContext) -> Dict[str, Any]:
        """
        NLG enhancement pipeline for RAG-generated cards using new NLG service.
        """
        if not self.nlg or not self.nlg.enabled:
            return card
            
        try:
            # Build conversation context for NLG using helper functions
            conversation_context = {
                'emotional_state': self._detect_emotional_state(context.last_answer),
                'severity_level': self._calculate_severity_level(context.severity_indicators),
                'session_stage': getattr(context, 'session_stage', 'initial'),
                'specific_mentions': getattr(context, 'specific_mentions', [])
            }
            
            # Use utility function for enhancement
            enhanced_card = enhance_info_card(card, conversation_context, nlg_service=self.nlg)
            
            return enhanced_card
            
        except Exception as e:
            logger.error(f"NLG enhancement failed for card: {e}")
            # Return original card if enhancement fails
            card["nlg_enhanced"] = False
            return card

    def _detect_emotional_state(self, text: str) -> str:
        """Detect user emotional state from text for NLG personalization"""
        text_lower = text.lower()
        
        # Anxious/worried indicators
        if any(word in text_lower for word in ['worried', 'anxious', 'scared', 'frightened', 'overwhelmed']):
            return 'anxious'
        
        # Sad/depressed indicators  
        if any(word in text_lower for word in ['sad', 'depressed', 'hopeless', 'down', 'crying']):
            return 'sad'
        
        # Frustrated/angry indicators
        if any(word in text_lower for word in ['frustrated', 'angry', 'mad', 'annoyed', 'irritated']):
            return 'frustrated'
        
        # Information-seeking indicators
        if any(word in text_lower for word in ['want to know', 'need information', 'tell me', 'explain']):
            return 'information_seeking'
        
        return 'neutral'
    
    def _calculate_severity_level(self, severity_indicators: List[str]) -> str:
        """Calculate severity level from indicators for NLG adaptation"""
        if not severity_indicators:
            return 'moderate'
        
        high_count = sum(1 for indicator in severity_indicators if indicator.startswith('high:'))
        low_count = sum(1 for indicator in severity_indicators if indicator.startswith('low:'))
        
        if high_count >= 2:
            return 'high'
        elif low_count >= 2:
            return 'low'
        else:
            return 'moderate'
    
    def _generate_fallback_card(self, context: InfoContext) -> Dict[str, Any]:
        """Generate fallback information card when no documents are retrieved"""
        from app.config import get_settings
        cfg = get_settings()
        
        # Get fallback templates from config
        fallback_templates = getattr(cfg, 'INFO_FALLBACK_TEMPLATES', {})
        
        # Determine which template to use based on current term/PNM
        term_lower = context.current_term.lower()
        template_bullets = []
        
        if 'breathing' in term_lower:
            template_bullets = fallback_templates.get('breathing', [
                "Consider discussing breathing support options with your respiratory therapist.",
                "Many people find that positioning with extra pillows helps improve comfort during sleep.",
                "Regular monitoring of breathing patterns can help your care team adjust treatments."
            ])
        elif 'swallow' in term_lower:
            template_bullets = fallback_templates.get('swallowing', [
                "Work with a speech-language pathologist to assess safe swallowing strategies.",
                "Consider modifying food textures and liquid consistency based on professional guidance.",
                "Many families find meal planning and preparation techniques help ensure proper nutrition."
            ])
        elif 'mobility' in term_lower or 'walk' in term_lower:
            template_bullets = fallback_templates.get('mobility', [
                "Physical therapy can help maintain strength and develop adaptive movement strategies.",
                "Consider mobility aids and equipment that can support independence and safety.",
                "Many people find that pacing activities throughout the day helps manage energy."
            ])
        else:
            # Default template
            default_templates = fallback_templates.get('default', [
                "Consider discussing {term} management with your ALS care team.",
                "Many people find that working with specialists helps develop effective strategies for {term}.",
                "Regular monitoring and adjustment of approaches can help optimize {term} management."
            ])
            template_bullets = [t.format(term=context.current_term) for t in default_templates]
        
        # Create fallback card
        fallback_card = {
            "title": f"Managing {context.current_term} with ALS",
            "bullets": template_bullets[:3],  # Limit to 3 bullets
            "source": "template_fallback",
            "pnm": context.current_pnm,
            "term": context.current_term
        }
        
        return fallback_card
    
    # _update_session_throttle method removed - not needed in document-based architecture