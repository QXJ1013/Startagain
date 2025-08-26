# app/routers/conversation.py
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Optional, Dict, Any, List
from pydantic import BaseModel

from app.deps import get_session_store, SessionStore, get_current_user, get_storage
from app.services.conversation_manager import ConversationManager
from app.services.storage import Storage
from app.services.conversation_service import ConversationService

router = APIRouter(prefix="/chat", tags=["conversation"])

# Pydantic models
class ConversationRequest(BaseModel):
    user_response: Optional[str] = None
    dimension_focus: Optional[str] = None

class ConversationResponse(BaseModel):
    question_text: str
    question_type: str
    options: List[Dict[str, str]]
    allow_text_input: bool = True
    transition_message: Optional[str] = None
    info_cards: Optional[List[Dict[str, Any]]] = None
    evidence_threshold_met: bool = False
    current_pnm: Optional[str] = None
    current_term: Optional[str] = None
    fsm_state: Optional[str] = None

class PNMProfileResponse(BaseModel):
    profile: Optional[Dict[str, Any]] = None
    suggestions: List[str] = []
    scores: List[Dict[str, Any]] = []

# Global conversation manager instance (lazy loading for hot reload)
conversation_manager = None

def get_conversation_manager():
    global conversation_manager
    if conversation_manager is None:
        conversation_manager = ConversationManager()
    return conversation_manager

@router.post("/conversation", response_model=ConversationResponse)
async def handle_conversation(
    conv_request: ConversationRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
    storage: Storage = Depends(get_storage)
):
    """Handle conversation flow - get next question or process user response"""
    try:
        # Get or create conversation for user
        conv_service = ConversationService(storage)
        
        # Determine conversation type
        conv_type = "dimension_specific" if conv_request.dimension_focus else "general"
        
        # Get or create active conversation
        conversation = conv_service.get_or_create_active_conversation(
            user_id=current_user["id"],
            conversation_type=conv_type,
            dimension_name=conv_request.dimension_focus
        )
        
        # Use conversation's session_id
        session_id = conversation["session_id"]
        conversation_id = conversation["id"]
        
        # Get session
        session_store = get_session_store(session_id)
        session = session_store.get_session()
        
        # Ensure session is associated with current user
        storage.upsert_session(
            session_id=session_id,
            user_id=current_user["id"],
            fsm_state=getattr(session, 'fsm_state', 'ROUTE')
        )
        
        # Get next question in conversation flow
        response = get_conversation_manager().get_next_question(
            session=session,
            user_response=conv_request.user_response,
            storage=storage,
            dimension_focus=conv_request.dimension_focus
        )
        
        # Save session state after processing
        session_store.save_session()
        
        # Save info cards if present
        if response.info_cards:
            conv_service.save_info_card(
                conversation_id=conversation_id,
                session_id=session_id,
                info_cards=response.info_cards,
                pnm=getattr(session, 'current_pnm', None),
                term=getattr(session, 'current_term', None)
            )
        
        # Link any new turns to conversation
        storage.link_turn_to_conversation(session_id, conversation_id)
        
        # Convert internal response to API response
        return ConversationResponse(
            question_text=response.question_text,
            question_type=response.question_type.value,
            options=[{"value": opt["value"], "label": opt["label"]} for opt in response.options],
            allow_text_input=response.allow_text_input,
            transition_message=response.transition_message,
            info_cards=response.info_cards,
            evidence_threshold_met=response.evidence_threshold_met,
            current_pnm=getattr(session, 'current_pnm', None),
            current_term=getattr(session, 'current_term', None),
            fsm_state=getattr(session, 'fsm_state', None)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Conversation error: {str(e)}")

@router.get("/pnm-profile", response_model=PNMProfileResponse)
async def get_pnm_profile(request: Request, current_user: dict = Depends(get_current_user)):
    """Get current PNM awareness profile for the session"""
    try:
        # Extract session ID from header, fallback to user-specific session
        session_id = request.headers.get("X-Session-Id", f"user_{current_user['id']}_default")
        session_store = get_session_store(session_id)
        session = session_store.get_session()
        
        # Ensure session is associated with current user
        storage = Storage()
        storage.upsert_session(
            session_id=session_id,
            user_id=current_user["id"],
            fsm_state=getattr(session, 'fsm_state', 'ROUTE')
        )
        
        # Get PNM profile from conversation manager
        profile = get_conversation_manager().get_pnm_awareness_profile(session)
        
        # Get improvement suggestions
        suggestions = []
        scores = []
        
        if profile and hasattr(session, 'pnm_scores') and session.pnm_scores:
            suggestions = get_conversation_manager().scoring_engine.generate_improvement_suggestions(profile)
            
            # Convert PNMScore objects to dictionaries
            scores = [
                {
                    "pnm_level": score.pnm_level,
                    "domain": score.domain,
                    "awareness_score": score.awareness_score,
                    "understanding_score": score.understanding_score,
                    "coping_score": score.coping_score,
                    "action_score": score.action_score,
                    "total_score": score.total_score,
                    "percentage": score.percentage
                }
                for score in session.pnm_scores
            ]
        
        return PNMProfileResponse(
            profile=profile,
            suggestions=suggestions,
            scores=scores
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Profile error: {str(e)}")

@router.get("/conversation-state")
async def get_conversation_state(request: Request):
    """Get current conversation state for debugging"""
    try:
        # Extract session ID from header, fallback to default
        session_id = request.headers.get("X-Session-Id", "default_session")
        session_store = get_session_store(session_id)
        session = session_store.get_session()
        
        return {
            "session_id": session.session_id,
            "current_qid": getattr(session, 'current_qid', None),
            "current_pnm": getattr(session, 'current_pnm', None),
            "current_term": getattr(session, 'current_term', None),
            "followup_ptr": getattr(session, 'followup_ptr', None),
            "evidence_count": getattr(session, 'evidence_count', {}),
            "turn_index": getattr(session, 'turn_index', 0),
            "asked_qids": getattr(session, 'asked_qids', []),
            "pnm_scores_count": len(getattr(session, 'pnm_scores', [])),
            "keyword_pool": getattr(session, 'keyword_pool', []),
            "ai_confidence": getattr(session, 'ai_confidence', 0.0),
            "routing_method": getattr(session, 'routing_method', None)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"State error: {str(e)}")

@router.post("/debug-session")
async def debug_session(request: Request):
    """Debug endpoint to check session information"""
    try:
        session_id = request.headers.get("X-Session-Id", "default_session")
        session_store = get_session_store(session_id)
        session = session_store.get_session()
        
        return {
            "received_header": session_id,
            "session_object_id": session.session_id,
            "asked_qids": getattr(session, 'asked_qids', []),
            "asked_count": len(getattr(session, 'asked_qids', [])),
            "current_qid": getattr(session, 'current_qid', None)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Debug error: {str(e)}")

@router.get("/debug-question-bank")
async def debug_question_bank():
    """Debug endpoint to check question bank status"""
    try:
        questions = get_conversation_manager().question_bank.questions
        available_questions = [q.id for q in questions]
        
        return {
            "total_questions": len(questions),
            "available_question_ids": available_questions,
            "question_bank_path": get_conversation_manager().cfg.QUESTION_BANK_PATH,
            "first_question_sample": {
                "id": questions[0].id,
                "pnm": questions[0].pnm,
                "term": questions[0].term,
                "main": questions[0].main[:100] + "..." if questions[0].main else None
            } if questions else None
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Debug error: {str(e)}")