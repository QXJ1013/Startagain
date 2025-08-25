# app/schemas/config.py
from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class BackendConfigOut(BaseModel):
    """
    Frontend-readable, non-sensitive runtime config.
    Only include booleans/thresholds/limits. No secrets, no IDs.
    """

    # Conversation / FSM
    LOCK_WINDOW_TURNS: int = 2
    EVIDENCE_MIN_FUP: int = 2
    MAX_FOLLOWUPS_PER_TERM: int = 3

    # Info provider
    INFO_PROVIDER_ENABLED: bool = True
    INFO_MIN_TURNS_INTERVAL: int = 2  # throttle in turns between info cards
    INFO_TOP_K: int = 6
    INFO_MAX_CARDS: int = 2
    INFO_BULLETS_PER_CARD: int = 2

    # Hybrid fusion
    HYBRID_ALPHA: float = 0.6  # lexical weight in [0,1]

    # Stage mapping thresholds (len == 6). Boundaries for 7 levels (0..6 indexes)
    STAGE_THRESHOLDS: List[float] = Field(default_factory=lambda: [1, 2, 3, 4, 5, 6])

    # Optional build/version info
    build_version: Optional[str] = None

    @classmethod
    def from_settings(cls, s) -> "BackendConfigOut":
        # s is app.config.Settings
        return cls(
            LOCK_WINDOW_TURNS=int(getattr(s, "LOCK_WINDOW_TURNS", 2)),
            EVIDENCE_MIN_FUP=int(getattr(s, "EVIDENCE_MIN_FUP", 2)),
            MAX_FOLLOWUPS_PER_TERM=int(getattr(s, "MAX_FOLLOWUPS_PER_TERM", 3)),
            INFO_PROVIDER_ENABLED=bool(getattr(s, "INFO_PROVIDER_ENABLED", True)),
            INFO_MIN_TURNS_INTERVAL=int(getattr(s, "INFO_MIN_TURNS_INTERVAL", getattr(s, "INFO_THROTTLE", 2))),
            INFO_TOP_K=int(getattr(s, "INFO_TOP_K", 6)),
            INFO_MAX_CARDS=int(getattr(s, "INFO_MAX_CARDS", 2)),
            INFO_BULLETS_PER_CARD=int(getattr(s, "INFO_BULLETS_PER_CARD", 2)),
            HYBRID_ALPHA=float(getattr(s, "HYBRID_ALPHA", 0.6)),
            STAGE_THRESHOLDS=list(getattr(s, "STAGE_THRESHOLDS", [1, 2, 3, 4, 5, 6])),
            build_version=getattr(s, "BUILD_VERSION", None),
        )
