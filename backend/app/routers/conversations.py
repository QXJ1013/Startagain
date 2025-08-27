# app/routers/conversations.py
"""
API endpoints for conversation history management
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.deps import get_storage, get_current_user, get_conversation_service
from app.services.conversation_service import ConversationService

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


# Request/Response models
class CreateConversationRequest(BaseModel):
    conversation_type: str = "general"
    dimension_name: Optional[str] = None
    title: Optional[str] = None


class UpdateConversationRequest(BaseModel):
    title: Optional[str] = None
    status: Optional[str] = None


class ConversationResponse(BaseModel):
    id: str
    user_id: str
    title: Optional[str]
    conversation_type: str
    dimension_name: Optional[str]
    status: str
    session_id: str
    started_at: str
    completed_at: Optional[str]
    last_activity: str
    message_count: int
    info_card_count: int
    summary: Optional[str]
    current_pnm: Optional[str]
    current_term: Optional[str]


class MessageResponse(BaseModel):
    id: int
    turn_index: int
    role: str
    text: str
    meta: dict
    created_at: str


class InfoCardResponse(BaseModel):
    id: int
    card_type: str
    card_data: dict
    created_at: str


class ConversationDetailResponse(BaseModel):
    conversation: ConversationResponse
    messages: Optional[List[MessageResponse]] = None
    info_cards: Optional[List[InfoCardResponse]] = None


class InterruptWarningResponse(BaseModel):
    should_warn: bool
    active_conversation: Optional[Dict[str, Any]] = None


# Dependency to get conversation service
def get_conversation_service(storage = Depends(get_storage)) -> ConversationService:
    return ConversationService(storage)


@router.get("/", response_model=List[ConversationResponse])
async def get_user_conversations(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service)
):
    """Get user's conversation history"""
    conversations = service.get_user_conversations(
        user_id=current_user["id"],
        status=status,
        limit=limit,
        offset=offset
    )
    
    return [ConversationResponse(**conv) for conv in conversations]


@router.post("/", response_model=ConversationResponse)
async def create_conversation(
    request: CreateConversationRequest,
    current_user: dict = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service)
):
    """Create a new conversation"""
    conversation = service.create_conversation(
        user_id=current_user["id"],
        conversation_type=request.conversation_type,
        dimension_name=request.dimension_name,
        title=request.title
    )
    
    return ConversationResponse(**conversation)


@router.get("/active", response_model=Optional[ConversationResponse])
async def get_active_conversation(
    current_user: dict = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service)
):
    """Get user's current active conversation"""
    active = service.get_active_conversation(current_user["id"])
    
    if not active:
        return None
    
    return ConversationResponse(**active)


