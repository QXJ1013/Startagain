# app/services/conversation_service.py
"""
Service for managing conversation lifecycle and state
"""
from __future__ import annotations
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid
import logging

from app.services.storage import Storage
from app.services.session import SessionState

log = logging.getLogger(__name__)


class ConversationService:
    """Manages conversation lifecycle, state transitions, and history"""
    
    def __init__(self, storage: Storage):
        self.storage = storage
    
    def create_conversation(
        self,
        user_id: str,
        conversation_type: str = "general",
        dimension_name: Optional[str] = None,
        title: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new conversation for a user
        
        Args:
            user_id: User ID
            conversation_type: 'general' or 'dimension_specific'
            dimension_name: Name of dimension if type is dimension_specific
            title: Optional custom title
            session_id: Session to link with conversation
        
        Returns:
            Created conversation details
        """
        # Check if user has active conversations that need interrupting
        active = self.get_active_conversation(user_id)
        if active:
            # Check user preferences for max active conversations
            prefs = self.storage.get_user_preferences(user_id)
            max_active = prefs.get('max_active_conversations', 1)
            
            if max_active == 1:
                # Interrupt the existing conversation
                log.info(f"Interrupting active conversation {active['id']} for user {user_id}")
                self.interrupt_conversation(active['id'])
        
        # Generate conversation ID
        conversation_id = f"conv_{uuid.uuid4().hex[:12]}"
        
        # Create session if not provided
        if not session_id:
            session_id = f"session_{uuid.uuid4().hex[:12]}"
            # Create session in database
            self.storage.upsert_session(
                session_id=session_id,
                user_id=user_id,
                status='active',
                fsm_state='ROUTE'
            )
        
        # Create the conversation
        self.storage.create_conversation(
            conversation_id=conversation_id,
            user_id=user_id,
            session_id=session_id,
            conversation_type=conversation_type,
            dimension_name=dimension_name,
            title=title
        )
        
        log.info(f"Created {conversation_type} conversation {conversation_id} for user {user_id}")
        
        return self.storage.get_conversation(conversation_id)
    
    def get_active_conversation(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user's active conversation"""
        return self.storage.get_active_conversation(user_id)
    
    def get_or_create_active_conversation(
        self,
        user_id: str,
        conversation_type: str = "general",
        dimension_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get existing active conversation or create a new one"""
        active = self.get_active_conversation(user_id)
        
        if active:
            # Check if it matches the requested type
            if active['conversation_type'] == conversation_type:
                if conversation_type == 'dimension_specific':
                    # Check if dimension matches
                    if active.get('dimension_name') == dimension_name:
                        return active
                else:
                    return active
        
        # No matching active conversation, create new one
        return self.create_conversation(
            user_id=user_id,
            conversation_type=conversation_type,
            dimension_name=dimension_name
        )
    
    def interrupt_conversation(self, conversation_id: str) -> None:
        """Interrupt an active conversation"""
        self.storage.interrupt_conversation(conversation_id)
        log.info(f"Interrupted conversation {conversation_id}")
    
    def complete_conversation(self, conversation_id: str) -> None:
        """Complete a conversation and generate summary"""
        # Get conversation details
        conv = self.storage.get_conversation(conversation_id)
        if not conv:
            raise ValueError(f"Conversation {conversation_id} not found")
        
        # Generate summary based on messages and scores
        summary = self._generate_summary(conversation_id)
        
        # Mark as completed
        self.storage.complete_conversation(conversation_id, summary)
        log.info(f"Completed conversation {conversation_id}")
    
    def update_conversation_title(
        self, 
        conversation_id: str, 
        title: str
    ) -> None:
        """Update conversation title"""
        self.storage.update_conversation(conversation_id, title=title)
    
    def get_user_conversations(
        self,
        user_id: str,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get user's conversation history"""
        return self.storage.get_user_conversations(
            user_id=user_id,
            status=status,
            limit=limit,
            offset=offset
        )
    
    def get_conversation_details(
        self, 
        conversation_id: str,
        include_messages: bool = True,
        include_info_cards: bool = True
    ) -> Dict[str, Any]:
        """Get full conversation details including messages and info cards"""
        # Get basic conversation info
        conversation = self.storage.get_conversation(conversation_id)
        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found")
        
        # Add messages if requested
        if include_messages:
            messages = self.storage.get_conversation_messages(conversation_id)
            conversation['messages'] = messages
        
        # Add info cards if requested
        if include_info_cards:
            info_cards = self.storage.get_conversation_info_cards(conversation_id)
            conversation['info_cards'] = info_cards
        
        return conversation
    
    def save_info_card(
        self,
        conversation_id: str,
        session_id: str,
        info_cards: List[Dict[str, Any]],
        turn_id: Optional[int] = None,
        pnm: Optional[str] = None,
        term: Optional[str] = None,
    ) -> None:
        """Save info cards for a conversation"""
        for idx, card in enumerate(info_cards):
            # Add display order
            card['order'] = idx
            
            self.storage.save_info_card(
                conversation_id=conversation_id,
                session_id=session_id,
                card_data=card,
                turn_id=turn_id,
                pnm=pnm,
                term=term
            )
        
        log.debug(f"Saved {len(info_cards)} info cards for conversation {conversation_id}")
    
    def link_turn_to_conversation(
        self,
        turn_index: int,
        session_id: str,
        conversation_id: str,
        role: str,
        content: str,
        meta: Optional[dict] = None
    ) -> int:
        """Add a turn and link it to conversation"""
        # First add the turn
        turn_id = self.storage.add_turn(
            session_id=session_id,
            turn_index=turn_index,
            role=role,
            content=content,
            meta=meta
        )
        
        # Link to conversation
        self.storage.link_turn_to_conversation(session_id, conversation_id)
        
        # Update conversation activity
        self.storage.update_conversation(conversation_id)
        
        return turn_id
    
    def check_interrupt_warning(self, user_id: str) -> Dict[str, Any]:
        """
        Check if user should be warned about interrupting active conversation
        
        Returns:
            Dict with 'should_warn' bool and 'active_conversation' details
        """
        prefs = self.storage.get_user_preferences(user_id)
        
        if not prefs.get('warn_on_interrupt', True):
            return {'should_warn': False, 'active_conversation': None}
        
        active = self.get_active_conversation(user_id)
        if active and active['status'] == 'active':
            return {
                'should_warn': True,
                'active_conversation': {
                    'id': active['id'],
                    'title': active.get('title', 'Untitled'),
                    'type': active.get('conversation_type', 'general'),
                    'dimension': active.get('dimension_name'),
                    'message_count': active.get('message_count', 0)
                }
            }
        
        return {'should_warn': False, 'active_conversation': None}
    
    def _generate_summary(self, conversation_id: str) -> str:
        """Generate summary for a completed conversation"""
        # Get conversation details
        conv = self.storage.get_conversation(conversation_id)
        
        # Get statistics
        messages = self.storage.get_conversation_messages(conversation_id, limit=5)
        info_cards = self.storage.get_conversation_info_cards(conversation_id)
        
        # Get session for scores
        session_id = conv.get('session_id')
        if session_id:
            term_scores = self.storage.list_term_scores(session_id)
            dim_scores = self.storage.list_dimension_scores(session_id)
        else:
            term_scores = []
            dim_scores = []
        
        # Build summary
        summary_parts = []
        
        # Type and focus
        if conv.get('conversation_type') == 'dimension_specific':
            summary_parts.append(f"Dimension assessment: {conv.get('dimension_name', 'Unknown')}")
        else:
            summary_parts.append("General assessment")
        
        # Statistics
        summary_parts.append(f"Messages: {conv.get('message_count', 0)}")
        summary_parts.append(f"Info cards: {len(info_cards)}")
        
        # Scores
        if dim_scores:
            avg_score = sum(d['score_0_7'] for d in dim_scores) / len(dim_scores)
            summary_parts.append(f"Avg dimension score: {avg_score:.1f}/7")
        
        if term_scores:
            summary_parts.append(f"Terms assessed: {len(term_scores)}")
        
        return " | ".join(summary_parts)


def get_conversation_service(storage: Storage) -> ConversationService:
    """Factory function to get conversation service instance"""
    return ConversationService(storage)