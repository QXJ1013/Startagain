# app/routers/conversations.py - Conversation Management API
"""
Conversation management endpoints that expose the storage layer functionality.
Provides REST API for conversation CRUD operations, history, and status management.
"""

from __future__ import annotations
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.deps import get_storage, get_current_user
from app.services.storage import DocumentStorage, ConversationDocument

log = logging.getLogger(__name__)
router = APIRouter(prefix="/conversations", tags=["conversations"])

# ---------- Request/Response Models ----------

class CreateConversationRequest(BaseModel):
    type: str = "general_chat"  # 'general_chat' | 'dimension' | 'assessment'
    dimension: Optional[str] = None
    title: Optional[str] = None

class UpdateConversationRequest(BaseModel):
    title: Optional[str] = None
    status: Optional[str] = None  # 'active' | 'completed' | 'paused' | 'archived'

class ConversationListItem(BaseModel):
    id: str
    title: Optional[str]
    type: str
    dimension: Optional[str]
    status: str
    created_at: str
    updated_at: str
    message_count: int
    last_message_at: Optional[str]
    current_pnm: Optional[str]
    current_term: Optional[str]
    fsm_state: Optional[str]

class ConversationListResponse(BaseModel):
    conversations: List[ConversationListItem]
    total_count: int

class ConversationDetailResponse(BaseModel):
    id: str
    user_id: str
    title: Optional[str]
    type: str
    dimension: Optional[str]
    status: str
    created_at: str
    updated_at: str
    completed_at: Optional[str]
    assessment_state: Dict[str, Any]
    messages: List[Dict[str, Any]]
    info_cards: List[Dict[str, Any]]
    metadata: Dict[str, Any]

class ConversationCreateResponse(BaseModel):
    id: str
    user_id: str
    title: Optional[str]
    type: str
    dimension: Optional[str]
    status: str
    created_at: str
    updated_at: str

class ConversationUpdateResponse(BaseModel):
    id: str
    title: Optional[str]
    type: str
    status: str
    updated_at: str
    message_count: int

class InterruptWarningResponse(BaseModel):
    should_warn: bool
    active_conversation: Optional[ConversationListItem]

# ---------- API Endpoints ----------

