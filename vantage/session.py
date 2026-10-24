"""Pure session transitions. Streamlit widget callbacks call these functions."""

from __future__ import annotations

import time
from collections import Counter
from collections.abc import MutableMapping
from uuid import uuid4

from .models import Analysis, Override, ResearchRequest, RoadmapAssumption, cell_id

CACHE_TTL = 1800


def activate(state: MutableMapping, analysis: Analysis) -> None:
    for key in list(state):
        if str(key).startswith("workspace_"):
            del state[key]
    state["active_analysis"] = analysis
    state["workspace_id"] = uuid4().hex[:12]
    state["overrides"] = {}
    state["roadmap_assumptions"] = {}
    state["editor_revision"] = 0
    state["insights"] = None
    state["insights_fingerprint"] = None


def is_current(analysis: Analysis, request: ResearchRequest) -> bool:
    return analysis.request.fingerprint() == request.fingerprint()


def apply_editor_delta(
    state: MutableMapping, analysis: Analysis, product_index: int, delta: dict
) -> None:
    # The editor emits its complete cumulative delta. Rebuild this product's
    # edits so undo/removing a delta cannot leave a stale manual correction.
    prefix = f"p{product_index}_"
    overrides = {k: v for k, v in state.get("overrides", {}).items() if not k.startswith(prefix)}
    for row_index, changes in delta.get("edited_rows", {}).items():
        row = int(row_index)
        if not 0 <= row < 5:
            raise ValueError("Invalid feature row.")
        key = cell_id(product_index, row)
        original = analysis.assessments[key]
        edit = Override(
            rating=changes.get("Rating", original.rating),
            note=changes.get("Override note", "") or "",
        )
        if edit.rating == original.rating and not edit.note:
            overrides.pop(key, None)
        else:
            overrides[key] = edit
    state["overrides"] = overrides
    record_event(state, "assessment_edit")


def apply_roadmap_delta(state: MutableMapping, delta: dict) -> None:
    assumptions = {}
    for row, changes in delta.get("edited_rows", {}).items():
        f = int(row)
        if not 0 <= f < 5:
            raise ValueError("Invalid feature row.")
        item = RoadmapAssumption(impact=changes.get("Impact", 3), effort=changes.get("Effort", 3))
        assumptions[f] = item.model_dump()
    state["roadmap_assumptions"] = assumptions
    record_event(state, "roadmap_edit")


def reset_overrides(state: MutableMapping) -> None:
    state["overrides"] = {}
    state["editor_revision"] = state.get("editor_revision", 0) + 1
    record_event(state, "assessment_reset")


def cached_analysis(state: MutableMapping, key: str, now: float | None = None) -> Analysis | None:
    now = time.time() if now is None else now
    entry = state.get("research_cache", {}).get(key)
    if entry and 0 <= now - entry[0] < CACHE_TTL:
        return entry[1].model_copy(deep=True)
    return None


def cache_analysis(
    state: MutableMapping, key: str, analysis: Analysis, now: float | None = None
) -> None:
    now = time.time() if now is None else now
    entries = dict(state.get("research_cache", {}))
    entries = {k: v for k, v in entries.items() if 0 <= now - v[0] < CACHE_TTL}
    entries[key] = (now, analysis.model_copy(deep=True))
    state["research_cache"] = dict(list(entries.items())[-5:])


def reserve_session_request(state: MutableMapping, now: float | None = None) -> None:
    now = time.time() if now is None else now
    recent = [v for v in state.get("paid_action_times", []) if now - v < 3600]
    if recent and now - recent[-1] < 30:
        raise ValueError(
            "Please wait 30 seconds between AI requests. Editing and exports remain available."
        )
    if len(recent) >= 10:
        raise ValueError(
            "This session has reached its hourly AI request limit. Use edits or a manual workspace."
        )
    state["paid_action_times"] = [*recent, now]


def record_event(state: MutableMapping, event: str) -> None:
    if state.get("usage_opt_in", False):
        counts = Counter(state.get("usage_counts", {}))
        counts[event] += 1
        state["usage_counts"] = dict(counts)
