import pytest

from vantage.models import ResearchRequest
from vantage.session import (
    activate,
    apply_editor_delta,
    apply_roadmap_delta,
    cache_analysis,
    cached_analysis,
    is_current,
    record_event,
    reserve_session_request,
    reset_overrides,
)


def test_edits_survive_other_controls_and_reset(demo):
    state = {}
    activate(state, demo)
    apply_editor_delta(
        state, demo, 0, {"edited_rows": {2: {"Rating": "Yes", "Override note": "Checked docs"}}}
    )
    state["workspace_any_weight_0"] = 9
    assert state["overrides"]["p0_f2"].rating == "Yes"
    assert state["overrides"]["p0_f2"].note == "Checked docs"
    reset_overrides(state)
    assert state["overrides"] == {} and state["editor_revision"] == 1
    assert state["workspace_any_weight_0"] == 9


def test_note_only_and_return_to_baseline(demo):
    state = {}
    activate(state, demo)
    apply_editor_delta(state, demo, 0, {"edited_rows": {0: {"Override note": "Reviewed"}}})
    assert state["overrides"]["p0_f0"].rating == "Partial"
    apply_editor_delta(
        state, demo, 0, {"edited_rows": {0: {"Rating": "Partial", "Override note": ""}}}
    )
    assert not state["overrides"]


def test_editor_undo_clears_only_selected_product(demo):
    state = {}
    activate(state, demo)
    apply_editor_delta(state, demo, 0, {"edited_rows": {2: {"Rating": "Yes"}}})
    apply_editor_delta(state, demo, 1, {"edited_rows": {1: {"Rating": "No"}}})
    apply_editor_delta(state, demo, 0, {"edited_rows": {}})
    assert "p0_f2" not in state["overrides"]
    assert state["overrides"]["p1_f1"].rating == "No"


def test_roadmap_undo_restores_baseline():
    state = {}
    apply_roadmap_delta(state, {"edited_rows": {0: {"Impact": 5, "Effort": 1}}})
    assert state["roadmap_assumptions"][0] == {"impact": 5, "effort": 1}
    apply_roadmap_delta(state, {"edited_rows": {0: {"Impact": 5}}})
    assert state["roadmap_assumptions"][0]["effort"] == 3
    apply_roadmap_delta(state, {"edited_rows": {}})
    assert state["roadmap_assumptions"] == {}


def test_invalid_roadmap_edit_is_atomic():
    state = {"roadmap_assumptions": {0: {"impact": 5, "effort": 1}}}
    with pytest.raises(ValueError):
        apply_roadmap_delta(state, {"edited_rows": {0: {"Effort": 0}}})
    assert state["roadmap_assumptions"][0]["effort"] == 1


def test_new_analysis_resets_workspace_state(demo):
    state = {"workspace_old_slider": 8, "roadmap_assumptions": {1: {"impact": 5}}}
    activate(state, demo)
    assert "workspace_old_slider" not in state and state["roadmap_assumptions"] == {}


def test_changed_products_are_not_current(demo):
    assert is_current(demo, demo.request)
    changed = ResearchRequest(product="Different Product", competitors=demo.request.competitors)
    assert not is_current(demo, changed)


def test_cache_ttl_identity_and_copy(demo):
    state = {}
    cache_analysis(state, "key-a", demo, now=100)
    assert cached_analysis(state, "key-a", now=1899) is not None
    assert cached_analysis(state, "key-a", now=1900) is None
    assert cached_analysis(state, "key-b", now=110) is None
    assert cached_analysis(state, "key-a", now=110) is not demo


def test_request_cooldown_and_hourly_limit():
    state = {}
    reserve_session_request(state, now=100)
    with pytest.raises(ValueError, match="30 seconds"):
        reserve_session_request(state, now=129)
    for n in range(1, 10):
        reserve_session_request(state, now=100 + n * 31)
    with pytest.raises(ValueError, match="hourly"):
        reserve_session_request(state, now=500)
    reserve_session_request(state, now=4000)


def test_usage_is_opt_in_and_has_no_names():
    state = {}
    record_event(state, "edit")
    assert "usage_counts" not in state
    state["usage_opt_in"] = True
    record_event(state, "edit")
    assert state["usage_counts"] == {"edit": 1}
