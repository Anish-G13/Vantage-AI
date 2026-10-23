"""One source of truth for UI scores, charts, roadmap, and exported figures."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass

from .models import Analysis, Assessment, Override, cell_id

VALUES = {"Yes": 1.0, "Partial": 0.5, "No": 0.0, "Unverified": None}


def valid_numbers(values: list[float], length: int, minimum: float, maximum: float) -> None:
    if len(values) != length or any(
        isinstance(v, bool) or not math.isfinite(v) or not minimum <= v <= maximum for v in values
    ):
        raise ValueError("Invalid scoring assumptions.")


@dataclass(frozen=True)
class Score:
    score: float | None
    assessed_weight_pct: float
    source_backed_weight_pct: float
    lower_bound: float
    upper_bound: float
    unverified_features: int


def effective_assessments(
    analysis: Analysis, overrides: dict[str, Override]
) -> dict[str, Assessment]:
    if not set(overrides).issubset(analysis.assessments):
        raise ValueError("An override refers to another analysis.")
    result = {key: a.model_copy(deep=True) for key, a in analysis.assessments.items()}
    for key, edit in overrides.items():
        result[key] = Assessment(
            rating=edit.rating,
            basis="User override",
            origin="Manual",
            explanation=edit.note or "User changed this assessment; no explanation supplied.",
            sources=[],
        )
    return result


def weighted_score(assessments: list[Assessment], weights: list[float]) -> Score:
    valid_numbers(weights, len(assessments), 0, 10)
    total = sum(weights)
    if not total:
        return Score(None, 0.0, 0.0, 0.0, 100.0, sum(a.rating == "Unverified" for a in assessments))
    known = [(a, w) for a, w in zip(assessments, weights) if VALUES[a.rating] is not None]
    known_weight = sum(w for _, w in known)
    weighted_sum = sum(VALUES[a.rating] * w for a, w in known)
    source_weight = sum(
        w for a, w in known if a.origin == "AI" and a.sources and a.basis == "Source-backed"
    )
    return Score(
        score=round(100 * weighted_sum / known_weight, 1) if known_weight else None,
        assessed_weight_pct=round(100 * known_weight / total, 1),
        source_backed_weight_pct=round(100 * source_weight / total, 1),
        lower_bound=round(100 * weighted_sum / total, 1),
        upper_bound=round(100 * (weighted_sum + total - known_weight) / total, 1),
        unverified_features=sum(a.rating == "Unverified" for a in assessments),
    )


def scores_for(
    analysis: Analysis, effective: dict[str, Assessment], weights: list[float]
) -> dict[str, Score]:
    return {
        product: weighted_score([effective[cell_id(p, f)] for f in range(5)], weights)
        for p, product in enumerate(analysis.request.products)
    }


@dataclass(frozen=True)
class RoadmapItem:
    feature: str
    feature_index: int
    own_rating: str
    competitor_reference: str
    gap: float | None
    importance: float
    impact: float
    effort: float
    priority: float | None
    rationale: str
    next_action: str


def prioritize(
    analysis: Analysis,
    effective: dict[str, Assessment],
    weights: list[float],
    impacts: list[float],
    efforts: list[float],
) -> list[RoadmapItem]:
    valid_numbers(weights, 5, 0, 10)
    valid_numbers(impacts, 5, 1, 5)
    valid_numbers(efforts, 5, 1, 5)
    items = []
    for f, feature in enumerate(analysis.discovery.features):
        own = effective[cell_id(0, f)]
        alternatives = [
            (analysis.request.products[p], effective[cell_id(p, f)].rating)
            for p in range(1, len(analysis.request.products))
            if VALUES[effective[cell_id(p, f)].rating] is not None
        ]
        reference = max((VALUES[r] for _, r in alternatives), default=None)
        own_value = VALUES[own.rating]
        gap = None if own_value is None or reference is None else max(0.0, reference - own_value)
        peers = (
            ", ".join(f"{p}: {r}" for p, r in alternatives) or "No assessed competitor reference"
        )
        if gap is None:
            rationale = "Evidence is incomplete; a competitive gap cannot yet be estimated."
            action = "Research the missing assessments and validate customer need before allocating engineering effort."
        elif gap > 0:
            rationale = f"Your rating is {own.rating}; the strongest assessed competitor is {'Yes' if reference == 1 else 'Partial' if reference == 0.5 else 'No'}."
            action = "Validate customer demand, define MVP acceptance criteria, and estimate delivery effort with engineering."
        else:
            rationale = "No positive gap against assessed competitors; this is not proof of market leadership."
            action = "Maintain and monitor; test differentiation or customer value before expanding scope."
        items.append(
            RoadmapItem(
                feature.name,
                f,
                own.rating,
                peers,
                gap,
                weights[f],
                impacts[f],
                efforts[f],
                round(gap * weights[f] * impacts[f] / efforts[f], 2) if gap is not None else None,
                rationale,
                action,
            )
        )
    return sorted(items, key=lambda x: (x.priority is None, -(x.priority or 0), x.feature_index))


def decision_fingerprint(
    analysis: Analysis,
    effective: dict[str, Assessment],
    weights: list[float],
    roadmap: list[RoadmapItem],
) -> str:
    payload = {
        "request": analysis.request.model_dump(),
        "research_date": analysis.researched_at,
        "assessments": {k: a.model_dump() for k, a in effective.items()},
        "weights": weights,
        "roadmap": [asdict(i) for i in roadmap],
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
