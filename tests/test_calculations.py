import math

import pytest

from vantage.calculations import (
    decision_fingerprint,
    effective_assessments,
    prioritize,
    scores_for,
    weighted_score,
)
from vantage.models import Assessment, Override, Source


def sample(rating):
    return Assessment(
        rating=rating, basis="Sample data", origin="Sample", explanation="Synthetic test input."
    )


def test_weighted_score_and_unknown_range():
    result = weighted_score(
        [sample(r) for r in ["Yes", "Partial", "No", "Unverified"]], [4, 2, 2, 2]
    )
    assert result.score == 62.5
    assert result.assessed_weight_pct == 80
    assert (result.lower_bound, result.upper_bound) == (50, 70)
    assert result.unverified_features == 1


def test_all_unknown_is_na_not_zero():
    s = weighted_score([sample("Unverified")] * 5, [5] * 5)
    assert s.score is None and s.assessed_weight_pct == 0
    assert (s.lower_bound, s.upper_bound) == (0, 100)


def test_source_backed_coverage_excludes_inference_and_manual():
    source = Source(
        url="https://docs.example.com/feature", title="Test source", supported_text="Test claim."
    )
    facts = Assessment(
        rating="Yes", basis="Source-backed", sources=[source], explanation="Test fact."
    )
    inference = Assessment(
        rating="Yes", basis="AI inference", sources=[source], explanation="Test inference."
    )
    manual = Assessment(
        rating="Yes", basis="User override", origin="Manual", explanation="User judgment."
    )
    s = weighted_score([facts, inference, manual, sample("Unverified")], [1, 1, 1, 1])
    assert s.score == 100
    assert s.assessed_weight_pct == 75 and s.source_backed_weight_pct == 25


def test_zero_weights_does_not_divide_by_zero():
    assert weighted_score([sample("Yes")] * 5, [0] * 5).score is None


@pytest.mark.parametrize(
    "weights", [[-1] * 5, [math.nan] * 5, [math.inf] * 5, [True] * 5, [11] * 5, [1]]
)
def test_invalid_weights_rejected(weights):
    with pytest.raises(ValueError):
        weighted_score([sample("Yes")] * 5, weights)


def test_manual_override_is_immutable_and_changes_scores(demo):
    before = demo.model_dump_json()
    effective = effective_assessments(
        demo, {"p0_f2": Override(rating="Yes", note="Reviewed a working integration.")}
    )
    assert effective["p0_f2"].origin == "Manual"
    assert effective["p0_f2"].sources == []
    assert demo.model_dump_json() == before
    assert scores_for(demo, effective, [5] * 5)[demo.request.product].score == 75


def test_override_from_wrong_analysis_rejected(demo):
    with pytest.raises(ValueError):
        effective_assessments(demo, {"p9_f9": Override(rating="Yes")})


def test_ranked_roadmap_and_unknown_are_distinct(demo):
    effective = effective_assessments(demo, {})
    ranked = prioritize(demo, effective, [5] * 5, [3] * 5, [3] * 5)
    assert ranked[0].feature == "API & integrations" and ranked[0].priority == 5
    assert ranked[1].feature == "Workflow automation" and ranked[1].priority == 2.5
    assert ranked[-1].feature == "Access controls" and ranked[-1].priority is None
    assert ranked[-1].gap is None


def test_impact_effort_changes_priority(demo):
    ranked = prioritize(
        demo, effective_assessments(demo, {}), [5] * 5, [5, 3, 3, 3, 3], [1, 3, 3, 3, 3]
    )
    assert ranked[0].feature == "Workflow automation"
    assert ranked[0].priority == 12.5


@pytest.mark.parametrize(
    "impacts,efforts", [([0] * 5, [3] * 5), ([3] * 5, [0] * 5), ([6] * 5, [1] * 5)]
)
def test_invalid_roadmap_assumptions(demo, impacts, efforts):
    with pytest.raises(ValueError):
        prioritize(demo, effective_assessments(demo, {}), [5] * 5, impacts, efforts)


def test_snapshot_hash_changes_on_edits_weights_and_roadmap(demo):
    e = effective_assessments(demo, {})
    r = prioritize(demo, e, [5] * 5, [3] * 5, [3] * 5)
    baseline = decision_fingerprint(demo, e, [5] * 5, r)
    assert baseline != decision_fingerprint(demo, e, [6] * 5, r)
    edited = effective_assessments(demo, {"p0_f2": Override(rating="Yes")})
    assert baseline != decision_fingerprint(demo, edited, [5] * 5, r)
    changed = prioritize(demo, e, [5] * 5, [4] * 5, [3] * 5)
    assert baseline != decision_fingerprint(demo, e, [5] * 5, changed)
