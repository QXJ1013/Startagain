# utils/text.py
# Purpose: Text utilities used across RAG pipeline and scoring:
# - normalization, whitespace cleanup
# - safe truncation by tokens/words
# - simple sentence splitting
# - keyword helpers

import re
import unicodedata
from typing import List

_whitespace_re = re.compile(r"\s+")
_sentence_split_re = re.compile(r"(?<=[.!?。！？])\s+")

def normalize_text(s: str) -> str:
    """Normalize unicode, collapse whitespace, strip."""
    if s is None:
        return ""
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("\u3000", " ")  # full-width space
    s = _whitespace_re.sub(" ", s)
    return s.strip()

def to_lower_ascii(s: str) -> str:
    """Lowercase and strip accents to ASCII where possible."""
    if s is None:
        return ""
    s = s.lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    # Keep common punctuation and spaces only
    return "".join(c for c in s if 32 <= ord(c) <= 126)

def split_sentences(s: str) -> List[str]:
    """Very simple sentence splitter for UI previews / snippets."""
    s = normalize_text(s)
    if not s:
        return []
    parts = _sentence_split_re.split(s)
    return [p.strip() for p in parts if p.strip()]

def truncate_words(s: str, max_words: int) -> str:
    """Cut by word count; safe for UI tooltips."""
    if max_words <= 0:
        return ""
    words = normalize_text(s).split(" ")
    if len(words) <= max_words:
        return " ".join(words)
    return " ".join(words[:max_words]) + " …"

def naive_token_count(s: str) -> int:
    """Rough token counter (whitespace-based). Good enough for guardrails."""
    return len(normalize_text(s).split())

def truncate_tokens(s: str, max_tokens: int) -> str:
    """Truncate to ~max_tokens using whitespace tokens."""
    if max_tokens <= 0:
        return ""
    toks = normalize_text(s).split()
    if len(toks) <= max_tokens:
        return " ".join(toks)
    return " ".join(toks[:max_tokens]) + " …"

def contains_any(s: str, terms: List[str]) -> bool:
    """Case-insensitive membership check."""
    s_norm = to_lower_ascii(s)
    for t in terms:
        if to_lower_ascii(t) in s_norm:
            return True
    return False

def highlight_terms(s: str, terms: List[str]) -> str:
    """
    Lightweight highlighter for UI (wrap term with ** **).
    Avoids regex DoS; only handles short term list.
    """
    out = s
    for t in sorted(terms, key=len, reverse=True):
        if not t:
            continue
        pattern = re.compile(re.escape(t), flags=re.IGNORECASE)
        out = pattern.sub(lambda m: f"**{m.group(0)}**", out)
    return out
