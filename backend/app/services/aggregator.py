# app/services/aggregator.py
from __future__ import annotations
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

"""
Aggregator:
- Aggregate term-level 0..7 scores to dimension-level 0..7 with coverage
- Map dimension score to stage (Processing diagnosis ... Reflect & share)
- Thresholds configurable; default experience thresholds

Backward-compatible helpers:
- aggregate_dimensions(term_scores_by_dim) -> Dict[pnm, float]
- map_stage(dim_scores) -> Dict[pnm, stage]
"""

from app.config import get_settings
# from .scoring import DimensionScorer, DimensionScore  # Removed - scoring.py deleted


@dataclass
class DimensionResult:
    pnm: str
    score_0_7: float
    coverage_ratio: float
    stage: str
    method_version: str = "agg_v2"
    details: Dict[str, Any] = None


# default thresholds (can be overridden by config)
_DEFAULT_THRESHOLDS = [1, 2, 3, 4, 5, 6]
_STAGES = [
    "Processing diagnosis",
    "Learning about ALS/MND",
    "Researching solutions",
    "Engage with technology",
    "Lifestyle/personal alignment",
    "Refine/evolve/extend",
    "Reflect & share"
]


def _thresholds() -> List[float]:
    s = get_settings()
    # allow override via config (comma-separated "1,2,3,4,5,6")
    raw = getattr(s, "STAGE_THRESHOLDS", "")
    if raw:
        try:
            vals = [float(x.strip()) for x in raw.split(",")]
            if len(vals) == 6:
                return vals
        except Exception:
            pass
    return list(_DEFAULT_THRESHOLDS)


def _map_one_stage(score_0_7: float) -> str:
    s = max(0.0, min(7.0, float(score_0_7)))
    t = _thresholds()
    # t = [1,2,3,4,5,6]
    if s <= t[0]: return _STAGES[0]
    if s <= t[1]: return _STAGES[1]
    if s <= t[2]: return _STAGES[2]
    if s <= t[3]: return _STAGES[3]
    if s <= t[4]: return _STAGES[4]
    if s <= t[5]: return _STAGES[5]
    return _STAGES[6]


def aggregate_dimension_for_pnm(
    pnm: str,
    term_scores_for_pnm: Dict[str, Dict[str, Any]],
    *,
    input_scale: str = "0_7",
    missing_strategy: str = "impute_min"
) -> DimensionResult:
    """
    Aggregate one PNM dimension from its term dict:
      term_scores_for_pnm = {"AAC":{"score":4}, "Breathing":{"score":2}, ...}
    Returns DimensionResult with score, coverage and stage.
    """
    ds = DimensionScorer().score_dimension(
        term_scores=term_scores_for_pnm,
        dimension_name=pnm,
        input_scale=input_scale,
        missing_strategy=missing_strategy
    )
    stage = _map_one_stage(ds.score_0_7)
    return DimensionResult(
        pnm=pnm,
        score_0_7=ds.score_0_7,
        coverage_ratio=ds.coverage_ratio,
        stage=stage,
        details={"scoring": asdict(ds)}
    )


# -------- Backward-compatible helpers --------

def aggregate_dimensions(term_scores: Dict[str, Dict[str, float]]) -> Dict[str, float]:
    """
    Old helper kept for compatibility.
    term_scores:
      {
        "Physiological": {"Breathing": 2, "Mobility": 3},
        "Esteem": {"AAC": 6, "Independence": 5}
      }
    return: {"Physiological": 2.5, "Esteem": 5.5}
    """
    out: Dict[str, float] = {}
    for pnm, terms in term_scores.items():
        values = [v for v in terms.values() if v is not None]
        out[pnm] = round(sum(values) / len(values), 2) if values else 0.0
    return out

def aggregate_pnm_scores_from_session(pnm_scores) -> Dict[str, float]:
    """
    New helper to aggregate PNMScore objects from session.
    Takes list of PNMScore objects and aggregates by PNM level.
    """
    if not pnm_scores:
        return {}
    
    pnm_totals = {}
    pnm_counts = {}
    
    # Group scores by PNM level
    for score in pnm_scores:
        pnm = score.pnm_level
        total = score.total_score  # Already calculated total
        
        if pnm not in pnm_totals:
            pnm_totals[pnm] = 0
            pnm_counts[pnm] = 0
        
        pnm_totals[pnm] += total
        pnm_counts[pnm] += 1
    
    # Calculate averages and convert to 0-7 scale
    aggregated = {}
    for pnm in pnm_totals:
        avg_score = pnm_totals[pnm] / pnm_counts[pnm]  # Average total score (0-16)
        normalized_score = (avg_score / 16.0) * 7.0  # Convert to 0-7 scale
        aggregated[pnm] = round(normalized_score, 2)
    
    return aggregated


def map_stage(dim_scores: Dict[str, float]) -> Dict[str, str]:
    """
    Backward-compatible: map each dimension score (0..7) to stage by current thresholds.
    """
    out: Dict[str, str] = {}
    for pnm, score in dim_scores.items():
        out[pnm] = _map_one_stage(score)
    return out


class Aggregator:
    """
    Main aggregator class for backward compatibility.
    Provides the interface expected by existing code.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
    
    def aggregate_dimensions(self, term_scores: Dict[str, Dict[str, float]]) -> Dict[str, float]:
        """
        Aggregate term scores to dimension scores.
        """
        return aggregate_dimensions(term_scores)
    
    def map_stage(self, dim_scores: Dict[str, float]) -> Dict[str, str]:
        """
        Map dimension scores to stages.
        """
        return map_stage(dim_scores)
    
    def aggregate_pnm_scores_from_session(self, pnm_scores) -> Dict[str, float]:
        """
        Aggregate PNM scores from session.
        """
        return aggregate_pnm_scores_from_session(pnm_scores)


@dataclass
class AggregationConfig:
    """
    Configuration for aggregation processes.
    Kept for backward compatibility.
    """
    input_scale: str = "0_7"
    missing_strategy: str = "impute_min"
    stage_thresholds: List[float] = None
    
    def __post_init__(self):
        if self.stage_thresholds is None:
            self.stage_thresholds = _DEFAULT_THRESHOLDS.copy()
