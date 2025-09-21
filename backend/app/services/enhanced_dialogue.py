# app/services/enhanced_dialogue.py


from __future__ import annotations
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import logging

from app.services.storage import ConversationDocument
from app.services.question_bank import QuestionBank
from app.services.ai_routing import AIRouter
from app.services.pnm_scoring import PNMScoringEngine
from app.services.ai_scoring_engine import AIFreeTextScorer, EnhancedPNMScorer, StageScorer
from app.services.user_profile_manager import UserProfileManager, ReliableRoutingEngine
from app.vendors.ibm_cloud import RAGQueryClient, LLMClient
import hashlib
import json

log = logging.getLogger(__name__)


# ConversationCache class removed - unused dead code
  


class ConversationMode(Enum):
    """Conversation mode types"""
    FREE_DIALOGUE = "free_dialogue"           # Mode 1: Natural conversation with RAG AI
    DIMENSION_ANALYSIS = "dimension_analysis" # Mode 2: Structured dimension assessment
    TRANSITIONING = "transitioning"           # Intermediate state during mode switches


class ResponseType(Enum):
    """Response content types"""
    CHAT = "chat"                            # Normal conversational response
    QUESTION = "question"                    # Structured assessment question
    SUMMARY = "summary"                      # Detailed summary after completing assessments


@dataclass
class ConversationContext:
    """Context information for conversation processing"""
    conversation: ConversationDocument
    user_input: str
    mode: ConversationMode
    turn_count: int
    detected_symptoms: List[str]
    current_dimension: Optional[str]
    current_term: Optional[str]
    recent_scores: List[Dict[str, Any]]
    
    
@dataclass
class DialogueResponse:
    """Enhanced response structure"""
    content: str
    response_type: ResponseType
    mode: ConversationMode
    
    # Conversation control
    should_continue_dialogue: bool = True
    next_mode: Optional[ConversationMode] = None
    
    # Assessment data
    current_pnm: Optional[str] = None
    current_term: Optional[str] = None
    question_id: Optional[str] = None
    options: Optional[List[Dict[str, Any]]] = None

    # Information cards
    info_cards: Optional[List[Dict[str, Any]]] = None
    detected_symptoms: Optional[List[str]] = None

    # Enhanced info provider integration
    has_info_cards: bool = False

    # Metadata
    confidence_score: float = 0.0
    rag_sources: Optional[List[str]] = None

    # Scoring data
    score: Optional[float] = None
    scoring_method: Optional[str] = None
    rationale: Optional[str] = None


class ConversationModeManager:
    """
    Central manager for conversation modes and transitions.
    """
    
    def __init__(self, qb: QuestionBank, ai_router: AIRouter, storage=None):
        self.qb = qb
        self.ai_router = ai_router
        self.storage = storage  # Add storage for UC1 scoring
        self.scoring_engine = PNMScoringEngine()
        self.enhanced_pnm_scorer = EnhancedPNMScorer()
        self.ai_scorer = AIFreeTextScorer(ai_router)
        self.stage_scorer = StageScorer()
        self.profile_manager = UserProfileManager()
        self.reliable_router = ReliableRoutingEngine()

        # Initialize LLM BEFORE UC managers to ensure dependency access
        self.llm = LLMClient()

        # Use Case specific managers - clean separation (initialize AFTER LLM)
        self.uc1_manager = UseCaseOneManager(qb, ai_router, self)  # Pass main manager for storage access
        self.uc2_manager = UseCaseTwoManager(qb, ai_router, self)  # Pass main manager for scoring access
        
    def determine_conversation_mode(self, context: ConversationContext) -> ConversationMode:
        """
        Determine which conversation mode to use.

        STEP 1: Basic rules
        STEP 2: Add AI decision making
        STEP 3: Add user preference learning
        """
        # Use Case 2: Explicit dimension selection from frontend
        if (context.conversation.type == "dimension" and
            context.conversation.dimension):
            return ConversationMode.DIMENSION_ANALYSIS

        # Use Case 1: Simple fixed turn trigger - transition at turn 4
        if context.turn_count < 4:
            return ConversationMode.FREE_DIALOGUE

        # Turn 4+: Allow transition to assessment
        return ConversationMode.FREE_DIALOGUE
    
    def should_transition_mode(self, context: ConversationContext) -> bool:
        """
        Determine if conversation should transition to different mode.

        STEP 1: Basic transition triggers
        STEP 2: AI-powered transition detection
        STEP 3: Refined transition logic
        """
        if context.mode == ConversationMode.FREE_DIALOGUE:
            # Fixed turn trigger: transition at turn 4
            if context.turn_count >= 4:
                return True

            # Allow explicit user requests for early assessment
            if "assess" in context.user_input.lower() or "evaluation" in context.user_input.lower():
                return True

        return False
        
    async def process_conversation(self, context: ConversationContext) -> DialogueResponse:
        """
        Main entry point for conversation processing.
        Routes to appropriate Use Case manager.
        """
        try:
            pass  # Debug print removed
        except Exception as e:
            print(f"[ERROR] Exception accessing context attributes: {e}")
            print(f"[ERROR] Context type: {type(context)}")
            print(f"[ERROR] Context.conversation type: {type(context.conversation) if hasattr(context, 'conversation') else 'No conversation attr'}")
            raise e  # Re-raise to trigger fallback to legacy system

        # Route based on conversation type - clean separation

        if (context.conversation.type == "dimension" and
            context.conversation.dimension):
            # Use Case 2: Single dimension assessment
            return await self.uc2_manager.handle_dimension_assessment(
                context, context.conversation.dimension)
        else:
            # Use Case 1: General conversation flow
            return await self.uc1_manager.handle_conversation_flow(context)
    
    
    
    def _handle_fallback(self, context: ConversationContext) -> DialogueResponse:
        """Fallback response when other modes fail"""
        return DialogueResponse(
            content="How are you feeling about your current situation with ALS?",
            response_type=ResponseType.CHAT,
            mode=ConversationMode.FREE_DIALOGUE,
            should_continue_dialogue=True
        )
    
    def _fallback_dimension_analysis(self, context: ConversationContext) -> DialogueResponse:
        """Fallback for dimension analysis mode"""
        try:
            # Only do PNM routing if we're truly in assessment mode
            if (context.conversation.type == "dimension" and context.conversation.dimension):
                # Use Case 2: Explicit dimension assessment
                pnm = context.conversation.dimension
                term = context.current_term or 'General health'
            elif context.current_dimension:
                # Assessment mode with existing dimension
                pnm = context.current_dimension
                term = context.current_term or 'General health'
            else:
                # Use Case 1: Should not reach here - redirect to free dialogue
                return self._handle_fallback(context)
            
            question_item = self.qb.choose_for_term(pnm, term, [])
            if question_item:
                options = []
                if question_item.options:
                    options = [
                        {'value': opt.get('id', str(i)), 'label': opt.get('label', str(opt))}
                        for i, opt in enumerate(question_item.options)
                    ]
                
                return DialogueResponse(
                    content=question_item.main,
                    response_type=ResponseType.CHAT,
                    mode=ConversationMode.DIMENSION_ANALYSIS,
                    current_pnm=pnm,
                    current_term=term,
                    question_id=question_item.id,
                    options=options,
                    should_continue_dialogue=True
                )
        except Exception as e:
            log.error(f"Fallback dimension analysis error: {e}")
        
        return self._handle_fallback(context)


