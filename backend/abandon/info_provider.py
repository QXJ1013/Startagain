# app/services/info_provider.py
from __future__ import annotations

from typing import List, Dict, Any, Optional
from app.config import get_settings
from app.vendors.ibm_cloud import RAGQueryClient
from app.vendors.bm25 import BM25Client
from app.utils.rerank import hybrid_fusion
from app.utils.text import normalize_text

class InfoProvider:
    """
    Retrieve short, actionable info cards from the background knowledge index.
    - Throttled by session.last_info_turn and INFO_MIN_TURNS_INTERVAL.
    - Uses hybrid retrieval: BM25 (optional) + IBM RAGQuery vector index.
    - Returns a small list of dicts consumable by frontend (schemas.chat.InfoCard).
    """

    def __init__(self):
        self.cfg = get_settings()
        self.enabled = bool(getattr(self.cfg, "INFO_PROVIDER_ENABLED", True))
        # channels (best-effort; each client internally handles missing config)
        self.rag = RAGQueryClient()
        self.bm25 = BM25Client(
            bg_index_dir=self.cfg.BM25_BG_INDEX_DIR,
            q_index_dir=self.cfg.BM25_Q_INDEX_DIR
        )

        # knobs
        self.top_k = int(getattr(self.cfg, "INFO_TOP_K", 6))
        self.max_cards = int(getattr(self.cfg, "INFO_MAX_CARDS", 2))
        self.bullets_per_card = int(getattr(self.cfg, "INFO_BULLETS_PER_CARD", 2))
        self.alpha = float(getattr(self.cfg, "HYBRID_ALPHA", 0.6))  # lexical weight in [0,1]

    # ---------- public API ----------

    def maybe_provide_info(
        self,
        *,
        session,                             # app.services.session.SessionState
        last_answer: str,
        current_pnm: Optional[str],
        current_term: Optional[str],
        storage=None                         # app.services.storage.Storage (optional for evidence logging)
    ) -> List[Dict[str, Any]]:
        """
        Return a small list of info cards or [] if throttled/disabled/no hits.
        """
        if not self.enabled:
            return []

        # throttle by turns
        min_gap = int(getattr(self.cfg, "INFO_MIN_TURNS_INTERVAL", 2))
        if hasattr(session, "last_info_turn"):
            if (session.turn_index - int(session.last_info_turn or -999)) < min_gap:
                return []

        # build query
        parts = [current_pnm or "", current_term or "", last_answer or ""]
        q = normalize_text(" ".join([p for p in parts if p])).strip()
        if not q:
            return []

        # hybrid retrieval over BACKGROUND index
        bm_docs = self.bm25.search_background(q, top_k=self.top_k)
        vx_docs = self.rag.search(q, top_k=self.top_k, index_kind="background")
        fused = hybrid_fusion(lexical_run=bm_docs, vector_run=vx_docs, alpha=self.alpha, normalize=True, topn=self.top_k)

        cards: List[Dict[str, Any]] = []
        for d in fused[: self.max_cards]:
            meta = d.get("metadata") or {}
            title = meta.get("title") or meta.get("heading") or (meta.get("term") or "").title() or "Helpful resource"
            url = meta.get("url") or meta.get("source_url") or None
            source = meta.get("source") or meta.get("domain") or None

            # bullets: prefer short, actionable lines if provided; otherwise truncate snippet
            bullets = []
            snippet = (meta.get("summary") or meta.get("snippet") or "").strip()
            if snippet:
                # simple sentence split; keep it robust
                for s in [x.strip() for x in snippet.replace("\n", " ").split(".") if x.strip()]:
                    bullets.append(s)
                    if len(bullets) >= self.bullets_per_card:
                        break
            if not bullets:
                bullets = ["This resource may be relevant to your concern."]

            cards.append({
                "title": title,
                "bullets": bullets[: self.bullets_per_card],
                "url": url,
                "source": source,
                "pnm": current_pnm,
                "term": current_term,
                "score": float(d.get("score") or 0.0),
            })

        # update throttle state if we produced cards
        if cards:
            session.last_info_turn = session.turn_index
            if storage is not None:
                try:
                    storage.upsert_session(
                        session_id=session.session_id,
                        user_id=session.user_id,
                        status=session.status,
                        fsm_state=session.fsm_state,
                        current_pnm=session.current_pnm,
                        current_term=session.current_term,
                        current_qid=session.current_qid,
                        asked_qids=session.asked_qids,
                        followup_ptr=session.followup_ptr,
                        lock_until_turn=session.lock_until_turn,
                        turn_index=session.turn_index,
                        last_info_turn=session.last_info_turn,
                    )
                except Exception:
                    # non-fatal
                    pass

        return cards
