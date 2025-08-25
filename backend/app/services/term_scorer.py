# app/services/term_scorer.py
from __future__ import annotations
"""
TermScorer (watsonx via LLMClient):
- Score a single (pnm, term) on 0..7 from recent turns.
- Returns real turn_index in evidence_turn_ids (not local 1..N).
- Strict JSON validation + clamp + robust fallback.

Public API:
    score_term(session_id, pnm, term, turns) -> dict
Returned example:
{
  "session_id": "...",
  "pnm": "Esteem",
  "term": "Communication",
  "score_0_7": 4,
  "rationale": "User reports daily difficulty using AAC at work.",
  "evidence_turn_ids": [12, 13, 15],  # real turn_index
  "method_version": "term_scorer_wx_v2"
}
"""
import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.config import get_settings
from app.vendors.ibm_cloud import LLMClient


@dataclass
class TermScorerConfig:
    model_id: str = "meta-llama/llama-3-3-70b-instruct"
    max_new_tokens: int = 320
    temperature: float = 0.1
    top_p: float = 0.9
    json_max_chars: int = 4000
    use_watsonx: bool = True
    rubric: str = (
        "Score how well the user understands and can act on THIS TERM within THIS PNM dimension.\n"
        "0 = no understanding/engagement; 3–4 = partial understanding with gaps; 7 = can teach others / shares.\n"
        "Use ONLY the dialogue evidence. Be conservative. Prefer lower score if uncertain."
    )


class _JSONGuard:
    @staticmethod
    def extract_first_json_block(text: str, max_chars: int) -> Optional[str]:
        if not text:
            return None
        m = re.search(r"\{[\s\S]*\}", text[:max_chars])
        return m.group(0) if m else None

    @staticmethod
    def validate_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
        # score
        try:
            score = float(payload.get("score_0_7"))
        except Exception:
            score = 0.0
        score = max(0.0, min(7.0, score))
        out = {
            "score_0_7": int(round(score)),
            "rationale": str(payload.get("rationale", "")).strip()[:240],
        }
        evid = payload.get("evidence_turn_ids", [])
        if not isinstance(evid, list):
            evid = []
        evid_clean: List[int] = []
        for x in evid:
            try:
                evid_clean.append(int(x))
            except Exception:
                continue
        out["evidence_turn_ids"] = evid_clean
        return out


class TermScorer:
    def __init__(self, cfg: Optional[TermScorerConfig] = None) -> None:
        self.cfg = cfg or TermScorerConfig()
        self.s = get_settings()
        self.llm = LLMClient(
            model_id=self.cfg.model_id,
            params={
                "max_new_tokens": self.cfg.max_new_tokens,
                "temperature": self.cfg.temperature,
                "top_p": self.cfg.top_p,
            },
            settings=self.s,
        ) if self.cfg.use_watsonx else None

    # ---------- public ----------

    def score_term(
        self,
        session_id: str,
        pnm: str,
        term: str,
        turns: List[Dict[str, Any]],
        last_n: int = 12
    ) -> Dict[str, Any]:
        recent = self._slice_turns(turns, last_n=last_n)
        try:
            if self.llm and self.llm.healthy():
                return self._score_with_llm(session_id, pnm, term, recent)
        except Exception:
            pass  # fall through
        return self._score_with_rules(session_id, pnm, term, recent)

    # ---------- internals ----------

    @staticmethod
    def _slice_turns(turns: List[Dict[str, Any]], last_n: int) -> List[Dict[str, Any]]:
        if not turns:
            return []
        return turns[-last_n:]

    def _build_prompt(self, pnm: str, term: str, recent: List[Dict[str, Any]]) -> str:
        # We enumerate but also include real 'turn_index' for the model to reference directly.
        records = []
        for t in recent:
            records.append({
                "turn_index": t.get("turn_index"),           # real id from storage
                "role": t.get("role") or t.get("speaker") or "user",
                "text": (t.get("text") or t.get("content") or "").strip()
            })

        prompt = f"""
You are an ALS/MND assistant scoring ONE term within ONE PNM dimension.

PNM dimension: {pnm}
Term: {term}

RUBRIC:
{self.cfg.rubric}

EVIDENCE (recent turns with real turn_index):
{json.dumps(records, ensure_ascii=False)}

OUTPUT RULES:
- Return ONLY a JSON object with keys: score_0_7 (0..7), rationale (<= 20 words), evidence_turn_ids (list of REAL turn_index).
- evidence_turn_ids MUST be values from the provided 'turn_index' fields.
- No prose, no code fences, no extra keys.
- Be conservative if evidence is partial.

EXAMPLE VALID JSON:
{{"score_0_7": 3, "rationale": "Needs guidance using AAC daily.", "evidence_turn_ids": [102, 106]}}
"""
        return prompt

    def _score_with_llm(self, session_id: str, pnm: str, term: str, recent: List[Dict[str, Any]]) -> Dict[str, Any]:
        prompt = self._build_prompt(pnm, term, recent)
        resp = self.llm.generate_text(prompt)
        block = _JSONGuard.extract_first_json_block(resp, self.cfg.json_max_chars)
        if not block:
            raise ValueError("No JSON block in LLM output.")
        raw = json.loads(block)
        clean = _JSONGuard.validate_payload(raw)
        clean.update({
            "session_id": session_id,
            "pnm": pnm,
            "term": term,
            "method_version": "term_scorer_wx_v2"
        })
        # If model mistakenly returned local indexes 1..N, map to real turn_index best-effort:
        clean["evidence_turn_ids"] = self._map_evidence_to_real_ids(clean["evidence_turn_ids"], recent)
        return clean

    @staticmethod
    def _map_evidence_to_real_ids(eids: List[int], recent: List[Dict[str, Any]]) -> List[int]:
        # If eids already look like real turn indices (intersect with recent), keep them.
        real = {int(t.get("turn_index")) for t in recent if t.get("turn_index") is not None}
        if any(e in real for e in eids):
            return [e for e in eids if e in real]
        # Else assume user returned 1..N enumeration and map positionally:
        mapping = []
        for e in eids:
            pos = e - 1
            if 0 <= pos < len(recent):
                ti = recent[pos].get("turn_index")
                if isinstance(ti, int):
                    mapping.append(ti)
        return mapping

    def _score_with_rules(self, session_id: str, pnm: str, term: str, recent: List[Dict[str, Any]]) -> Dict[str, Any]:
        text = " ".join([(t.get("text") or "") for t in recent]).lower()
        lower_cues = {"confused", "hard", "difficulty", "cannot", "stuck", "fatigue", "worse", "fail"}
        upper_cues = {"confident", "independent", "share", "teach", "coach"}
        score = 3
        if any(w in text for w in lower_cues):
            score = 2
        if any(w in text for w in upper_cues):
            score = max(score, 5)
        rationale = "Fallback rule: conservative mid score."
        ev = [t.get("turn_index") for t in recent[:3] if isinstance(t.get("turn_index"), int)]
        return {
            "session_id": session_id,
            "pnm": pnm,
            "term": term,
            "score_0_7": int(max(0, min(7, score))),
            "rationale": rationale,
            "evidence_turn_ids": ev,
            "method_version": "term_scorer_fallback_v2"
        }


def score_term(session_id: str, pnm: str, term: str, turns: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Backward-compatible functional entry."""
    return TermScorer().score_term(session_id=session_id, pnm=pnm, term=term, turns=turns)
