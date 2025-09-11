# app/routers/chat_unified.py - Unified Simple Conversation API
"""
Unified conversation endpoint that handles all chat interactions in a simple way.
This replaces the complex multi-endpoint approach with a single conversation API.
"""

from __future__ import annotations
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
import logging
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from app.deps import get_storage, get_question_bank, get_ai_router, get_current_user
from app.services.storage import DocumentStorage, ConversationDocument, ConversationMessage
from app.services.fsm import ConversationFSM
from app.services.question_bank import QuestionBank
from app.services.ai_routing import AIRouter
from app.services.info_provider_enhanced import EnhancedInfoProvider

log = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["unified-chat"])

# ---------- Request/Response Models ----------

class ConversationRequest(BaseModel):
    user_response: str = ""
    dimension_focus: Optional[str] = None
    request_info: bool = True

class ConversationResponse(BaseModel):
    # Essential response fields
    question_text: str
    question_type: str = "main"
    options: List[Dict[str, str]] = []
    allow_text_input: bool = True
    
    # Optional enhancement fields
    transition_message: Optional[str] = None
    info_cards: Optional[List[Dict[str, Any]]] = None
    
    # State tracking
    current_pnm: Optional[str] = None
    current_term: Optional[str] = None
    fsm_state: Optional[str] = None
    turn_index: int = 0
    
    # Dialogue mode control
    dialogue_mode: bool = False
    dialogue_content: Optional[str] = None
    should_continue_dialogue: bool = False
    
    # Conversation metadata
    conversation_id: str
    next_state: str = "continue"

# ---------- Core Logic Functions ----------

def _get_or_create_conversation(
    storage: DocumentStorage, 
    conversation_id: Optional[str], 
    user_id: str,
    dimension_focus: Optional[str] = None
) -> ConversationDocument:
    """Get existing conversation or create new one"""
    
    if conversation_id:
        doc = storage.get_conversation(conversation_id)
        if doc and doc.user_id == user_id:
            return doc
        elif conversation_id.startswith('temp-'):
            # Handle temporary IDs by creating new conversation
            pass
        else:
            raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Create new conversation
    conversation_type = "dimension" if dimension_focus else "general_chat"
    title = f"{dimension_focus} Assessment" if dimension_focus else "General Chat"
    
    return storage.create_conversation(
        user_id=user_id,
        type=conversation_type,
        dimension=dimension_focus,
        title=title
    )

def _process_user_input(
    conversation: ConversationDocument,
    user_input: str,
    storage: DocumentStorage,
    qb: QuestionBank,
    ai_router: AIRouter
) -> Dict[str, Any]:
    """Process user input and determine next response"""
    
    # Add user message if provided
    if user_input.strip():
        user_message = ConversationMessage(
            id=len(conversation.messages) + 1,
            role='user',
            content=user_input.strip(),
            type='text'
        )
        storage.add_message(conversation.id, user_message)
        conversation.messages.append(user_message)
    
    # Initialize FSM for this conversation
    fsm = ConversationFSM(storage, qb, ai_router, conversation)
    
    # Determine if we should enter dialogue mode (80% chance for natural conversation)
    import random
    should_dialogue = random.random() < 0.8
    
    if should_dialogue and user_input.strip():
        # Dialogue mode - natural conversation
        return _generate_dialogue_response(conversation, user_input)
    else:
        # Assessment mode - structured questions
        return _generate_assessment_response(conversation, fsm, qb)

def _generate_dialogue_response(conversation: ConversationDocument, user_input: str) -> Dict[str, Any]:
    """Generate natural dialogue response"""
    
    # Simple dialogue responses (can be enhanced with LLM later)
    dialogue_responses = [
        "I understand. Can you tell me more about how this affects your daily life?",
        "That sounds challenging. How are you managing with this situation?",
        "Thank you for sharing. What concerns you most about this?",
        "I hear you. What kind of support would be most helpful right now?",
        "That's important information. How has your family been handling this?"
    ]
    
    import random
    dialogue_content = random.choice(dialogue_responses)
    
    return {
        "question_text": dialogue_content,
        "question_type": "dialogue",
        "options": [],
        "allow_text_input": True,
        "dialogue_mode": True,
        "dialogue_content": dialogue_content,
        "should_continue_dialogue": True,
        "next_state": "dialogue"
    }

