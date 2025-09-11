# app/deps.py - Document-based Dependencies
from __future__ import annotations

import json
import logging
import os
from typing import Optional, Any, Dict

from fastapi import FastAPI, HTTPException, Depends, Header

from app.config import get_settings
from app.services.storage import DocumentStorage
from app.services.question_bank import QuestionBank
from app.services.ai_routing import AIRouter
from app.services.auth import auth_service

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
_storage: Optional[DocumentStorage] = None
_qb: Optional[QuestionBank] = None
_ai_router: Optional[AIRouter] = None
_info: Optional[Any] = None  # Enhanced InfoProvider

# For hot-reload of local JSONs (optional)
_qb_mtime: Optional[float] = None
_lex_mtime: Optional[float] = None


# ------------ DI providers (FastAPI Depends) ------------

def get_storage() -> DocumentStorage:
    global _storage
    if _storage is None:
        s = get_settings()
        # Use schema_v2.sql for document-based structure
        schema_path = s.SCHEMA_PATH.replace('schema.sql', 'schema_v2.sql') if hasattr(s, 'SCHEMA_PATH') else None
        _storage = DocumentStorage(db_path=s.DB_PATH, schema_path=schema_path)
    return _storage


def get_current_user(
    authorization: Optional[str] = Header(None),
    storage: DocumentStorage = Depends(get_storage)
) -> Dict[str, Any]:
    """Extract and validate user from Authorization header"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Extract token from "Bearer <token>"
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid authentication scheme")
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid authorization header format")
    
    # Validate token and get user
    user = auth_service.get_current_user(storage, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return user


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


def get_ai_router() -> AIRouter:
    """
    Get AI router instance for semantic routing.
    """
    global _ai_router
    if _ai_router is None:
        from app.services.ai_routing import AIRouter
        _ai_router = AIRouter()
    return _ai_router


def get_info_provider():
    """Get enhanced info provider instance"""
    global _info
    if _info is None:
        from app.services.info_provider_enhanced import EnhancedInfoProvider
        _info = EnhancedInfoProvider()
    return _info


# ------------ app startup warmup ------------

def warmup_dependencies(app: Optional[FastAPI] = None) -> None:
    """
    Warm core dependencies at startup for document-based system.
    - Initialize document storage & run schema
    - Load question bank
    - Initialize AI router
    - Best-effort health checks for RAG/BM25 channels
    """
    s = get_settings()

    # document storage
    st = get_storage()
    st.ping()
    log.info("Document storage ready at %s", s.DB_PATH)

    # question bank
    qb = get_question_bank()
    n_items = _qb_size(qb)
    log.info("Question bank loaded: %d items", n_items)

    # AI router
    try:
        router = get_ai_router()
        log.info("AI router initialized")
    except Exception as e:
        log.warning("AI router initialization failed: %s", e)

    # Enhanced info provider
    try:
        info = get_info_provider()
        log.info("Enhanced info provider ready")
    except Exception as e:
        log.warning("Info provider initialization failed: %s", e)

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


# ------------ Simplified Conversation Helpers ------------

def get_or_create_simple_conversation(user_id: str, conversation_id: str = None, dimension: str = None) -> str:
    """Get existing conversation or create simple new one"""
    storage = get_storage()
    
    if conversation_id:
        conv = storage.get_conversation(conversation_id)
        if conv and conv.user_id == user_id:
            return conversation_id
    
    # Create new conversation
    return create_simple_conversation(storage, user_id, "general_chat", dimension)


# ------------ Health Check Utilities ------------

def check_document_storage_health() -> Dict[str, Any]:
    """Check document storage system health"""
    try:
        storage = get_storage()
        is_healthy = storage.ping()
        
        # Get some basic stats
        # Note: would need to implement these methods in DocumentStorage
        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "connection": is_healthy,
            "storage_type": "document",
            "schema_version": "v2"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "connection": False,
            "error": str(e)
        }


def check_ai_services_health() -> Dict[str, Any]:
    """Check AI services health"""
    health = {
        "question_bank": False,
        "ai_router": False,
        "info_provider": False
    }
    
    try:
        qb = get_question_bank()
        health["question_bank"] = _qb_size(qb) > 0
    except Exception:
        pass
    
    try:
        router = get_ai_router()
        health["ai_router"] = True
    except Exception:
        pass
    
    try:
        info = get_info_provider()
        health["info_provider"] = True
    except Exception:
        pass
    
    return health


# ------------ Simplified Conversation Management ------------

def create_simple_conversation(storage: DocumentStorage, user_id: str, conversation_type: str = "general_chat", dimension: str = None) -> str:
    """Create a simple conversation and return ID"""
    title = f"{dimension} Assessment" if dimension else "General Chat"
    
    conversation = storage.create_conversation(
        user_id=user_id,
        type=conversation_type,
        dimension=dimension,
        title=title
    )
    
    return conversation.id