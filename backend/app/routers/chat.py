# app/routers/chat.py
from __future__ import annotations

from typing import Optional, List, Dict, Any
import logging

from fastapi import APIRouter, Depends, Header, HTTPException

from app.schemas.chat import (
    RouteIn, RouteOut,
    QuestionOut,
    AnswerIn, AnswerOut,
    StateOut,
    ScoresOut,
    FinishIn, FinishOut, DimensionResultOut,
    ResumeOut
)
from app.schemas.base import TermScoreOut, DimensionScoreOut
from app.services.session import SessionState
from app.services.fsm import DialogueFSM
from app.services.storage import Storage
from app.services.question_bank import QuestionBank
from app.services.lexicon_router import LexiconRouter
# from app.services.info_provider import InfoProvider
from app.services.info_provider_enhanced import EnhancedInfoProvider as InfoProvider

from app.services.aggregator import aggregate_dimension_for_pnm
from app.deps import get_storage, get_question_bank, get_lexicon_router, get_info_provider

log = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


# -------- helpers --------

def _load_state(storage: Storage, session_id: Optional[str]) -> SessionState:
    """
    Load SessionState from storage. Does NOT create a DB row.
    Raise 400 if header missing.
    """
    if not session_id:
        raise HTTPException(status_code=400, detail="Missing X-Session-Id header.")
    return SessionState.load(storage, session_id)


def _fsm(storage: Storage, qb: QuestionBank, router_: LexiconRouter, state: SessionState) -> DialogueFSM:
    return DialogueFSM(store=storage, qb=qb, router=router_, session=state)


def _make_question_out(item: Dict[str, Any], state: SessionState) -> QuestionOut:
    # Handle different question formats with debugging
    log.debug(f"_make_question_out: item keys = {list(item.keys())}")
    log.debug(f"_make_question_out: item['text'] type = {type(item.get('text'))}")
    
    if isinstance(item.get("text"), str):
        question_text = item["text"]
        question_type = item.get("type", "single")
        log.debug("Using item['text'] format")
    elif isinstance(item.get("question"), dict):
        question_text = item["question"]["text"]
        question_type = item["question"].get("type", "single")
        log.debug("Using item['question']['text'] format")
    else:
        # Fallback: use main field or error
        question_text = item.get("main", "No question text available")
        question_type = item.get("type", "single")
        log.debug("Using fallback format")
    
    # Ensure question_text is always a string
    if not isinstance(question_text, str):
        log.error(f"question_text is not string: {type(question_text)}, value: {question_text}")
        question_text = str(question_text) if question_text else "Error: No question text"
    
    # Convert followups to proper schema format
    followups = None
    if item.get("followups"):
        followups = []
        for followup_item in item["followups"]:
            if isinstance(followup_item, dict):
                # Convert dict followup to FollowupOut schema
                followup_options = []
                if followup_item.get("options"):
                    for opt in followup_item["options"]:
                        if isinstance(opt, dict):
                            followup_options.append({
                                "id": opt.get("id", ""),
                                "label": opt.get("label", "")
                            })
                
                followups.append({
                    "id": followup_item.get("id", ""),
                    "text": followup_item.get("text", ""),
                    "type": followup_item.get("type", "single"),
                    "options": followup_options if followup_options else None
                })
            else:
                # Handle string followups as simple text
                followups.append({
                    "id": f"followup_{len(followups)}",
                    "text": str(followup_item),
                    "type": "single",
                    "options": None
                })
    
    return QuestionOut(
        id=item["id"],
        type=question_type,
        text=question_text,
        pnm=state.current_pnm,
        term=state.current_term,
        followups=followups
    )


def _row_to_term_score(row: Dict[str, Any]) -> TermScoreOut:
    return TermScoreOut(
        session_id=row["session_id"],
        pnm=row["pnm"],
        term=row["term"],
        score_0_7=int(row["score_0_7"]),
        rationale=row.get("rationale"),
        evidence_turn_ids=list(row.get("evidence_turn_ids") or []),
        method_version=row.get("method_version"),
        updated_at=row.get("updated_at"),
    )


def _row_to_dim_score(row: Dict[str, Any]) -> DimensionScoreOut:
    return DimensionScoreOut(
        session_id=row["session_id"],
        pnm=row["pnm"],
        score_0_7=float(row["score_0_7"]),
        coverage_ratio=float(row.get("coverage_ratio") or 0.0),
        stage=row.get("stage"),
        method_version=row.get("method_version"),
        updated_at=row.get("updated_at"),
    )


# -------- endpoints --------

