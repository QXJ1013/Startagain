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
# Removed import: EnhancedInfoProvider was zombie code
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

    # AI response content (for test compatibility)
    response: str = ""

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
        print(f"[STORAGE_DEBUG] Looking for conversation: {conversation_id}")
        doc = storage.get_conversation(conversation_id)
        print(f"[STORAGE_DEBUG] Found conversation: {doc is not None}")

        if doc:
            print(f"[STORAGE_DEBUG] Conversation has {len(doc.messages)} messages")
            if doc.user_id == user_id:
                return doc
            else:
                # Conversation exists but belongs to different user
                raise HTTPException(status_code=403, detail="Access denied to conversation")
        elif conversation_id.startswith('temp-'):
            # Handle temporary IDs by creating new conversation
            pass
        else:
            # Conversation doesn't exist, create new one with the provided ID
            # This allows frontend to specify conversation IDs
            conversation_type = "dimension" if dimension_focus else "general_chat"
            title = f"{dimension_focus} Assessment" if dimension_focus else "General Chat"

            try:
                new_conv = storage.create_conversation_with_id(
                    conversation_id=conversation_id,
                    user_id=user_id,
                    type=conversation_type,
                    dimension=dimension_focus,
                    title=title
                )
                return new_conv
            except ValueError as e:
                # If there's an error (like ID already exists), fall through to creating new conversation
                pass

    # Create new conversation (only if no conversation_id provided or creation with ID failed)
    print(f"[STORAGE_DEBUG] Creating new conversation - conversation_id was: {conversation_id}")
    conversation_type = "dimension" if dimension_focus else "general_chat"
    title = f"{dimension_focus} Assessment" if dimension_focus else "General Chat"

    new_conv = storage.create_conversation(
        user_id=user_id,
        type=conversation_type,
        dimension=dimension_focus,
        title=title
    )
    print(f"[STORAGE_DEBUG] Created new conversation: {new_conv.id}")
    return new_conv