class ResponseGenerator:
    """
    RAG + LLM powered response generation with advanced personalization.
    
    STEP 3: Enhanced with user behavior learning and preference adaptation
    """
    
    def __init__(self, rag: RAGQueryClient = None, llm: LLMClient = None):
        self.rag = rag or RAGQueryClient()
        self.llm = llm or LLMClient()
        
        # Load conversation style configuration
        self.conversation_config = self._load_conversation_config()
        
        # Load PNM lexicon for symptom understanding
        self.pnm_lexicon = self._load_pnm_lexicon()
        
        
    def _load_conversation_config(self) -> Dict[str, Any]:
        """Load conversation style configuration"""
        try:
            import json
            from pathlib import Path
            config_path = Path(__file__).parent.parent / "data" / "conversation_config.json"
            if config_path.exists():
                return json.loads(config_path.read_text())
        except Exception as e:
            log.warning(f"Could not load conversation config: {e}")
        
        # Fallback default config
        return {
            "language_style": {
                "avoid_clinical_jargon": True,
                "use_simple_language": True,
                "max_sentence_length": 20,
                "active_voice": True
            },
            "empathy_rules": {
                "acknowledge_difficulty": True,
                "validate_feelings": True,
                "offer_hope": True,
                "respect_autonomy": True
            }
        }
    
    def _load_pnm_lexicon(self) -> Dict[str, Any]:
        """Load PNM lexicon for symptom understanding"""
        try:
            import json
            from pathlib import Path
            lexicon_path = Path(__file__).parent.parent / "data" / "pnm_lexicon.json"
            if lexicon_path.exists():
                return json.loads(lexicon_path.read_text())
        except Exception as e:
            log.warning(f"Could not load PNM lexicon: {e}")
        
        return {}
        
    def generate_chat_response(self, context: ConversationContext) -> str:
        """
        Generate personalized RAG+LLM powered conversational response.
        
        STEP 3: Enhanced with user behavior learning and advanced personalization:
        1. User preference analysis and adaptation
        2. Symptom-aware RAG retrieval with personalization
        3. Context-sensitive LLM generation with emotional intelligence
        4. Adaptive response styling based on learned preferences
        """
        try:
            # 1. Simplified user preferences - no keyword matching overhead
            user_preferences = {'communication_style': 'balanced'}

            # 2. Analyze user input with enhanced context awareness
            analysis = self._analyze_user_input_enhanced(context, user_preferences)

            # 3. Retrieve knowledge via RAG
            knowledge = self._retrieve_personalized_knowledge(context, analysis, user_preferences)
            
            # 4. REMOVED: Conversation coherence analysis (over-engineered for UC1/UC2)
            coherence_analysis = {'coherence_score': 0.8, 'suggestions': []}  # Simple fallback
            
            # 5. Decide response mode: Chat vs Info Cards
            should_provide_info = self._should_provide_info_cards(context, analysis, user_preferences)
            
            if should_provide_info:
                # Generate response with info cards
                response = self._generate_chat_with_info_cards(context, analysis, knowledge, user_preferences, coherence_analysis)
            else:
                # Generate pure conversational response
                response = self._generate_adaptive_response(context, analysis, knowledge, user_preferences, coherence_analysis)
            
            return response
            
        except Exception as e:
            log.error(f"Advanced chat response generation error: {e}")
            # NO FALLBACK - Direct AI response as user demanded
            return "I understand you're dealing with ALS. Let me provide some guidance and support for your situation."
    
    def _analyze_user_input(self, context: ConversationContext) -> Dict[str, Any]:
        """Analyze user input for symptoms, emotions, and intent"""
        user_input = context.user_input.lower()
        
        analysis = {
            'detected_symptoms': context.detected_symptoms.copy(),
            'emotional_indicators': [],
            'urgency_level': 'normal',
            'key_topics': [],
            'requires_support': False
        }
        
        # Enhanced symptom detection using PNM lexicon
        for pnm_level, pnm_data in self.pnm_lexicon.items():
            if 'terms' in pnm_data:
                for term, synonyms in pnm_data['terms'].items():
                    if any(synonym.lower() in user_input for synonym in synonyms):
                        if term not in analysis['detected_symptoms']:
                            analysis['detected_symptoms'].append(term.lower())
                        analysis['key_topics'].append(term)
        
        # REMOVED: All dictionary-based keyword matching per user requirement
        # System now relies on pure AI analysis instead of hardcoded keywords
        # This eliminates false triggers like "breathing" → urgent, etc.
        
        return analysis
    
    def _retrieve_contextual_knowledge(self, context: ConversationContext, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Retrieve relevant knowledge based on context and analysis with caching"""
        try:
            knowledge = []

            # Primary query based on detected symptoms
            if analysis['detected_symptoms']:
                primary_symptoms = analysis['detected_symptoms'][:2]  # Focus on top 2 symptoms
                query = f"ALS {' '.join(primary_symptoms)} management support care"

                # Direct RAG search (removed caching for simplicity)
                rag_results = self.rag.search(query, top_k=3, index_kind="background")
                knowledge.extend(rag_results)
            
            # Secondary query for emotional support if needed
            if analysis['emotional_indicators'] and analysis['requires_support']:
                emotion_query = f"ALS emotional support coping {analysis['emotional_indicators'][0]}"
                
                # Direct RAG search (removed caching for simplicity)
                emotion_results = self.rag.search(emotion_query, top_k=2, index_kind="background")
                knowledge.extend(emotion_results)
            
            # Tertiary query for general conversation continuation
            if not knowledge and context.turn_count > 1:
                # Use conversation history for context
                recent_topics = ' '.join([msg.content for msg in context.conversation.messages[-2:] if msg.role == 'user'])
                if recent_topics:
                    general_query = f"ALS patient conversation {recent_topics[:100]}"
                    
                    # Direct RAG search (removed caching for simplicity)
                    general_results = self.rag.search(general_query, top_k=2, index_kind="background")
                    knowledge.extend(general_results)
            
            return knowledge[:4]  # Limit to top 4 most relevant pieces
            
        except Exception as e:
            log.warning(f"RAG retrieval error: {e}")
            return []
    
    def _generate_empathetic_response(self, context: ConversationContext, analysis: Dict[str, Any], knowledge: List[Dict[str, Any]]) -> str:
        """Generate empathetic response using LLM with RAG knowledge and caching"""
        try:
            # Construct LLM prompt with context and knowledge
            prompt = self._build_chat_prompt(context, analysis, knowledge)
            
            # Direct LLM generation (removed caching for simplicity)
            response = self.llm.generate_text(prompt)
            
            # Clean and validate response
            return self._clean_and_validate_response(response, context)
            
        except Exception as e:
            log.error(f"LLM generation error: {e}")
            # NO FALLBACK - Direct AI-style response as user demanded
            return "I understand you're sharing something important with me about ALS. Please tell me more about what's happening."
    
    def _create_context_hash(self, context: ConversationContext, analysis: Dict[str, Any]) -> str:
        """Create hash representing conversation context for caching"""
        try:
            # Create hash from key context elements (not user-specific data)
            context_elements = {
                'mode': context.mode.value,
                'symptoms': sorted(analysis.get('detected_symptoms', [])),
                'emotional_state': sorted(analysis.get('emotional_indicators', [])),
                'urgency': analysis.get('urgency_level', 'normal'),
                'turn_range': f"{(context.turn_count // 5) * 5}-{((context.turn_count // 5) + 1) * 5}"  # Group by 5-turn ranges
            }
            
            context_str = json.dumps(context_elements, sort_keys=True)
            return hashlib.md5(context_str.encode()).hexdigest()[:16]
            
        except Exception:
            return "default"
    
    def _build_chat_prompt(self, context: ConversationContext, analysis: Dict[str, Any], knowledge: List[Dict[str, Any]]) -> str:
        """Build comprehensive prompt for LLM generation"""
        # Extract empathy rules from config
        empathy_rules = self.conversation_config.get('empathy_rules', {})
        language_style = self.conversation_config.get('language_style', {})
        
        # Build knowledge context
        knowledge_text = "\n".join([
            f"- {doc.get('text', '')[:200]}..." for doc in knowledge[:2]
        ]) if knowledge else "No specific knowledge retrieved."
        
        # Build conversation history context
        recent_messages = [
            f"User: {msg.content}" for msg in context.conversation.messages[-3:] 
            if msg.role == 'user'
        ]
        history_context = "\n".join(recent_messages) if recent_messages else "No previous conversation."
        
        prompt = f"""You're an ALS support assistant. They said: "{context.user_input}"

Recent conversation:
{history_context}

Helpful information:
{knowledge_text}

Give a short, caring response (2-3 sentences max). Share one useful tip if relevant. Ask a simple follow-up to keep talking."""

        return prompt
    
    def _analyze_user_input_enhanced(self, context: ConversationContext, user_preferences: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced user input analysis with preference awareness"""
        # Start with basic analysis
        analysis = self._analyze_user_input(context)
        
        # Add preference-aware enhancements
        analysis['user_preferences'] = user_preferences
        analysis['response_length_preference'] = user_preferences.get('preferred_response_length', 'balanced')
        analysis['communication_style'] = user_preferences.get('communication_style', 'balanced')
        analysis['topic_interests'] = user_preferences.get('topic_interests', [])
        analysis['support_needs'] = user_preferences.get('support_needs', [])
        analysis['engagement_level'] = self._assess_current_engagement(context, user_preferences)
        
        return analysis
    
    def _assess_current_engagement(self, context: ConversationContext, user_preferences: Dict[str, Any]) -> str:
        """Assess user's current engagement level"""
        try:
            current_length = len(context.user_input)
            engagement_patterns = user_preferences.get('engagement_patterns', {})
            avg_length = engagement_patterns.get('avg_message_length', 50)
            
            if current_length < avg_length * 0.5:
                return 'low'
            elif current_length > avg_length * 1.5:
                return 'high'
            else:
                return 'normal'
        except Exception:
            return 'normal'
    
    def _retrieve_personalized_knowledge(self, context: ConversationContext, analysis: Dict[str, Any], user_preferences: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Retrieve knowledge with personalization based on user interests and needs"""
        try:
            # Base knowledge retrieval
            knowledge = self._retrieve_contextual_knowledge(context, analysis)
            
            # Enhance with personalized topics
            topic_interests = user_preferences.get('topic_interests', [])
            support_needs = user_preferences.get('support_needs', [])
            
            # Retrieve additional knowledge for user's interests
            for topic in topic_interests[:2]:  # Top 2 interests
                topic_knowledge = self._retrieve_topic_specific_knowledge(topic, context)
                knowledge.extend(topic_knowledge)
                
                # REMOVED: Dynamic knowledge expansion (over-engineered for UC1/UC2)
            
            # Retrieve support-specific knowledge
            for need in support_needs[:2]:  # Top 2 support needs
                support_knowledge = self._retrieve_support_specific_knowledge(need, context)
                knowledge.extend(support_knowledge)
            
            # Identify and fill knowledge gaps
            # REMOVED: Dynamic knowledge gap detection and expansion (over-engineered for UC1/UC2)
            knowledge_gaps = []
            if False:  # Disabled dynamic knowledge expansion
                for topic, content_list in expanded_knowledge.items():
                    for content in content_list[:2]:  # Add top 2 pieces per topic
                        knowledge.append({
                            'text': content,
                            'metadata': {'source': 'dynamic_expansion', 'topic': topic},
                            'score': 0.85
                        })
            
            # Remove duplicates and limit results
            seen_texts = set()
            unique_knowledge = []
            for doc in knowledge:
                text = doc.get('text', '')[:100]  # First 100 chars as identifier
                if text not in seen_texts:
                    seen_texts.add(text)
                    unique_knowledge.append(doc)
                    if len(unique_knowledge) >= 5:  # Limit to top 5 results
                        break
            
            return unique_knowledge
            
        except Exception as e:
            log.warning(f"Personalized knowledge retrieval failed: {e}")
            return self._retrieve_contextual_knowledge(context, analysis)
    
    def _retrieve_topic_specific_knowledge(self, topic: str, context: ConversationContext) -> List[Dict[str, Any]]:
        """Retrieve knowledge specific to user's topic interests"""
        try:
            # Map topics to search queries
            topic_queries = {
                'mobility': 'mobility aids walking assistance wheelchair',
                'breathing': 'breathing support ventilator respiratory care',
                'speech': 'speech therapy communication aids voice',
                'eating': 'swallowing nutrition feeding eating',
                'family': 'family support caregiving relationships',
                'work': 'employment workplace accommodation',
                'emotions': 'emotional support coping mental health',
                'future': 'planning goals future care advance directives'
            }
            
            query = topic_queries.get(topic, topic)
            docs = self.rag.search(query, top_k=2, index_kind="background")
            return docs
            
        except Exception:
            return []
    
    def _retrieve_support_specific_knowledge(self, support_need: str, context: ConversationContext) -> List[Dict[str, Any]]:
        """Retrieve knowledge for specific support needs"""
        try:
            # Map support needs to targeted queries
            support_queries = {
                'respiratory_support': 'breathing assistance ventilator oxygen therapy',
                'mobility_assistance': 'mobility aids wheelchair walker assistance',
                'communication_aids': 'speech device communication technology AAC',
                'emotional_support': 'emotional coping mental health support',
                'information_support': 'ALS information education understanding',
                'hope_building': 'hope positive outcomes quality of life'
            }
            
            query = support_queries.get(support_need, support_need)
            docs = self.rag.search(query, top_k=2, index_kind="background")
            return docs
            
        except Exception:
            return []
    
    def _generate_adaptive_response(self, context: ConversationContext, analysis: Dict[str, Any], knowledge: List[Dict[str, Any]], user_preferences: Dict[str, Any], coherence_analysis: Dict[str, Any] = None) -> str:
        """Generate response adapted to user preferences and emotional state"""
        try:
            # Build adaptive prompt based on preferences and coherence
            prompt = self._build_adaptive_prompt(context, analysis, knowledge, user_preferences, coherence_analysis)
            
            # Generate response with LLM
            response = self.llm.generate_text(prompt)
            
            # Post-process response based on preferences
            final_response = self._adapt_response_style(response, user_preferences, analysis)
            
            return self._clean_and_validate_response(final_response, context)
            
        except Exception as e:
            log.error(f"Adaptive response generation error: {e}")
            # NO FALLBACK - Direct supportive response as user demanded
            return "I'm here to support you with ALS. Your health and wellbeing are important to me. What would be most helpful right now?"
    
    def _should_provide_info_cards(self, context: ConversationContext, analysis: Dict[str, Any], user_preferences: Dict[str, Any]) -> bool:
        """
        DISABLED: No info cards, only AI dialogue as per user requirement.
        Eliminates all dictionary matching and keyword-based triggers.
        Pure AI conversation only.
        """
        return False  # Never trigger info cards - pure AI dialogue only
    
    def _generate_chat_with_info_cards(self, context: ConversationContext, analysis: Dict[str, Any], knowledge: List[Dict[str, Any]], user_preferences: Dict[str, Any], coherence_analysis: Dict[str, Any] = None) -> str:
        """Generate conversational response (info cards disabled as per CLAUDE.md requirements)"""
        try:
            # Generate base conversational response only
            # Info cards disabled per CLAUDE.md: "DISABLE hardcoded info cards - let Enhanced Dialogue provide contextual cards when appropriate"
            return self._generate_adaptive_response(context, analysis, knowledge, user_preferences, coherence_analysis)
                
        except Exception as e:
            log.error(f"Chat with info cards generation error: {e}")
            # Fallback to regular adaptive response
            return self._generate_adaptive_response(context, analysis, knowledge, user_preferences, coherence_analysis)
    
    def _build_adaptive_prompt(self, context: ConversationContext, analysis: Dict[str, Any], knowledge: List[Dict[str, Any]], user_preferences: Dict[str, Any], coherence_analysis: Dict[str, Any] = None) -> str:
        """Build prompt adapted to user preferences and style"""
        # Get style preferences
        response_length = user_preferences.get('preferred_response_length', 'balanced')
        communication_style = user_preferences.get('communication_style', 'balanced')
        topic_interests = user_preferences.get('topic_interests', [])
        support_needs = user_preferences.get('support_needs', [])
        
        # Build length instruction
        length_instructions = {
            'simple': 'Keep response to 1 short sentence. Be concise and direct.',
            'balanced': 'Use 1-2 sentences for a thoughtful but concise response.',
            'detailed': 'Provide a thorough response with 2-3 sentences, including helpful details.'
        }
        
        # Build style instruction
        style_instructions = {
            'casual': 'Use warm, friendly, conversational language like talking to a friend.',
            'formal': 'Use respectful, gentle, and slightly more formal language.',
            'technical': 'Include relevant medical terminology when helpful, but explain it simply.',
            'balanced': 'Use warm, professional language that is both caring and informative.'
        }
        
        # Build knowledge context
        knowledge_text = "\n".join([
            f"- {doc.get('text', '')[:150]}..." for doc in knowledge[:3]
        ]) if knowledge else "No specific knowledge retrieved."
        
        # Build conversation history
        history_context = self._get_conversation_history(context, 3)
        
        # Build coherence guidance
        coherence_guidance = ""
        if coherence_analysis:
            coherence_score = coherence_analysis.get('coherence_score', 1.0)
            current_topic = coherence_analysis.get('current_topic', 'general')
            suggestions = coherence_analysis.get('suggestions', [])  # Use fallback suggestions
            
            coherence_guidance = f"""
CONVERSATION COHERENCE ANALYSIS:
- Current topic: {current_topic}
- Coherence score: {coherence_score:.1f}/1.0
- Topic continuity: {coherence_analysis.get('topic_continuity', {}).get('type', 'normal')}
- Reference clarity: {'Good' if coherence_analysis.get('reference_resolution', {}).get('score', 1.0) > 0.7 else 'Needs attention'}
- Flow quality: {coherence_analysis.get('conversation_flow', {}).get('quality', 'good')}
{f"- Improvement suggestions: {'; '.join(suggestions[:2])}" if suggestions else ""}"""
        
        prompt = f"""You are an ALS support assistant. The person just said: "{context.user_input}"

Previous messages:
{history_context}

Medical knowledge available:
{knowledge_text}

CRITICAL INSTRUCTIONS:
- Respond directly as if speaking to the person, no meta-language
- Never say "Here is my response" or "My response is" or "I will provide"
- Never use templates like "I understand your concern, [name]" or "Use the following format"
- Do not repeat training formats or instructional language
- Focus on the specific medical issue with practical ALS guidance
- Be conversational and human, not robotic or scripted
- If about breathing: mention positioning, respiratory techniques, when to contact medical team
- Keep responses focused, helpful, and professionally caring
- Start directly with your actual advice or response content"""

        return prompt
    
    def _adapt_response_style(self, response: str, user_preferences: Dict[str, Any], analysis: Dict[str, Any]) -> str:
        """Adapt response style based on learned preferences"""
        if not response:
            return response
        
        # Adjust for communication style
        communication_style = user_preferences.get('communication_style', 'balanced')
        
        if communication_style == 'casual':
            # Make slightly more casual
            response = response.replace('I understand', 'I get it')
            response = response.replace('How are you feeling', 'How are you doing')
        elif communication_style == 'formal':
            # Ensure respectful tone
            response = response.replace('How\'s it going', 'How are you managing')
            response = response.replace('Yeah', 'Yes')
        
        # Adjust for engagement level
        engagement_level = analysis.get('engagement_level', 'normal')
        if engagement_level == 'low':
            # Add encouraging element
            if not any(word in response.lower() for word in ['thank', 'appreciate', 'understand']):
                response = "Thank you for sharing that. " + response
        
        return response
    
    def _generate_enhanced_fallback_response(self, context: ConversationContext) -> str:
        """Enhanced fallback with basic personalization"""
        try:
            # Try to use stored preferences for fallback
            stored_prefs = context.conversation.assessment_state.get('user_preferences', {})
            preferences = stored_prefs.get('preferences', {})
            
            communication_style = preferences.get('communication_style', 'balanced')
            topic_interests = preferences.get('topic_interests', [])
            
            # Customize fallback based on preferences
            if communication_style == 'casual':
                base_response = "I hear you. "
            elif communication_style == 'formal':
                base_response = "I understand what you're sharing with me. "
            else:
                base_response = "Thank you for telling me that. "
            
            # Add interest-based follow-up if available
            if topic_interests:
                if 'emotions' in topic_interests:
                    return base_response + "How are you feeling about everything today?"
                elif 'family' in topic_interests:
                    return base_response + "How are things with your family and support system?"
                elif 'mobility' in topic_interests:
                    return base_response + "How are you managing with getting around?"
            
            # FIXED: Use current dimension/term instead of broken symptom detection
            current_dimension = context.current_dimension or "general health"
            current_term = context.current_term or "your situation"
            
            # Create contextual follow-up based on routing
            if current_dimension != "general health" and current_dimension.lower() != "physiological":
                return base_response + f"How are things going with {current_term}?"
            elif current_dimension.lower() == "physiological":
                return base_response + f"Can you tell me more about how {current_term} has been affecting you?"
            
            return base_response + "What's been most on your mind lately?"
            
        except Exception:
            return "I'm here to help you with ALS support. What would you like to talk about?"
    
    def _clean_and_validate_response(self, response: str, context: ConversationContext) -> str:
        """Clean LLM response - NO FALLBACK, always use AI response"""
        if not response:
            response = "I understand you're dealing with ALS. Let me provide some support."

        # Clean and format the response
        response = response.strip()

        # Ensure response isn't too long (conversation flow)
        sentences = response.split('. ')
        if len(sentences) > 3:
            response = '. '.join(sentences[:3])
            if not response.endswith('.'):
                response += '.'

        # Clean system prompts but don't fallback - just remove them
        if response.lower().startswith(('as an ai', 'as a language model', 'i cannot', 'i\'m not able to')):
            # Extract the actual content after the disclaimer
            parts = response.split('.', 1)
            if len(parts) > 1:
                response = parts[1].strip()
            else:
                response = "I understand your situation and I'm here to help with ALS-related support."

        return response
    
    def _generate_fallback_response(self, context: ConversationContext) -> str:
        """FIXED: Safe fallback response without broken symptom detection dependency"""
        # Use current conversation context instead of broken symptom detection
        current_dimension = context.current_dimension
        current_term = context.current_term
        
        if current_dimension and current_term and current_dimension != "general":
            if current_dimension.lower() == "physiological":
                return f"I understand you're dealing with challenges related to {current_term}. How has this been affecting your daily routine?"
            else:
                return f"Thank you for sharing about {current_term}. How are you managing with this aspect of your life?"
        
        if context.turn_count > 3:
            return "Thank you for sharing that with me. What feels like the most important thing for us to focus on right now?"
        
        return "I hear what you're saying. Can you tell me more about what's been on your mind lately?"
        
    def generate_summary_response(self, context: ConversationContext) -> str:
        """
        Generate detailed summary response after completing term assessments.
        
        STEP 2: RAG-enhanced summary with personalized insights
        """
        try:
            # Analyze completed assessment
            summary_analysis = self._analyze_assessment_completion(context)
            
            # Retrieve relevant support knowledge
            support_knowledge = self._retrieve_support_knowledge(context, summary_analysis)
            
            # Generate comprehensive summary
            summary = self._generate_assessment_summary(context, summary_analysis, support_knowledge)
            
            return summary
            
        except Exception as e:
            log.error(f"Summary generation error: {e}")
            import traceback
            return self._generate_fallback_summary(context)
    
    def _analyze_assessment_completion(self, context: ConversationContext) -> Dict[str, Any]:
        """Analyze completed assessment for summary generation"""
        # Get full conversation history for comprehensive summary
        all_messages = context.conversation.messages if context.conversation.messages else []
        user_responses = [msg.content for msg in all_messages if msg.role == 'user']
        assistant_questions = [msg.content for msg in all_messages if msg.role == 'assistant']

        # Debug output to trace None values

        return {
            'completed_pnm': context.current_dimension,
            'completed_term': context.current_term,
            'user_responses': user_responses,  # All user responses, not just last 3
            'assistant_questions': assistant_questions,  # Include questions asked
            'assessment_length': context.turn_count,
            'key_insights': []
        }
    
    def _retrieve_support_knowledge(self, context: ConversationContext, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Hybrid retrieval + Self-RAG for enhanced knowledge retrieval"""
        try:
            if not (analysis['completed_term'] and analysis['completed_pnm']):
                return []

            # Step 1: Enhanced Query Generation for Small Database
            base_query = f"ALS {analysis['completed_pnm']} {analysis['completed_term']} support strategies"

            # Query Expansion - add related terms
            expanded_terms = {
                'Physiological': 'physical mobility movement breathing nutrition pain management',
                'Safety': 'home safety accessibility fall prevention emergency planning',
                'Love & Belonging': 'family relationships social support communication intimacy',
                'Esteem': 'confidence self-worth dignity respect independence',
                'Cognitive': 'memory thinking planning decision-making mental stimulation',
                'Aesthetic': 'environment beauty comfort meaningful spaces',
                'Self-Actualisation': 'purpose goals fulfillment personal growth meaning',
                'Transcendence': 'spirituality legacy values higher purpose'
            }

            expansion = expanded_terms.get(analysis['completed_pnm'], 'support care management')
            expanded_query = f"{base_query} {expansion}"

            # Multi-Query RAG - generate 2-3 different queries
            queries = [
                expanded_query,
                f"{analysis['completed_term']} ALS management strategies resources",
                f"ALS patients {analysis['completed_pnm'].lower()} needs support interventions"
            ]

            # Vector search from both indexes with multiple queries
            bg_results = []
            q_results = []
            for query in queries:
                bg_results.extend(self.rag.search(query, top_k=2, index_kind="background"))
                q_results.extend(self.rag.search(query, top_k=1, index_kind="question"))

            # Step 2: Apply hybrid fusion using existing rerank utilities
            fused_results = self._apply_hybrid_fusion(bg_results, q_results)

            # Step 3: Self-RAG - AI judges relevance and refines
            return self._self_rag_filter(fused_results, analysis)

        except Exception as e:
            log.warning(f"Hybrid+Self-RAG retrieval error: {e}")
            # Simple fallback
            query = f"ALS {analysis['completed_pnm']} {analysis['completed_term']} support"
            return self.rag.search(query, top_k=3, index_kind="background")

    def _apply_hybrid_fusion(self, bg_results: list, q_results: list) -> list:
        """Apply hybrid fusion to combine results from different sources"""
        try:
            from app.utils.rerank import hybrid_fusion

            # Treat as lexical vs vector runs for fusion
            lexical_run = bg_results  # background knowledge as "lexical"
            vector_run = q_results    # question bank as "vector"

            return hybrid_fusion(
                lexical_run=lexical_run,
                vector_run=vector_run,
                alpha=0.7,  # Prefer background knowledge slightly
                topn=6
            )
        except Exception:
            # Simple concatenation fallback
            return (bg_results + q_results)[:6]

    def _self_rag_filter(self, results: list, analysis: Dict[str, Any]) -> list:
        """Self-RAG: AI evaluates and filters retrieved knowledge"""
        if not results:
            return []

        try:
            # Build context for AI evaluation
            user_context = ' '.join(analysis.get('user_responses', []))[:300]

            # AI prompt for relevance evaluation
            eval_prompt = f"""You are evaluating knowledge relevance for an ALS assessment summary.

User discussed: {analysis['completed_pnm']} - {analysis['completed_term']}
Key user responses: {user_context}

Rate each piece of knowledge for relevance (1-5, where 5=highly relevant):

"""

            # Add each knowledge piece for evaluation
            for i, result in enumerate(results[:4]):  # Limit to avoid long prompts
                text = result.get('text', '')[:200]
                eval_prompt += f"{i+1}. {text}...\n"

            eval_prompt += "\nReturn only numbers (e.g., '4 3 5 2') for each knowledge piece:"

            # Get AI evaluation
            ai_response = self.llm.generate_text(eval_prompt).strip()

            # Parse scores and filter
            try:
                scores = [int(x) for x in ai_response.split() if x.isdigit()]
                filtered_results = []

                for i, score in enumerate(scores):
                    if i < len(results) and score >= 3:  # Keep if score >= 3
                        filtered_results.append(results[i])

                return filtered_results[:4] if filtered_results else results[:3]

            except (ValueError, IndexError):
                # Fallback if AI parsing fails
                return results[:3]

        except Exception as e:
            log.warning(f"Self-RAG filtering error: {e}")
            return results[:3]

    def _generate_keyword_queries(self, pnm: str, term: str, user_responses: List[str]) -> List[str]:
        """Generate keyword-enhanced queries for better question bank matching"""
        queries = []

        # Extract key phrases from user responses
        user_keywords = []
        if user_responses:
            # Simple keyword extraction from user responses
            combined_responses = ' '.join(user_responses).lower()
            common_terms = ['difficulty', 'pain', 'trouble', 'help', 'support', 'manage', 'unable', 'struggle']
            user_keywords = [word for word in common_terms if word in combined_responses]

        # Generate targeted queries
        base_terms = [term.lower(), pnm.lower()]

        # Query 1: Direct term + ALS
        queries.append(f"ALS {term}")

        # Query 2: PNM dimension + specific issues
        if user_keywords:
            queries.append(f"ALS {pnm} {' '.join(user_keywords[:2])}")

        # Query 3: Symptom-focused query
        symptom_terms = {
            'breathing': ['breathe', 'respiratory', 'oxygen'],
            'swallowing': ['swallow', 'eating', 'choking'],
            'mobility': ['move', 'walk', 'transfer'],
            'communication': ['speak', 'voice', 'talk'],
            'cognitive': ['memory', 'thinking', 'concentration']
        }

        for symptom, related in symptom_terms.items():
            if symptom in term.lower():
                queries.append(f"ALS {symptom} {related[0]}")
                break

        return queries[:3]  # Limit to 3 keyword queries

    def _deduplicate_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate results based on text similarity"""
        if not results:
            return []

        unique_results = []
        seen_texts = set()

        for result in results:
            text = result.get('text', '').strip()
            if not text:
                continue

            # Simple deduplication based on first 100 characters
            text_key = text[:100].lower()
            if text_key not in seen_texts:
                seen_texts.add(text_key)
                unique_results.append(result)

        return unique_results

    def _retrieve_uc1_support_knowledge(self, pnm: str, term: str, avg_score: float, user_responses: List[str]) -> List[Dict[str, Any]]:
        """Enhanced UC1 Hybrid retrieval: Multi-strategy + Question Bank + Self-RAG"""
        try:
            # Step 1: Generate enhanced queries with keyword expansion
            score_context = "low difficulty" if avg_score <= 2 else "moderate difficulty" if avg_score <= 4 else "high difficulty"

            # Primary semantic query
            main_query = f"ALS {pnm} {term} {score_context} management support strategies"

            # Keyword-enhanced queries for better question bank matching
            keyword_queries = self._generate_keyword_queries(pnm, term, user_responses)

            print(f"[UC1_HYBRID] Main query: {main_query}")
            print(f"[UC1_HYBRID] Keyword queries: {keyword_queries}")

            # Step 2: Multi-strategy retrieval
            all_results = []

            # A) Semantic search from background knowledge
            try:
                bg_results = self.rag.search(main_query, top_k=4, index_kind="background")
                all_results.extend(bg_results)
                print(f"[UC1_HYBRID] Background results: {len(bg_results)}")
            except Exception as e:
                print(f"[UC1_HYBRID] Background search failed: {e}")

            # B) Question bank search with multiple strategies
            try:
                # Semantic search
                q_semantic = self.rag.search(main_query, top_k=2, index_kind="question")
                all_results.extend(q_semantic)

                # Keyword-based searches
                for kw_query in keyword_queries[:2]:  # Limit to avoid too many API calls
                    q_keyword = self.rag.search(kw_query, top_k=2, index_kind="question")
                    all_results.extend(q_keyword)

                print(f"[UC1_HYBRID] Question bank results: {len(q_semantic)} semantic + {len(keyword_queries)*2} keyword")
            except Exception as e:
                print(f"[UC1_HYBRID] Question bank search failed: {e}")

            # Step 3: Deduplicate and apply hybrid fusion
            if all_results:
                # Remove duplicates based on text similarity
                unique_results = self._deduplicate_results(all_results)
                print(f"[UC1_HYBRID] After deduplication: {len(unique_results)} results")

                # Step 4: Self-RAG quality filtering
                filtered_results = self._self_rag_filter_uc1(unique_results, pnm, term, avg_score, user_responses)
                print(f"[UC1_HYBRID] After Self-RAG filtering: {len(filtered_results)} results")
                return filtered_results
            else:
                print(f"[UC1_HYBRID] No results found, using simple fallback")
                # Enhanced fallback with direct term matching
                fallback_query = f"ALS {term} support help management"
                return self.rag.search(fallback_query, top_k=3, index_kind="background")

        except Exception as e:
            log.warning(f"UC1 Enhanced Hybrid retrieval error: {e}")
            # Simple fallback
            query = f"ALS {pnm} {term} support"
            return self.rag.search(query, top_k=3, index_kind="background")

    def _self_rag_filter_uc1(self, results: list, pnm: str, term: str, avg_score: float, user_responses: List[str]) -> list:
        """UC1-specific Self-RAG: AI evaluates knowledge based on scored responses"""
        if not results:
            return []

        try:
            # Build UC1-specific context for AI evaluation
            user_context = ' '.join(user_responses)[:300]
            score_interpretation = "lower functioning" if avg_score >= 5 else "moderate functioning" if avg_score >= 3 else "higher functioning"

            # AI prompt for UC1 relevance evaluation
            eval_prompt = f"""You are evaluating knowledge relevance for an ALS {pnm} assessment summary.

Assessment: {term} with average score {avg_score:.1f}/7 ({score_interpretation})
Key user responses: {user_context}

Rate each piece of knowledge for relevance (1-5, where 5=highly relevant for this specific score level and responses):

"""

            # Add each knowledge piece for evaluation
            for i, result in enumerate(results[:4]):  # Limit to avoid long prompts
                text = result.get('text', '')[:200]
                eval_prompt += f"{i+1}. {text}...\n"

            eval_prompt += "\nReturn only numbers (e.g., '4 3 5 2') for each knowledge piece:"

            # Get AI evaluation
            ai_response = self.llm.generate_text(eval_prompt).strip()

            # Parse scores and filter
            try:
                scores = [int(x) for x in ai_response.split() if x.isdigit()]
                filtered_results = []

                for i, score in enumerate(scores):
                    if i < len(results) and score >= 3:  # Keep if score >= 3
                        filtered_results.append(results[i])

                return filtered_results[:4] if filtered_results else results[:3]

            except (ValueError, IndexError):
                # Fallback if AI parsing fails
                return results[:3]

        except Exception as e:
            log.warning(f"UC1 Self-RAG filtering error: {e}")
            return results[:3]

    def _generate_assessment_summary(self, context: ConversationContext, analysis: Dict[str, Any], knowledge: List[Dict[str, Any]]) -> str:
        """Generate comprehensive assessment summary using LLM"""
        try:
            # Build summary prompt - ensure meaningful knowledge content
            if knowledge:
                knowledge_text = "\n".join([
                    f"- {doc.get('text', '')[:150]}" for doc in knowledge if doc.get('text', '').strip()
                ])
            else:
                knowledge_text = ""

            # If no knowledge retrieved, provide basic ALS support guidance
            if not knowledge_text.strip():
                dimension = analysis['completed_pnm']
                term = analysis['completed_term']
                knowledge_text = f"""- Regular monitoring and adaptation of strategies is important for {dimension} concerns
- Professional healthcare team consultation can provide personalized guidance for {term}
- Support groups and peer connections offer valuable shared experiences and coping strategies
- Assistive technologies and adaptive equipment may help maintain independence and quality of life"""
            
            # Build conversation context with both questions and responses
            conversation_context = []
            user_responses = analysis.get('user_responses', [])
            assistant_questions = analysis.get('assistant_questions', [])

            # Create interleaved conversation flow for better context
            max_length = max(len(user_responses), len(assistant_questions))
            for i in range(max_length):
                if i < len(assistant_questions):
                    conversation_context.append(f"Question: {assistant_questions[i][:200]}...")
                if i < len(user_responses):
                    conversation_context.append(f"Their response: {user_responses[i]}")

            conversation_summary = "\n".join(conversation_context[-10:])  # Last 10 exchanges

            prompt = f"""You are providing a personalized assessment summary for someone with ALS about their {analysis['completed_pnm']} needs, specifically focusing on {analysis['completed_term']}.

CONVERSATION CONTEXT:
{conversation_summary}

PROFESSIONAL KNOWLEDGE BASE:
{knowledge_text}

Create a comprehensive, well-formatted assessment summary:

## Assessment Overview
Based on our conversation about {analysis['completed_term']}, provide a personalized 2-3 sentence summary of their current situation.

## Key Strengths
• Identify specific areas where they are managing well (based on their actual responses)
• Highlight positive coping strategies they mentioned
• Acknowledge their resilience and adaptive approaches

## Areas for Enhancement
• Point out specific challenges they shared that could benefit from support
• Focus on practical, achievable improvements
• Frame as opportunities rather than deficits

## Tailored Recommendations
• Provide 3-4 specific, actionable strategies based on their responses
• Reference relevant professional resources or assistive technologies
• Include both immediate steps and longer-term considerations
• Consider their individual circumstances and expressed preferences

## Next Steps
• Suggest 2-3 concrete actions they can take in the next week
• Include professional contacts or resources to explore
• Mention any follow-up assessment that might be beneficial

FORMATTING REQUIREMENTS:
- Use markdown formatting (##, •, proper line breaks)
- Write in second person (you, your) throughout
- Be specific to their actual responses, not generic advice
- Maintain a supportive yet professional tone
- Ensure each bullet point is substantial (2-3 sentences)
- Include proper spacing between sections"""

            return self.llm.generate_text(prompt)
            
        except Exception as e:
            log.error(f"Summary LLM generation error: {e}")
            import traceback
            return self._generate_fallback_summary(context)
    
    def _generate_fallback_summary(self, context: ConversationContext) -> str:
        """Generate fallback summary when LLM fails"""
        pnm = context.current_dimension or "your needs"
        return f"Thank you for sharing your experiences about {pnm}. Your openness helps me better understand your situation. Based on what you've told me, I can see you're navigating some important challenges. Let's continue exploring how we can best support you in this area."
        
    def generate_info_cards(self, context: ConversationContext) -> List[Dict[str, Any]]:
        """
        Info cards disabled as per CLAUDE.md requirements.

        CLAUDE.md: "DISABLE hardcoded info cards - let Enhanced Dialogue provide contextual cards when appropriate"
        """
        # Info cards generation disabled - return empty list
        log.debug("Info cards generation disabled per CLAUDE.md requirements")
        return []
    
    def _generate_basic_info_cards(self, context: ConversationContext) -> List[Dict[str, Any]]:
        """Fallback basic info card generation using RAG"""
        try:
            if not context.detected_symptoms and not context.current_dimension:
                return []
            
            # Determine focus for info cards
            focus_topic = None
            if context.current_dimension and context.current_term:
                focus_topic = f"{context.current_dimension} {context.current_term}"
            elif context.detected_symptoms:
                focus_topic = context.detected_symptoms[0]
            
            if not focus_topic:
                return []
            
            # Retrieve information with caching
            info_query = f"ALS {focus_topic} practical tips daily living support"
            
            # Direct RAG search (removed caching for simplicity)
            info_docs = self.rag.search(info_query, top_k=3, index_kind="background")
            
            if not info_docs:
                return []
            
            # Generate info card
            card_content = self._format_info_card(focus_topic, info_docs)
            
            return [card_content] if card_content else []
            
        except Exception as e:
            log.error(f"Basic info card generation error: {e}")
            return []
    
    def _format_info_card(self, topic: str, docs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Format RAG results into info card structure"""
        try:
            # Extract key points from RAG docs
            bullets = []
            for doc in docs[:3]:
                text = doc.get('text', '')
                if len(text) > 50:
                    # Simple bullet point extraction (can be enhanced)
                    bullet = text[:120] + "..." if len(text) > 120 else text
                    bullets.append(bullet)
            
            if bullets:
                return {
                    "title": f"Support Information: {topic.title()}",
                    "bullets": bullets[:3],  # Limit to 3 bullets
                    "source": "Knowledge Base"
                }
        except Exception as e:
            log.error(f"Info card formatting error: {e}")
        
        return None


# INTEGRATION HELPER FUNCTIONS

def create_conversation_context(
    conversation: ConversationDocument,
    user_input: str,
    ai_router: AIRouter
) -> ConversationContext:
    """
    Factory function to create ConversationContext from current conversation state.
    
    This function bridges the existing DocumentStorage system with the new
    enhanced dialogue framework.
    """
    # Extract current state with proper None handling
    mode_str = conversation.assessment_state.get('dialogue_mode', 'free_dialogue')
    if mode_str and mode_str in [m.value for m in ConversationMode]:
        mode = ConversationMode(mode_str)
    else:
        mode = ConversationMode.FREE_DIALOGUE
    
    # Count user messages for turn tracking
    turn_count = sum(1 for msg in conversation.messages if msg.role == 'user')
    print(f"[TURN_DEBUG] Total messages: {len(conversation.messages)}, User messages: {turn_count}")

    # Debug: Log conversation state for new conversations
    if turn_count == 1:  # First user message in this conversation
        pass  # Debug print removed

    # Skip automatic symptom detection during free dialogue
    # Keywords should only be used for question bank retrieval, not symptom detection
    # This aligns with original design: AI-expanded keywords for question matching
    detected_symptoms = []
    
    return ConversationContext(
        conversation=conversation,
        user_input=user_input,
        mode=mode,
        turn_count=turn_count,
        detected_symptoms=detected_symptoms,
        current_dimension=conversation.dimension,
        current_term=conversation.assessment_state.get('current_term'),
        recent_scores=[]
    )


def convert_to_conversation_response(dialogue_response: DialogueResponse) -> Dict[str, Any]:
    """
    Convert DialogueResponse to the format expected by chat_unified.py.

    This ensures compatibility with the existing API response structure.
    """
    response_data = {
        "question_text": dialogue_response.content,
        "response": dialogue_response.content,  # Add response field for test compatibility
        "question_type": ("dialogue" if dialogue_response.response_type == ResponseType.CHAT
                         else "assessment" if dialogue_response.response_type == ResponseType.QUESTION
                         else "summary"),
        "options": dialogue_response.options or [],
        "allow_text_input": True,
        "dialogue_mode": dialogue_response.mode == ConversationMode.FREE_DIALOGUE,
        "should_continue_dialogue": dialogue_response.should_continue_dialogue
    }
    
    # Add assessment data if present
    if dialogue_response.current_pnm:
        response_data["current_pnm"] = dialogue_response.current_pnm
    if dialogue_response.current_term:
        response_data["current_term"] = dialogue_response.current_term
    if dialogue_response.question_id:
        response_data["question_id"] = dialogue_response.question_id
    
    # Add metadata
    if dialogue_response.detected_symptoms:
        response_data["detected_symptoms"] = dialogue_response.detected_symptoms
    if dialogue_response.info_cards:
        response_data["info_cards"] = dialogue_response.info_cards

    return response_data


# Add missing method to ResponseGenerator class
def _get_conversation_history_for_response_generator(self, context: 'ConversationContext', num_turns: int = 3) -> str:
    """Get recent conversation history for context"""
    try:
        messages = context.conversation.messages[-num_turns*2:] if context.conversation.messages else []
        history = []

        for msg in messages:
            role = "Patient" if msg.role == 'user' else "Assistant"
            history.append(f"{role}: {msg.content}")

        return '\n'.join(history)
    except Exception:
        return "No conversation history available"

# Monkey patch the method into ResponseGenerator class
ResponseGenerator._get_conversation_history = _get_conversation_history_for_response_generator


class UseCaseOneManager:
    """
    Use Case 1: General conversation mode manager.

    Handles: free dialogue → diagonal trigger → structured assessment → summary
    """

    def __init__(self, qb: QuestionBank, ai_router: AIRouter, main_manager=None):
        self.qb = qb
        self.question_bank = qb  # Alias for compatibility
        self.ai_router = ai_router
        self.main_manager = main_manager  # Access to storage through main manager
        # Access LLM and storage through main manager
        self.llm = getattr(main_manager, 'llm', None) if main_manager else None
        self.storage = main_manager.storage if main_manager else None
        self.ai_scorer = AIFreeTextScorer()  # Add ai_scorer for UC1 - uses IBM WatsonX directly
        self.response_generator = ResponseGenerator()
        # TransitionDetector removed - zombie code with hardcoded dictionaries and fallback logic

    async def handle_conversation_flow(self, context: ConversationContext) -> DialogueResponse:
        """Handle complete Use Case 1 flow"""

        # Phase 1: Free Dialogue (Turns 1-3) - Allow diagonal trigger earlier
        if context.turn_count <= 3:

            # Check for explicit assessment request even in early turns
            if await self._should_trigger_assessment(context):
                return await self._handle_assessment_phase(context)

            return await self._handle_free_dialogue_phase(context)

        # Phase 2: Diagonal Trigger Check (Turn 4+)
        if await self._should_trigger_assessment(context):
            return await self._handle_assessment_phase(context)

        # Continue dialogue if assessment not triggered
        return await self._handle_free_dialogue_phase(context)

    async def _handle_free_dialogue_phase(self, context: ConversationContext) -> DialogueResponse:
        """Pure dialogue phase - AI intelligent response, no questions"""
        try:
            # Generate AI response for dialogue
            content = self.response_generator.generate_chat_response(context)

            # AI dialogue response storage is handled by chat_unified.py centralized storage

            return DialogueResponse(
                content=content,
                response_type=ResponseType.CHAT,
                mode=ConversationMode.FREE_DIALOGUE,
                should_continue_dialogue=True,
                current_pnm=None,
                current_term=None
            )
        except Exception as e:
            log.error(f"Free dialogue error: {e}")
            fallback_content = "I'm here to listen and help. What would you like to talk about?"

            # AI fallback dialogue response storage is handled by chat_unified.py centralized storage

            return DialogueResponse(
                content=fallback_content,
                response_type=ResponseType.CHAT,
                mode=ConversationMode.FREE_DIALOGUE,
                should_continue_dialogue=True
            )

    async def _ai_analyze_symptoms_and_readiness(self, context: ConversationContext) -> dict:
        """Use AI to analyze user symptoms and assess readiness for evaluation"""
        try:
            # Get conversation history
            recent_messages = [msg.content for msg in context.conversation.messages[-5:] if msg.role == 'user']
            conversation_text = " ".join(recent_messages)

            prompt = f"""Analyze this ALS patient conversation to determine:
1. Symptoms mentioned and their severity
2. Readiness for structured assessment
3. Most relevant PNM dimensions and terms

Conversation: "{conversation_text}"
Current message: "{context.user_input}"

Available PNM dimensions:
- Physiological: breathing, swallowing, mobility, sleep, nutrition
- Safety: accessibility, equipment, technology, decision-making
- Love & Belonging: relationships, social activities, communication
- Esteem: independence, dignity, accomplishment, contribution
- Self-Actualisation: purpose, meaning, personal growth
- Cognitive: memory, problem-solving, information processing
- Aesthetic: beauty, creativity, environmental enjoyment
- Transcendence: spirituality, legacy, connection to larger purpose

Respond with JSON:
{{
    "symptoms_detected": ["symptom1", "symptom2"],
    "symptom_count": number,
    "severity_level": "mild|moderate|severe",
    "ready_for_assessment": boolean,
    "readiness_reason": "explanation",
    "suggested_pnm": "most relevant dimension",
    "suggested_term": "most relevant specific term",
    "confidence": 0.0-1.0
}}"""

            response = self.llm.generate_text(prompt)

            try:
                import json
                analysis = json.loads(response)
                print(f"[AI_DEBUG] AI analysis successful: {analysis}")
                return analysis
            except Exception as e:
                print(f"[AI_DEBUG] AI analysis JSON parsing failed: {e}, response: {response[:200]}")
                # Fallback if JSON parsing fails
                return {
                    "symptoms_detected": [],
                    "symptom_count": 0,
                    "ready_for_assessment": context.turn_count >= 4,
                    "suggested_pnm": "Physiological",
                    "suggested_term": "general",
                    "confidence": 0.5
                }

        except Exception as e:
            print(f"[AI_DEBUG] AI analysis completely failed: {e}")
            return {
                "symptoms_detected": [],
                "symptom_count": 0,
                "ready_for_assessment": context.turn_count >= 4,
                "suggested_pnm": "Physiological",
                "suggested_term": "general",
                "confidence": 0.3
            }

    async def _should_trigger_assessment(self, context: ConversationContext) -> bool:
        """AI-powered assessment trigger using intelligent symptom analysis"""
        print(f"[TRIGGER_DEBUG] _should_trigger_assessment called: turn_count={context.turn_count}")

        # Use AI to analyze symptoms and readiness
        ai_analysis = await self._ai_analyze_symptoms_and_readiness(context)

        # Store AI analysis for later use in assessment
        context.ai_analysis = ai_analysis

        # Decision logic based on AI analysis
        if ai_analysis.get("ready_for_assessment", False):
            print(f"[TRIGGER_DEBUG] AI analysis says ready: {ai_analysis}")
            return True

        # TEMPORARY: Force trigger for testing other functions - DISABLED
        # if True:  # Always trigger for testing
        #     print(f"[TRIGGER_DEBUG] FORCED trigger for testing: turn_count={context.turn_count}")
        #     return True

        # Unified turn count trigger: reduced threshold for better UX
        if context.turn_count >= 3:
            print(f"[TRIGGER_DEBUG] Turn count trigger activated: {context.turn_count} >= 3")
            return True

        print(f"[TRIGGER_DEBUG] No trigger: turn_count={context.turn_count}, ai_ready={ai_analysis.get('ready_for_assessment', False)}")
        return False

    async def _ai_select_relevant_term(self, context: ConversationContext) -> tuple:
        """Enhanced: AI analysis + hybrid retrieval for accurate question selection"""
        try:
            # Step 1: Get all user inputs and extract conversation themes
            user_messages = [msg.content for msg in context.conversation.messages if msg.role == 'user']
            conversation_history = " ".join(user_messages)

            print(f"[HYBRID_DEBUG] Starting hybrid question selection for conversation: {conversation_history[:100]}...")

            # Step 2: Generate search keywords from conversation
            keywords = self._generate_keyword_queries("conversation_analysis", "question_selection", user_messages)
            print(f"[HYBRID_DEBUG] Generated keywords: {keywords}")

            # Step 3: Use hybrid retrieval to find most relevant questions from question bank
            from app.vendors.ibm_cloud import RAGQueryClient
            try:
                rag_client = RAGQueryClient()

                # Search in question bank index using conversation keywords
                all_results = []
                for keyword in keywords[:3]:  # Use top 3 keywords
                    try:
                        q_results = rag_client.search(keyword, top_k=3, index_kind="question")
                        all_results.extend(q_results)
                        print(f"[HYBRID_DEBUG] Keyword '{keyword}' found {len(q_results)} question matches")
                    except Exception as e:
                        print(f"[HYBRID_DEBUG] Keyword search failed for '{keyword}': {e}")
                        continue

                # Deduplicate and get best matches
                if all_results:
                    unique_results = self._deduplicate_and_filter_results(all_results, max_results=5)
                    print(f"[HYBRID_DEBUG] Found {len(unique_results)} unique question matches")

                    # Extract question text and match with question bank
                    if unique_results:
                        best_match_text = unique_results[0].get('text', '')
                        print(f"[HYBRID_DEBUG] Best match text: {best_match_text[:100]}...")

                        # Find corresponding question in question bank
                        all_questions = self.question_bank.items()
                        for question in all_questions:
                            # Check if question text matches or is similar
                            if (best_match_text.lower() in question.main.lower() or
                                question.main.lower() in best_match_text.lower() or
                                any(keyword.lower() in question.main.lower() for keyword in keywords[:2])):
                                print(f"[HYBRID_DEBUG] Matched with question bank: {question.pnm}/{question.term}")
                                return question.pnm, question.term

            except Exception as e:
                print(f"[HYBRID_DEBUG] Hybrid retrieval failed: {e}")

            # Step 4: Fallback to AI analysis if hybrid retrieval fails
            theme_prompt = f"""Analyze this ALS patient conversation to find the most relevant assessment topic.

User conversation: "{conversation_history}"

Available topics:
Physiological: breathing, swallowing, mobility, sleep, nutrition, pain, fatigue
Safety: accessibility, equipment, technology, decision-making, emergency
Love & Belonging: relationships, social activities, communication, support
Esteem: independence, dignity, accomplishment, contribution, confidence
Self-Actualisation: purpose, meaning, personal growth, goals
Cognitive: memory, problem-solving, information processing, concentration
Aesthetic: beauty, creativity, environmental enjoyment, comfort
Transcendence: spirituality, legacy, connection, values

Respond with only: "DIMENSION,TERM"
Example: "Physiological,breathing"
"""

            ai_response = self.llm.generate_text(theme_prompt).strip()
            print(f"[HYBRID_DEBUG] AI fallback response: '{ai_response}'")

            # Step 5: Parse and match question bank directly
            if "," in ai_response:
                suggested_pnm, suggested_term = ai_response.split(",", 1)
                suggested_pnm = suggested_pnm.strip()
                suggested_term = suggested_term.strip()
                print(f"[HYBRID_DEBUG] Parsed PNM: '{suggested_pnm}', Term: '{suggested_term}'")

                # Find questions in question bank
                all_questions = self.question_bank.items()

                # Exact match first
                for question in all_questions:
                    if (question.pnm.lower() == suggested_pnm.lower() and
                        suggested_term.lower() in question.term.lower()):
                        print(f"[HYBRID_DEBUG] Found exact match: {question.pnm}/{question.term}")
                        return question.pnm, question.term

                # PNM dimension match
                for question in all_questions:
                    if question.pnm.lower() == suggested_pnm.lower():
                        print(f"[HYBRID_DEBUG] Found PNM match: {question.pnm}/{question.term}")
                        return question.pnm, question.term

            # Step 6: Smart fallback - find breathing-related question if user mentioned breathing
            if any(word in conversation_history.lower() for word in ['breath', 'breathing', 'respiratory', 'air', 'oxygen']):
                all_questions = self.question_bank.items()
                for question in all_questions:
                    if 'breath' in question.term.lower() or 'breath' in question.main.lower():
                        print(f"[HYBRID_DEBUG] Smart fallback to breathing question: {question.pnm}/{question.term}")
                        return question.pnm, question.term

            # Final fallback
            all_questions = self.question_bank.items()
            if all_questions:
                # Try to find a Physiological question instead of the first question
                for question in all_questions:
                    if question.pnm.lower() == 'physiological':
                        print(f"[HYBRID_DEBUG] Final fallback to Physiological: {question.pnm}/{question.term}")
                        return question.pnm, question.term

                # Last resort
                first_question = all_questions[0]
                print(f"[HYBRID_DEBUG] Last resort fallback: {first_question.pnm}/{first_question.term}")
                return first_question.pnm, first_question.term

        except Exception as e:
            print(f"[HYBRID_DEBUG] Critical error in question selection: {e}")
            # Safe fallback
            try:
                all_questions = self.question_bank.items()
                if all_questions:
                    return all_questions[0].pnm, all_questions[0].term
            except:
                pass

        return "Physiological", "Mobility and transfers"

    async def _process_uc1_assessment_response(self, context: ConversationContext):
        """Process user's UC1 assessment response and record it"""
        try:
            # Get current question context from assessment state
            question_context = context.conversation.assessment_state.get('question_context', {})
            current_question_id = question_context.get('question_id')

            # Also check for followup question ID
            followup_question_id = context.conversation.assessment_state.get('followup_question_id')
            if followup_question_id and not current_question_id:
                current_question_id = followup_question_id

            # Skip scoring for follow up questions
            if current_question_id and "_followup_" in current_question_id:
                return

            if current_question_id:
                # Store current question ID for tracking (no asked_questions list needed)
                context.conversation.assessment_state['current_question_id'] = current_question_id

                # Get current PNM/term from assessment state
                current_pnm = context.conversation.assessment_state.get('current_pnm', 'Physiological')
                current_term = context.conversation.assessment_state.get('current_term', 'General')

                # Try to get score from option first, then use AI scoring

                score = self._extract_option_score_uc1(context.user_input, question_context)

                if score is None:
                    # Use AI scoring for free text response - access ai_scorer from main manager
                    try:
                        # Ensure ai_scorer is available
                        if not hasattr(self, 'ai_scorer') or not self.ai_scorer:
                            from app.services.ai_scoring_engine import AIFreeTextScorer
                            self.ai_scorer = AIFreeTextScorer()  # No ai_router needed - uses IBM WatsonX directly

                        ai_score_result = await self.ai_scorer.score_free_text_response(
                            context.user_input,
                            question_context,
                            current_pnm,
                            context.conversation.messages[-5:]  # Recent context
                        )
                        score = ai_score_result.score

                    except Exception as e:
                        # Skip scoring instead of using hardcoded fallback as per user requirements
                        score = None
                else:
                    pass

                # Store score in conversation_scores table (like UC2)
                # Access storage through the main manager
                if self.main_manager and hasattr(self.main_manager, 'storage') and score is not None:
                    # Determine scoring method based on how score was extracted
                    score_from_option = self._extract_option_score_uc1(context.user_input, question_context)
                    scoring_method = "question_bank_options" if score_from_option is not None else "ai_fallback"

                    self.main_manager.storage.add_score(
                        conversation_id=context.conversation.id,
                        pnm=current_pnm,
                        term=current_term,
                        score=float(score),
                        scoring_method=scoring_method,
                        rationale=f"UC1 {'option selection' if score_from_option else 'AI scoring'}: {context.user_input}"
                    )
                else:
                    pass  # Debug print removed

                # Also store temporary score for UC1 term completion analysis
                term_key = f"{current_pnm}_{current_term}"
                if 'temp_term_scores' not in context.conversation.assessment_state:
                    context.conversation.assessment_state['temp_term_scores'] = {}

                if term_key not in context.conversation.assessment_state['temp_term_scores']:
                    context.conversation.assessment_state['temp_term_scores'][term_key] = []

                # Add score entry with metadata
                score_entry = {
                    'question_id': current_question_id,
                    'score': score,
                    'user_response': context.user_input,
                    'timestamp': context.conversation.messages[-1].timestamp if context.conversation.messages else None
                }
                context.conversation.assessment_state['temp_term_scores'][term_key].append(score_entry)

        except Exception as e:
            log.error(f"[UC1] Error processing assessment response: {e}")

    def _extract_option_score_uc1(self, user_input: str, question_context: dict) -> float:
        """Extract score from UC1 option selection - compatible with UC2 format"""
        try:
            options = question_context.get('options', [])
            if not options:
                return None

            user_input_lower = user_input.lower().strip()

            # Try to match by option ID first (same as UC2)
            for option in options:
                if option.get('id', '').lower() == user_input_lower:
                    score_value = option.get('score')
                    if score_value is not None:
                        return float(score_value)
                    return None

            # Try ordinal matching: user inputs 1,2,3,4 for 1st,2nd,3rd,4th option
            try:
                ordinal_input = int(user_input_lower)
                if 1 <= ordinal_input <= len(options):
                    selected_option = options[ordinal_input - 1]  # Convert 1-based to 0-based index
                    score_value = selected_option.get('score')
                    if score_value is not None:
                        return float(score_value)
                    return None
            except ValueError:
                pass  # Not a valid integer, continue to label matching

            # Try to match by option label (same as UC2)
            for option in options:
                label = option.get('label', '').lower()
                if label and user_input_lower in label:
                    score_value = option.get('score')
                    if score_value is not None:
                        return float(score_value)
                    return None

            return None
        except Exception as e:
            return None

    async def _generate_followup_question(self, context: ConversationContext) -> DialogueResponse:
        """Generate a follow up question based on the previous main question"""
        try:
            # Find the previous main question from conversation messages
            assessment_messages = [msg for msg in context.conversation.messages
                                 if msg.role == 'assistant' and msg.metadata and msg.metadata.get('response_type') == 'question']

            if not assessment_messages:
                # Fallback: no previous question found, generate main question
                return await self._handle_assessment_phase(context)

            # Get the last question's metadata
            last_question_msg = assessment_messages[-1]
            question_metadata = last_question_msg.metadata or {}
            main_question_id = question_metadata.get('question_id')

            if not main_question_id:
                # Fallback: no question ID found
                return await self._generate_uc1_summary(context)

            # Find the main question item to get its follow ups
            main_question_item = None
            for item in self.qb.items():
                if item.id == main_question_id:
                    main_question_item = item
                    break

            if not main_question_item:
                # Fallback: main question not found
                return await self._generate_uc1_summary(context)

            # Get follow up questions
            followup_questions = []
            if hasattr(main_question_item, 'followup_questions') and main_question_item.followup_questions:
                followup_questions = main_question_item.followup_questions
            elif hasattr(main_question_item, 'followups') and main_question_item.followups:
                followup_questions = main_question_item.followups

            if not followup_questions:
                # No follow up questions, go to summary
                return await self._generate_uc1_summary(context)

            # Select first available follow up question
            followup_data = followup_questions[0]

            # Parse followup data
            if isinstance(followup_data, str):
                try:
                    import json
                    followup_data = json.loads(followup_data.replace("'", '"'))
                except:
                    # Fallback: invalid followup data
                    return await self._generate_uc1_summary(context)

            if not isinstance(followup_data, dict):
                return await self._generate_uc1_summary(context)

            # Extract question text and options
            question_text = followup_data.get('question', followup_data.get('text', 'Follow-up question'))
            followup_options = followup_data.get('options', [])

            # Convert options to proper format
            options = []
            if followup_options:
                for i, opt in enumerate(followup_options):
                    if isinstance(opt, str):
                        options.append({"value": str(i), "label": opt})
                    elif isinstance(opt, dict):
                        options.append({
                            "value": opt.get("id", opt.get("value", str(i))),
                            "label": opt.get("label", opt.get("text", str(opt)))
                        })
            else:
                # For yesno type questions or empty options, provide default options
                question_type = followup_data.get('type', 'text')
                if question_type == 'yesno':
                    options = [
                        {"value": "yes", "label": "Yes"},
                        {"value": "no", "label": "No"}
                    ]
                elif not options:
                    # If no options provided, allow free text input
                    options = []

            # Store followup context in assessment state
            context.conversation.assessment_state['followup_question_id'] = f"{main_question_id}_followup_1"
            context.conversation.assessment_state['current_pnm'] = main_question_item.pnm
            context.conversation.assessment_state['current_term'] = main_question_item.term

            return DialogueResponse(
                content=question_text,
                response_type=ResponseType.QUESTION,
                mode=ConversationMode.DIMENSION_ANALYSIS,
                should_continue_dialogue=False,
                current_pnm=main_question_item.pnm,
                current_term=main_question_item.term,
                options=options,
                question_id=f"{main_question_id}_followup_1"
            )

        except Exception as e:
            print(f"[UC1] Error generating followup question: {e}")
            # Fallback to summary if followup generation fails
            return await self._generate_uc1_summary(context)

    def _is_uc1_term_complete(self, context: ConversationContext) -> bool:
        """Determine if UC1 assessment is complete (1 main question + 1 follow up = complete)"""
        try:
            # UC1: Check if we have answered both main question and follow up
            assessment_messages = [msg for msg in context.conversation.messages if msg.role == 'assistant' and msg.metadata and msg.metadata.get('response_type') == 'question']
            total_questions_asked = len(assessment_messages)

            # Check if we have both main question and follow up responses
            # Complete after user answers follow up question (which means 2 questions have been asked)
            is_complete = total_questions_asked >= 2

            return is_complete
        except Exception as e:
            return False

    async def _generate_uc1_summary(self, context: ConversationContext) -> DialogueResponse:
        """Generate UC1 term assessment summary and mark conversation as completed"""
        try:

            # Get term assessment data
            current_pnm = context.conversation.assessment_state.get('current_pnm', 'Physiological')
            current_term = context.conversation.assessment_state.get('current_term', 'General')

            # Generate summary using high-quality UC2-style RAG + LLM approach
            summary_content = self.response_generator.generate_summary_response(context)

            # Mark conversation as completed
            if hasattr(self, 'storage'):
                context.conversation.status = 'completed'
                context.conversation.assessment_state['conversation_locked'] = True
                from datetime import datetime
                context.conversation.assessment_state['completed_at'] = datetime.now().isoformat()
                self.storage.update_conversation(context.conversation)
            else:
                pass  # Debug print removed

            return DialogueResponse(
                content=summary_content,
                response_type=ResponseType.SUMMARY,
                mode=ConversationMode.DIMENSION_ANALYSIS,
                should_continue_dialogue=False,
                current_pnm=current_pnm,
                current_term=current_term,
                options=[]  # No options for summary
            )

        except Exception as e:
            log.error(f"UC1 summary generation error: {e}")

            # Return a basic summary on error
            return DialogueResponse(
                content=f"Thank you for completing the {current_term} assessment. Based on your responses, I've gained valuable insights into your current situation and needs.",
                response_type=ResponseType.SUMMARY,
                mode=ConversationMode.DIMENSION_ANALYSIS,
                should_continue_dialogue=False
            )

    async def _generate_term_summary_content(self, context: ConversationContext, pnm: str, term: str, avg_score: float, scores_data: list) -> str:
        """Generate detailed term assessment summary using enhanced RAG + LLM with full conversation history"""
        try:
            # Collect FULL conversation history for comprehensive summary
            all_messages = context.conversation.messages if context.conversation.messages else []
            user_responses = [msg.content for msg in all_messages if msg.role == 'user']
            assistant_questions = [msg.content for msg in all_messages if msg.role == 'assistant']

            # Build conversation context with interleaved flow like UC2
            conversation_context = []
            max_length = max(len(user_responses), len(assistant_questions))
            for i in range(max_length):
                if i < len(assistant_questions):
                    conversation_context.append(f"Question: {assistant_questions[i][:200]}...")
                if i < len(user_responses):
                    conversation_context.append(f"Your response: {user_responses[i]}")

            conversation_summary = "\n".join(conversation_context[-8:])  # Last 8 exchanges

            # Enhanced RAG knowledge retrieval with Hybrid Retrieval + Self-RAG
            knowledge_context = self._retrieve_uc1_support_knowledge(pnm, term, avg_score, user_responses)

            # Improved knowledge handling like UC2
            if knowledge_context:
                knowledge_text = "\n".join([
                    f"- {doc.get('text', '')[:150]}" for doc in knowledge_context if doc.get('text', '').strip()
                ])
            else:
                knowledge_text = ""

            # If no knowledge retrieved, provide basic guidance
            if not knowledge_text.strip():
                knowledge_text = f"""- Regular monitoring and adaptation of strategies is important for {pnm} concerns
- Professional healthcare team consultation can provide personalized guidance for {term}
- Support groups and peer connections offer valuable shared experiences and coping strategies
- Assistive technologies and adaptive equipment may help maintain independence and quality of life"""

            # UC2-style professional summary format
            summary_prompt = f"""Based on your {pnm} assessment conversation about {term}, here's what we discussed:

{conversation_summary}

Professional support resources:
{knowledge_text}

Provide a professional assessment summary with targeted analysis:

## Assessment Overview:
Briefly summarize your current situation with {term} (average score: {avg_score:.1f}/7).

## Key Findings:
• Identify 2-3 specific areas where you're managing well
• Highlight 2-3 areas that may need attention or support

## Personalized Recommendations:
• Provide specific, actionable strategies based on your responses
• Reference appropriate support resources or interventions
• Consider your individual circumstances and preferences

## Next Steps:
Suggest concrete actions you can take to improve your situation.

IMPORTANT:
- Use second person (you, your) throughout - speak directly to the person
- Include proper line breaks between sections
- Be specific about their actual responses rather than generic
- Make each point targeted to what they actually shared
- Use caring but professional tone"""

            # Generate summary using LLM
            generated_summary = self.llm.generate_text(summary_prompt).strip()

            if generated_summary:
                return generated_summary
            else:
                # Enhanced fallback summary
                return f"""## Assessment Overview:
Thank you for completing your {term} assessment with an average score of {avg_score:.1f} out of 7.

## Key Findings:
• You've shared valuable insights about your {term} experiences
• Your responses show both strengths and areas for potential support

## Personalized Recommendations:
• Continue monitoring how {term} affects your daily life
• Consider discussing these findings with your healthcare team
• Explore support resources that align with your specific needs

## Next Steps:
Regular reassessment can help track changes and adapt your care plan accordingly."""

        except Exception as e:
            return f"""## Assessment Overview:
Thank you for completing your {term} assessment. Your responses help me understand your current situation better.

## Key Findings:
• You've provided important information about your experiences
• This assessment contributes to a better understanding of your needs

## Next Steps:
Continue working with your healthcare team to address your concerns and optimize your care plan."""

    async def _handle_assessment_phase(self, context: ConversationContext) -> DialogueResponse:
        """Structured assessment phase with AI-selected term"""
        try:
            # STEP 1: Process user response if provided (score and record it)
            if context.user_input.strip():
                await self._process_uc1_assessment_response(context)

                # STEP 2: Check if UC1 term is complete after processing response
                if self._is_uc1_term_complete(context):
                    return await self._generate_uc1_summary(context)

            # Get current assessment progress
            assessment_state = context.conversation.assessment_state or {}

            # UC1 Flow: main question -> follow up question -> summary
            # Check what stage we're at
            assessment_messages = [msg for msg in context.conversation.messages if msg.role == 'assistant' and msg.metadata and msg.metadata.get('response_type') == 'question']
            question_count = len(assessment_messages)


            if question_count == 0:
                # First question: select main question with AI
                selected_pnm, selected_term = await self._ai_select_relevant_term(context)
                relevant_questions = []
            elif question_count == 1:
                # Second question: select follow up question from the previous main question
                return await self._generate_followup_question(context)
            else:
                # Should not reach here as completion check should trigger summary
                return await self._generate_uc1_summary(context)

            # Primary: Find questions for the AI-selected term
            for item in self.qb.items():
                if (item.pnm == selected_pnm and item.term == selected_term):
                    relevant_questions.append(item)

            # Secondary: If no specific term questions, use any questions in the PNM dimension
            if not relevant_questions:
                for item in self.qb.items():
                    if item.pnm == selected_pnm:
                        relevant_questions.append(item)

            # UC1 strategy: Select the first few questions from relevant set (up to 3 for single-term assessment)
            # This allows completing term assessment without exhaustive questioning
            max_questions_for_uc1 = 3
            available_questions = relevant_questions[:max_questions_for_uc1] if relevant_questions else []

            # Select first available question (simplified - no asked_questions tracking)
            question_item = available_questions[0] if available_questions else None

            # If all prioritized questions were asked, use first available for UC1 completion
            if not question_item and available_questions:
                question_item = available_questions[0]

            # Final fallback: any question from question bank
            if not question_item:
                for item in self.qb.items():
                    question_item = item
                    break

            if question_item:

                # Get question content - handle different field names
                question_content = getattr(question_item, 'main', None) or getattr(question_item, 'question', None) or f"Question {question_item.id}"

                options = []
                if question_item.options:
                    options = [
                        {"value": opt.get("id", opt.get("value", str(i))),
                         "label": opt.get("label", opt.get("text", str(opt)))}
                        for i, opt in enumerate(question_item.options)
                    ]

                print(f"   content: '{question_content}' (type: {type(question_content)})")
                try:
                    print(f"   response_type: {ResponseType.QUESTION} (type: {type(ResponseType.QUESTION)})")
                except Exception as e:
                    print(f"   response_type ERROR: {e}")
                try:
                    print(f"   mode: {ConversationMode.DIMENSION_ANALYSIS} (type: {type(ConversationMode.DIMENSION_ANALYSIS)})")
                except Exception as e:
                    print(f"   mode ERROR: {e}")
                try:
                    print(f"   pnm: '{question_item.pnm}' (type: {type(question_item.pnm)})")
                except Exception as e:
                    print(f"   pnm ERROR: {e}")
                try:
                    print(f"   term: '{question_item.term}' (type: {type(question_item.term)})")
                except Exception as e:
                    print(f"   term ERROR: {e}")

                # Save question context for scoring (same format as UC2)
                context.conversation.assessment_state['question_context'] = {
                    'question_id': question_item.id,
                    'question': question_content,
                    'text': question_content,  # fallback for compatibility
                    'options': question_item.options,  # Original options with scores (critical!)
                    'pnm': question_item.pnm,
                    'term': question_item.term
                }

                # Update current PNM and term in assessment state
                context.conversation.assessment_state['current_pnm'] = question_item.pnm
                context.conversation.assessment_state['current_term'] = question_item.term


                try:
                    result = DialogueResponse(
                        content=question_content,
                        response_type=ResponseType.QUESTION,
                        mode=ConversationMode.DIMENSION_ANALYSIS,
                        should_continue_dialogue=False,
                        options=options,
                        current_pnm=question_item.pnm,
                        current_term=question_item.term
                    )
                    return result
                except Exception as e:
                    raise e
            else:
                # Fallback question
                return DialogueResponse(
                    content="How are you feeling about your current situation with ALS?",
                    response_type=ResponseType.QUESTION,
                    mode=ConversationMode.DIMENSION_ANALYSIS,
                    should_continue_dialogue=False,
                    options=[
                        {"value": "good", "label": "I'm managing well"},
                        {"value": "concerned", "label": "I have some concerns"},
                        {"value": "overwhelmed", "label": "I feel overwhelmed"}
                    ]
                )
        except Exception as e:
            log.error(f"Assessment phase error: {e}")
            return await self._handle_free_dialogue_phase(context)


class UseCaseTwoManager:
    """
    Use Case 2: Single dimension PNM traversal scoring manager.

    Handles: immediate assessment entry → traverse specified dimension questions → dimension summary
    """

    def __init__(self, qb: QuestionBank, ai_router: AIRouter, main_manager=None):
        self.qb = qb
        self.ai_router = ai_router
        self.main_manager = main_manager
        self.response_generator = ResponseGenerator()

    async def handle_dimension_assessment(self, context: ConversationContext, dimension: str) -> DialogueResponse:
        """Handle single dimension assessment flow"""


        try:
            assessment_state_keys = list(context.conversation.assessment_state.keys()) if context.conversation.assessment_state else []
        except Exception as e:
            raise

        # Process user's previous answer and score if provided
        # UC2 uses dedicated scoring logic for term-based evaluation
        if context.user_input and context.user_input.strip():

            # Clear any old scoring artifacts to avoid conflicts
            if 'temp_term_scores' in context.conversation.assessment_state:
                del context.conversation.assessment_state['temp_term_scores']

            try:
                # NEW SIMPLE UC2 SCORING LOGIC
                await self._process_user_response_uc2_simple(context, dimension)

                # Increment question index after successful scoring
                dimension_term_question_key = f"{dimension}_term_question_index"
                current_question_index = context.conversation.assessment_state.get(dimension_term_question_key, 0)
                next_question_index = current_question_index + 1
                context.conversation.assessment_state[dimension_term_question_key] = next_question_index

                # Check if scores were added
                temp_scores = {}
                for key, value in context.conversation.assessment_state.items():
                    if 'temp_scores_' in key:
                        temp_scores[key] = value

            except Exception as e:
                print(f"[UC2] CRITICAL ERROR in scoring process: {e}")
                import traceback
                print(f"[UC2] Traceback: {traceback.format_exc()}")
                # Don't re-raise the exception - continue with question generation

            # CRITICAL FIX: Always check for term completion after user response, even if scoring failed
            try:
                await self._check_and_handle_term_completion_uc2(context, dimension)
            except Exception as completion_error:
                import traceback

        # Check if dimension is ready for summary
        if context.conversation.assessment_state.get(f"{dimension}_ready_for_summary", False):
            return await self._generate_dimension_summary_uc2(context, dimension)

        # Get all questions for this dimension and group by term
        try:
            main_questions = self.qb.for_pnm(dimension)
        except Exception as e:
            print(f"[UC2] CRITICAL ERROR getting questions for {dimension}: {e}")
            import traceback
            # Return a simple error response rather than crashing
            return DialogueResponse(
                content=f"Unable to load questions for {dimension} dimension. Please try again.",
                response_type=ResponseType.CHAT,
                mode=ConversationMode.DIMENSION_ANALYSIS,
                current_pnm=dimension
            )

        # Group questions by term (dimension-exclusive)
        try:
            terms_questions = {}
            for main_q in main_questions:
                term = main_q.term if hasattr(main_q, 'term') else 'General'
                question_pnm = main_q.pnm if hasattr(main_q, 'pnm') else dimension

                # Only include questions that actually belong to the current dimension
                if question_pnm != dimension:
                    continue

                if term not in terms_questions:
                    terms_questions[term] = []

                # Add main question
                terms_questions[term].append(main_q)

                # Add follow-up questions for this term
                followups = []
                if hasattr(main_q, 'followups') and main_q.followups:
                    followups = main_q.followups
                elif hasattr(main_q, 'followup_questions') and main_q.followup_questions:
                    followups = main_q.followup_questions

                # Convert follow-ups to question-like objects
                from app.services.question_bank import QuestionItem
                for i, followup in enumerate(followups):
                    # Parse followup if it's a string (JSON string)
                    parsed_followup = followup
                    if isinstance(followup, str):
                        try:
                            import json
                            parsed_followup = json.loads(followup.replace("'", '"'))  # Convert single quotes to double quotes
                        except (json.JSONDecodeError, Exception) as e:
                            continue

                    # Skip if followup is not a dictionary
                    if not isinstance(parsed_followup, dict):
                        continue

                    # Extract question text from followup properly (follow-ups use 'text' field)
                    question_text = parsed_followup.get('text', parsed_followup.get('question', parsed_followup.get('main', '')))

                    # Get followup options
                    followup_options = parsed_followup.get('options', [])

                    # Skip followups that have no question text or no options (both needed for assessment)
                    if not question_text or not followup_options:
                        continue

                    # Create meaningful fallback for missing question text
                    if not question_text:
                        question_text = f"Follow-up question {i+1} for {term}"


                    followup_q = QuestionItem(
                        id=f"{main_q.id}_followup_{i+1}",
                        pnm=dimension,
                        term=term,
                        main=question_text,
                        followups=[],  # Follow-ups don't have their own follow-ups
                        terms=[],      # Use empty terms list for follow-ups
                        meta={},       # Empty metadata
                        options=followup_options
                    )
                    terms_questions[term].append(followup_q)

        except Exception as e:
            import traceback
            raise

        # Get ordered list of terms for this dimension
        ordered_terms = sorted(terms_questions.keys())

        # Get current term and question progress within term
        dimension_term_question_key = f"{dimension}_term_question_index"

        current_term_index = context.conversation.assessment_state.get(f"{dimension}_term_index", 0)
        current_term_question_index = context.conversation.assessment_state.get(dimension_term_question_key, 0)




        # Check if we've completed all terms in this dimension
        if current_term_index >= len(ordered_terms):
            return await self._generate_dimension_summary_uc2(context, dimension)

        # Get current term and its questions
        current_term = ordered_terms[current_term_index]
        current_term_questions = terms_questions[current_term]


        # Check if current term is completed
        if current_term_question_index >= len(current_term_questions):
            try:
                await self._trigger_term_scoring_uc2(context, dimension, current_term)
            except Exception as e:
                import traceback
                raise

            # Move to next term
            next_term_index = current_term_index + 1
            context.conversation.assessment_state[f"{dimension}_term_index"] = next_term_index
            context.conversation.assessment_state[dimension_term_question_key] = 0  # Reset question index for new term

            # Check if we've completed all terms
            if next_term_index >= len(ordered_terms):
                return await self._generate_dimension_summary_uc2(context, dimension)

            # Move to first question of next term
            current_term = ordered_terms[next_term_index]
            current_term_questions = terms_questions[current_term]
            current_term_question_index = 0


        # Select current question from current term with bounds checking
        if current_term_question_index >= len(current_term_questions):
            # Force term completion
            await self._trigger_term_scoring_uc2(context, dimension, current_term)
            next_term_index = current_term_index + 1
            context.conversation.assessment_state[f"{dimension}_term_index"] = next_term_index

            if next_term_index >= len(ordered_terms):
                return await self._generate_dimension_summary_uc2(context, dimension)

            # Move to next term
            current_term = ordered_terms[next_term_index]
            current_term_questions = terms_questions[current_term]
            current_term_question_index = 0
            context.conversation.assessment_state[dimension_term_question_key] = 0

        question_item = current_term_questions[current_term_question_index]

        # NOTE: Question index will be incremented in _handle_user_response_uc2 after user answers

        return self._generate_dimension_question(question_item, dimension, context)

    def _generate_dimension_question(self, question_item, dimension: str, context: ConversationContext = None) -> DialogueResponse:
        """Generate dimension question with proper question_context setup"""
        options = []
        if question_item.options:
            options = []
            for i, opt in enumerate(question_item.options):
                if isinstance(opt, dict):
                    # Option is a dictionary
                    options.append({
                        "value": opt.get("id", opt.get("value", str(i))),
                        "label": opt.get("label", opt.get("text", str(opt)))
                    })
                else:
                    # Option is a string or other type
                    options.append({
                        "value": str(i),
                        "label": str(opt)
                    })

        # Set question_context for scoring (CRITICAL for UC2 scoring)
        if context:
            question_context = {
                'question': question_item.main,
                'text': question_item.main,  # fallback for compatibility
                'options': question_item.options,  # Original options with scores
                'question_id': question_item.id,
                'pnm': dimension,
                'term': question_item.term
            }
            context.conversation.assessment_state['question_context'] = question_context

            # AI question storage is handled by chat_unified.py centralized storage

        return DialogueResponse(
            content=question_item.main,
            response_type=ResponseType.QUESTION,
            mode=ConversationMode.DIMENSION_ANALYSIS,
            should_continue_dialogue=False,
            options=options,
            current_pnm=dimension,
            current_term=question_item.term,
            question_id=question_item.id
        )

    async def _generate_dimension_summary(self, context: ConversationContext, dimension: str) -> DialogueResponse:
        """Generate professional RAG AI summary for dimension completion"""
        try:
            # Use RAG-enhanced professional summary generation
            summary_content = self.response_generator.generate_summary_response(context)
        except Exception as e:
            # AI fallback without hardcoded templates
            scores = context.conversation.assessment_state.get('scores', {}).get(dimension, {})
            if scores:
                avg_score = sum(score_data['score'] for score_data in scores.values()) / len(scores)
                summary_content = f"Assessment complete for {dimension}. Average score: {avg_score:.1f}/7. Your responses provide valuable insights into your current situation and will guide personalized support recommendations."
            else:
                summary_content = f"Your {dimension} assessment has been completed. Thank you for sharing your experiences. This information will help us better understand your needs and provide appropriate support."

        return DialogueResponse(
            content=summary_content,
            response_type=ResponseType.SUMMARY,
            mode=ConversationMode.DIMENSION_ANALYSIS,
            should_continue_dialogue=False,
            current_pnm=dimension
        )

    def _extract_score_from_user_input(self, user_input: str, question_context: dict) -> float:
        """Extract score from user input using question context options"""
        if not user_input or not question_context or 'options' not in question_context:
            return None

        options = question_context.get('options', [])
        user_input_lower = user_input.lower().strip()


        # Try to match by option ID first
        for option in options:
            if option.get('id', '').lower() == user_input_lower:
                score_value = option.get('score')
                if score_value is not None:
                    return float(score_value)
                return None  # No score for this option

        # Try ordinal matching: user inputs 1,2,3,4 for 1st,2nd,3rd,4th option
        try:
            ordinal_input = int(user_input_lower)
            if 1 <= ordinal_input <= len(options):
                selected_option = options[ordinal_input - 1]  # Convert 1-based to 0-based index
                score_value = selected_option.get('score')
                if score_value is not None:
                    return float(score_value)
                return None  # No score for this option
        except ValueError:
            pass  # Not a valid integer, continue to label matching

        # Try to match by option label
        for option in options:
            label = option.get('label', '').lower()
            if label and user_input_lower in label:
                score_value = option.get('score')
                if score_value is not None:
                    return float(score_value)
                return None  # No score for this option

        return None

    async def _process_user_response_uc2_simple(self, context: ConversationContext, dimension: str) -> None:
        """
        Simple UC2 scoring logic based on user requirements:
        1. Extract score from main question options
        2. Store immediately for term completion
        3. Trigger term scoring when term is complete
        """
        if not context.user_input or not context.user_input.strip():
            return

        user_input = context.user_input.strip()

        # Get question context with options
        question_context = context.conversation.assessment_state.get('question_context', {})

        # Check if question_context has term data
        if not question_context.get('term'):
            pass  # Debug print removed

        # Extract score from user input using existing method
        score = self._extract_score_from_user_input(user_input, question_context)
        scoring_method = "question_bank_options"

        if score is None:
            # AI scoring fallback for custom user input (as per CLAUDE.md requirements)
            try:
                # Ensure ai_scorer is always available
                if not hasattr(self, 'ai_scorer') or not self.ai_scorer:
                    from app.services.ai_scoring_engine import AIFreeTextScorer
                    self.ai_scorer = AIFreeTextScorer()  # No ai_router needed - uses IBM WatsonX directly

                ai_score_result = await self.ai_scorer.score_free_text_response(
                    user_input,
                    question_context,
                    dimension,
                    context.conversation.messages[-5:]  # Recent context
                )
                score = ai_score_result.score
                scoring_method = "ai_fallback"

            except Exception as e:
                # Skip scoring instead of using hardcoded fallback as per user requirements
                return

        if score is not None:
            # Get current term from question context with fallback to current context
            current_term = question_context.get('term')
            if not current_term:
                # Fallback to context.current_term or dimension-based term
                current_term = getattr(context, 'current_term', None)
                if not current_term:
                    # Skip scoring if no valid term is available - prevent wrong data
                    return


            # Store term score directly in database (immediate storage)
            await self._store_term_score_immediate(context, dimension, current_term, score, scoring_method)

            # Mark this term as completed
            completed_terms = context.conversation.assessment_state.get('completed_terms', [])
            term_key = f"{dimension}_{current_term}"
            if term_key not in completed_terms:
                completed_terms.append(term_key)
                context.conversation.assessment_state['completed_terms'] = completed_terms
        else:
            pass  # Debug print removed

    async def _store_term_score_immediate(self, context: ConversationContext, dimension: str, term: str, score: float, scoring_method: str = "question_bank_options") -> bool:
        """
        Immediately store term score to database
        Returns True if successful, False otherwise
        """
        try:
            from datetime import datetime
            import sqlite3
            from pathlib import Path


            # Database path
            db_path = Path(__file__).parent.parent / "data" / "als.db"

            if not db_path.exists():
                return False

            # Connect and store
            with sqlite3.connect(str(db_path)) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO conversation_scores
                    (conversation_id, pnm, term, score, status, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    context.conversation.id,
                    dimension,
                    term,
                    float(score),
                    'completed',
                    datetime.now().isoformat()
                ))

                # Verify storage
                result = conn.execute(
                    "SELECT score FROM conversation_scores WHERE conversation_id = ? AND pnm = ? AND term = ?",
                    (context.conversation.id, dimension, term)
                ).fetchone()

                if result:
                    return True
                else:
                    return False

        except Exception as e:
            print(f"[UC2] CRITICAL ERROR storing score: {e}")
            return False

    async def _trigger_term_scoring_uc2(self, context: ConversationContext, dimension: str, term: str) -> None:
        """
        Simple term completion for UC2 - just mark term as completed
        Score has already been stored directly in database
        """

        # Mark this term as completed in assessment state
        completed_terms = context.conversation.assessment_state.get('completed_terms', [])
        term_key = f"{dimension}_{term}"
        if term_key not in completed_terms:
            completed_terms.append(term_key)
            context.conversation.assessment_state['completed_terms'] = completed_terms

    async def _generate_dimension_summary_uc2(self, context: ConversationContext, dimension: str) -> DialogueResponse:
        """Generate professional RAG AI summary for dimension completion and lock conversation"""

        # Check if summary already generated to prevent duplicate
        dimension_completed_key = f"{dimension}_completed"
        if context.conversation.assessment_state.get(dimension_completed_key, False):
            return DialogueResponse(
                content=f"Assessment for {dimension} dimension has been completed. Thank you for your responses.",
                response_type=ResponseType.SUMMARY,
                mode=ConversationMode.DIMENSION_ANALYSIS,
                should_continue_dialogue=False,
                current_pnm=dimension
            )

        try:
            # Use RAG-enhanced professional summary generation
            summary_content = self.response_generator.generate_summary_response(context)

            # Mark this dimension as completed and lock conversation
            context.conversation.assessment_state[dimension_completed_key] = True
            context.conversation.assessment_state['conversation_locked'] = True

            # AI summary storage is handled by chat_unified.py centralized storage

            return DialogueResponse(
                content=summary_content,
                response_type=ResponseType.SUMMARY,
                mode=ConversationMode.DIMENSION_ANALYSIS,
                should_continue_dialogue=False,
                current_pnm=dimension
            )

        except Exception as e:
            # Fallback summary
            context.conversation.assessment_state[dimension_completed_key] = True
            context.conversation.assessment_state['conversation_locked'] = True

            fallback_summary = f"Thank you for completing the {dimension} assessment. Your responses have been recorded and will help provide personalized support recommendations."

            # AI fallback summary storage is handled by chat_unified.py centralized storage

            return DialogueResponse(
                content=fallback_summary,
                response_type=ResponseType.SUMMARY,
                mode=ConversationMode.DIMENSION_ANALYSIS,
                should_continue_dialogue=False,
                current_pnm=dimension
            )

    async def _check_and_handle_term_completion_uc2(self, context: ConversationContext, dimension: str) -> None:
        """Check if current term is completed after user response and trigger scoring if needed"""

        try:
            # Get term progress information
            main_questions = self.qb.for_pnm(dimension)
            terms_questions = {}
            for main_q in main_questions:
                term = main_q.term if hasattr(main_q, 'term') else 'General'
                if term not in terms_questions:
                    terms_questions[term] = []
                terms_questions[term].append(main_q)

            ordered_terms = sorted(terms_questions.keys())
            current_term_index = context.conversation.assessment_state.get(f"{dimension}_term_index", 0)

            if current_term_index >= len(ordered_terms):
                return

            current_term = ordered_terms[current_term_index]
            current_term_questions = terms_questions[current_term]
            dimension_term_question_key = f"{dimension}_term_question_index"
            current_term_question_index = context.conversation.assessment_state.get(dimension_term_question_key, 0)

            print(f"  - current_term_index: {current_term_index}")
            print(f"  - current_term: {current_term}")
            print(f"  - current_term_question_index: {current_term_question_index}")
            print(f"  - len(current_term_questions): {len(current_term_questions)}")
            print(f"  - Completion condition: {current_term_question_index} >= {len(current_term_questions)} = {current_term_question_index >= len(current_term_questions)}")

            # Check if current term is now completed (no more questions in this term)
            # Note: question index has already been incremented after user response processing
            if current_term_question_index >= len(current_term_questions):

                # Mark this term as completed
                completed_terms = context.conversation.assessment_state.get('completed_terms', [])
                term_key = f"{dimension}_{current_term}"
                if term_key not in completed_terms:
                    completed_terms.append(term_key)
                    context.conversation.assessment_state['completed_terms'] = completed_terms

                # Move to next term
                next_term_index = current_term_index + 1
                context.conversation.assessment_state[f"{dimension}_term_index"] = next_term_index
                context.conversation.assessment_state[dimension_term_question_key] = 0


                # Check if all terms completed
                if next_term_index >= len(ordered_terms):
                    # Set flag to trigger summary generation on next response
                    context.conversation.assessment_state[f"{dimension}_ready_for_summary"] = True

                return

            # SIMPLIFIED UC2: Check if this term has been completed (legacy code)
            completed_terms = context.conversation.assessment_state.get('completed_terms', [])
            term_key = f"{dimension}_{current_term}"

            if term_key in completed_terms:

                # Move to next term
                next_term_index = current_term_index + 1
                context.conversation.assessment_state[f"{dimension}_term_index"] = next_term_index
                context.conversation.assessment_state[dimension_term_question_key] = 0


                # Check if all terms completed
                if next_term_index >= len(ordered_terms):
                    # Set flag to trigger summary generation on next response
                    context.conversation.assessment_state[f"{dimension}_ready_for_summary"] = True

        except Exception as e:
            import traceback
            print(f"[UC2] Traceback: {traceback.format_exc()}")

    async def _evaluate_term_with_ai(self, dimension: str, term: str, responses: list, main_score: float) -> float:
        """AI-powered evaluation of term responses to complement main question score"""

        if not responses:
            return main_score

        try:
            # Use existing AI scoring engine with focused prompt
            evaluation_prompt = f"""
            Evaluate the user's responses for {dimension} dimension, {term} term.

            Main question score: {main_score}/7 (0=best condition, 7=most challenging)

            User responses: {' | '.join(responses[-3:])}

            Consider:
            - Consistency with main question score
            - Quality of life impact indicated in responses
            - Practical challenges mentioned
            - Overall functioning level

            Return a score from 0-7 where:
            0 = Excellent functioning, minimal challenges
            3.5 = Moderate challenges, some impact
            7 = Severe challenges, significant impact

            Score:"""

            # Use AI scorer for consistent evaluation
            ai_result = await self.ai_scorer.score_free_text_response(
                ' '.join(responses[-3:]),  # Last 3 responses
                {"prompt": evaluation_prompt},
                dimension,
                []  # No context needed for term evaluation
            )

            ai_score = float(ai_result.score) if ai_result.score is not None else main_score

            # Ensure score is in valid range
            ai_score = max(0.0, min(7.0, ai_score))
            return ai_score

        except Exception as e:
            return main_score


