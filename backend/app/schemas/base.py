# app/schemas/base.py - Document-based Base Schemas
from __future__ import annotations

from typing import Any, Dict, List, Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field


# ---------- generic responses ----------

class ErrorResponse(BaseModel):
    ok: bool = Field(default=False)
    error_code: str = Field(..., description="Stable application-level error code")
    message: str
    detail: Optional[Dict[str, Any]] = None
    conversation_id: Optional[str] = None


class OKResponse(BaseModel):
    ok: bool = Field(default=True)
    message: Optional[str] = None
    conversation_id: Optional[str] = None


class HealthProbeOut(BaseModel):
    status: Literal["ok", "degraded", "down"] = "ok"
    checks: Dict[str, bool] = Field(default_factory=dict)
    version: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    storage_type: str = "document"


# ---------- Document Storage Base Models ----------

class ConversationMessageBase(BaseModel):
    """Base model for conversation messages"""
    id: int
    role: Literal["user", "assistant", "system"]
    content: str
    type: str = "response"
    timestamp: str
    metadata: Optional[Dict[str, Any]] = None


class ConversationStateBase(BaseModel):
    """Base model for conversation assessment state"""
    current_pnm: Optional[str] = None
    current_term: Optional[str] = None
    fsm_state: str = "ROUTE"
    turn_index: int = 0
    asked_questions: List[str] = Field(default_factory=list)
    completed_terms: List[str] = Field(default_factory=list)
    scores: Dict[str, Dict[str, Any]] = Field(default_factory=dict)


class ConversationMetadataBase(BaseModel):
    """Base model for conversation metadata"""
    total_messages: int = 0
    user_messages: int = 0
    assistant_messages: int = 0
    info_cards_count: int = 0
    session_duration: Optional[float] = None
    completion_percentage: float = 0.0


# ---------- scoring DTOs (document-based) ----------

class TermScoreOut(BaseModel):
    conversation_id: Optional[str] = None  # Optional for compatibility
    session_id: Optional[str] = None  # Legacy field for compatibility
    pnm: str
    term: str
    score_0_5: float = Field(..., ge=0, le=5)
    rationale: Optional[str] = Field(default=None, max_length=240)
    status: str = "completed"
    timestamp: Optional[str] = None
    method_version: Optional[str] = "document_scorer_v1"


class DimensionScoreOut(BaseModel):
    conversation_id: Optional[str] = None  # Optional for compatibility
    session_id: Optional[str] = None  # Legacy field for compatibility
    pnm: str
    score_0_5: float = Field(..., ge=0.0, le=5.0)
    coverage_ratio: float = Field(..., ge=0.0, le=1.0)
    stage: Optional[str] = None
    method_version: Optional[str] = "document_agg_v1"
    timestamp: Optional[str] = None


# ---------- Info Card Base Models ----------

class InfoCardBase(BaseModel):
    """Base model for information cards"""
    id: str
    type: str = "info"
    title: str
    content: Dict[str, Any]
    triggered_at_turn: int = 0
    timestamp: str


# ---------- Pagination and Filtering ----------

class PaginationParams(BaseModel):
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class ConversationFilters(BaseModel):
    status: Optional[str] = None
    type: Optional[str] = None
    dimension: Optional[str] = None
    user_id: Optional[str] = None


# ---------- API Response Wrappers ----------

class ListResponse(BaseModel):
    """Generic list response wrapper"""
    items: List[Any]
    total_count: int
    has_more: bool = False
    pagination: Optional[Dict[str, Any]] = None


class ConversationListResponse(BaseModel):
    """Specific response for conversation lists"""
    conversations: List[Any]
    total_count: int
    active_count: int = 0
    completed_count: int = 0


# ---------- Assessment Base Models ----------

class AssessmentStateBase(BaseModel):
    """Base model for assessment state tracking"""
    current_pnm: Optional[str] = None
    current_term: Optional[str] = None
    progress_percentage: float = 0.0
    estimated_completion_time: Optional[int] = None  # minutes
    can_switch_dimension: bool = True


class ScoresSummary(BaseModel):
    """Summary of scores for an assessment"""
    term_count: int = 0
    dimension_count: int = 0
    average_term_score: Optional[float] = None
    highest_scoring_dimension: Optional[str] = None
    lowest_scoring_dimension: Optional[str] = None
    completion_status: str = "in_progress"


# ---------- System Status Models ----------

class StorageHealth(BaseModel):
    """Storage system health check"""
    connection_status: bool = True
    total_conversations: int = 0
    active_conversations: int = 0
    storage_size_mb: Optional[float] = None
    last_backup: Optional[str] = None


class SystemStatus(BaseModel):
    """Overall system status"""
    service_status: str = "healthy"
    storage_health: StorageHealth
    active_users: int = 0
    total_messages_today: int = 0
    ai_service_status: bool = True
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


# ---------- Migration Compatibility Models ----------

class LegacySessionCompat(BaseModel):
    """Compatibility model for legacy session-based endpoints"""
    session_id: str  # Maps to conversation_id
    conversation_id: str
    user_id: str
    migration_status: str = "completed"


class MigrationStatus(BaseModel):
    """Status of data migration from session to document model"""
    total_sessions: int = 0
    migrated_conversations: int = 0
    failed_migrations: int = 0
    migration_complete: bool = False
    started_at: Optional[str] = None
    completed_at: Optional[str] = None