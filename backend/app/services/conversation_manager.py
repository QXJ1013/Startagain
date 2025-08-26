# app/services/conversation_manager.py
from __future__ import annotations
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from app.config import get_settings
from app.services.question_bank import QuestionBank
from app.services.info_provider_enhanced import EnhancedInfoProvider
from app.services.pnm_scoring import PNMScoringEngine, PNMScore
from app.services.ai_routing import AIRoutingService


class QuestionType(Enum):
    MAIN = "main"
    FOLLOWUP = "followup"


@dataclass
class QuestionResponse:
    """Structured response for a conversation turn"""
    question_text: str
    question_type: QuestionType
    options: List[Dict[str, Any]]  # For frontend buttons
    allow_text_input: bool = True  # Whether to show text input field
    transition_message: Optional[str] = None  # Message before asking question
    info_cards: Optional[List[Dict[str, Any]]] = None  # Generated info cards
    evidence_threshold_met: bool = False


class ConversationManager:
    """
    Manages structured Q&A conversation flow for ALS/MND assessment.
    
    Features:
    - Main question + followup question sequences
    - Evidence threshold tracking
    - Information card generation at appropriate times
    - Transition messages between topics
    """
    
    def __init__(self):
        self.cfg = get_settings()
        self.question_bank = QuestionBank(self.cfg.QUESTION_BANK_PATH)
        self.info_provider = EnhancedInfoProvider()
        self.scoring_engine = PNMScoringEngine()
        
        # Configuration
        self.evidence_threshold = int(getattr(self.cfg, "EVIDENCE_THRESHOLD", 3))
        self.max_followups = int(getattr(self.cfg, "MAX_FOLLOWUPS", 3))
    
    def get_next_question(
        self,
        session,
        user_response: Optional[str] = None,
        storage=None,
        dimension_focus: Optional[str] = None
    ) -> QuestionResponse:
        """
        Get the next question in the conversation flow.
        
        Args:
            session: Current session state
            user_response: User's answer to previous question
            storage: Storage instance for persistence
            dimension_focus: Optional PNM dimension to focus on
            
        Returns:
            QuestionResponse with question, options, and any info cards
        """
        import logging
        log = logging.getLogger(__name__)
        log.info(f"get_next_question called: user_response={bool(user_response)}, dimension_focus={dimension_focus}, turn_index={session.turn_index}, current_pnm={session.current_pnm}")
        
        # Route if this is a new conversation or dimension selection
        # Always route if:
        # 1. Dimension focus is provided
        # 2. First user message (turn_index == 0) 
        # 3. No PNM set yet (fresh session)
        should_route = (
            dimension_focus is not None or
            (user_response and (session.turn_index == 0 or not session.current_pnm))
        )
        
        log.info(f"Should route: {should_route}")
        
        if should_route:
            # When dimension_focus is provided without user_response, 
            # create a synthetic message for routing
            routing_input = user_response or f"I want to assess my {dimension_focus} dimension"
            self._route_initial_query(session, routing_input, dimension_focus)
        
        # If user provided a response, process it
        if user_response:
            self._process_user_response(session, user_response, storage)
        
        # Determine what question to ask next
        # Check if this is a dimension start (dimension_focus provided without user_response)
        is_dimension_start = (dimension_focus is not None and not user_response)
        
        if self._should_ask_main_question(session):
            return self._get_main_question(session, storage, dimension_focus, is_dimension_start)
        elif self._should_ask_followup(session):
            return self._get_followup_question(session, storage)
        else:
            # Move to next term or provide session summary
            return self._handle_term_completion(session, storage)
    
    def _process_user_response(self, session, user_response: str, storage=None):
        """Process user's response and update session state"""
        # Store the response for AI routing context
        session.last_user_response = user_response
        
        # Store the response
        if storage:
            # Get current turn index and increment
            turn_index = session.next_turn_index()
            storage.add_turn(
                session_id=session.session_id,
                turn_index=turn_index,
                role='user',
                content=user_response
            )
        
        # Update evidence tracking
        self._update_evidence(session, user_response)
        
        # Generate PNM score for user response
        current_pnm = getattr(session, 'current_pnm', None)
        current_term = getattr(session, 'current_term', None)
        
        # Ensure we have a PNM and term for scoring
        if not current_pnm or not current_term:
            # Use fallback values based on response content
            if any(word in user_response.lower() for word in ['breath', 'bipap', 'oxygen', 'ventil']):
                current_pnm, current_term = 'Physiological', 'Breathing exercises'
            elif any(word in user_response.lower() for word in ['walk', 'move', 'mobility', 'wheelchair']):
                current_pnm, current_term = 'Physiological', 'Mobility and transfers'
            elif any(word in user_response.lower() for word in ['safe', 'emergency', 'plan', 'access']):
                current_pnm, current_term = 'Safety', 'Emergency preparedness'
            elif any(word in user_response.lower() for word in ['swallow', 'choke', 'eat', 'food', 'drink', 'nutrition']):
                current_pnm, current_term = 'Physiological', 'Nutrition management'
            elif any(word in user_response.lower() for word in ['speak', 'communic', 'talk', 'speech', 'voice']):
                current_pnm, current_term = 'Love & Belonging', 'Communication with support network'
            else:
                current_pnm, current_term = 'Cognitive', 'Emergency preparedness'
            
            # Update session with these values
            session.current_pnm = current_pnm
            session.current_term = current_term
        
        # Generate PNM score with fallback mechanisms
        pnm_score = None
        
        try:
            # Try primary PNM scoring engine
            pnm_score = self.scoring_engine.score_response(
                user_response, current_pnm, current_term
            )
            
        except Exception:
            # Try AI-based fallback scoring
            try:
                from app.services.ai_scorer import create_ai_fallback_score
                pnm_score = create_ai_fallback_score(user_response, current_pnm, current_term)
                
            except Exception:
                # Last resort: create minimal score
                from app.services.pnm_scoring import PNMScore
                pnm_score = PNMScore(
                    pnm_level=current_pnm,
                    domain=current_term,
                    awareness_score=2,
                    understanding_score=1,
                    coping_score=1,
                    action_score=1
                )
        
        # Add score to session
        if not hasattr(session, 'pnm_scores'):
            session.pnm_scores = []
        if session.pnm_scores is None:
            session.pnm_scores = []
            
        if pnm_score:
            session.pnm_scores.append(pnm_score)
        
        # Update followup pointer
        if hasattr(session, 'followup_ptr') and session.followup_ptr is not None:
            session.followup_ptr += 1
    
    def _route_initial_query(self, session, user_response: str, dimension_focus: Optional[str] = None):
        """Route initial user query to appropriate PNM dimension and term using AI routing"""
        
        import logging
        log = logging.getLogger(__name__)
        log.info(f"_route_initial_query called with: user_response='{user_response}', dimension_focus='{dimension_focus}'")
        
        try:
            # If dimension_focus is provided, use it directly for routing
            if dimension_focus:
                # Map dimension names to PNM levels
                dimension_mapping = {
                    'Physiological': 'Physiological',
                    'Safety': 'Safety',
                    'Love & Belonging': 'Love & Belonging',
                    'Esteem': 'Esteem',
                    'Self-Actualisation': 'Self-Actualisation',
                    'Cognitive': 'Cognitive',
                    'Aesthetic': 'Aesthetic',
                    'Transcendence': 'Transcendence'
                }
                
                pnm = dimension_mapping.get(dimension_focus, dimension_focus)
                # Use AI routing to find best term for this dimension
                routing_result = AIRoutingService.route_query(user_response, pnm)
            else:
                # Use the new AI routing service normally
                routing_result = AIRoutingService.route_query(user_response, None)
            
            # Update session with routing results
            session.current_pnm = routing_result.pnm
            session.current_term = routing_result.term
            session.keyword_pool = routing_result.keywords
            session.ai_confidence = routing_result.confidence
            session.routing_method = routing_result.method
            
            # Log routing for debugging
            log.info(f"[AI Routing] Method: {routing_result.method}")
            log.info(f"[AI Routing] PNM: {routing_result.pnm}, Term: {routing_result.term}")
            log.info(f"[AI Routing] Keywords: {routing_result.keywords}")
            log.info(f"[AI Routing] Confidence: {routing_result.confidence}")
            
        except Exception as e:
            log.error(f"AI Routing failed: {e}")
            # Fallback to Cognitive/Emergency preparedness
            session.current_pnm = 'Cognitive'
            session.current_term = 'Emergency preparedness'
            session.keyword_pool = []
            session.ai_confidence = 0.0
            session.routing_method = 'fallback_error'
        
        return
    
    def _should_ask_main_question(self, session) -> bool:
        """Check if we should ask a main question"""
        # If no current question ID, we need to start
        if not hasattr(session, 'current_qid') or not session.current_qid:
            return True
        
        # If followup sequence is complete
        if (hasattr(session, 'followup_ptr') and 
            session.followup_ptr is not None and 
            session.followup_ptr >= self.max_followups):
            return True
        
        # If evidence threshold met for current term
        if self._evidence_threshold_met(session):
            return True
            
        return False
    
    def _should_ask_followup(self, session) -> bool:
        """Check if we should ask a followup question"""
        if not hasattr(session, 'current_qid') or not session.current_qid:
            return False
        
        # Start followups if never started
        if not hasattr(session, 'followup_ptr') or session.followup_ptr is None:
            return True  # Start followups
            
        return (session.followup_ptr < self.max_followups and 
                not self._evidence_threshold_met(session))
    
    def _get_main_question(self, session, storage=None, dimension_focus: Optional[str] = None, is_dimension_start: bool = False) -> QuestionResponse:
        """Get the next main question"""
        # Select next question from bank
        question_item = self._select_next_question(session)
        
        if not question_item:
            return self._handle_session_completion(session)
        
        # Check if we're moving to a new term and generate info cards accordingly
        info_cards = None
        evidence_threshold_met = False
        
        # Generate info cards only if:
        # 1. Evidence threshold is met for current term, OR
        # 2. We're moving to a new term (term completion)
        # BUT NOT when starting fresh from dimension focus or first question
        
        # Skip info cards if this is a dimension start OR the very first question
        if is_dimension_start:
            # Never show info cards when starting from dimension selection
            info_cards = None
        elif not hasattr(session, 'asked_qids') or len(session.asked_qids) == 0:
            # Never show info cards on the very first question
            info_cards = None
        elif self._evidence_threshold_met(session) or self._is_term_changing(session, question_item):
            # Show info cards when evidence threshold met or changing terms
            info_cards = self._generate_info_cards(session, storage)
            evidence_threshold_met = True
        
        # Generate transition message BEFORE updating session state
        transition_msg = self._generate_transition_message(session, question_item)
        
        # Update session state
        session.current_qid = question_item.id
        session.current_pnm = question_item.pnm
        session.current_term = question_item.term
        session.followup_ptr = None  # Reset followup tracking
        
        # Create structured response
        return QuestionResponse(
            question_text=question_item.main,
            question_type=QuestionType.MAIN,
            options=self._format_question_options(question_item.options) or self._extract_question_options(question_item.main),
            allow_text_input=True,
            transition_message=transition_msg,
            info_cards=info_cards,
            evidence_threshold_met=evidence_threshold_met
        )
    
    def _get_followup_question(self, session, storage=None) -> QuestionResponse:
        """Get the next followup question"""
        question_item = self.question_bank.get_question(session.current_qid)
        
        if not question_item or not question_item.followups:
            # No more followups, try main question
            return self._get_main_question(session, storage, None, False)
        
        # Get followup index
        followup_idx = session.followup_ptr if session.followup_ptr is not None else 0
        
        if followup_idx >= len(question_item.followups):
            # All followups exhausted
            return self._handle_followup_completion(session, storage)
        
        followup_obj = question_item.followups[followup_idx]
        
        # Extract text and options from followup object
        if isinstance(followup_obj, dict):
            followup_text = followup_obj.get('text', str(followup_obj))
            followup_options = followup_obj.get('options')
        else:
            followup_text = str(followup_obj)
            followup_options = None
        
        # Initialize followup pointer if needed
        if session.followup_ptr is None:
            session.followup_ptr = 0
        
        return QuestionResponse(
            question_text=followup_text,
            question_type=QuestionType.FOLLOWUP,
            options=self._format_question_options(followup_options) or self._format_question_options(question_item.options) or self._extract_question_options(followup_text),
            allow_text_input=True
        )
    
    def _handle_followup_completion(self, session, storage=None) -> QuestionResponse:
        """Handle completion of followup sequence"""
        # Check if evidence threshold met
        if self._evidence_threshold_met(session):
            # Generate info cards
            info_cards = self._generate_info_cards(session, storage)
            
            # Move to next term or complete
            next_question = self._get_main_question(session, storage, None, False)
            next_question.info_cards = info_cards
            next_question.evidence_threshold_met = True
            
            return next_question
        else:
            # Continue with more questions
            return self._get_main_question(session, storage, None, False)
    
    def _handle_term_completion(self, session, storage=None) -> QuestionResponse:
        """Handle completion of a term's questions"""
        # Generate final info cards for the term
        info_cards = self._generate_info_cards(session, storage)
        
        # Generate summary message
        summary_msg = self._generate_term_summary(session)
        
        # Try to get next term question
        next_question = self._get_main_question(session, storage, None, False)
        
        if next_question:
            next_question.info_cards = info_cards
            next_question.transition_message = summary_msg
            next_question.evidence_threshold_met = True
        
        return next_question
    
    def _select_next_question(self, session) -> Optional[Any]:
        """Select the next appropriate question using AI routing"""
        # Get questions not yet asked
        asked_qids = getattr(session, 'asked_qids', []) or []
        
        # Filter by current PNM and term if set
        current_pnm = getattr(session, 'current_pnm', None)
        current_term = getattr(session, 'current_term', None)
        keywords = getattr(session, 'keyword_pool', [])
        
        # Debug logging
        import logging
        log = logging.getLogger(__name__)
        log.info(f"_select_next_question: PNM='{current_pnm}', Term='{current_term}', Keywords={keywords}, asked={len(asked_qids)}")
        
        # Convert question bank to dict format for AI routing
        question_dicts = []
        for q in self.question_bank.questions:
            question_dicts.append({
                'id': q.id,
                'Prompt_Main': q.main,  # Changed from q.prompt_main to q.main
                'Primary_Need_Model': q.pnm,
                'Term': q.term,
                'options': q.options
            })
        
        # Use AI routing to find matching questions with flexible matching
        matching_questions = AIRoutingService.find_matching_questions(
            current_pnm, current_term, question_dicts
        )
        
        # If we have keywords and matching questions, use scoring to select best
        if matching_questions and keywords:
            # Get the user's original input if available (stored during routing)
            user_input = ''
            if hasattr(session, 'last_user_response'):
                user_input = session.last_user_response
            
            selected_dict = AIRoutingService.select_best_question(
                matching_questions, keywords, user_input, asked_qids
            )
            
            if selected_dict:
                # Find the corresponding Question object
                for q in self.question_bank.questions:
                    if str(q.id) == str(selected_dict.get('id')):
                        # Update asked questions
                        if not hasattr(session, 'asked_qids') or session.asked_qids is None:
                            session.asked_qids = []
                        session.asked_qids.append(q.id)
                        log.info(f"Selected question ID {q.id} using AI scoring")
                        return q
        
        # Fallback: Try to find any question in the PNM dimension
        if current_pnm:
            available_questions = [
                q for q in self.question_bank.questions 
                if q.id not in asked_qids 
                and q.pnm == current_pnm
            ]
            
            if available_questions:
                selected = available_questions[0]
                if not hasattr(session, 'asked_qids') or session.asked_qids is None:
                    session.asked_qids = []
                session.asked_qids.append(selected.id)
                log.info(f"Fallback: Selected question ID {selected.id} from PNM {current_pnm}")
                return selected
        
        # Last resort: Get any available question
        available_questions = [
            q for q in self.question_bank.questions 
            if q.id not in asked_qids
        ]
        
        if not available_questions:
            return None
        
        # Select the first available question
        selected = available_questions[0]
        
        # Update asked questions
        if not hasattr(session, 'asked_qids') or session.asked_qids is None:
            session.asked_qids = []
        session.asked_qids.append(selected.id)
        log.warning(f"Last resort: Selected any available question ID {selected.id}")
        
        return selected
    
    def _format_question_options(self, options: Optional[List[Dict[str, Any]]]) -> Optional[List[Dict[str, Any]]]:
        """Convert v2_full.json options format to frontend format"""
        if not options:
            return None
        
        formatted_options = []
        for option in options:
            if isinstance(option, dict):
                # Convert {id: "value", label: "Label"} to {value: "value", label: "Label"}
                formatted_option = {
                    'value': option.get('id', option.get('value', '')),
                    'label': option.get('label', option.get('text', ''))
                }
                formatted_options.append(formatted_option)
        
        return formatted_options if formatted_options else None
    
    def _extract_question_options(self, question_text: str) -> List[Dict[str, Any]]:
        """Extract button options from question text"""
        # This is a simplified implementation
        # In production, options would be stored in the question bank
        
        common_patterns = {
            'frequency': [
                {'value': 'never', 'label': 'Never'},
                {'value': 'sometimes', 'label': 'Sometimes'},
                {'value': 'often', 'label': 'Often'},
                {'value': 'always', 'label': 'Always'}
            ],
            'difficulty': [
                {'value': 'no_difficulty', 'label': 'No difficulty'},
                {'value': 'mild', 'label': 'Mild difficulty'},
                {'value': 'moderate', 'label': 'Moderate difficulty'},
                {'value': 'severe', 'label': 'Severe difficulty'}
            ],
            'yes_no': [
                {'value': 'yes', 'label': 'Yes'},
                {'value': 'no', 'label': 'No'},
                {'value': 'unsure', 'label': 'Not sure'}
            ]
        }
        
        # Simple pattern matching to determine option type
        question_lower = question_text.lower()
        
        if any(word in question_lower for word in ['how often', 'frequency', 'how frequently']):
            return common_patterns['frequency']
        elif any(word in question_lower for word in ['difficulty', 'hard', 'difficult']):
            return common_patterns['difficulty']
        elif '?' in question_text and any(word in question_lower for word in ['do you', 'have you', 'are you']):
            return common_patterns['yes_no']
        else:
            return common_patterns['yes_no']  # Default fallback
    
    def _generate_transition_message(self, session, question_item) -> Optional[str]:
        """Generate transition message when moving to new term"""
        if not hasattr(session, 'current_term') or not session.current_term:
            return None
        
        if session.current_term != question_item.term:
            return f"Now let's move on to {question_item.term}."
        
        return None
    
    def _is_term_changing(self, session, new_question_item) -> bool:
        """Check if we're moving to a new term"""
        if not hasattr(session, 'current_term') or not session.current_term:
            return False
        
        return session.current_term != new_question_item.term
    
    def _update_evidence(self, session, user_response: str):
        """Update evidence tracking based on user response"""
        if not hasattr(session, 'evidence_count') or session.evidence_count is None:
            session.evidence_count = {}
        
        term = getattr(session, 'current_term', 'unknown')
        if term not in session.evidence_count:
            session.evidence_count[term] = 0
        
        # Simple evidence scoring - in production this would be more sophisticated
        response_lower = user_response.lower()
        if any(word in response_lower for word in ['yes', 'often', 'always', 'severe', 'difficult']):
            session.evidence_count[term] += 1
    
    def _evidence_threshold_met(self, session) -> bool:
        """Check if evidence threshold has been met for current term"""
        if (not hasattr(session, 'evidence_count') or 
            session.evidence_count is None or 
            not hasattr(session, 'current_term') or
            not session.current_term):
            return False
        
        term = session.current_term
        count = session.evidence_count.get(term, 0)
        
        return count >= self.evidence_threshold
    
    def _generate_info_cards(self, session, storage=None) -> List[Dict[str, Any]]:
        """Generate information cards when threshold is met or term completes"""
        if not self.info_provider or not hasattr(session, 'current_term'):
            return []
        
        # Get the most recent user response for context
        recent_response = "User has completed questions about this topic"
        if storage and hasattr(session, 'session_id'):
            try:
                turns = storage.list_turns(session.session_id)
                # Get the last user response
                user_turns = [t for t in turns if t.get('role') == 'user']
                if user_turns:
                    recent_response = user_turns[-1].get('content', recent_response)
            except Exception:
                pass
        
        try:
            # Force info card generation by bypassing the interval throttling
            # This ensures cards are generated at term completion
            original_last_info_turn = getattr(session, 'last_info_turn', None)
            session.last_info_turn = None  # Reset to force generation
            
            cards = self.info_provider.maybe_provide_info(
                session=session,
                last_answer=recent_response,
                current_pnm=getattr(session, 'current_pnm', None),
                current_term=getattr(session, 'current_term', None),
                storage=storage
            )
            
            # Restore the original value if no cards were generated
            if not cards:
                session.last_info_turn = original_last_info_turn
            
            return cards or []
        except Exception:
            return []
    
    def _generate_term_summary(self, session) -> str:
        """Generate summary message for completed term"""
        term = getattr(session, 'current_term', 'this topic')
        return f"Thank you for sharing information about {term}. This helps us understand your current situation better."
    
    def _handle_session_completion(self, session) -> QuestionResponse:
        """Handle completion of entire session"""
        # Generate final PNM awareness profile
        if hasattr(session, 'pnm_scores') and session.pnm_scores:
            profile = self.scoring_engine.calculate_overall_pnm_profile(session.pnm_scores)
            suggestions = self.scoring_engine.generate_improvement_suggestions(profile)
            
            # Store final profile in session
            session.pnm_profile = profile
            session.improvement_suggestions = suggestions
            
            completion_message = f"Assessment completed successfully. Your overall ALS awareness level: {profile.get('overall', {}).get('level', 'Not calculated')}"
        else:
            completion_message = "Assessment completed successfully."
        
        return QuestionResponse(
            question_text="Thank you for completing the assessment. You can review your responses in the data section or start a new topic.",
            question_type=QuestionType.MAIN,
            options=[],
            allow_text_input=False,
            transition_message=completion_message
        )
    
    def get_pnm_awareness_profile(self, session) -> Optional[Dict[str, Any]]:
        """Get current PNM awareness profile for the session"""
        if not hasattr(session, 'pnm_scores') or not session.pnm_scores:
            return None
        
        return self.scoring_engine.calculate_overall_pnm_profile(session.pnm_scores)