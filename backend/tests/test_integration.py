# tests/smoke_ai_end_to_end.py
import os
import uuid
import time
from typing import Optional, List, Dict, Any

import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import get_settings
from app.deps import get_storage, get_question_bank, get_lexicon_router, get_info_provider
from app.services.session import SessionState
from app.services.fsm import DialogueFSM
from app.services.info_provider_enhanced import EnhancedInfoProvider  # we will call a private fallback
from app.vendors.ibm_cloud import RAGQueryClient, LLMClient

def _log(title: str, obj: Any):
    print(f"\n=== {title} ===")
    print(obj)

def ensure_session(session_id: str) -> SessionState:
    storage = get_storage()
    storage.ensure_session(session_id)
    return SessionState.load(storage, session_id)

def write_assistant_turn(storage, session: SessionState, text: str):
    """
    InfoProvider expects to see assistant questions in recent turns.
    We insert an assistant turn whenever we ask a question.
    """
    idx = session.next_turn_index()
    storage.add_turn(
        session_id=session.session_id,
        turn_index=idx,
        role="assistant",
        content=text,
        meta={"kind": "question"}
    )
    session.save(storage)

def try_info_cards(info_provider, storage, session, last_answer: str) -> Optional[List[Dict[str, Any]]]:
    """
    Try to fetch info cards; if retrieval returns empty documents,
    force a LLM-only fallback by calling a private helper.
    """
    # normal path
    cards = info_provider.maybe_provide_info(
        session=session,
        last_answer=last_answer,
        current_pnm=session.current_pnm,
        current_term=session.current_term,
        storage=storage
    ) or []

    # If empty and we have an LLM, attempt a zero-doc LLM fallback (AI-only)
    if not cards and isinstance(info_provider, EnhancedInfoProvider):
        try:
            if getattr(info_provider, "llm", None) and info_provider.llm.healthy():
                # Synthesize a minimal context-driven card via LLM
                prompt = f"""Create 1 actionable info card for ALS/MND based ONLY on this context:

Current PNM: {session.current_pnm}
Current term: {session.current_term}
Patient last answer: "{last_answer}"

Return JSON: {{"title": "...", "bullets": ["...", "..."]}}
"""
                j = info_provider.llm.generate_json(prompt)
                if j and "title" in j and "bullets" in j:
                    cards = [{
                        "title": j["title"][:80],
                        "bullets": j["bullets"][: info_provider.bullets_per_card],
                        "url": None,
                        "source": "AI (no doc)",
                        "pnm": session.current_pnm,
                        "term": session.current_term,
                        "score": 0.6
                    }]
        except Exception:
            pass
    return cards or None

def main():
    s = get_settings()
    storage = get_storage()
    qb = get_question_bank()
    router = get_lexicon_router()
    info = get_info_provider()

    # Health probes (best-effort)
    rag_ok = False
    try:
        rag_ok = RAGQueryClient().healthy()
    except Exception:
        pass
    llm_ok = False
    try:
        dummy = LLMClient(model_id=getattr(s, "AI_MODEL_ID", "meta-llama/llama-3-3-70b-instruct"))
        llm_ok = dummy.healthy()
    except Exception:
        pass

    _log("Health", {"RAGQuery": rag_ok, "LLM": llm_ok})

    # Create a new session
    session_id = f"smoke-{uuid.uuid4().hex[:8]}"
    state = ensure_session(session_id)
    fsm = DialogueFSM(store=storage, qb=qb, router=router, session=state)

    # 1) Route with an AI-friendly complaint (mix of breathing and hand)
    user_opening = "My hands feel weak and I sometimes struggle to breathe at night."
    pnm, term = fsm.route_intent(user_opening)
    _log("Routing result", {"pnm": pnm, "term": term, "fsm_state": state.fsm_state})

    assert pnm and term, "Routing failed (pnm/term is None). Check lexicon/semantic backoff/AI router."

    # 2) Ask main question (and record assistant turn)
    q = fsm.get_current_question()
    assert q and q["type"] == "main", "Failed to fetch main question"
    _log("Main Question", q)
    write_assistant_turn(storage, state, q["text"])

    # 3) User answers main
    ans_main = "Sometimes I wake up short of breath and my grip is much weaker."
    next_state = fsm.receive_answer(ans_main)
    _log("After main answer", {"next_state": next_state, "turn_index": state.turn_index})

    # Info cards attempt (throttled internally). Allow in test
    cards = try_info_cards(info, storage, state, ans_main)
    if cards:
        _log("Info cards (after main)", cards)

    # 4) Keep asking followups until we hit scoring (respect thresholds)
    max_steps = 6
    steps = 0
    while steps < max_steps:
        steps += 1
        q = fsm.get_current_question()
        if not q:
            break
        assert q["type"] in ("followup", "main"), "Unexpected question type"
        _log(f"Q{steps}", q)
        write_assistant_turn(storage, state, q["text"])

        # Dummy followup answer
        ans = "It happens a few times per week and worsens when I lie flat."
        st = fsm.receive_answer(ans)
        _log(f"After answer {steps}", {"next_state": st, "turn_index": state.turn_index})

        # Try info card again (should be throttled if too soon)
        cards = try_info_cards(info, storage, state, ans)
        if cards:
            _log(f"Info cards (step {steps})", cards)

        if st == "scored":
            break
        if st == "done":
            break

    # 5) Verify term score exists
    trows = storage.list_term_scores(state.session_id, pnm=state.current_pnm)
    _log("Term scores", trows)
    assert any(r.get("term") == state.current_term for r in trows), "Current term was not scored."

    # 6) Dimension score (aggregation may already run inside FSM)
    drow = storage.get_dimension_score(state.session_id, state.current_pnm)
    _log("Dimension score", drow or {})
    assert drow is not None, "Dimension score missing; check _aggregate_dimension_if_possible."

    # 7) Print uncovered terms (for visibility)
    from app.services.lexicon_router import LexiconRouter as LR
    all_terms = set(router.topics_for_pnm(state.current_pnm))
    covered = set(r["term"] for r in trows if r.get("term"))
    _log("Uncovered terms", sorted(list(all_terms - covered)))

    print("\n✅ Smoke test finished OK.")

if __name__ == "__main__":
    main()
