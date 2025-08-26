# app/services/term_scorer.py
from __future__ import annotations
"""
Enhanced TermScorer with option-aware scoring:
- Integrates predefined option scoring for better consistency
- Score a single (pnm, term) on 0..7 from recent turns
- Returns real turn_index in evidence_turn_ids (not local 1..N)
- Strict JSON validation + clamp + robust fallback

Public API:
    score_term(session_id, pnm, term, turns, question_options) -> dict
Returned example:
{
  "session_id": "...",
  "pnm": "Esteem",
  "term": "Communication",
  "score_0_7": 4,
  "rationale": "User reports daily difficulty using AAC at work.",
  "evidence_turn_ids": [12, 13, 15],  # real turn_index
  "method_version": "term_scorer_wx_v3_option_aware"
}
"""
import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from app.config import get_settings
from app.vendors.ibm_cloud import LLMClient
from app.services.option_scorer import OptionScorer, score_from_option
try:
    from app.services.enhanced_option_scorer import EnhancedOptionScorer
    USE_ENHANCED = True
except ImportError:
    USE_ENHANCED = False


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
        # Try to find a complete JSON object with balanced braces
        # First, try to extract just the first valid JSON object
        text_to_scan = text[:max_chars]
        
        # Remove any markdown code blocks if present
        text_to_scan = re.sub(r'```json?\s*', '', text_to_scan)
        text_to_scan = re.sub(r'```\s*', '', text_to_scan)
        
        # Try to find JSON object with balanced braces
        brace_count = 0
        start_idx = -1
        end_idx = -1
        
        for i, char in enumerate(text_to_scan):
            if char == '{':
                if brace_count == 0:
                    start_idx = i
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0 and start_idx != -1:
                    end_idx = i + 1
                    break
        
        if start_idx != -1 and end_idx != -1:
            return text_to_scan[start_idx:end_idx]
        
        # Fallback to regex if balanced brace method fails
        m = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text_to_scan)
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
        # Use enhanced scorer if available
        if USE_ENHANCED and getattr(self.s, 'USE_ENHANCED_SCORING', True):
            self.option_scorer = EnhancedOptionScorer()
            self.use_enhanced = True
        else:
            self.option_scorer = OptionScorer()
            self.use_enhanced = False
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
        last_n: int = 12,
        question_options: Optional[List[Dict[str, str]]] = None,
        selected_option: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        recent = self._slice_turns(turns, last_n=last_n)
        
        # PRIORITY 1: AI scoring with full context (options and dialogue)
        try:
            if self.llm and self.llm.healthy():
                return self._score_with_llm(
                    session_id, pnm, term, recent, 
                    question_options=question_options,
                    selected_option=selected_option
                )
        except Exception as e:
            import logging
            logging.warning(f"AI scoring failed: {str(e)}, falling back to option scoring")
        
        # FALLBACK 1: Option-based scoring if AI unavailable
        if selected_option and question_options:
            option_result = self._try_option_scoring(
                session_id, pnm, term, recent, 
                selected_option, question_options
            )
            if option_result and option_result.get('option_confidence', 0) > 0.4:
                return option_result
        
        # FALLBACK 2: Rule-based scoring as last resort
        return self._score_with_rules(session_id, pnm, term, recent)

    # ---------- internals ----------
    
    def _try_option_scoring(
        self,
        session_id: str,
        pnm: str,
        term: str,
        recent: List[Dict[str, Any]],
        selected_option: Dict[str, str],
        question_options: List[Dict[str, str]]
    ) -> Optional[Dict[str, Any]]:
        """
        Try to score based on selected predefined option.
        Only returns score if confidence is high enough.
        """
        option_value = selected_option.get('value', '')
        option_label = selected_option.get('label', '')
        
        if not option_value and not option_label:
            return None
        
        # Get option-based score with enhanced context if available
        if self.use_enhanced and hasattr(self.option_scorer, 'score_with_context'):
            # Extract question text from recent turns
            question_text = None
            for turn in reversed(recent):
                if turn.get("role") == "assistant":
                    question_text = turn.get("content", "")
                    break
            
            option_score = self.option_scorer.score_with_context(
                option_value=option_value,
                option_label=option_label,
                all_options=question_options,
                question_text=question_text,
                user_response=recent[-1].get("content") if recent else None
            )
        else:
            option_score = self.option_scorer.score_option(
                option_value=option_value,
                option_label=option_label,
                all_options=question_options
            )
        
        # Only use option scoring if confidence is high enough
        if option_score.confidence < 0.6:
            return None
        
        # Extract evidence from recent turns
        evidence_ids = []
        for turn in recent[-3:]:  # Last 3 turns most relevant
            if turn.get("turn_index") is not None:
                evidence_ids.append(turn["turn_index"])
        
        return {
            "session_id": session_id,
            "pnm": pnm,
            "term": term,
            "score_0_7": int(round(option_score.score_0_7)),
            "rationale": f"Selected '{option_label}'. {option_score.rationale}",
            "evidence_turn_ids": evidence_ids,
            "method_version": "term_scorer_option_v1",
            "option_confidence": option_score.confidence
        }

    @staticmethod
    def _slice_turns(turns: List[Dict[str, Any]], last_n: int) -> List[Dict[str, Any]]:
        if not turns:
            return []
        return turns[-last_n:]

    def _build_prompt(
        self, 
        pnm: str, 
        term: str, 
        recent: List[Dict[str, Any]],
        question_options: Optional[List[Dict[str, str]]] = None,
        selected_option: Optional[Dict[str, str]] = None
    ) -> str:
        # We enumerate but also include real 'turn_index' for the model to reference directly.
        records = []
        for t in recent:
            records.append({
                "turn_index": t.get("turn_index"),           # real id from storage
                "role": t.get("role") or t.get("speaker") or "user",
                "text": (t.get("text") or t.get("content") or "").strip()
            })

        # Build options context if available
        options_context = ""
        selected_context = ""
        
        if question_options:
            # Analyze option distribution for AI understanding
            if hasattr(self.option_scorer, 'analyze_option_distribution'):
                option_analysis = self.option_scorer.analyze_option_distribution(question_options)
            else:
                # Fallback for EnhancedOptionScorer or other scorers
                option_analysis = {
                    'scale_type': 'proficiency',
                    'suggested_scoring': [
                        {'value': opt.get('value', ''), 'label': opt.get('label', ''), 
                         'suggested_score': 7.0 * (1 - i/(len(question_options)-1)) if len(question_options) > 1 else 3.5}
                        for i, opt in enumerate(question_options)
                    ]
                }
            
            options_context = f"""
QUESTION OPTIONS PROVIDED (for scoring reference):
Scale type: {option_analysis.get('scale_type', 'unknown')}
Available options with suggested scores:
"""
            for i, opt_info in enumerate(option_analysis.get('suggested_scoring', [])):
                is_selected = (selected_option and 
                             (opt_info['value'] == selected_option.get('value') or 
                              opt_info['label'] == selected_option.get('label')))
                marker = " [USER SELECTED THIS]" if is_selected else ""
                options_context += f"- Option {i+1}: '{opt_info['label']}' (typical score: {opt_info['suggested_score']:.1f}){marker}\n"
            
            options_context += """
These options form a scale from highest to lowest capability.
"""
        
        if selected_option:
            selected_context = f"""
USER'S SELECTED OPTION:
- Value: {selected_option.get('value', 'N/A')}
- Label: {selected_option.get('label', 'N/A')}
This should be the primary basis for scoring, unless the dialogue strongly contradicts it.
"""

        prompt = f"""
You are an ALS/MND assistant scoring ONE term within ONE PNM dimension.

PNM dimension: {pnm}
Term: {term}

IMPORTANT: This is about the {term} aspect specifically within the {pnm} dimension.
Different dimensions focus on different aspects of the same capability.

RUBRIC:
{self.cfg.rubric}
{selected_context}
{options_context}
DIALOGUE CONTEXT (recent turns with real turn_index):
{json.dumps(records, ensure_ascii=False)}

SCORING GUIDELINES:
1. If user selected a predefined option, that is the PRIMARY evidence for scoring
2. Use the option scale as your reference (0=lowest capability, 7=highest)
3. Consider the specific PNM dimension context - same response may score differently across dimensions
4. Look for evidence in the dialogue that supports or contradicts the selected option

OUTPUT RULES:
- Return ONLY ONE SINGLE JSON object on ONE LINE
- Required keys: score_0_7 (integer 0-7), rationale (string, max 20 words), evidence_turn_ids (array of integers)
- evidence_turn_ids MUST be values from the provided 'turn_index' fields
- NO markdown, NO code blocks, NO extra text, NO multiple lines
- Score should align with the selected option unless dialogue strongly contradicts

RESPOND WITH EXACTLY THIS FORMAT (all on one line):
{{"score_0_7": 3, "rationale": "Selected moderate option, dialogue confirms occasional help needed", "evidence_turn_ids": [102, 106]}}
"""
        return prompt

    def _score_with_llm(
        self, 
        session_id: str, 
        pnm: str, 
        term: str, 
        recent: List[Dict[str, Any]],
        question_options: Optional[List[Dict[str, str]]] = None,
        selected_option: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        prompt = self._build_prompt(pnm, term, recent, question_options, selected_option)
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
            "method_version": "term_scorer_wx_v3_option_aware" if question_options else "term_scorer_wx_v2"
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
        # Combine all text from recent turns
        text = " ".join([(t.get("content") or t.get("text") or "") for t in recent]).lower()
        
        # Enhanced keyword sets for better differentiation
        severe_cues = {
            "cannot", "unable", "impossible", "completely dependent", "no longer",
            "totally", "fully dependent", "caregiver handles", "rely completely"
        }
        struggle_cues = {
            "difficult", "hard", "struggle", "problem", "stuck", "worse", 
            "fail", "confused", "frustrated", "challenging"
        }
        moderate_cues = {
            "manage", "okay", "cope", "sometimes", "occasionally", "some help",
            "getting by", "partial", "moderate", "fair"
        }
        good_cues = {
            "well", "good", "confident", "comfortable", "effective", "successful",
            "independently", "easily", "no problem", "fine"
        }
        expert_cues = {
            "expert", "teach", "mentor", "coach", "help others", "share experience",
            "excellent", "perfect", "mastered", "proficient"
        }
        
        # Start with base score and adjust based on evidence
        score = 3  # Default neutral
        rationale = "Rule-based assessment: "
        
        # Check for different levels of function (order matters - check from extreme to moderate)
        if any(cue in text for cue in severe_cues):
            score = 1
            rationale += "severe limitations detected"
        elif any(cue in text for cue in expert_cues):
            score = 6
            rationale += "expert level capability"
        elif any(cue in text for cue in good_cues):
            score = 5
            rationale += "good function reported"
        elif any(cue in text for cue in struggle_cues):
            score = 2
            rationale += "significant difficulties"
        elif any(cue in text for cue in moderate_cues):
            score = 3
            rationale += "moderate function"
        else:
            score = 3
            rationale += "neutral/unclear function"
        
        # Get evidence turn IDs
        ev = [t.get("turn_index") for t in recent[:3] if isinstance(t.get("turn_index"), int)]
        
        return {
            "session_id": session_id,
            "pnm": pnm,
            "term": term,
            "score_0_7": int(max(0, min(7, score))),
            "rationale": rationale[:240],  # Limit rationale length
            "evidence_turn_ids": ev,
            "method_version": "term_scorer_fallback_v3_enhanced"
        }


def score_term(
    session_id: str, 
    pnm: str, 
    term: str, 
    turns: List[Dict[str, Any]],
    question_options: Optional[List[Dict[str, str]]] = None,
    selected_option: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """Backward-compatible functional entry with enhanced option support."""
    return TermScorer().score_term(
        session_id=session_id,
        pnm=pnm,
        term=term,
        turns=turns,
        question_options=question_options,
        selected_option=selected_option
    )