@router.post("", response_model=ConversationCreateResponse)
async def create_conversation(
    request: CreateConversationRequest,
    storage: DocumentStorage = Depends(get_storage),
    current_user: dict = Depends(get_current_user)
):
    """Create a new conversation"""
    try:
        # Generate title if not provided
        title = request.title
        if not title:
            if request.dimension:
                title = f"{request.dimension} Assessment"
            elif request.type == "assessment":
                title = "ALS Assessment"
            else:
                title = "General Chat"

        # Create conversation using storage layer
        conversation = storage.create_conversation(
            user_id=current_user["id"],
            type=request.type,
            dimension=request.dimension,
            title=title
        )

        return ConversationCreateResponse(
            id=conversation.id,
            user_id=conversation.user_id,
            title=conversation.title,
            type=conversation.type,
            dimension=conversation.dimension,
            status=conversation.status,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        log.error(f"Create conversation error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create conversation: {str(e)}")


@router.get("", response_model=ConversationListResponse)
async def get_conversations(
    status: Optional[str] = Query(None, description="Filter by status: active, completed, paused, archived"),
    limit: int = Query(20, ge=1, le=100, description="Number of conversations to return"),
    offset: int = Query(0, ge=0, description="Number of conversations to skip"),
    storage: DocumentStorage = Depends(get_storage),
    current_user: dict = Depends(get_current_user)
):
    """Get user's conversations with pagination and filtering"""
    try:
        # Get conversations from storage
        conversations_data = storage.list_conversations(
            user_id=current_user["id"],
            status=status,
            limit=limit + offset  # Get extra to calculate total
        )

        # Apply pagination
        paginated_conversations = conversations_data[offset:offset + limit]

        # Transform data for response
        conversation_items = []
        for conv_data in paginated_conversations:
            conversation_items.append(ConversationListItem(
                id=conv_data["id"],
                title=conv_data.get("title"),
                type=conv_data["type"],
                dimension=conv_data.get("dimension"),
                status=conv_data["status"],
                created_at=conv_data["created_at"],
                updated_at=conv_data["updated_at"],
                message_count=conv_data.get("message_count", 0),
                last_message_at=conv_data.get("last_message_at"),
                current_pnm=conv_data.get("current_pnm"),
                current_term=conv_data.get("current_term"),
                fsm_state=conv_data.get("fsm_state")
            ))

        return ConversationListResponse(
            conversations=conversation_items,
            total_count=len(conversations_data)
        )

    except Exception as e:
        log.error(f"Get conversations error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get conversations: {str(e)}")


@router.get("/active", response_model=Optional[ConversationListItem])
async def get_active_conversation(
    storage: DocumentStorage = Depends(get_storage),
    current_user: dict = Depends(get_current_user)
):
    """Get user's current active conversation"""
    try:
        conversation = storage.get_active_conversation(current_user["id"])

        if not conversation:
            return None

        return ConversationListItem(
            id=conversation.id,
            title=conversation.title,
            type=conversation.type,
            dimension=conversation.dimension,
            status=conversation.status,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            message_count=len(conversation.messages),
            last_message_at=conversation.messages[-1].timestamp if conversation.messages else None,
            current_pnm=conversation.assessment_state.get("current_pnm"),
            current_term=conversation.assessment_state.get("current_term"),
            fsm_state=conversation.assessment_state.get("fsm_state")
        )

    except Exception as e:
        log.error(f"Get active conversation error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get active conversation: {str(e)}")


@router.get("/check-interrupt", response_model=InterruptWarningResponse)
async def check_interrupt_warning(
    storage: DocumentStorage = Depends(get_storage),
    current_user: dict = Depends(get_current_user)
):
    """Check if user has an active conversation that would be interrupted"""
    try:
        active_conversation = storage.get_active_conversation(current_user["id"])

        if not active_conversation:
            return InterruptWarningResponse(should_warn=False, active_conversation=None)

        # Only warn if conversation has messages
        should_warn = len(active_conversation.messages) > 0

        active_conv_data = None
        if should_warn:
            active_conv_data = ConversationListItem(
                id=active_conversation.id,
                title=active_conversation.title,
                type=active_conversation.type,
                dimension=active_conversation.dimension,
                status=active_conversation.status,
                created_at=active_conversation.created_at,
                updated_at=active_conversation.updated_at,
                message_count=len(active_conversation.messages),
                last_message_at=active_conversation.messages[-1].timestamp if active_conversation.messages else None,
                current_pnm=active_conversation.assessment_state.get("current_pnm"),
                current_term=active_conversation.assessment_state.get("current_term"),
                fsm_state=active_conversation.assessment_state.get("fsm_state")
            )

        return InterruptWarningResponse(
            should_warn=should_warn,
            active_conversation=active_conv_data
        )

    except Exception as e:
        log.error(f"Check interrupt warning error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to check interrupt warning: {str(e)}")


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: str,
    storage: DocumentStorage = Depends(get_storage),
    current_user: dict = Depends(get_current_user)
):
    """Get conversation details with messages"""
    try:
        conversation = storage.get_conversation(conversation_id)

        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Verify user owns this conversation
        if conversation.user_id != current_user["id"]:
            raise HTTPException(status_code=403, detail="Access denied")

        # Transform messages for response
        messages_data = []
        for msg in conversation.messages:
            messages_data.append({
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "type": msg.type,
                "timestamp": msg.timestamp,
                "metadata": msg.metadata or {}
            })

        return ConversationDetailResponse(
            id=conversation.id,
            user_id=conversation.user_id,
            title=conversation.title,
            type=conversation.type,
            dimension=conversation.dimension,
            status=conversation.status,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            completed_at=conversation.assessment_state.get("completed_at"),
            assessment_state=conversation.assessment_state,
            messages=messages_data,
            info_cards=conversation.info_cards,
            metadata=conversation.metadata
        )

    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Get conversation error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get conversation: {str(e)}")


@router.put("/{conversation_id}", response_model=ConversationUpdateResponse)
async def update_conversation(
    conversation_id: str,
    request: UpdateConversationRequest,
    storage: DocumentStorage = Depends(get_storage),
    current_user: dict = Depends(get_current_user)
):
    """Update conversation title or status"""
    try:
        conversation = storage.get_conversation(conversation_id)

        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Verify user owns this conversation
        if conversation.user_id != current_user["id"]:
            raise HTTPException(status_code=403, detail="Access denied")

        # Update fields
        if request.title is not None:
            conversation.title = request.title

        if request.status is not None:
            if request.status not in ['active', 'completed', 'paused', 'archived']:
                raise HTTPException(status_code=400, detail="Invalid status")
            conversation.status = request.status

            # Set completion timestamp if completed
            if request.status == 'completed':
                conversation.assessment_state['completed_at'] = datetime.now().isoformat()

        # Update timestamp
        conversation.updated_at = datetime.now().isoformat()

        # Save to storage
        updated_conversation = storage.update_conversation(conversation)

        return ConversationUpdateResponse(
            id=updated_conversation.id,
            title=updated_conversation.title,
            type=updated_conversation.type,
            status=updated_conversation.status,
            updated_at=updated_conversation.updated_at,
            message_count=len(updated_conversation.messages)
        )

    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Update conversation error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update conversation: {str(e)}")


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    storage: DocumentStorage = Depends(get_storage),
    current_user: dict = Depends(get_current_user)
):
    """Delete conversation (actually archives it)"""
    try:
        conversation = storage.get_conversation(conversation_id)

        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Verify user owns this conversation
        if conversation.user_id != current_user["id"]:
            raise HTTPException(status_code=403, detail="Access denied")

        # Archive instead of delete
        conversation.status = 'archived'
        conversation.updated_at = datetime.now().isoformat()

        storage.update_conversation(conversation)

        return {"success": True, "message": "Conversation archived"}

    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Delete conversation error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete conversation: {str(e)}")