@router.post("/route", response_model=RouteOut)
def route_intent(
    payload: RouteIn,
    storage: Storage = Depends(get_storage),
    qb: QuestionBank = Depends(get_question_bank),
    router_: LexiconRouter = Depends(get_lexicon_router),
    session_id: Optional[str] = Header(default=None, convert_underscores=False, alias="X-Session-Id")
):
    """
    Determine current (pnm, term) and respect lock window.
    Always ensure a session DB row exists to avoid FK issues later.
    """
    state = _load_state(storage, session_id)

    # Ensure session row exists (prevents FK failures on /answer)
    storage.ensure_session(state.session_id, fsm_state=state.fsm_state or "ROUTE")

    fsm = _fsm(storage, qb, router_, state)
    pnm_before, term_before = state.current_pnm, state.current_term

    # Route to (pnm, term)
    pnm, term = fsm.route_intent(payload.text)

    # Hard guard: if no hit, return 422, do NOT return empty values
    if not pnm or not term:
        raise HTTPException(status_code=422, detail="No lexicon/semantic hit for this text.")

    # REMOVED: Pre-selecting questions advances FSM state prematurely
    # This causes the FSM to jump from ASK_MAIN -> ASK_FOLLOWUPS during routing
    # Instead, let /chat/question handle question selection properly
    # try:
    #     item = fsm.get_current_question()
    #     if item:
    #         # fsm may have advanced internal pointers; persist state
    #         state.save(storage)
    # except Exception as e:
    #     log.warning("Pre-select question failed after routing: %s", e)

    locked = bool(pnm_before and pnm != pnm_before)
    reason = "locked to current dimension" if locked else None

    # Persist any changes from routing (current_pnm/term, lock window, etc.)
    state.save(storage)

    return RouteOut(
        session_id=state.session_id,
        current_pnm=pnm,
        current_term=term,
        locked=locked,
        reason=reason
    )


@router.get("/question", response_model=QuestionOut)
def get_question(
    storage: Storage = Depends(get_storage),
    qb: QuestionBank = Depends(get_question_bank),
    router_: LexiconRouter = Depends(get_lexicon_router),
    session_id: Optional[str] = Header(default=None, convert_underscores=False, alias="X-Session-Id")
):
    """
    Get the next question for the current (pnm, term).
    """
    state = _load_state(storage, session_id)

    # Guard: session row must exist (skip /route -> friendly 400)
    if not storage.has_session(state.session_id):
        raise HTTPException(status_code=400, detail="Route first: /chat/route must succeed before asking questions.")

    fsm = _fsm(storage, qb, router_, state)
    item = fsm.get_current_question()
    if not item:
        # Either routing not done or bank missing questions for this term
        raise HTTPException(status_code=404, detail="No question available; route first or answers exhausted.")

    # Reload state to get FSM's updates
    updated_state = _load_state(storage, session_id)
    return _make_question_out(item, updated_state)


@router.post("/answer", response_model=AnswerOut)
def post_answer(
    payload: AnswerIn,
    storage: Storage = Depends(get_storage),
    qb: QuestionBank = Depends(get_question_bank),
    router_: LexiconRouter = Depends(get_lexicon_router),
    info: InfoProvider = Depends(get_info_provider),
    session_id: Optional[str] = Header(default=None, convert_underscores=False, alias="X-Session-Id")
):
    """
    Submit user's answer. FSM will:
    - record turn
    - advance followups or trigger scoring
    - possibly aggregate dimension
    - (optionally) return info cards from InfoProvider
    """
    state = _load_state(storage, session_id)

    # Guard: session row must exist
    if not storage.has_session(state.session_id):
        storage.ensure_session(state.session_id, state=state.fsm_state or "ROUTE")
        if not storage.has_session(state.session_id):
            raise HTTPException(status_code=400, detail="Route first: /chat/route must succeed before answering.")

    # Guard: must have an active question id (prevent answering without question)
    if not state.current_qid:
        raise HTTPException(status_code=400, detail="No active question. Call /chat/question first.")

    fsm = _fsm(storage, qb, router_, state)

    try:
        next_state = fsm.receive_answer(payload.text, meta=payload.meta)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Optional info cards (throttled inside InfoProvider)
    info_cards = None
    if payload.request_info:
        try:
            info_cards = info.maybe_provide_info(
                session=state,
                last_answer=payload.text,
                current_pnm=state.current_pnm,
                current_term=state.current_term,
                storage=storage
            ) or None
        except Exception as e:
            log.warning("Info provider failed: %s", e)
            info_cards = None

    # If the term has just been scored, return the latest term score for transparency
    scored_obj = None
    if next_state == "scored" and state.current_pnm and state.current_term:
        rows = storage.list_term_scores(state.session_id, pnm=state.current_pnm) or []
        for r in rows:
            if r.get("term") == state.current_term:
                scored_obj = _row_to_term_score(r)

    state.save(storage)
    return AnswerOut(
        next_state=next_state,
        turn_index=state.turn_index,
        current_pnm=state.current_pnm,
        current_term=state.current_term,
        scored=scored_obj,
        info_cards=info_cards
    )


