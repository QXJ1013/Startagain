# app/vendors/bm25.py
from __future__ import annotations

"""
BM25 (Whoosh) sparse retrieval:
- Two indices: background (knowledge) and question (question bank).
- Real BM25F scores (hit.score), normalized output schema consistent with semantic channel.
- Health checks and safe (re)creation on corruption.

NOTE: For large-scale/Chinese corpora, consider OpenSearch/Elasticsearch with BM25.
"""

from typing import List, Dict, Any, Optional
import os
import shutil
import logging

from app.config import get_settings

log = logging.getLogger(__name__)

try:
    from whoosh import index
    from whoosh.fields import Schema, TEXT, ID, STORED
    from whoosh.qparser import MultifieldParser, OrGroup
    from whoosh.analysis import StemmingAnalyzer
except Exception:  # pragma: no cover
    index = None  # type: ignore


def _ensure_dir(p: str) -> None:
    os.makedirs(p, exist_ok=True)


def _bg_schema():
    if not index:
        return None
    return Schema(
        id=ID(stored=True, unique=True),
        title=TEXT(stored=True, analyzer=StemmingAnalyzer()),
        body=TEXT(stored=True, analyzer=StemmingAnalyzer()),
        pnm=TEXT(stored=True),
        term=TEXT(stored=True),
        url=STORED,
        source=STORED,
    )


def _q_schema():
    if not index:
        return None
    return Schema(
        id=ID(stored=True, unique=True),
        pnm=TEXT(stored=True),
        term=TEXT(stored=True),
        main=TEXT(stored=True, analyzer=StemmingAnalyzer()),
        followups=TEXT(stored=True, analyzer=StemmingAnalyzer()),
        payload=STORED,  # original record for fallback mapping
    )


class _Index:
    def __init__(self, path: str, schema) -> None:
        if index is None:
            raise RuntimeError("Whoosh is not installed. Please `pip install whoosh`.")
        _ensure_dir(path)
        self.path = path
        if not os.listdir(path):
            self.ix = index.create_in(path, schema=schema)
        else:
            try:
                self.ix = index.open_dir(path)
            except Exception:  # corrupted -> recreate
                shutil.rmtree(path, ignore_errors=True)
                _ensure_dir(path)
                self.ix = index.create_in(path, schema=schema)

    def upsert_many(self, docs: List[Dict[str, Any]]) -> int:
        n = 0
        w = self.ix.writer(limitmb=256)
        try:
            for d in docs:
                if "id" not in d:
                    continue
                w.update_document(**d)
                n += 1
            w.commit()
        except Exception:  # pragma: no cover
            w.cancel()
            raise
        return n

    def search(self, query: str, fields: List[str], top_k: int) -> List[Dict[str, Any]]:
        with self.ix.searcher() as s:
            parser = MultifieldParser(fields, schema=self.ix.schema, group=OrGroup)
            q = parser.parse(query or "")
            res = s.search(q, limit=top_k)
            out = []
            for hit in res:
                d = dict(hit)
                d["_score"] = float(getattr(hit, "score", 0.0))
                out.append(d)
            return out


class BM25Client:
    """
    Two-channel BM25 client:
    - Background knowledge index
    - Question bank index
    """

    def __init__(self, bg_index_dir: Optional[str] = None, q_index_dir: Optional[str] = None) -> None:
        cfg = get_settings()
        self.bg_dir = bg_index_dir or cfg.BM25_BG_INDEX_DIR
        self.q_dir = q_index_dir or cfg.BM25_Q_INDEX_DIR
        
        # Only create indices if whoosh is available
        if index:
            self.bg = _Index(self.bg_dir, _bg_schema()) if self.bg_dir and _bg_schema() else None
            self.q = _Index(self.q_dir, _q_schema()) if self.q_dir and _q_schema() else None
        else:
            self.bg = None
            self.q = None

    # ---------- health ----------

    def healthy_bg(self) -> bool:
        return self.bg is not None

    def healthy_q(self) -> bool:
        return self.q is not None

    # ---------- background ----------

    def index_background(self, records: List[Dict[str, Any]]) -> int:
        """
        records: [{"id","title","body","pnm","term","url","source"}]
        """
        if not self.bg:
            return 0
        docs = []
        for r in records:
            docs.append({
                "id": str(r.get("id")),
                "title": r.get("title", "") or "",
                "body": r.get("body", "") or "",
                "pnm": r.get("pnm", "") or "",
                "term": r.get("term", "") or "",
                "url": r.get("url"),
                "source": r.get("source"),
            })
        return self.bg.upsert_many(docs)

    def search_background(
        self, query: str, *, top_k: int = 8, filter_pnm: Optional[str] = None, filter_term: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        if not self.bg or not query:
            return []
        raw = self.bg.search(query, fields=["title", "body"], top_k=top_k * 2)
        out: List[Dict[str, Any]] = []
        for d in raw:
            # best-effort post-filter (we still keep spillover; fusion will handle)
            out.append({
                "id": str(d.get("id")),
                "text": f"{d.get('title','')}. {d.get('body','')}",
                "score": float(d.get("_score", 0.0)),
                "metadata": {
                    "pnm": d.get("pnm"),
                    "term": d.get("term"),
                    "title": d.get("title"),
                    "url": d.get("url"),
                    "source": d.get("source") or "bm25_bg",
                    "index_kind": "background",
                    "index_id": self.bg_dir
                }
            })
        # small deterministic rank by score
        out.sort(key=lambda x: x["score"], reverse=True)
        return out[:top_k]

    # ---------- question ----------

    def index_questions(self, records: List[Dict[str, Any]]) -> int:
        """
        records: [{"id","pnm","term","main","followups":[...], "payload":{...}}]
        """
        if not self.q:
            return 0
        docs = []
        for r in records:
            docs.append({
                "id": str(r.get("id")),
                "pnm": r.get("pnm", "") or "",
                "term": r.get("term", "") or "",
                "main": r.get("main", "") or "",
                "followups": " ".join(r.get("followups", []) or []),
                "payload": r
            })
        return self.q.upsert_many(docs)

    def search_questions(
        self, query: str, *, top_k: int = 8, filter_pnm: Optional[str] = None, filter_term: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        if not self.q or not query:
            return []
        raw = self.q.search(query, fields=["main", "followups"], top_k=top_k * 2)
        out: List[Dict[str, Any]] = []
        for d in raw:
            main = d.get("main", "") or ""
            foll = d.get("followups", "") or ""
            out.append({
                "id": str(d.get("id")),
                "text": f"{main}\n{foll}",
                "score": float(d.get("_score", 0.0)),
                "metadata": {
                    "pnm": d.get("pnm"),
                    "term": d.get("term"),
                    "source": "bm25_q",
                    "index_kind": "question",
                    "index_id": self.q_dir,
                    "question_payload": d.get("payload")
                }
            })
        out.sort(key=lambda x: x["score"], reverse=True)
        return out[:top_k]
