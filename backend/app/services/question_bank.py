# app/services/question_bank.py
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Iterable
import json

@dataclass
class QuestionItem:
    id: str
    pnm: str
    term: str
    main: str
    followups: List[str]
    terms: List[str]          # synonyms/patterns for routing
    meta: Dict[str, Any]
    options: List[Dict[str, str]] = None  # Button options for the question

class QuestionBank:
    """
    Unified loader + accessor for the question bank JSON.
    Supports two shapes:
      A) legacy:
         { "id": "...", "pnm": "...", "term": "...", "main": "...",
           "followups": [...], "terms": [...], ... }

      B) new (your current file):
         { "id": "...",
           "routing": { "pnm": "...", "term": "...", "patterns": [...] },
           "question": "...",
           "followups": [...],
           ... }
    """
    def __init__(self, source: str | Path | List[Dict[str, Any]] | Dict[str, Any]):
        if isinstance(source, (str, Path)):
            p = Path(source)
            if not p.exists():
                raise FileNotFoundError(f"Question bank not found: {p}")
            raw = json.loads(p.read_text(encoding="utf-8"))
        else:
            raw = source

        # flatten to list
        if isinstance(raw, dict):
            # allow {"items":[...]} or {"data":[...]}
            for k in ("items", "data", "questions"):
                if k in raw and isinstance(raw[k], list):
                    raw = raw[k]
                    break
        if not isinstance(raw, list):
            raise ValueError("Question bank JSON must be a list or dict with 'items'/'data'.")

        self._items: List[QuestionItem] = []
        self._by_key: Dict[tuple, QuestionItem] = {}
        self._index_by_pnm: Dict[str, List[QuestionItem]] = {}

        for obj in raw:
            try:
                item = self._normalize(obj)
                if not item:
                    continue
                self._items.append(item)
                key = (item.pnm.lower(), item.term.lower())
                self._by_key[key] = item
                self._index_by_pnm.setdefault(item.pnm.lower(), []).append(item)
            except Exception:
                # Skip bad rows defensively
                continue

        if not self._items:
            raise RuntimeError("Question bank is empty after normalization.")

    # ---------- normalization ----------

    def _normalize(self, obj: Dict[str, Any]) -> Optional[QuestionItem]:
        """
        Map both schemas to QuestionItem. Return None if required fields are missing.
        """
        # Try legacy first
        pnm = obj.get("pnm")
        term = obj.get("term")
        main = obj.get("main")
        followups = obj.get("followups")
        terms = obj.get("terms")
        options = obj.get("options")

        if pnm and term and main:
            return QuestionItem(
                id=str(obj.get("id") or f"{pnm}:{term}:{abs(hash(main))%10**6}"),
                pnm=str(pnm),
                term=str(term),
                main=str(main),
                followups=self._as_list_of_str(followups),
                terms=self._as_list_of_str(terms),
                options=options if isinstance(options, list) else None,
                meta={k: v for k, v in obj.items()
                      if k not in {"id","pnm","term","main","followups","terms","options"}}
            )

        # Fallback to new schema (v2_full format)
        routing = obj.get("routing") or {}
        pnm = routing.get("pnm")
        term = routing.get("term")
        patterns = routing.get("patterns") or routing.get("aliases") or []
        question_obj = obj.get("question")
        followups = obj.get("followups")

        if pnm and term and question_obj:
            # Extract question text and options from question object
            if isinstance(question_obj, dict):
                question_text = question_obj.get("text")
                question_options = question_obj.get("options")
            else:
                question_text = str(question_obj)
                question_options = None
            
            if question_text:
                return QuestionItem(
                    id=str(obj.get("id") or f"{pnm}:{term}:{abs(hash(question_text))%10**6}"),
                    pnm=str(pnm),
                    term=str(term),
                    main=str(question_text),
                    followups=self._process_followups(followups),
                    terms=self._as_list_of_str(patterns),
                    options=question_options if isinstance(question_options, list) else None,
                    meta={k: v for k, v in obj.items() if k not in {"id","routing","question","followups"}}
                )

        # Not recognizable
        return None

    @staticmethod
    def _as_list_of_str(x: Any) -> List[str]:
        if not x:
            return []
        if isinstance(x, list):
            return [str(s).strip() for s in x if str(s).strip()]
        # tolerate accidental newline joined string
        return [s.strip() for s in str(x).split("\n") if s.strip()]
    
    def _process_followups(self, val) -> List:
        """Process followups to keep objects intact while ensuring list format"""
        if not val:
            return []
        if isinstance(val, list):
            return val  # Keep original structure (objects or strings)
        return [val]  # Wrap single item in list

    # ---------- accessors ----------

    def size(self) -> int:
        return len(self._items)

    def __len__(self) -> int:
        return len(self._items)

    def items(self) -> List[QuestionItem]:
        return list(self._items)
    
    @property
    def questions(self) -> List[QuestionItem]:
        """Get all questions in the bank"""
        return list(self._items)
    
    def get_question_by_id(self, qid: str) -> Optional[QuestionItem]:
        """Get question by exact ID match"""
        for item in self._items:
            if item.id == qid:
                return item
        return None
    
    def get_question(self, qid: str) -> Optional[QuestionItem]:
        """Alias for get_question_by_id"""
        return self.get_question_by_id(qid)

    def get(self, pnm: str, term: str) -> Optional[QuestionItem]:
        if not pnm or not term:
            return None
        return self._by_key.get((pnm.lower(), term.lower()))

    def has(self, pnm: str, term: str) -> bool:
        return (pnm.lower(), term.lower()) in self._by_key

    def for_pnm(self, pnm: str) -> List[QuestionItem]:
        return self._index_by_pnm.get(pnm.lower(), [])

    def approx_by_term(self, pnm: str, term: str) -> List[QuestionItem]:
        """
        Return candidates in same PNM whose `.terms` or `main` loosely mention `term`.
        Deterministic fallback in case of slight mismatch.
        """
        pnm_lc = pnm.lower()
        term_lc = term.lower()
        same = self._index_by_pnm.get(pnm_lc, [])
        hits: List[QuestionItem] = []
        for it in same:
            hay = [t.lower() for t in it.terms] + [it.term.lower(), it.main.lower()]
            if any(term_lc in h for h in hay):
                hits.append(it)
        return hits
    
        
    def choose_for_term(
        self, 
        pnm: str, 
        term: str, 
        asked_ids: List[str]
    ) -> Optional[QuestionItem]:
        """
        Choose next question for a term, avoiding already asked ones.
        Enhanced with better fallback and logging.
        """
        import logging
        log = logging.getLogger(__name__)
        
        log.debug(f"choose_for_term: pnm={pnm}, term={term}, asked_ids={asked_ids}")
        
        # 1. Try exact match
        item = self.get(pnm, term)
        log.debug(f"Exact match result: {item.id if item else None}")
        if item and item.id not in asked_ids:
            log.debug(f"Returning exact match: {item.id}")
            return item
            
        # 2. Try approximate match in same PNM
        approx_items = self.approx_by_term(pnm, term)
        log.debug(f"Approx match found {len(approx_items)} items")
        for item in approx_items:
            if item.id not in asked_ids:
                log.debug(f"Returning approx match: {item.id}")
                return item
                
        # 3. Try any unasked question in same PNM
        pnm_items = self.for_pnm(pnm)
        log.debug(f"PNM {pnm} has {len(pnm_items)} total questions")
        for item in pnm_items:
            log.debug(f"Checking PNM item {item.id}: asked={item.id in asked_ids}")
            if item.id not in asked_ids:
                log.debug(f"Returning PNM fallback: {item.id}")
                return item
                
        # 4. No cross-PNM fallback - stay within the current PNM
        # This ensures we only ask questions relevant to the current dimension
        log.warning(f"All questions for PNM {pnm} have been asked (total: {len(pnm_items)}, asked: {len([id for id in asked_ids if any(item.id == id for item in pnm_items)])})")
        return None