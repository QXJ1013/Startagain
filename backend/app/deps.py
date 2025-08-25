# app/deps.py
from __future__ import annotations

import json
import logging
import os
from typing import Optional, Any

from fastapi import FastAPI

from app.config import get_settings
from app.services.storage import Storage
from app.services.question_bank import QuestionBank
from app.services.lexicon_router import LexiconRouter
# from app.services.info_provider import InfoProvider  # Old version moved to abandon
from app.services.ai_router import AIEnhancedRouter
from app.services.session import SessionState

# Optional: warm checks
try:
    from app.vendors.ibm_cloud import RAGQueryClient
except Exception:  # pragma: no cover
    RAGQueryClient = None  # type: ignore
try:
    from app.vendors.bm25 import BM25Client
except Exception:  # pragma: no cover
    BM25Client = None  # type: ignore

log = logging.getLogger(__name__)

# ------------ singletons ------------
_storage: Optional[Storage] = None
_qb: Optional[QuestionBank] = None
_router: Optional[LexiconRouter] = None
_info: Optional[Any] = None  # Can be InfoProvider or EnhancedInfoProvider
_ai_router: Optional[AIEnhancedRouter] = None

# For hot-reload of local JSONs (optional)
_qb_mtime: Optional[float] = None
_lex_mtime: Optional[float] = None


# ------------ DI providers (FastAPI Depends) ------------

def get_storage() -> Storage:
    global _storage
    if _storage is None:
        s = get_settings()
        _storage = Storage(db_path=s.DB_PATH, schema_path=s.SCHEMA_PATH)
    return _storage


def get_question_bank() -> QuestionBank:
    """
    Load the question bank once. If the JSON file on disk changes (mtime),
    reload on the next call (useful during development).
    """
    global _qb, _qb_mtime
    s = get_settings()
    path = s.QUESTION_BANK_PATH

    if _qb is None:
        _qb = QuestionBank(path)
        _qb_mtime = _safe_mtime(path)
        return _qb

    # hot-reload support (optional)
    mt = _safe_mtime(path)
    if mt and _qb_mtime and mt > _qb_mtime:
        log.info("Question bank changed on disk, reloading: %s", path)
        _qb = QuestionBank(path)
        _qb_mtime = mt
    return _qb


def get_lexicon_router() -> LexiconRouter:
    """
    Build the AC automaton from pnm_lexicon.json.
    Supports hot-reload on file change.
    """
    global _router, _lex_mtime
    s = get_settings()
    path = s.PNM_LEXICON_PATH

    if _router is None:
        lex = _load_json(path)
        _router = LexiconRouter(lexicon=lex)
        _lex_mtime = _safe_mtime(path)
        return _router

    mt = _safe_mtime(path)
    if mt and _lex_mtime and mt > _lex_mtime:
        log.info("PNM lexicon changed on disk, rebuilding AC automaton: %s", path)
        lex = _load_json(path)
        _router = LexiconRouter(lexicon=lex)
        _lex_mtime = mt
    return _router


# def get_info_provider() -> InfoProvider:
#     global _info
#     if _info is None:
#         _info = InfoProvider()
#     return _info

def get_info_provider():
    global _info
    if _info is None:
        cfg = get_settings()
        if getattr(cfg, 'USE_ENHANCED_INFO', True):
            from app.services.info_provider_enhanced import EnhancedInfoProvider
            _info = EnhancedInfoProvider()
        else:
            # Fallback: create a basic info provider interface
            from app.services.info_provider_enhanced import EnhancedInfoProvider
            _info = EnhancedInfoProvider()  # Use enhanced as default
    return _info
# ------------ app startup warmup ------------

def warmup_dependencies(app: Optional[FastAPI] = None) -> None:
    """
    Warm core dependencies at startup.
    - Initialize DB & run schema
    - Load question bank
    - Build lexicon automaton
    - Best-effort health checks for RAG/BM25 channels
    """
    s = get_settings()

    # storage
    st = get_storage()
    st.ping()
    log.info("Storage ready at %s", s.DB_PATH)

    # question bank
    qb = get_question_bank()
    # robust size detection for different QuestionBank implementations
    n_items = _qb_size(qb) if hasattr(qb, "size") else len(qb)
    log.info("Question bank loaded: %d items", n_items)

    # lexicon
    lx = get_lexicon_router()
    try:
        # touch topics to ensure AC is ready
        topics_total = 0
        if hasattr(lx, "lexicon") and isinstance(lx.lexicon, dict):
            for pnm in lx.lexicon.keys():
                try:
                    topics_total += len(lx.topics_for_pnm(pnm))
                except Exception:
                    pass
        log.info("Lexicon router ready. Topics total (approx): %d", topics_total)
    except Exception as e:
        log.warning("Lexicon warmup skipped: %s", e)

    # optional best-effort checks (do not fail startup)
    if RAGQueryClient is not None:
        try:
            rag = RAGQueryClient()
            log.info("RAGQuery healthy: %s", rag.healthy())
        except Exception as e:
            log.warning("RAGQuery warmup failed: %s", e)

    if BM25Client is not None:
        try:
            bm = BM25Client(s.BM25_BG_INDEX_DIR, s.BM25_Q_INDEX_DIR)
            ok = bm.healthy_bg() or bm.healthy_q()
            log.info("BM25 healthy: %s", ok)
        except Exception as e:
            log.warning("BM25 warmup failed: %s", e)


def _qb_size(qb) -> int:
    """
    Try multiple strategies to get question bank size without assuming a concrete API.
    """
    # method-based
    for m in ("size", "count"):
        fn = getattr(qb, m, None)
        if callable(fn):
            try:
                return int(fn())
            except Exception:
                pass
    # attribute or callable collections
    for attr in ("items", "all", "questions", "data", "records", "_items", "_data"):
        obj = getattr(qb, attr, None)
        if obj is None:
            continue
        try:
            # if callable (e.g., items()), call and measure
            if callable(obj):
                obj = obj()
            return len(obj)  # may succeed if list/dict
        except Exception:
            continue
    # last resort: __len__
    try:
        return len(qb)  # if __len__ implemented
    except Exception:
        return 0

# ------------ helpers ------------

def _safe_mtime(path: Optional[str]) -> Optional[float]:
    try:
        return os.path.getmtime(path) if path and os.path.exists(path) else None
    except Exception:
        return None


def _load_json(path: Optional[str]) -> dict:
    if not path or not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        log.exception("Failed to load JSON: %s", path)
        return {}


def get_ai_router() -> Optional[AIEnhancedRouter]:
    global _ai_router
    if _ai_router is None:
        cfg = get_settings()
        if getattr(cfg, 'ENABLE_AI_ENHANCEMENT', False):
            _ai_router = AIEnhancedRouter(
                lexicon_router=get_lexicon_router(),
                question_bank=get_question_bank(),
                enable_ai=True
            )
    return _ai_router


# ------------ Session Store ------------

class SessionStore:
    """Session store for managing user sessions"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self._session_state = None
    
    def get_session(self) -> SessionState:
        """Get or create session state"""
        if self._session_state is None:
            storage = get_storage()
            self._session_state = SessionState.load(storage, self.session_id)
        return self._session_state
    
    def save_session(self):
        """Save current session state"""
        if self._session_state:
            storage = get_storage()
            self._session_state.save(storage)


def get_session_store(session_id: str = "default_session") -> SessionStore:
    """Get session store instance"""
    return SessionStore(session_id)