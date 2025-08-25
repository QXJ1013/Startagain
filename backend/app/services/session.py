# app/services/session.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from .storage import Storage
from .pnm_scoring import PNMScore

@dataclass
class SessionState:
    session_id: str
    user_id: Optional[str] = None
    status: str = "active"
    fsm_state: str = "ROUTE"
    current_pnm: Optional[str] = None
    current_term: Optional[str] = None
    current_qid: Optional[str] = None           
    asked_qids: List[str] = field(default_factory=list)
    followup_ptr: int = 0
    lock_until_turn: int = 0
    turn_index: int = 0
    last_info_turn: int = -999

    keyword_pool: List[str] = field(default_factory=list)
    ai_confidence: float = 0.0
    routing_method: str = "exact"
    
    # New fields for PNM scoring
    pnm_scores: List = field(default_factory=list)
    evidence_count: Dict = field(default_factory=dict)


    def save(self, store: Storage) -> None:
        # Convert PNMScore objects to dictionaries for serialization
        pnm_scores_dicts = []
        if self.pnm_scores:
            for score in self.pnm_scores:
                if hasattr(score, 'to_dict'):
                    pnm_scores_dicts.append(score.to_dict())
                else:
                    # Already a dict
                    pnm_scores_dicts.append(score)
        
        store.upsert_session(
            session_id=self.session_id,
            user_id=self.user_id,
            status=self.status,
            fsm_state=self.fsm_state,
            current_pnm=self.current_pnm,
            current_term=self.current_term,
            current_qid=self.current_qid,
            asked_qids=self.asked_qids,
            followup_ptr=self.followup_ptr,
            lock_until_turn=self.lock_until_turn,
            turn_index=self.turn_index,
            last_info_turn=self.last_info_turn,
            pnm_scores=pnm_scores_dicts,
            evidence_count=self.evidence_count,
        )

    @staticmethod
    def load(store: Storage, session_id: str) -> "SessionState":
        row = store.get_session(session_id)
        if not row:
            state = SessionState(session_id=session_id)
            state.save(store)
            return state
        # Convert pnm_scores from dictionaries back to PNMScore objects
        pnm_scores = []
        raw_scores = row.get("pnm_scores") or []
        for score_data in raw_scores:
            if isinstance(score_data, dict):
                pnm_scores.append(PNMScore.from_dict(score_data))
            else:
                pnm_scores.append(score_data)  # Already a PNMScore object
        
        return SessionState(
            session_id=row.get("session_id", session_id),
            user_id=row.get("user_id"),
            status=row.get("status") or "active",
            fsm_state=row.get("fsm_state") or "ROUTE",
            current_pnm=row.get("current_pnm"),
            current_term=row.get("current_term"),
            current_qid=row.get("current_qid"),
            asked_qids=list(row.get("asked_qids") or []),
            followup_ptr=int(row.get("followup_ptr") or 0),
            lock_until_turn=int(row.get("lock_until_turn") or 0),
            turn_index=int(row.get("turn_index") or 0),
            last_info_turn=int(row.get("last_info_turn") or -999),
            keyword_pool=list(row.get("keyword_pool") or []),
            ai_confidence=float(row.get("ai_confidence") or 0.0),
            routing_method=row.get("routing_method") or "exact",
            pnm_scores=pnm_scores,
            evidence_count=dict(row.get("evidence_count") or {})
        )

    def mark_question_asked(self, qid: str) -> None:
        if qid and qid not in self.asked_qids:
            self.asked_qids.append(qid)

    def next_turn_index(self) -> int:
        self.turn_index += 1
        return self.turn_index

    def reset_for_new_term(self, pnm: str, term: str) -> None:
        self.current_pnm = pnm
        self.current_term = term
        self.current_qid = None                # reset
        self.followup_ptr = 0
        self.fsm_state = "ASK_MAIN"
