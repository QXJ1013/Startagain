# app/main.py
from __future__ import annotations

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings

# Routers
from app.routers import chat as chat_router     
from app.routers import health as health_router
from app.routers import conversation as conversation_router

# Optional warmup
try:
    from app.deps import warmup_dependencies
except Exception:
    warmup_dependencies = None  # type: ignore

log = logging.getLogger(__name__)


def create_app() -> FastAPI:
    s = get_settings()
    app = FastAPI(title=s.APP_NAME, debug=s.DEBUG)

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=s.CORS_ORIGINS or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(health_router.router)
    app.include_router(chat_router.router)
    app.include_router(conversation_router.router)

    @app.on_event("startup")
    async def _startup():
        
        pass
    @app.get("/", tags=["meta"])
    def root():
        return {"ok": True, "service": s.APP_NAME, "version": s.BUILD_VERSION}

    return app


app = create_app()
