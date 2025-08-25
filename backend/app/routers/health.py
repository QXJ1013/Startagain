# app/routers/health.py
from __future__ import annotations

from fastapi import APIRouter, Depends
from app.schemas.base import HealthProbeOut
from app.deps import get_storage
from app.services.storage import Storage
from app.vendors.ibm_cloud import RAGQueryClient
from app.vendors.bm25 import BM25Client
from app.config import get_settings

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/livez", response_model=HealthProbeOut)
def livez():
    """Liveness: process is up."""
    return HealthProbeOut(status="ok", checks={"process": True})


@router.get("/readyz", response_model=HealthProbeOut)
def readyz(storage: Storage = Depends(get_storage)):
    """
    Readiness: core dependencies are ready.
    We do lightweight checks: storage connectivity; IBM/BM25 best-effort.
    """
    cfg = get_settings()

    # storage check
    db_ok = False
    try:
        storage.ping()
        db_ok = True
    except Exception:
        db_ok = False

    # ibm ragquery check (best-effort)
    rag_ok = False
    try:
        rag = RAGQueryClient()
        rag_ok = rag.healthy()
    except Exception:
        rag_ok = False

    # bm25 check (best-effort)
    bm_ok = False
    try:
        bm = BM25Client(cfg.BM25_BG_INDEX_DIR, cfg.BM25_Q_INDEX_DIR)
        bm_ok = bm.healthy_bg() or bm.healthy_q()
    except Exception:
        bm_ok = False

    status_overall = "ok" if (db_ok and (rag_ok or True) and (bm_ok or True)) else "degraded"
    return HealthProbeOut(status=status_overall, checks={
        "db": db_ok,
        "ragquery": rag_ok,
        "bm25": bm_ok
    })


@router.get("/healthz", response_model=HealthProbeOut)
def healthz(storage: Storage = Depends(get_storage)):
    """
    Full health: same as readyz for now, can include more diagnostics.
    """
    return readyz(storage)
