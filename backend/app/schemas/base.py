# app/schemas/base.py
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


class OKResponse(BaseModel):
    ok: bool = Field(default=True)
    message: Optional[str] = None


class HealthProbeOut(BaseModel):
    status: Literal["ok", "degraded", "down"] = "ok"
    checks: Dict[str, bool] = Field(default_factory=dict)
    version: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ---------- scoring DTOs (shared) ----------

class TermScoreOut(BaseModel):
    session_id: str
    pnm: str
    term: str
    score_0_7: int = Field(..., ge=0, le=7)
    rationale: Optional[str] = Field(default=None, max_length=240)
    evidence_turn_ids: List[int] = Field(default_factory=list, description="Real turn_index list")
    method_version: Optional[str] = "term_scorer_wx_v2"
    updated_at: Optional[datetime] = None


class DimensionScoreOut(BaseModel):
    session_id: str
    pnm: str
    score_0_7: float = Field(..., ge=0.0, le=7.0)
    coverage_ratio: float = Field(..., ge=0.0, le=1.0)
    stage: Optional[str] = None
    method_version: Optional[str] = "agg_v2"
    updated_at: Optional[datetime] = None