async def _process_user_input(
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
        # storage.add_message() returns updated conversation object with the new message
        conversation = storage.add_message(conversation.id, user_message)
        print(f"[CONVERSATION_DEBUG] After adding user message: {len(conversation.messages)} messages")
    
    # ENHANCED DIALOGUE INTEGRATION
    try:
        # Create conversation context for new framework
        context = create_conversation_context(conversation, user_input, ai_router)
        
        # Initialize enhanced dialogue manager
        mode_manager = ConversationModeManager(qb, ai_router, storage)
        print(f"[CHAT_UNIFIED] mode_manager type: {type(mode_manager)}")
        print(f"[CHAT_UNIFIED] About to call process_conversation")

        # Process conversation with enhanced framework
        print(f"[CHAT_UNIFIED] About to call process_conversation with context.turn_count={context.turn_count}")
        dialogue_response = await mode_manager.process_conversation(context)
        print(f"[CHAT_UNIFIED] process_conversation completed, response_type={dialogue_response.response_type.value}")
        
        # Convert to expected API response format
        response_data = convert_to_conversation_response(dialogue_response)

        # Store AI response in database (centralized storage for all response types)
        try:
            # CRITICAL: Preserve assessment_state before storage to prevent loss of question_context
            preserved_assessment_state = conversation.assessment_state.copy()

            ai_response_message = ConversationMessage(
                id=len(conversation.messages) + 1,
                role='assistant',
                content=dialogue_response.content,
                type=('question' if dialogue_response.response_type.value == 'question'
                      else 'summary' if dialogue_response.response_type.value == 'summary'
                      else 'response'),
                metadata={
                    'response_type': dialogue_response.response_type.value,
                    'mode': dialogue_response.mode.value,
                    'current_pnm': dialogue_response.current_pnm,
                    'current_term': dialogue_response.current_term,
                    'question_id': getattr(dialogue_response, 'question_id', None),
                    'options': dialogue_response.options or []
                }
            )
            # Add message to conversation and update conversation object
            conversation = storage.add_message(conversation.id, ai_response_message)

            # CRITICAL: Restore assessment_state to prevent loss of scoring context
            conversation.assessment_state.update(preserved_assessment_state)
            print(f"[CHAT_UNIFIED] Preserved assessment_state during AI response storage")

            print(f"[CHAT_UNIFIED] Stored AI response message: {dialogue_response.content[:50]}...")
        except Exception as e:
            print(f"[CHAT_UNIFIED] Error storing AI response: {e}")
            import traceback
            print(f"[CHAT_UNIFIED] AI response storage traceback: {traceback.format_exc()}")

        # Update conversation mode in storage for persistence
        if hasattr(storage, 'update_assessment_state'):
            # Update the assessment state in the conversation object first
            conversation.assessment_state['dialogue_mode'] = dialogue_response.mode.value
            if dialogue_response.current_pnm:
                conversation.assessment_state['current_pnm'] = dialogue_response.current_pnm
            if dialogue_response.current_term:
                conversation.assessment_state['current_term'] = dialogue_response.current_term

            # CRITICAL: Update asked_questions list when a question is generated
            if dialogue_response.response_type.value == 'question':
                question_id = getattr(dialogue_response, 'question_id', None)
                if question_id:
                    asked_questions = conversation.assessment_state.get('asked_questions', [])
                    if question_id not in asked_questions:
                        asked_questions.append(question_id)
                        conversation.assessment_state['asked_questions'] = asked_questions
                        print(f"[CHAT_UNIFIED] Added question {question_id} to asked_questions: {asked_questions}")

            # Check if conversation is completed (based on enhanced dialogue signals)
            conversation_locked = conversation.assessment_state.get('conversation_locked', False)
            response_type_value = dialogue_response.response_type.value
            is_summary = response_type_value == 'summary'

            print(f"[CHAT_UNIFIED] Completion check: locked={conversation_locked}, response_type='{response_type_value}', is_summary={is_summary}")

            if conversation_locked or is_summary:
                print(f"[CHAT_UNIFIED] Conversation completed, updating status")
                conversation.status = 'completed'

                # Set completion timestamp
                from datetime import datetime
                conversation.assessment_state['completed_at'] = datetime.now().isoformat()

                print(f"[CHAT_UNIFIED] Conversation {conversation.id} marked as completed")

            # Save the updated conversation (this preserves current_question_index)
            storage.update_conversation(conversation)
        
        log.info(f"Enhanced dialogue processed: mode={dialogue_response.mode.value}, "
                f"type={dialogue_response.response_type.value}")
        
        return response_data
        
    except Exception as e:
        # Fallback to legacy system if enhanced dialogue fails
        import traceback
        log.warning(f"Enhanced dialogue failed, falling back to legacy: {e}")
        log.warning(f"Full traceback: {traceback.format_exc()}")
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
    # Check if this is a UC2 dimension conversation - if so, avoid state modifications
    is_uc2_conversation = (conversation.type == "dimension" and conversation.dimension)
    log.warning(f"Legacy fallback check: type='{conversation.type}', dimension='{conversation.dimension}', is_uc2={is_uc2_conversation}")

    if is_uc2_conversation:
        log.warning(f"Legacy fallback called for UC2 conversation {conversation.id} - UC2 system failed")
        # Return a simple error response without modifying conversation state
        return {
            "question_text": f"There was an issue processing your {conversation.dimension} assessment. Please try again.",
            "question_type": "error",
            "options": [],
            "allow_text_input": True,
            "current_pnm": conversation.assessment_state.get('current_pnm', conversation.dimension),
            "current_term": conversation.assessment_state.get('current_term', 'Assessment'),
            "next_state": "retry"
        }

    # Initialize FSM for this conversation
    fsm = ConversationFSM(storage, qb, ai_router, conversation)
    
    # Force intelligent mode selection - no random logic
    # Always use structured assessment mode in legacy fallback
    # Enhanced dialogue system handles intelligent mode selection
    return _generate_assessment_response(conversation, fsm, qb, ai_router)

# _generate_dialogue_response function removed - hardcoded templates eliminated
# Enhanced Dialogue system handles all conversation generation via RAG+LLM

def _generate_assessment_response(
    conversation: ConversationDocument,
    fsm: ConversationFSM,
    qb: QuestionBank,
    ai_router: AIRouter
) -> Dict[str, Any]:
    """Generate structured assessment response"""
    
    current_state = fsm.get_current_state()
    
    if current_state == 'ROUTE':
        # Route to appropriate PNM dimension using AI routing instead of database routing
        try:
            # Use AI router for intelligent routing based on user input
            user_messages = [msg for msg in conversation.messages if msg.role == 'user']
            if user_messages:
                latest_input = user_messages[-1].content
                routing_result = ai_router.route_query(latest_input)
                recommended_pnm = routing_result.pnm
                recommended_term = routing_result.term
            else:
                # No user input yet, start with physiological basics
                recommended_pnm = 'Physiological'
                recommended_term = 'General health'

            fsm.set_state('ASK_QUESTION')
            conversation = fsm.storage.update_assessment_state(
                conversation_id=conversation.id,
                current_pnm=recommended_pnm,
                current_term=recommended_term
            )
        except Exception as e:
            # Fallback to first available question in question bank
            log.warning(f"AI routing failed, using question bank fallback: {e}")
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
                    current_term='General health'
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
                "current_pnm": current_pnm,
                "current_term": current_term,
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
        print(f"[CONVERSATION_DEBUG] Initial conversation: {len(conversation.messages)} messages")
        
        # Process user input and generate response
        response_data = await _process_user_input(
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
        
        # DISABLE hardcoded info cards - let Enhanced Dialogue provide contextual cards when appropriate
        # This prevents repetitive template responses and allows natural conversation flow
        # Enhanced Dialogue will provide info cards based on actual conversation context
        pass
        
        return response
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        log.error(f"Conversation endpoint error: {e}")
        log.error(f"Full traceback: {error_details}")
        raise HTTPException(status_code=500, detail=f"Conversation error: {str(e)} | Type: {type(e).__name__}")

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