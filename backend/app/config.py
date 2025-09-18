# app/config.py
from __future__ import annotations

from functools import lru_cache
from typing import List, Optional

try:
    # Pydantic v2
    from pydantic_settings import BaseSettings
    from pydantic import Field, field_validator
    PYDANTIC_V2 = True
except ImportError:
    # Pydantic v1
    from pydantic import BaseSettings, Field, validator
    PYDANTIC_V2 = False


class Settings(BaseSettings):
    # ---------- app ----------
    APP_NAME: str = "ALS Assistant Backend"
    DEBUG: bool = False
    BUILD_VERSION: Optional[str] = None

    # ---------- server / CORS ----------
    CORS_ORIGINS: List[str] = Field(default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"])  # Production: set to your frontend URLs
    
    if PYDANTIC_V2:
        from pydantic import field_validator
        @field_validator("CORS_ORIGINS", mode="before")
        @classmethod
        def _split_origins(cls, v):
            if isinstance(v, str):
                return [s.strip() for s in v.split(",") if s.strip()]
            return v
    else:
        @validator("CORS_ORIGINS", pre=True)
        def _split_origins(cls, v):
            if isinstance(v, str):
                return [s.strip() for s in v.split(",") if s.strip()]
            return v

    # ---------- database ----------
    DB_PATH: str = "app/data/app.db"
    SCHEMA_PATH: str = "app/data/schema.sql"

    # ---------- IBM watsonx / vector indices ----------
    WATSONX_URL: str = "https://eu-gb.ml.cloud.ibm.com"
    WATSONX_APIKEY: str = ""                 # set via env
    SPACE_ID: str = ""
    PROJECT_ID: Optional[str] = None

    ENABLE_SEMANTIC_BACKOFF: bool = True   # Enable semantic understanding
    ENABLE_AI_ENHANCEMENT: bool = True     # Enable AI-enhanced routing
    BACKGROUND_VECTOR_INDEX_ID: str = ""     # knowledge base
    QUESTION_VECTOR_INDEX_ID: str = ""       # question bank
    VECTOR_INDEX_ID: str = ""                # legacy fallback (unused if both above provided)


    

    ENABLE_KEYWORD_EXPANSION: bool = True
    ENABLE_AI_QUESTION_SELECTION: bool = True
    AI_MODEL_ID: str = "meta-llama/llama-4-maverick-17b-128e-instruct-fp8"
    AI_CONFIDENCE_THRESHOLD: float = 0.6
    MAX_KEYWORDS_PER_TURN: int = 8
    WATSONX_DEFAULT_MODEL_ID: str = "meta-llama/llama-4-maverick-17b-128e-instruct-fp8"

    # ---------- BM25 (Whoosh) ----------
    BM25_ENABLED: bool = True
    BM25_BG_INDEX_DIR: str = "app/data/bm25_bg"
    BM25_Q_INDEX_DIR: str = "app/data/bm25_q"

    # ---------- FSM / flow ----------
    LOCK_WINDOW_TURNS: int = 2
    EVIDENCE_MIN_FUP: int = 2
    MAX_FOLLOWUPS_PER_TERM: int = 3

    # ---------- Info provider / hybrid fusion ----------
    INFO_PROVIDER_ENABLED: bool = True
    INFO_MIN_TURNS_INTERVAL: int = 2      # throttle: minimum turns between info cards
    INFO_TOP_K: int = 8                   # Increased for better knowledge coverage
    INFO_MAX_CARDS: int = 3               # Increased to allow more diverse information
    INFO_BULLETS_PER_CARD: int = 4        # Increased for more comprehensive advice
    HYBRID_ALPHA: float = 0.6             # lexical weight in [0,1]

    # backward-compat alias (if you had INFO_THROTTLE before)
    INFO_THROTTLE: Optional[int] = None
    
    if PYDANTIC_V2:
        @field_validator("INFO_MIN_TURNS_INTERVAL", mode="before")
        @classmethod  
        def _compat_info_throttle(cls, v):
            return v if v is not None else 2
    else:
        @validator("INFO_MIN_TURNS_INTERVAL", pre=True, always=True)
        def _compat_info_throttle(cls, v, values):
            return v if v is not None else (values.get("INFO_THROTTLE") or 2)

    # ---------- stage mapping ----------
    STAGE_THRESHOLDS: List[float] = Field(default_factory=lambda: [1, 2, 3, 4, 5, 6])


    USE_BOOTSTRAP_SCORER: bool = True
    SCORER_MODEL_ID: str = "meta-llama/llama-4-maverick-17b-128e-instruct-fp8"
    SCORING_MEMORY_PATH: str = "app/data/scoring_memory.pkl"
    
    # Enhanced Info Provider
    USE_ENHANCED_INFO: bool = True
    INFO_MODEL_ID: str = "meta-llama/llama-3-3-70b-instruct"  # Better model for information generation


    # ---------- data paths ----------
    PNM_LEXICON_PATH: str = "app/data/pnm_lexicon.json"
    QUESTION_BANK_PATH: str = "app/data/pnm_questions_v3_final.json"

    if PYDANTIC_V2:
        model_config = {
            'case_sensitive': False,
            'env_file': '.env',
            'env_file_encoding': 'utf-8',
            'extra': 'ignore'  # Allow extra fields to be ignored
        }
    else:
        class Config:
            case_sensitive = False
            env_file = ".env"
            env_file_encoding = "utf-8"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
