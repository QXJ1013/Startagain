# app/schemas/chat.py - Document-based Chat Schemas
from __future__ import annotations

from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime

from .base import TermScoreOut, DimensionScoreOut


# ---------- shared UI objects ----------

class InfoCard(BaseModel):
    title: str
    bullets: List[str] = Field(default_factory=list, max_length=5)
    url: Optional[str] = None
    source: Optional[str] = None
    pnm: Optional[str] = None
    term: Optional[str] = None
    score: Optional[float] = None
    type: str = "info"


# ---------- Conversation Message Schema ----------

class MessageIn(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str
    type: str = "response"
    metadata: Optional[Dict[str, Any]] = None

class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    type: str
    timestamp: str
    metadata: Optional[Dict[str, Any]] = None


# ---------- Conversation Document Schema ----------

class ConversationSummary(BaseModel):
    id: str
    title: Optional[str] = None
    type: str = "assessment"
    dimension: Optional[str] = None
    status: str = "active"
    created_at: str
    updated_at: str
    message_count: int
    current_pnm: Optional[str] = None
    current_term: Optional[str] = None
    fsm_state: Optional[str] = None

class ConversationDetail(BaseModel):
    id: str
    user_id: str
    title: Optional[str] = None
    type: str = "assessment"
    dimension: Optional[str] = None
    status: str = "active"
    created_at: str
    updated_at: str
    completed_at: Optional[str] = None
    assessment_state: Dict[str, Any]
    messages: List[MessageOut]
    info_cards: List[Dict[str, Any]]
    metadata: Dict[str, Any]


# ---------- Followup Schema ----------

class FollowupOption(BaseModel):
    id: str
    label: str

class FollowupOut(BaseModel):
    id: str
    text: str
    type: str
    options: Optional[List[FollowupOption]] = None


# ---------- /chat/route ----------

class RouteIn(BaseModel):
    text: str
    keyword_pool: Optional[List[str]] = None

class RouteOut(BaseModel):
    session_id: str  # For compatibility, actually conversation_id
    current_pnm: Optional[str] = None
    current_term: Optional[str] = None
    locked: bool = False
    reason: Optional[str] = None


# ---------- /chat/question ----------

class QuestionOut(BaseModel):
    id: str
    type: Literal["main", "followup", "single", "multiple"]
    text: str
    pnm: Optional[str] = None
    term: Optional[str] = None
    options: Optional[List[Dict[str, str]]] = None
    followups: Optional[List[FollowupOut]] = None


# ---------- /chat/answer ----------

class AnswerIn(BaseModel):
    text: str
    meta: Optional[Dict[str, Any]] = None
    request_info: Optional[bool] = Field(default=True, description="Allow info cards if throttling permits")

class AnswerOut(BaseModel):
    next_state: Literal["ask_question", "scored", "dialogue", "pnm_completed", "next_term"]
    turn_index: Optional[int] = None
    current_pnm: Optional[str] = None
    current_term: Optional[str] = None
    scored: Optional[Dict[str, Any]] = None
    info_cards: Optional[List[InfoCard]] = None
    
    # Dialogue mode extensions
    dialogue_mode: bool = False
    dialogue_content: Optional[str] = None
    transition_message: Optional[str] = None
    should_continue_dialogue: bool = False
    next_question: Optional[QuestionOut] = None
    
    # Compatibility field
    session_id: Optional[str] = None


# ---------- /chat/state ----------

class StateOut(BaseModel):
    session_id: str  # For compatibility, actually conversation_id
    status: str
    fsm_state: Optional[str] = None
    current_pnm: Optional[str] = None
    current_term: Optional[str] = None
    current_qid: Optional[str] = None
    asked_qids: List[str] = Field(default_factory=list)
    followup_ptr: int = 0
    lock_until_turn: Optional[int] = None
    turn_index: int = 0
    last_info_turn: int = -999


# ---------- /chat/scores ----------

class ScoresOut(BaseModel):
    term_scores: List[Dict[str, Any]] = Field(default_factory=list)
    dimension_scores: List[Dict[str, Any]] = Field(default_factory=list)


# ---------- /chat/finish ----------

class FinishIn(BaseModel):
    commit: bool = True

class DimensionResultOut(BaseModel):
    pnm: str
    score_0_7: Optional[float] = None
    stage: Optional[str] = None
    term_scores: List[Dict[str, Any]] = Field(default_factory=list)
    uncovered_terms: List[str] = Field(default_factory=list)
    next_steps: List[str] = Field(default_factory=list)

class FinishOut(BaseModel):
    results: List[DimensionResultOut] = Field(default_factory=list)


# ---------- /chat/resume ----------

class ResumeOut(BaseModel):
    state: StateOut


# ---------- Natural Dialogue Schemas ----------

class DialogueIn(BaseModel):
    text: str
    meta: Optional[Dict[str, Any]] = None

class DialogueOut(BaseModel):
    conversation_id: str
    response: Dict[str, Any]
    mode: str
    info_cards: Optional[List[InfoCard]] = None


# ---------- Conversation Management Schemas ----------

class ConversationCreateIn(BaseModel):
    type: str = "assessment"
    dimension: Optional[str] = None
    title: Optional[str] = None

class ConversationUpdateIn(BaseModel):
    title: Optional[str] = None
    status: Optional[str] = None

class ConversationListOut(BaseModel):
    conversations: List[ConversationSummary]
    total_count: int


# ---------- Assessment Progress Schemas ----------

class AssessmentProgress(BaseModel):
    current_pnm: Optional[str] = None
    current_term: Optional[str] = None
    fsm_state: str = "ROUTE"
    completed_terms: List[str] = Field(default_factory=list)
    completed_dimensions: int = 0
    total_messages: int = 0
    can_switch_dimension: bool = True

class AssessmentScore(BaseModel):
    pnm: str
    term: str
    score_0_7: float
    rationale: Optional[str] = None
    status: str = "completed"
    timestamp: str

class DimensionScore(BaseModel):
    pnm: str
    score_0_7: float
    coverage_ratio: float = 0.0
    stage: Optional[str] = None
    method_version: Optional[str] = None


# ---------- Error Response Schemas ----------

class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    conversation_id: Optional[str] = None


# ---------- Health Check Schema ----------

class HealthCheck(BaseModel):
    status: str = "healthy"
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    conversation_count: Optional[int] = None
    active_conversations: Optional[int] = None