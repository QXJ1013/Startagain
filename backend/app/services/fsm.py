# app/services/fsm.py
from __future__ import annotations
"""
Deterministic dialogue FSM for the ALS assistant (fixed & enhanced).

- Enforce evidence threshold: only score when enough follow-ups or exhausted.
- Lock window: prevent cross-dimension switching for N turns after routing.
- NEXT: pick next unscored term in the same dimension before leaving.
- Dimension aggregation: simple mean fallback after each term scoring.

States:
ROUTE -> ASK_MAIN -> ASK_FOLLOWUPS -> SCORE_TERM -> NEXT -> (ASK_MAIN | ROUTE)
"""

from typing import Dict, List, Optional, Tuple
from app.services.ai_router import create_ai_router

from app.config import get_settings
from app.services.question_bank import QuestionBank, QuestionItem
from app.services.lexicon_router import LexiconRouter
from app.services.session import SessionState
from app.services.storage import Storage
from app.config import get_settings
from app.services.term_scorer import score_term
from app.services.aggregator import Aggregator, AggregationConfig


class DialogueFSM:
    def __init__(
        self,
        store: Storage,
        qb: QuestionBank,
        router: LexiconRouter,
        session: SessionState,
    ):
        self.store = store
        self.qb = qb
        self.router = router
        self.session = session
        self.cfg = get_settings()
        self.ai_router = None
        if getattr(self.cfg, 'ENABLE_AI_ENHANCEMENT', False):
            self.ai_router = create_ai_router(router, qb)

        self.cfg = get_settings()

    # ---------------- Routing ----------------

    def _within_lock_window(self, new_pnm: str) -> bool:
        """Return True if cross-dimension switch is disallowed by lock window."""
        if not self.session.current_pnm:
            return False
        if new_pnm.lower() == self.session.current_pnm.lower():
            return False  # same dimension is allowed
        return self.session.turn_index < int(self.session.lock_until_turn or 0)

    def route_intent(self, user_text: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Route onto (pnm, term) via lexicon hits.
        Enforce lock window: forbid cross-dimension change until lock expires.
        """
        if self.ai_router:
            result = self.ai_router.route(user_text, self.session)
            if result and result.confidence > 0.6:
                # 保存 AI 路由元数据
                self.session.keyword_pool = result.keywords or []
                self.session.ai_confidence = result.confidence
                self.session.routing_method = result.method
                
                # 检查锁定窗口
                if self._within_lock_window(result.pnm):
                    return (self.session.current_pnm, self.session.current_term)
                
                # 应用新路由
                self.session.reset_for_new_term(result.pnm, result.term)
                self.session.lock_until_turn = self.session.turn_index + self.cfg.LOCK_WINDOW_TURNS
                self.session.save(self.store)
                return (result.pnm, result.term)
        
        # 降级到原有逻辑
        hits = self.router.locate(user_text or "")
        if not hits:
            return (self.session.current_pnm, self.session.current_term)
        
        term, pnm = hits[0]
        if self._within_lock_window(pnm):
            return (self.session.current_pnm, self.session.current_term)
        
        self.session.reset_for_new_term(pnm=pnm, term=term)
        self.session.lock_until_turn = self.session.turn_index + self.cfg.LOCK_WINDOW_TURNS
        self.session.save(self.store)
        return (pnm, term)

    # ---------------- Questions ----------------

    def get_current_question(self) -> Optional[Dict]:
        """
        Return next question to ask (main or next follow-up).
        """
        import logging
        log = logging.getLogger(__name__)
        
        log.warning(f"FSM get_current_question: pnm={self.session.current_pnm}, term={self.session.current_term}, fsm_state={self.session.fsm_state}")
        
        if not self.session.current_pnm or not self.session.current_term:
            log.warning("FSM: No current PNM/term, returning None")
            return None

        item = self.qb.choose_for_term(
            pnm=self.session.current_pnm,
            term=self.session.current_term,
            asked_ids=self.session.asked_qids,
        )
        if not item:
            # Try cross-PNM fallback when no questions exist for this PNM
            # The question bank's smart fallback will handle this automatically
            log.warning(f"FSM: No questions found for PNM {self.session.current_pnm}, trying fallback with dummy term")
            item = self.qb.choose_for_term(
                pnm=self.session.current_pnm,  # Keep the original PNM for hash-based diversity
                term="NonExistentFallbackTerm",  # Use a term that definitely doesn't exist to trigger fallback
                asked_ids=self.session.asked_qids,
            )
        if not item:
            log.warning("FSM: No item chosen even after fallback, returning None")
            return None
        
        log.warning(f"FSM: Chosen item {item.id}, fsm_state={self.session.fsm_state}")

        # ask main
        if self.session.fsm_state == "ASK_MAIN":
            self.session.mark_question_asked(item.id)
            self.session.current_qid = item.id  # Set current question ID
            self.session.fsm_state = "ASK_FOLLOWUPS"
            self.session.save(self.store)  # Save after all changes
            return {
                "id": item.id,
                "type": "main",
                "text": item.main,
                "followups": item.followups,
            }

        # ask followups
        if self.session.fsm_state == "ASK_FOLLOWUPS":
            idx = self.session.followup_ptr
            if idx < len(item.followups):
                if idx >= self.cfg.MAX_FOLLOWUPS_PER_TERM:
                    return None
                
                # Handle both string and object followup formats
                followup_item = item.followups[idx]
                if isinstance(followup_item, str):
                    q_text = followup_item
                elif isinstance(followup_item, dict):
                    q_text = followup_item.get("text", "No followup text available")
                else:
                    q_text = str(followup_item)
                
                qid = f"{item.id}#fu{idx+1}"
                self.session.mark_question_asked(qid)
                self.session.current_qid = qid  # Set current question ID
                self.session.followup_ptr += 1
                
                # Debug logging
                import logging
                log = logging.getLogger(__name__)
                log.warning(f"FSM: Before save - current_qid={self.session.current_qid}, followup_ptr={self.session.followup_ptr}")
                
                self.session.save(self.store)  # Save after all changes
                
                log.warning(f"FSM: After save - current_qid={self.session.current_qid}")
                
                return {"id": qid, "type": "followup", "text": q_text}

        return None

    # ---------------- Answers & Transitions ----------------

    def receive_answer(self, user_text: str, meta: Optional[Dict] = None) -> str:
        """
        Persist the user answer as a turn, then decide next transition.
        Returns one of: 'followup' | 'scored' | 'main' | 'done'
        """
        # persist user's turn (named args to avoid param order mistakes)
        turn_idx = self.session.next_turn_index()
        self.store.add_turn(
            session_id=self.session.session_id,
            turn_index=turn_idx,
            role="user",
            content=user_text,
            meta=meta or {},
        )

        # If there is no active item, fall back to ROUTE
        item = self.qb.choose_for_term(
            pnm=self.session.current_pnm or "",
            term=self.session.current_term or "",
            asked_ids=self.session.asked_qids,
        )
        if not item:
            self.session.fsm_state = "ROUTE"
            self.session.save(self.store)
            return "done"

        # From ROUTE -> prepare to ask main next
        if self.session.fsm_state == "ROUTE":
            self.session.fsm_state = "ASK_MAIN"
            self.session.save(self.store)
            return "main"

        # In ASK_FOLLOWUPS: check evidence threshold
        if self.session.fsm_state == "ASK_FOLLOWUPS":
            asked_followups = self.session.followup_ptr
            need = max(0, int(self.cfg.EVIDENCE_MIN_FUP or 0))
            more_available = asked_followups < len(item.followups)
            under_cap = asked_followups < self.cfg.MAX_FOLLOWUPS_PER_TERM

            if asked_followups < need and more_available and under_cap:
                return "followup"

            # move to scoring
            self.session.fsm_state = "SCORE_TERM"
            self.session.save(self.store)

        # SCORE_TERM
        if self.session.fsm_state == "SCORE_TERM":
            self._score_current_term(item=item)
            self.session.fsm_state = "NEXT"
            self.session.save(self.store)
            # Optional: aggregate dimension after each term
            self._aggregate_dimension_if_possible(self.session.current_pnm)
            return "scored"

        # NEXT: pick another term within the same PNM
        if self.session.fsm_state == "NEXT":
            next_term = self._pick_next_term_same_pnm()
            if next_term:
                self.session.reset_for_new_term(self.session.current_pnm or "", next_term)
                self.session.lock_until_turn = self.session.turn_index + self.cfg.LOCK_WINDOW_TURNS
                self.session.save(self.store)
                return "main"
            self.session.fsm_state = "ROUTE"
            self.session.save(self.store)
            return "done"

        return "done"

    # ---------------- Helpers ----------------

    def _pick_next_term_same_pnm(self) -> Optional[str]:
        """
        Choose next unscored term from the same PNM (lexicon order).
        Avoid the current term and any term already scored in DB.
        """
        if not self.session.current_pnm:
            return None
        all_terms = self.router.topics_for_pnm(self.session.current_pnm)

        # terms already scored for this session/pnm
        scored_rows = self.store.list_term_scores(self.session.session_id, pnm=self.session.current_pnm)
        scored_terms = {r.get("term", "").lower() for r in scored_rows if r.get("term")}

        banned = { (self.session.current_term or "").lower() } | scored_terms
        for t in all_terms:
            if t.lower() not in banned:
                return t
        return None

    def _score_current_term(self, item: QuestionItem) -> None:
        """
        Score the current term using LLM scorer or a simple rule fallback.
        """
        turns = self.store.list_turns(self.session.session_id)
        # heuristic evidence set: last (1 main + N followups) *2 to be safe
        evidence_ids = [t.get("id") for t in turns[-(2 + max(0, self.session.followup_ptr)):] if t.get("id")]

        if callable(score_term):
            out = score_term(
                session_id=self.session.session_id,
                pnm=item.pnm,
                term=item.term,
                turns=turns,
            )
            score = float(out.get("score_0_7", 3.0))
            rationale = out.get("rationale", "")
            ev_ids = out.get("evidence_turn_ids", evidence_ids) or []
            method_version = out.get("method_version", "term_scorer_llm_v1")
        else:
            score = 3.0
            rationale = "Fallback rule: insufficient configured scorer; default mid-level."
            ev_ids = evidence_ids or []
            method_version = "term_scorer_fallback_v1"

        self.store.upsert_term_score(
            session_id=self.session.session_id,
            pnm=item.pnm,
            term=item.term,
            score_0_7=score,
            rationale=rationale,
            evidence_turn_ids=ev_ids,
            status="complete",
            method_version=method_version,
        )

    def _aggregate_dimension_if_possible(self, pnm: Optional[str]) -> None:
        """Aggregate into dimension score after each term score (simple mean fallback)."""
        if not pnm:
            return
        rows = self.store.list_term_scores(self.session.session_id, pnm=pnm)
        if not rows:
            return

        # simple mean fallback (Aggregator optional)
        vals = [float(r.get("score_0_7") or 0.0) for r in rows]
        score = sum(vals) / max(1, len(vals))
        coverage = min(1.0, len(rows) / 5.0)  # crude coverage proxy
        self.store.upsert_dimension_score(
            session_id=self.session.session_id,
            pnm=pnm,
            score_0_7=score,
            coverage_ratio=coverage,
            method_version="agg_mean_fallback_v1",
        )

    # -------- Public helper for API: dimension result --------

    def dimension_result(self, pnm: str) -> Dict:
        """
        Build a structured result for one dimension:
        {
          "pnm": "...",
          "score_0_7": float or None,
          "term_scores": [{term, score_0_7, rationale, evidence_turn_ids}, ...],
          "uncovered_terms": [...],
          "next_steps": []
        }
        """
        trows = self.store.list_term_scores(self.session.session_id, pnm=pnm)
        term_scores = [
            {
                "term": r.get("term"),
                "score_0_7": r.get("score_0_7"),
                "rationale": r.get("rationale"),
                "evidence_turn_ids": r.get("evidence_turn_ids"),
            }
            for r in trows
        ]

        drow = self.store.get_dimension_score(self.session.session_id, pnm)
        dim_score = float(drow["score_0_7"]) if drow and drow.get("score_0_7") is not None else None

        all_terms = set(self.router.topics_for_pnm(pnm))
        covered = set([r.get("term") for r in trows if r.get("term")])
        uncovered = sorted(list(all_terms - covered))

        return {
            "pnm": pnm,
            "score_0_7": dim_score,
            "term_scores": term_scores,
            "uncovered_terms": uncovered,
            "next_steps": [],
        }
