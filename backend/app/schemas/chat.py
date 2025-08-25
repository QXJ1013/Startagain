# app/schemas/chat.py
from __future__ import annotations

from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field

from .base import TermScoreOut, DimensionScoreOut


# ---------- shared UI objects ----------

class InfoCard(BaseModel):
    title: str
    bullets: List[str] = Field(default_factory=list, max_length=5)
    url: Optional[str] = None
    source: Optional[str] = None
    pnm: Optional[str] = None
    term: Optional[str] = None
    score: Optional[float] = None  # fused score for transparency


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
    session_id: str
    current_pnm: Optional[str] = None
    current_term: Optional[str] = None
    locked: bool = False
    reason: Optional[str] = None


# ---------- /chat/question ----------

class QuestionOut(BaseModel):
    id: str
    type: Literal["main", "followup"]
    text: str
    pnm: Optional[str] = None
    term: Optional[str] = None
    followups: Optional[List[FollowupOut]] = None  # present only when type=main to preview


# ---------- /chat/answer ----------

class AnswerIn(BaseModel):
    text: str
    meta: Optional[Dict[str, Any]] = None
    request_info: Optional[bool] = Field(default=True, description="Allow info cards if throttling permits")


class AnswerOut(BaseModel):
    next_state: Literal["main", "followup", "scored", "done"]
    turn_index: int
    current_pnm: Optional[str] = None
    current_term: Optional[str] = None
    scored: Optional[TermScoreOut] = None
    info_cards: Optional[List[InfoCard]] = None


# ---------- /chat/state ----------

class StateOut(BaseModel):
    session_id: str
    status: str
    fsm_state: str
    current_pnm: Optional[str] = None
    current_term: Optional[str] = None
    current_qid: Optional[str] = None
    asked_qids: List[str] = Field(default_factory=list)
    followup_ptr: int = 0
    lock_until_turn: int = 0
    turn_index: int = 0
    last_info_turn: int = -999


# ---------- /chat/scores ----------

class ScoresOut(BaseModel):
    term_scores: List[TermScoreOut] = Field(default_factory=list)
    dimension_scores: List[DimensionScoreOut] = Field(default_factory=list)


# ---------- /chat/finish ----------

class FinishIn(BaseModel):
    commit: Optional[bool] = Field(default=True, description="If true, (re)aggregate dimension scores and persist.")


class DimensionResultOut(BaseModel):
    pnm: str
    score_0_7: Optional[float] = None
    stage: Optional[str] = None
    term_scores: List[TermScoreOut] = Field(default_factory=list)
    uncovered_terms: List[str] = Field(default_factory=list)
    next_steps: List[str] = Field(default_factory=list)


class FinishOut(BaseModel):
    results: List[DimensionResultOut] = Field(default_factory=list)


# ---------- /chat/resume ----------

class ResumeIn(BaseModel):
    pass


class ResumeOut(BaseModel):
    state: StateOut
