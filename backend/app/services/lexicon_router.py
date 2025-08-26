# app/services/lexicon_router.py
from __future__ import annotations
from typing import List, Tuple, Optional, Dict
import json, os
import ahocorasick
from app.config import get_settings
from app.utils.text import to_lower_ascii, normalize_text
from app.utils.rerank import hybrid_fusion
from app.vendors.ibm_cloud import RAGQueryClient
from app.vendors.bm25 import BM25Client

class LexiconRouter:
    """
    Primary trigger via Aho–Corasick over pnm_lexicon.json.
    Semantic backoff: if no hit, query BM25 (background) + RAGQuery (background),
    fuse with hybrid_fusion(), then map doc.metadata -> (pnm, term).
    """

    # Term aliases to map lexicon terms to actual question bank terms
    TERM_ALIASES = {
        # Physiological
        "Breathing": "Breathing exercises",
        "Pain": "Bathroom and hygiene aids (shower chair/bidet)",
        "Mobility": "Mobility and transfers", 
        "Speech": "Speech clarity and intelligibility",
        "Swallowing": "Nutrition management",
        "Sleep": "Sleep quality and rest",
        
        # Safety
        "Falls risk": "Care decision-maker designation",
        "Equipment safety": "Equipment readiness and proficiency",
        "Home adaptations": "Accessibility of key places",
        
        # Love & Belonging
        "Isolation": "Communication with support network",
        "Social support": "Virtual support and webinars participation",
        "Relationship & intimacy": "Intimacy and relationships self‑management",
        
        # Esteem
        "Independence": "Home adaptations implementation",
        "Control & choice": "Assistive technologies for daily tasks",
        "Work & role": "Eye-gaze access for devices",
        "Confidence": "Voice-activated interaction (assistants)",
        
        # Cognitive
        "Planning & organisation": "Emergency preparedness",
        "Understanding ALS/MND": "Clinical trials information seeking",
        "Memory & attention": "Family planning considerations",
        "Decision making": "Genetic counselling",
        
        # Aesthetic
        "Personal appearance": "Gaming with adaptive devices",
        "Comfortable environment": "Adaptive entertainment controls",
        
        # Self-Actualisation (map to closest available)
        "Hobbies & goals": "Gaming with adaptive devices",
        "Contribute & advocacy": "Virtual support and webinars participation",
        "Learning & skills": "Clinical trials information seeking",
        
        # Transcendence (map to closest available)
        "Meaning & purpose": "Family planning considerations",
        "Spirituality & faith": "Intimacy and relationships self‑management",
        "Legacy & sharing": "Virtual support and webinars participation",
        "Gratitude & reflection": "Genetic counselling"
    }

    def __init__(self, lexicon: Optional[dict] = None):
        self.cfg = get_settings()
        self.lexicon = lexicon or self._load_default_lexicon()
        self.automaton = self._build_ac(self.lexicon)
        # backoff channels
        self.rag = RAGQueryClient()
        # Only initialize BM25 if available
        try:
            from app.vendors.bm25 import BM25Client
            self.bm25 = BM25Client(
                bg_index_dir=self.cfg.BM25_BG_INDEX_DIR,
                q_index_dir=self.cfg.BM25_Q_INDEX_DIR
            )
        except Exception:
            self.bm25 = None

    # ---------- public ----------

    def resolve_term_alias(self, term: str) -> str:
        """Resolve term alias to actual question bank term"""
        return self.TERM_ALIASES.get(term, term)

    def locate(self, user_text: str, keyword_pool: Optional[List[str]] = None) -> List[Tuple[str, str]]:
        """
        Return list[(term, pnm)] from lexicon. If empty, try semantic backoff.
        """
        q = normalize_text(user_text or "")
        hits = self._ac_hits(q)
        if hits:
            return hits

        if not getattr(self.cfg, "ENABLE_SEMANTIC_BACKOFF", False):
            return []

        queries = [q]
        if keyword_pool:
            queries.append(normalize_text(" ".join(keyword_pool)))

        # Enhanced lexical + semantic search with optimized weights
        # Increase top_k for better coverage and use vector-biased fusion for semantic matching
        lx = self.bm25.search_background(" ".join(queries), top_k=15)
        vx = self.rag.search(" ".join(queries), top_k=15, index_kind="background")
        # Use vector-weighted fusion (alpha=0.3 means 70% vector, 30% lexical) for better semantic matching
        fused = hybrid_fusion(lexical_run=lx, vector_run=vx, alpha=0.3, normalize=True, topn=10)

        mapped: List[Tuple[str, str]] = []
        for d in fused:
            meta = d.get("metadata") or {}
            pnm, term = meta.get("pnm"), meta.get("term")
            if pnm and term:
                mapped.append((term, pnm))
        # de-dup & stable
        seen = set()
        out: List[Tuple[str, str]] = []
        for term, pnm in mapped:
            # Apply term alias resolution
            resolved_term = self.resolve_term_alias(term)
            t = (resolved_term, pnm)
            if t not in seen:
                seen.add(t)
                out.append(t)
        return out

    def topics_for_pnm(self, pnm: str) -> List[str]:
        """
        List all terms in the lexicon under a PNM (deterministic order).
        """
        body = (self.lexicon or {}).get(pnm) or {}
        terms: Dict[str, List[str]] = body.get("terms", {})
        return sorted(list(terms.keys()))

    # ---------- internals ----------

    def _load_default_lexicon(self) -> dict:
        path = self.cfg.PNM_LEXICON_PATH
        if not path or not os.path.exists(path):
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _build_ac(self, lex: dict):
        A = ahocorasick.Automaton()
        for pnm, body in (lex or {}).items():
            terms = (body or {}).get("terms", {})
            for term, aliases in terms.items():
                for w in [term] + list(aliases or []):
                    key = to_lower_ascii(w)
                    if key:
                        A.add_word(key, (term, pnm))
        A.make_automaton()
        return A

    def _ac_hits(self, q: str) -> List[Tuple[str, str]]:
        if not self.automaton or not q:
            return []
        qn = to_lower_ascii(q)
        found, seen = [], set()
        for _, payload in self.automaton.iter(qn):
            term, pnm = payload
            # Apply term alias resolution
            resolved_term = self.resolve_term_alias(term)
            k = (resolved_term.lower(), pnm)
            if k not in seen:
                seen.add(k)
                found.append((resolved_term, pnm))
        found.sort(key=lambda x: (x[1], x[0]))
        return found
