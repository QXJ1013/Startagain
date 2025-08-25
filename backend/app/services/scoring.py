# app/services/scoring.py
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, List, Tuple

"""
Dimension-level scoring from term-level scores.

Supports:
- input_scale="0_7" (default) or "0_1"
- missing handling: drop | impute_min | impute_mean
- returns float score_0_7 (keep precision), plus coverage & details
"""

@dataclass
class DimensionScore:
    dimension: str
    score_0_7: float
    n_terms: int
    n_present: int
    coverage_ratio: float
    method: str
    details: Dict[str, Any]


class DimensionScorer:
    def __init__(self) -> None:
        pass

    def _normalize_values(
        self, values: List[Optional[float]], input_scale: str
    ) -> List[Optional[float]]:
        if input_scale == "0_1":
            # clamp to [0,1]
            return [None if v is None else max(0.0, min(1.0, float(v))) for v in values]
        # default 0..7
        return [None if v is None else max(0.0, min(7.0, float(v))) for v in values]

    def _to_0_7(self, x: float, input_scale: str) -> float:
        if input_scale == "0_1":
            return max(0.0, min(7.0, float(x) * 7.0))
        return max(0.0, min(7.0, float(x)))

    def _handle_missing(self, values: List[Optional[float]], strategy: str, input_scale: str) -> List[float]:
        """
        Return a fully filled list (no None).
        - For 0..7 scale, min=0.0; for 0..1 scale, min=0.0 too (then *7 later)
        """
        present = [v for v in values if v is not None]
        if strategy == "drop":
            return [v for v in present]  # may be empty
        if strategy == "impute_mean":
            if not present:
                return [0.0 for _ in values]
            mean_v = sum(present) / len(present)
            return [mean_v if (v is None) else v for v in values]
        # default conservative: impute_min
        return [0.0 if (v is None) else v for v in values]

    def score_dimension(
        self,
        term_scores: Dict[str, Dict[str, Any]],
        *,
        dimension_name: Optional[str] = None,
        input_scale: str = "0_7",
        missing_strategy: str = "impute_min",
    ) -> DimensionScore:
        """
        term_scores example:
            {
              "AAC": {"score": 4, "rationale": "..."},
              "Breathing": {"score": 2, ...},
              ...
            }
        Accepts key 'score' in input_scale (0..7 default). Also accepts 'score_raw' for backward compatibility.
        """
        vals_raw: List[Optional[float]] = []
        for _, rec in term_scores.items():
            v = rec.get("score")
            if v is None:
                v = rec.get("score_raw")
                if v is not None and input_scale == "0_7":
                    # old 0..1 value -> convert later; keep as-is here
                    pass
            vals_raw.append(v if v is None else float(v))

        n_terms = len(vals_raw)
        n_present = sum(1 for v in vals_raw if v is not None)

        normed = self._normalize_values(vals_raw, input_scale=input_scale)
        filled = self._handle_missing(normed, strategy=missing_strategy, input_scale=input_scale)
        if not filled:
            avg_internal = 0.0
        else:
            avg_internal = sum(filled) / len(filled)

        # map to 0..7
        score_0_7 = self._to_0_7(avg_internal, input_scale=input_scale)
        coverage = (n_present / n_terms) if n_terms > 0 else 0.0

        return DimensionScore(
            dimension=dimension_name or "Unknown",
            score_0_7=round(score_0_7, 2),
            n_terms=n_terms,
            n_present=n_present,
            coverage_ratio=round(coverage, 3),
            method=f"mean+{missing_strategy}+input:{input_scale}->0_7",
            details={
                "values_raw": vals_raw,
                "values_normed": normed,
                "values_filled": filled,
                "avg_internal": avg_internal
            }
        )

    @staticmethod
    def to_dict(score: 'DimensionScore') -> Dict[str, Any]:
        return asdict(score)
