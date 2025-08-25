# app/utils/rerank.py
from __future__ import annotations

"""
Hybrid fusion & reranking utilities for RAG:
- hybrid_fusion: combine BM25 (lexical) and semantic (vector) runs with score normalization
- rrf_merge: reciprocal rank fusion (optional)
- mmr_diversify: Maximal Marginal Relevance (optional, not used by default)

Unified document schema expected for inputs:
{
  "id": str,
  "text": str,
  "score": float,
  "metadata": {
     "url": str|None,
     "pnm": str|None,
     "term": str|None,
     "title": str|None,
     "source": str|None,
     "index_kind": "background"|"question"|None,
     "index_id": str|None
  }
}
"""

from typing import Any, Dict, List, Callable, Optional, Tuple
import math

Document = Dict[str, Any]
Run = List[Document]


def _key_of(d: Document) -> str:
    """Primary merge key: prefer URL, else id."""
    md = d.get("metadata") or {}
    url = (md.get("url") or "").strip()
    if url:
        return url
    return (d.get("id") or "").strip()


def _min_max_norm(scores: List[float]) -> List[float]:
    if not scores:
        return []
    lo, hi = min(scores), max(scores)
    if hi <= lo:
        return [0.0 for _ in scores]
    return [(s - lo) / (hi - lo) for s in scores]


def _normalize_run(run: Run) -> Run:
    if not run:
        return []
    vals = [float(d.get("score") or 0.0) for d in run]
    norm_vals = _min_max_norm(vals)
    out: Run = []
    for d, ns in zip(run, norm_vals):
        c = dict(d)
        c["score"] = float(ns)
        out.append(c)
    return out


def hybrid_fusion(
    *,
    lexical_run: Run,
    vector_run: Run,
    alpha: float = 0.6,           # lexical weight
    normalize: bool = True,
    topn: int = 6
) -> Run:
    """
    Fuse two runs by weighted sum after per-run normalization.
    - alpha in [0,1], higher -> prefer lexical(BM25)
    - If one run empty -> return the other (normalized if requested)
    - Merges by (url or id)
    - Adds 'fused_score' to each document
    """
    alpha = max(0.0, min(1.0, float(alpha)))
    lx = _normalize_run(lexical_run) if normalize else list(lexical_run or [])
    vx = _normalize_run(vector_run) if normalize else list(vector_run or [])

    if not lx and not vx:
        return []
    if lx and not vx:
        out = sorted(lx, key=lambda d: d.get("score", 0.0), reverse=True)[:topn]
        for d in out:
            d["fused_score"] = float(d.get("score") or 0.0)
        return out
    if vx and not lx:
        out = sorted(vx, key=lambda d: d.get("score", 0.0), reverse=True)[:topn]
        for d in out:
            d["fused_score"] = float(d.get("score") or 0.0)
        return out

    bucket: Dict[str, Dict[str, Any]] = {}

    def add(run: Run, tag: str):
        for d in run:
            k = _key_of(d)
            if not k:
                continue
            ref = bucket.setdefault(k, {"doc": d, "lex": None, "vec": None})
            if tag == "lex":
                ref["lex"] = float(d.get("score") or 0.0)
            else:
                ref["vec"] = float(d.get("score") or 0.0)

    add(lx, "lex")
    add(vx, "vec")

    fused: Run = []
    for k, entry in bucket.items():
        base = dict(entry["doc"])
        s_lex = float(entry.get("lex") or 0.0)
        s_vec = float(entry.get("vec") or 0.0)
        fused_score = alpha * s_lex + (1.0 - alpha) * s_vec
        base["fused_score"] = fused_score
        fused.append(base)

    fused.sort(key=lambda d: d.get("fused_score", 0.0), reverse=True)
    return fused[:topn]


def rrf_merge(runs: List[Run], *, k: int = 60, topn: int = 10) -> Run:
    """
    Reciprocal Rank Fusion for multiple runs.
    Score = sum(1 / (k + rank_i))
    """
    board: Dict[str, Dict[str, Any]] = {}
    for run in runs:
        for rank, d in enumerate(run, start=1):
            kkey = _key_of(d)
            if not kkey:
                continue
            cell = board.setdefault(kkey, {"doc": d, "rrf": 0.0})
            cell["rrf"] += 1.0 / (k + rank)

    out = []
    for cell in board.values():
        doc = dict(cell["doc"])
        doc["rrf_score"] = cell["rrf"]
        out.append(doc)
    out.sort(key=lambda d: d.get("rrf_score", 0.0), reverse=True)
    return out[:topn]


def mmr_diversify(
    *,
    candidates: Run,
    select_k: int = 6,
    lambda_weight: float = 0.7,
    sim_fn: Optional[Callable[[Document, Document], float]] = None
) -> Run:
    """
    Optional diversification via MMR (greedy).
    - sim_fn defaults to simple overlap over titles/urls/text (lightweight).
    """
    if not candidates:
        return []
    sims = sim_fn or _default_sim
    picked: List[Document] = []
    pool = list(candidates)

    while pool and len(picked) < select_k:
        best_doc, best_score = None, -1e9
        for d in pool:
            rel = float(d.get("fused_score") or d.get("score") or 0.0)
            div = 0.0 if not picked else max(sims(d, p) for p in picked)
            mmr = lambda_weight * rel - (1 - lambda_weight) * div
            if mmr > best_score:
                best_doc, best_score = d, mmr
        picked.append(best_doc)  # type: ignore[arg-type]
        pool.remove(best_doc)    # type: ignore[arg-type]
    return picked


def _default_sim(a: Document, b: Document) -> float:
    """Very light overlap-based similarity in [0,1]."""
    def toks(d: Document) -> set:
        md = d.get("metadata") or {}
        text = " ".join([
            str(md.get("title") or ""),
            str(md.get("url") or ""),
            str(d.get("text") or "")
        ]).lower()
        return set(t for t in text.replace("\n", " ").split() if t)

    A, B = toks(a), toks(b)
    if not A or not B:
        return 0.0
    inter = len(A & B)
    denom = math.sqrt(len(A) * len(B))
    return inter / denom if denom else 0.0
