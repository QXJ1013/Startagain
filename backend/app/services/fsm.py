# app/services/fsm.py - Simplified Document-based Conversation FSM
"""
Simplified FSM for document-based conversations.
States: ROUTE -> ASK -> PROCESS -> SCORE -> CONTINUE
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from app.services.storage import DocumentStorage, ConversationDocument, ConversationMessage
from app.services.question_bank import QuestionBank
from app.services.ai_routing import AIRouter
from app.services.pnm_scoring import PNMScoringEngine, PNMScore

log = logging.getLogger(__name__)

class ConversationFSM:
    """Simplified Document-based Finite State Machine"""
    
    def __init__(
        self,
        storage: DocumentStorage,
        qb: QuestionBank,
        ai_router: AIRouter,
        conversation: ConversationDocument
    ):
        self.storage = storage
        self.qb = qb
        self.ai_router = ai_router
        self.conversation = conversation
        self.scoring_engine = PNMScoringEngine()
        
        # Simplified configuration
        self.evidence_threshold = 3
        self.max_questions_per_term = 5
        
    def get_current_state(self) -> str:
        """Get current FSM state"""
        return self.conversation.assessment_state.get('fsm_state', 'ROUTE')
    
    def set_state(self, state: str):
        """Update FSM state"""
        self.conversation = self.storage.update_assessment_state(
            conversation_id=self.conversation.id,
            fsm_state=state
        )
    
    def get_turn_index(self) -> int:
        """Get current turn index"""
        return len(self.conversation.messages)
    
    def process_user_input(self, user_input: str) -> Dict[str, Any]:
        """
        Main FSM processing method - simplified for document approach
        """
        current_state = self.get_current_state()
        
        # Add user message
        if user_input.strip():
            self._add_user_message(user_input)
        
        # Process based on current state
        if current_state == 'ROUTE':
            return self._handle_routing(user_input)
        elif current_state == 'ASK':
            return self._handle_question_response(user_input)
        elif current_state == 'PROCESS':
            return self._handle_processing()
        elif current_state == 'SCORE':
            return self._handle_scoring(user_input)
        else:
            return self._handle_continue()
    
    def _add_user_message(self, user_input: str):
        """Add user message to conversation"""
        message = ConversationMessage(
            id=len(self.conversation.messages) + 1,
            role='user',
            content=user_input,
            type='text'
        )
        self.storage.add_message(self.conversation.id, message)
        self.conversation.messages.append(message)
    
    def _handle_routing(self, user_input: str) -> Dict[str, Any]:
        """Handle initial routing to PNM dimension"""
        try:
            # Simple routing based on keywords using correct method name
            routing_result = self.ai_router.route_query(user_input)
            pnm = routing_result.pnm
            term = routing_result.term
            
            # Update conversation state
            self.storage.update_assessment_state(
                conversation_id=self.conversation.id,
                current_pnm=pnm,
                current_term=term,
                fsm_state='ASK'
            )
            
            return self._get_next_question(pnm, term)
            
        except Exception as e:
            log.warning(f"Routing failed: {e}, using default")
            return self._get_default_question()
    
    def _handle_question_response(self, user_input: str) -> Dict[str, Any]:
        """Handle response to assessment question"""
        current_pnm = self.conversation.assessment_state.get('current_pnm')
        current_term = self.conversation.assessment_state.get('current_term')
        
        # Count user responses for this term
        user_messages = [m for m in self.conversation.messages if m.role == 'user']
        responses_for_term = len(user_messages)
        
        # Check if we should score
        if responses_for_term >= self.evidence_threshold:
            return self._handle_scoring(user_input)
        else:
            # Continue asking questions
            return self._get_next_question(current_pnm, current_term)
    
    def _handle_scoring(self, user_input: str) -> Dict[str, Any]:
        """Handle scoring for current term"""
        current_pnm = self.conversation.assessment_state.get('current_pnm')
        current_term = self.conversation.assessment_state.get('current_term')
        
        try:
            # Get user messages for this term
            user_messages = [m.content for m in self.conversation.messages if m.role == 'user']
            combined_text = ' '.join(user_messages[-3:])  # Use last 3 responses
            
            # Generate score using the correct method name
            score = self.scoring_engine.score_response(
                user_response=combined_text,
                pnm_level=current_pnm,
                domain=current_term
            )
            
            # Save score to document
            self._save_score(current_pnm, current_term, score)
            
            # Check if PNM dimension is complete
            if self._is_pnm_complete(current_pnm):
                return self._complete_pnm(current_pnm)
            else:
                return self._move_to_next_term(current_pnm)
                
        except Exception as e:
            log.error(f"Scoring error: {e}")
            return self._handle_continue()
    
    def _handle_processing(self) -> Dict[str, Any]:
        """Handle processing state"""
        self.set_state('ASK')
        return self._handle_continue()
    
    def _handle_continue(self) -> Dict[str, Any]:
        """Handle continuation or completion"""
        current_pnm = self.conversation.assessment_state.get('current_pnm')
        current_term = self.conversation.assessment_state.get('current_term')
        
        if current_pnm and current_term:
            return self._get_next_question(current_pnm, current_term)
        else:
            return self._get_default_question()
    
    def _get_next_question(self, pnm: str, term: str) -> Dict[str, Any]:
        """Get next question for PNM/term"""
        try:
            # Get already asked question IDs from conversation messages  
            asked_qids = []
            for msg in self.conversation.messages:
                if msg.role == 'assistant' and hasattr(msg, 'question_id'):
                    asked_qids.append(msg.question_id)
            
            # Choose next question using the correct method
            question_item = self.qb.choose_for_term(pnm, term, asked_qids)
            
            if question_item:
                options = []
                if question_item.options:
                    options = [
                        {'value': opt.get('id', opt.get('value', str(i))), 
                         'label': opt.get('label', opt.get('text', str(opt)))} 
                        for i, opt in enumerate(question_item.options)
                    ]
                
                return {
                    'question_text': question_item.main,
                    'question_type': 'assessment',
                    'options': options,
                    'current_pnm': pnm,
                    'current_term': term,
                    'question_id': question_item.id,
                    'next_state': 'ask_question'
                }
        except Exception as e:
            log.warning(f"Question retrieval failed: {e}")
        
        return self._get_default_question()
    
    def _get_default_question(self) -> Dict[str, Any]:
        """Get default fallback question from question bank"""
        try:
            # Try to get a general question from question bank
            fallback_question = self.qb.choose_for_term('Physiological', 'Breathing', [])
            
            if fallback_question:
                options = []
                if fallback_question.options:
                    options = [
                        {'value': opt.get('id', opt.get('value', str(i))), 
                         'label': opt.get('label', opt.get('text', str(opt)))} 
                        for i, opt in enumerate(fallback_question.options)
                    ]
                else:
                    # Default severity options if no specific options
                    options = [
                        {'value': 'minimal', 'label': 'Minimal impact'},
                        {'value': 'moderate', 'label': 'Moderate impact'},
                        {'value': 'significant', 'label': 'Significant impact'},
                        {'value': 'severe', 'label': 'Severe impact'}
                    ]
                
                return {
                    'question_text': fallback_question.main,
                    'question_type': 'assessment',
                    'options': options,
                    'current_pnm': 'Physiological',
                    'current_term': 'Breathing',
                    'question_id': fallback_question.id,
                    'next_state': 'continue'
                }
        except Exception as e:
            log.warning(f"Failed to get default question from question bank: {e}")
        
        # Final hardcoded fallback (should rarely be used)
        return {
            'question_text': 'How has ALS been affecting your daily activities?',
            'question_type': 'general',
            'options': [
                {'value': 'minimal', 'label': 'Minimal impact'},
                {'value': 'moderate', 'label': 'Moderate impact'},
                {'value': 'significant', 'label': 'Significant impact'},
                {'value': 'severe', 'label': 'Severe impact'}
            ],
            'next_state': 'continue'
        }
    
    def _save_score(self, pnm: str, term: str, score: PNMScore):
        """Save score to conversation document"""
        if 'scores' not in self.conversation.assessment_state:
            self.conversation.assessment_state['scores'] = {}
        
        if pnm not in self.conversation.assessment_state['scores']:
            self.conversation.assessment_state['scores'][pnm] = {}
        
        self.conversation.assessment_state['scores'][pnm][term] = {
            'total_score': score.total_score,
            'awareness_score': score.awareness_score,
            'understanding_score': score.understanding_score,
            'coping_score': score.coping_score,
            'action_score': score.action_score,
            'percentage': score.percentage,
            'timestamp': datetime.now().isoformat(),
            'status': 'completed'
        }
        
        # Also save to index table for quick queries
        self.storage.add_score(self.conversation.id, pnm, term, score.total_score)
        
        # Update conversation
        self.storage.update_conversation(self.conversation)
    
    def _is_pnm_complete(self, pnm: str) -> bool:
        """Check if PNM dimension assessment is complete"""
        scores = self.conversation.assessment_state.get('scores', {})
        pnm_scores = scores.get(pnm, {})
        
        # Load completion threshold from config, fallback to 1
        completion_threshold = getattr(self, 'evidence_threshold', 1)
        return len(pnm_scores) >= completion_threshold
    
    def _complete_pnm(self, pnm: str) -> Dict[str, Any]:
        """Complete PNM dimension assessment"""
        # Calculate dimension aggregate score
        scores = self.conversation.assessment_state.get('scores', {})
        pnm_scores = scores.get(pnm, {})
        
        if pnm_scores:
            avg_score = sum(term_data['total_score'] for term_data in pnm_scores.values()) / len(pnm_scores)
            avg_percentage = sum(term_data['percentage'] for term_data in pnm_scores.values()) / len(pnm_scores)
        else:
            avg_score = 0
            avg_percentage = 0
        
        return {
            'question_text': f'Thank you for completing the {pnm} assessment. Your overall score: {avg_percentage:.1f}%',
            'question_type': 'completion',
            'options': [
                {'value': 'continue', 'label': 'Continue to next area'},
                {'value': 'review', 'label': 'Review my results'},
                {'value': 'finish', 'label': 'Finish assessment'}
            ],
            'next_state': 'completed',
            'pnm_completed': pnm,
            'pnm_score': avg_percentage
        }
    
    def _move_to_next_term(self, pnm: str) -> Dict[str, Any]:
        """Move to next term in current PNM"""
        # For simplicity, complete the PNM after one term
        return self._complete_pnm(pnm)
    
    def generate_info_cards(self, pnm: str = None) -> List[Dict[str, Any]]:
        """Generate info cards based on current conversation state"""
        cards = []
        
        if pnm:
            cards.append({
                'title': f'{pnm} Support Information',
                'bullets': [
                    f'Understanding {pnm.lower()} needs is important for ALS care',
                    'Consider discussing these areas with your healthcare team',
                    'Support groups can provide valuable insights and assistance'
                ],
                'source': 'ALS Assistant'
            })
        
        return cards