# ---------- Message Management ----------

@router.post("/{conversation_id}/messages")
async def add_message_to_conversation(
    conversation_id: str,
    message_data: Dict[str, Any],
    storage: DocumentStorage = Depends(get_storage),
    current_user: dict = Depends(get_current_user)
):
    """Add message to conversation"""
    try:
        conversation = storage.get_conversation(conversation_id)

        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Verify user owns this conversation
        if conversation.user_id != current_user["id"]:
            raise HTTPException(status_code=403, detail="Access denied")

        # Add message using storage layer - fix parameter order
        updated_conversation = storage.add_message(
            conversation_id,
            message_data["role"],
            message_data["content"],
            type=message_data.get("type", "text"),
            metadata=message_data.get("metadata", {})
        )

        return {"success": True, "message_count": len(updated_conversation.messages)}

    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Add message error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to add message: {str(e)}")


# ---------- Info Cards ----------

@router.post("/{conversation_id}/info-cards")
async def add_info_card_to_conversation(
    conversation_id: str,
    card_data: Dict[str, Any],
    storage: DocumentStorage = Depends(get_storage),
    current_user: dict = Depends(get_current_user)
):
    """Add info card to conversation"""
    try:
        conversation = storage.get_conversation(conversation_id)

        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Verify user owns this conversation
        if conversation.user_id != current_user["id"]:
            raise HTTPException(status_code=403, detail="Access denied")

        # Add info card using storage layer
        updated_conversation = storage.add_info_card(
            conversation_id=conversation_id,
            card_type=card_data.get("type", "general"),
            card_data=card_data
        )

        return {"success": True, "info_cards_count": len(updated_conversation.info_cards)}

    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Add info card error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to add info card: {str(e)}")


# ---------- User Scores ----------

@router.get("/scores/summary", response_model=Dict[str, Any])
async def get_user_scores_summary(
    storage: DocumentStorage = Depends(get_storage),
    current_user: dict = Depends(get_current_user)
):
    """Get user's PNM scores summary across all conversations"""
    try:
        # Get all conversations for user
        conversations_data = storage.list_conversations(current_user["id"])

        # Initialize scores dictionary
        dimension_scores = {
            "Physiological": [],
            "Safety": [],
            "Love & Belonging": [],
            "Esteem": [],
            "Self-Actualisation": [],
            "Cognitive": [],
            "Aesthetic": [],
            "Transcendence": []
        }

        # Collect scores from conversation_scores database table
        import sqlite3
        from pathlib import Path

        # Get database path
        db_path = Path(__file__).parent.parent / "data" / "als.db"

        # Get user's conversation IDs
        user_conv_ids = [conv["id"] for conv in conversations_data]

        # Also collect term-level data for frontend
        term_scores = []

        if user_conv_ids and db_path.exists():
            with sqlite3.connect(str(db_path)) as conn:
                # Get all term scores for user's conversations
                placeholders = ','.join(['?' for _ in user_conv_ids])
                query = f"""
                    SELECT pnm, term, score, updated_at
                    FROM conversation_scores
                    WHERE conversation_id IN ({placeholders})
                    AND status = 'completed'
                    ORDER BY updated_at DESC
                """

                cursor = conn.execute(query, user_conv_ids)
                rows = cursor.fetchall()

                # Collect scores by dimension for PNM averages
                for pnm, term, score, updated_at in rows:
                    if pnm in dimension_scores:
                        # Use score as-is (0-5 scale, suitable for display)
                        dimension_scores[pnm].append(float(score))

                    # Also collect term data for frontend display
                    term_scores.append({
                        "pnm": pnm,
                        "term": term,
                        "score": float(score),
                        "updated_at": updated_at
                    })

        # Calculate averages
        summary = []
        for dimension, scores in dimension_scores.items():
            if scores:
                avg_score = sum(scores) / len(scores)
                summary.append({
                    "name": dimension,
                    "score": round(avg_score, 1),
                    "assessments_count": len(scores)
                })
            else:
                # No scores yet - show placeholder
                summary.append({
                    "name": dimension,
                    "score": 0.0,
                    "assessments_count": 0
                })

        return {
            "dimensions": summary,
            "term_scores": term_scores,  # Return all term scores for frontend display
            "total_conversations": len(conversations_data),
            "completed_assessments": len([c for c in conversations_data if c.get("status") == "completed"])
        }

    except Exception as e:
        log.error(f"Get user scores error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get user scores: {str(e)}")