def _generate_assessment_response(
    conversation: ConversationDocument, 
    fsm: ConversationFSM, 
    qb: QuestionBank
) -> Dict[str, Any]:
    """Generate structured assessment response"""
    
    current_state = fsm.get_current_state()
    
    if current_state == 'ROUTE':
        # Route to appropriate PNM dimension
        # For now, start with Safety as default
        fsm.set_state('ASK_QUESTION')
        conversation = fsm.storage.update_assessment_state(
            conversation_id=conversation.id,
            current_pnm='Safety',
            current_term='Advance care directives'
        )
    
    # Get next question from question bank
    try:
        # Use proper question bank method
        question_item = qb.choose_for_term('Safety', 'Advance care directives', [])
        if question_item:
            options = []
            if question_item.options:
                options = [
                    {"value": opt.get("id", opt.get("value", str(i))), 
                     "label": opt.get("label", opt.get("text", str(opt)))} 
                    for i, opt in enumerate(question_item.options)
                ]
            
            return {
                "question_text": question_item.main,
                "question_type": "main",
                "options": options,
                "allow_text_input": True,
                "current_pnm": "Safety",
                "current_term": "Advance care directives",
                "question_id": question_item.id,
                "next_state": "ask_question"
            }
    except Exception as e:
        log.warning(f"Question bank error: {e}")
    
    # Fallback response
    return {
        "question_text": "How are you feeling about your current situation with ALS?",
        "question_type": "main", 
        "options": [
            {"value": "good", "label": "I'm managing well"},
            {"value": "concerned", "label": "I have some concerns"},
            {"value": "overwhelmed", "label": "I feel overwhelmed"},
            {"value": "other", "label": "Other"}
        ],
        "allow_text_input": True,
        "next_state": "continue"
    }

# ---------- Main Endpoint ----------

@router.post("/conversation", response_model=ConversationResponse)
async def conversation_endpoint(
    request: ConversationRequest,
    storage: DocumentStorage = Depends(get_storage),
    qb: QuestionBank = Depends(get_question_bank), 
    ai_router: AIRouter = Depends(get_ai_router),
    conversation_id: Optional[str] = Header(default=None, convert_underscores=False, alias="X-Conversation-Id"),
    current_user: dict = Depends(get_current_user)
):
    """
    Unified conversation endpoint that handles all chat interactions.
    
    This single endpoint replaces multiple chat endpoints and provides:
    - Natural dialogue mode (80% of interactions)
    - Structured assessment mode (20% of interactions) 
    - Automatic conversation management
    - Simple request/response pattern
    """
    
    try:
        # Get or create conversation
        conversation = _get_or_create_conversation(
            storage=storage,
            conversation_id=conversation_id,
            user_id=current_user["id"],
            dimension_focus=request.dimension_focus
        )
        
        # Process user input and generate response
        response_data = _process_user_input(
            conversation=conversation,
            user_input=request.user_response,
            storage=storage,
            qb=qb,
            ai_router=ai_router
        )
        
        # Build response
        response = ConversationResponse(
            conversation_id=conversation.id,
            turn_index=len(conversation.messages),
            **response_data
        )
        
        # Add info cards if requested
        if request.request_info and not response.dialogue_mode:
            # Simple info card for demo
            response.info_cards = [{
                "title": "ALS Support Information",
                "bullets": [
                    "Remember that you're not alone in this journey",
                    "Consider connecting with ALS support groups",
                    "Discuss treatment options with your healthcare team"
                ]
            }]
        
        return response
        
    except Exception as e:
        log.error(f"Conversation endpoint error: {e}")
        raise HTTPException(status_code=500, detail=f"Conversation error: {str(e)}")

# ---------- Health Check ----------

@router.get("/health")
async def chat_health():
    """Simple health check for chat system"""
    return {
        "status": "healthy",
        "endpoint": "/chat/conversation",
        "features": [
            "unified_conversation",
            "dialogue_mode",
            "assessment_mode", 
            "simple_database"
        ]
    }