@router.get("/check-interrupt", response_model=InterruptWarningResponse)
async def check_interrupt_warning(
    current_user: dict = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service)
):
    """Check if user should be warned about interrupting active conversation"""
    result = service.check_interrupt_warning(current_user["id"])
    return InterruptWarningResponse(**result)


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation_details(
    conversation_id: str,
    include_messages: bool = Query(True, description="Include message history"),
    include_cards: bool = Query(True, description="Include info cards"),
    current_user: dict = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
    storage = Depends(get_storage)
):
    """Get detailed conversation information"""
    # Verify conversation belongs to user
    conversation = storage.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    if conversation["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get full details
    details = service.get_conversation_details(
        conversation_id=conversation_id,
        include_messages=include_messages,
        include_info_cards=include_cards
    )
    
    # Return raw details directly - let Pydantic handle the conversion
    return details


@router.put("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: str,
    request: UpdateConversationRequest,
    current_user: dict = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
    storage = Depends(get_storage)
):
    """Update conversation (e.g., edit title)"""
    # Verify conversation belongs to user
    conversation = storage.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    if conversation["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Update fields
    update_data = request.dict(exclude_unset=True)
    if update_data:
        storage.update_conversation(conversation_id, **update_data)
    
    # Return updated conversation
    updated = storage.get_conversation(conversation_id)
    return ConversationResponse(**updated)


class AddMessageRequest(BaseModel):
    role: str  # 'user' or 'assistant'
    text: str
    meta: Optional[Dict[str, Any]] = {}


class MessageResponse(BaseModel):
    id: int
    turn_index: int
    role: str
    text: str
    meta: Optional[Dict[str, Any]]
    created_at: str


@router.post("/{conversation_id}/messages")
async def add_message(
    conversation_id: str,
    request: AddMessageRequest,
    current_user: dict = Depends(get_current_user),
    storage = Depends(get_storage)
):
    """Add a message to the conversation"""
    # Verify conversation belongs to user
    conversation = storage.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    if conversation["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get session_id from conversation
    session_id = conversation["session_id"]
    
    # Ensure session exists in sessions table
    storage.ensure_session(session_id)
    
    # Store the message
    turn_index = storage.get_message_count(session_id)
    
    # Save to turns table
    storage.add_turn(
        session_id=session_id,
        turn_index=turn_index,
        role=request.role,
        content=request.text,
        meta=request.meta
    )
    
    # Increment message count in conversation
    storage.increment_message_count(conversation_id)
    
    # Return the created message
    return {
        "id": turn_index,
        "turn_index": turn_index,
        "role": request.role,
        "text": request.text,
        "meta": request.meta,
        "created_at": datetime.now().isoformat()
    }


class AddInfoCardRequest(BaseModel):
    card_type: str
    card_data: Dict[str, Any]


class InfoCardResponse(BaseModel):
    id: int
    card_type: str
    card_data: Dict[str, Any]
    created_at: str


@router.post("/{conversation_id}/info-cards", response_model=InfoCardResponse)
async def add_info_card(
    conversation_id: str,
    request: AddInfoCardRequest,
    current_user: dict = Depends(get_current_user),
    storage = Depends(get_storage)
):
    """Add an info card to the conversation"""
    # Verify conversation belongs to user
    conversation = storage.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    if conversation["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Save info card
    session_id = conversation["session_id"]
    card_id = storage.save_info_card(conversation_id, session_id, request.card_data, request.card_type)
    
    # Increment info card count in conversation  
    storage.increment_info_card_count(conversation_id)
    
    return InfoCardResponse(
        id=card_id,
        card_type=request.card_type,
        card_data=request.card_data,
        created_at=datetime.now().isoformat()
    )


@router.post("/{conversation_id}/complete", response_model=ConversationResponse)
async def complete_conversation(
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
    storage = Depends(get_storage)
):
    """Mark conversation as completed"""
    # Verify conversation belongs to user
    conversation = storage.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    if conversation["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Complete the conversation
    service.complete_conversation(conversation_id)
    
    # Return updated conversation
    completed = storage.get_conversation(conversation_id)
    return ConversationResponse(**completed)


@router.post("/{conversation_id}/interrupt", response_model=ConversationResponse)
async def interrupt_conversation(
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
    storage = Depends(get_storage)
):
    """Interrupt an active conversation"""
    # Verify conversation belongs to user
    conversation = storage.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    if conversation["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Interrupt the conversation
    service.interrupt_conversation(conversation_id)
    
    # Return updated conversation
    interrupted = storage.get_conversation(conversation_id)
    return ConversationResponse(**interrupted)


@router.get("/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_conversation_messages(
    conversation_id: str,
    limit: int = Query(None, description="Limit number of messages"),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
    storage = Depends(get_storage)
):
    """Get messages for a conversation"""
    # Verify conversation belongs to user
    conversation = storage.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    if conversation["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get messages
    messages = storage.get_conversation_messages(
        conversation_id=conversation_id,
        limit=limit,
        offset=offset
    )
    
    return [MessageResponse(**msg) for msg in messages]


@router.get("/{conversation_id}/info-cards", response_model=List[InfoCardResponse])
async def get_conversation_info_cards(
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
    storage = Depends(get_storage)
):
    """Get info cards for a conversation"""
    # Verify conversation belongs to user
    conversation = storage.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    if conversation["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get info cards
    cards = storage.get_conversation_info_cards(conversation_id)
    
    return [InfoCardResponse(**card) for card in cards]