@router.get("/state", response_model=StateOut)
def get_state(
    storage: Storage = Depends(get_storage),
    session_id: Optional[str] = Header(default=None, convert_underscores=False, alias="X-Session-Id")
):
    state = _load_state(storage, session_id)
    return StateOut(
        session_id=state.session_id,
        status=state.status,
        fsm_state=state.fsm_state,
        current_pnm=state.current_pnm,
        current_term=state.current_term,
        current_qid=state.current_qid,
        asked_qids=state.asked_qids,
        followup_ptr=state.followup_ptr,
        lock_until_turn=state.lock_until_turn,
        turn_index=state.turn_index,
        last_info_turn=state.last_info_turn
    )


@router.get("/scores", response_model=ScoresOut)
def get_scores(
    storage: Storage = Depends(get_storage),
    session_id: Optional[str] = Header(default=None, convert_underscores=False, alias="X-Session-Id")
):
    """
    Return all term scores and dimension scores for this session.
    """
    state = _load_state(storage, session_id)

    if not storage.has_session(state.session_id):
        raise HTTPException(status_code=400, detail="Route first: /chat/route must succeed before querying scores.")

    trows = storage.list_term_scores(state.session_id) or []
    drows = storage.list_dimension_scores(state.session_id) or []

    terms = [_row_to_term_score(r) for r in trows]
    dims = [_row_to_dim_score(r) for r in drows]
    return ScoresOut(term_scores=terms, dimension_scores=dims)


@router.post("/finish", response_model=FinishOut)
def finish(
    payload: FinishIn,
    storage: Storage = Depends(get_storage),
    qb: QuestionBank = Depends(get_question_bank),
    router_: LexiconRouter = Depends(get_lexicon_router),
    session_id: Optional[str] = Header(default=None, convert_underscores=False, alias="X-Session-Id")
):
    """
    Commit dimension aggregation across all PNMs that have term scores.
    """
    state = _load_state(storage, session_id)

    if not storage.has_session(state.session_id):
        raise HTTPException(status_code=400, detail="Route first: /chat/route must succeed before finishing.")

    # recompute aggregation if commit=True
    if payload.commit:
        trows = storage.list_term_scores(state.session_id) or []
        by_pnm: Dict[str, Dict[str, Dict[str, Any]]] = {}
        for r in trows:
            pnm = r["pnm"]
            by_pnm.setdefault(pnm, {})
            by_pnm[pnm][r["term"]] = {"score": float(r.get("score_0_7") or 0.0)}
        for pnm, term_dict in by_pnm.items():
            res = aggregate_dimension_for_pnm(pnm, term_dict, input_scale="0_7", missing_strategy="impute_min")
            storage.upsert_dimension_score(
                session_id=state.session_id,
                pnm=pnm,
                score_0_7=res.score_0_7,
                coverage_ratio=res.coverage_ratio,
                stage=res.stage,
                method_version=res.method_version,
            )

    results: List[DimensionResultOut] = []
    for pnm in storage.list_dimensions_with_scores(state.session_id):
        drow = storage.get_dimension_score(state.session_id, pnm)
        trows = storage.list_term_scores(state.session_id, pnm=pnm) or []

        # uncovered terms
        all_terms = set(qb.list_terms_for_pnm(pnm) or router_.topics_for_pnm(pnm))
        covered = set(r["term"] for r in trows if r.get("term"))
        uncovered = sorted(list(all_terms - covered))

        results.append(DimensionResultOut(
            pnm=pnm,
            score_0_7=drow["score_0_7"] if drow else None,
            stage=drow.get("stage") if drow else None,
            term_scores=[_row_to_term_score(r) for r in trows],
            uncovered_terms=uncovered,
            next_steps=[]
        ))
    return FinishOut(results=results)


@router.post("/resume", response_model=ResumeOut)
def resume(
    storage: Storage = Depends(get_storage),
    session_id: Optional[str] = Header(default=None, convert_underscores=False, alias="X-Session-Id")
):
    """
    Return current state so frontend can continue the conversation flow.
    """
    state = _load_state(storage, session_id)
    return ResumeOut(state=StateOut(
        session_id=state.session_id,
        status=state.status,
        fsm_state=state.fsm_state,
        current_pnm=state.current_pnm,
        current_term=state.current_term,
        current_qid=state.current_qid,
        asked_qids=state.asked_qids,
        followup_ptr=state.followup_ptr,
        lock_until_turn=state.lock_until_turn,
        turn_index=state.turn_index,
        last_info_turn=state.last_info_turn
    ))
