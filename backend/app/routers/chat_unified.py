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
from app.services.enhanced_dialogue import (
    ConversationModeManager, 
    create_conversation_context, 
    convert_to_conversation_response
)

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
    """
    Process user input using Enhanced Dialogue Framework.
    
    STEP 1: Basic integration with new framework
    STEP 2: Will add RAG + LLM integration
    STEP 3: Will add advanced conversation features
    """
    
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
    
    # ENHANCED DIALOGUE INTEGRATION
    try:
        # Create conversation context for new framework
        context = create_conversation_context(conversation, user_input, ai_router)
        
        # Initialize enhanced dialogue manager
        mode_manager = ConversationModeManager(qb, ai_router)
        
        # Process conversation with enhanced framework
        dialogue_response = mode_manager.process_conversation(context)
        
        # Convert to expected API response format
        response_data = convert_to_conversation_response(dialogue_response)
        
        # Update conversation mode in storage for persistence
        if hasattr(storage, 'update_assessment_state'):
            storage.update_assessment_state(
                conversation_id=conversation.id,
                dialogue_mode=dialogue_response.mode.value,
                current_pnm=dialogue_response.current_pnm,
                current_term=dialogue_response.current_term
            )
        
        log.info(f"Enhanced dialogue processed: mode={dialogue_response.mode.value}, "
                f"type={dialogue_response.response_type.value}")
        
        return response_data
        
    except Exception as e:
        # Fallback to legacy system if enhanced dialogue fails
        log.warning(f"Enhanced dialogue failed, falling back to legacy: {e}")
        return _process_user_input_legacy(conversation, user_input, storage, qb, ai_router)


def _process_user_input_legacy(
    conversation: ConversationDocument,
    user_input: str,
    storage: DocumentStorage,
    qb: QuestionBank,
    ai_router: AIRouter
) -> Dict[str, Any]:
    """
    Legacy processing logic as fallback.
    Uses structured assessment mode only - random logic removed.
    """
    # Initialize FSM for this conversation
    fsm = ConversationFSM(storage, qb, ai_router, conversation)
    
    # Force intelligent mode selection - no random logic
    # Always use structured assessment mode in legacy fallback
    # Enhanced dialogue system handles intelligent mode selection
    return _generate_assessment_response(conversation, fsm, qb)

# _generate_dialogue_response function removed - hardcoded templates eliminated
# Enhanced Dialogue system handles all conversation generation via RAG+LLM

def _generate_assessment_response(
    conversation: ConversationDocument, 
    fsm: ConversationFSM, 
    qb: QuestionBank
) -> Dict[str, Any]:
    """Generate structured assessment response"""
    
    current_state = fsm.get_current_state()
    
    if current_state == 'ROUTE':
        # Route to appropriate PNM dimension using intelligent routing
        # Use enhanced dialogue system's reliable routing instead of hardcoded Safety
        try:
            from app.services.user_profile_manager import ReliableRoutingEngine
            reliable_router = ReliableRoutingEngine()
            routing_decision = reliable_router.get_reliable_route(conversation.user_id)
            
            recommended_pnm = routing_decision.get('pnm_dimension', 'Physiological')
            recommended_term = routing_decision.get('term', 'General assessment')
            
            fsm.set_state('ASK_QUESTION')
            conversation = fsm.storage.update_assessment_state(
                conversation_id=conversation.id,
                current_pnm=recommended_pnm,
                current_term=recommended_term
            )
        except Exception as e:
            # Fallback to first available question in question bank
            log.warning(f"Reliable routing failed, using question bank fallback: {e}")
            available_questions = qb.items() if hasattr(qb, 'items') else []
            if available_questions:
                first_question = available_questions[0]
                fsm.set_state('ASK_QUESTION')
                conversation = fsm.storage.update_assessment_state(
                    conversation_id=conversation.id,
                    current_pnm=first_question.pnm,
                    current_term=first_question.term
                )
            else:
                # Ultimate fallback
                fsm.set_state('ASK_QUESTION') 
                conversation = fsm.storage.update_assessment_state(
                    conversation_id=conversation.id,
                    current_pnm='Physiological',
                    current_term='General assessment'
                )
    
    # Get next question from question bank using current PNM/term
    try:
        # Use current assessment state instead of hardcoded values
        current_pnm = conversation.assessment_state.get('current_pnm', 'Physiological')
        current_term = conversation.assessment_state.get('current_term', 'General assessment')
        asked_questions = conversation.assessment_state.get('asked_questions', [])
        
        question_item = qb.choose_for_term(current_pnm, current_term, asked_questions)
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
    - Enhanced Dialogue system with intelligent mode selection
    - Database-driven routing with user profile optimization
    - AI-powered response generation via RAG+LLM
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