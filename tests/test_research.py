import json
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest
from conftest import fake_response
from google.genai import errors, types

from vantage.calculations import effective_assessments, prioritize
from vantage.models import Insight
from vantage.research import (
    CallBudget,
    GeminiResearcher,
    ResearchError,
    clean_json,
    manual_analysis,
    validate_grounded_response,
)


def researcher_with(*responses):
    models = SimpleNamespace(generate_content=Mock(side_effect=list(responses)))
    client = SimpleNamespace(models=models)
    return GeminiResearcher("test-key-never-used", client=client), models.generate_content


def test_claim_linkage_not_global_source_attachment(grounded_fixture, request_data):
    text, metadata = grounded_fixture
    cells, html = validate_grounded_response(fake_response(text, metadata), request_data)
    assert cells["p0_f0"].rating == "Yes" and len(cells["p0_f0"].sources) == 1
    assert cells["p0_f0"].basis == "Source-backed"
    assert all(c.rating == "Unverified" for k, c in cells.items() if k != "p0_f0")
    assert "Test search attribution" in html


def test_real_sdk_response_contract(grounded_fixture, request_data):
    text, metadata = grounded_fixture
    response = types.GenerateContentResponse(
        candidates=[
            types.Candidate(
                content=types.Content(parts=[types.Part(text=text)]),
                grounding_metadata=types.GroundingMetadata.model_validate(metadata),
            )
        ]
    )
    cells, _ = validate_grounded_response(response, request_data)
    assert cells["p0_f0"].sources[0].url == "https://docs.example.com/features"


def test_missing_support_is_unverified(grounded_fixture, request_data):
    text, metadata = grounded_fixture
    metadata["grounding_supports"] = []
    cells, _ = validate_grounded_response(fake_response(text, metadata), request_data)
    assert all(c.rating == "Unverified" for c in cells.values())


def test_cross_claim_support_is_not_misassigned(grounded_fixture, request_data):
    text, metadata = grounded_fixture
    metadata["grounding_supports"][0]["segment"] = {
        "text": text,
        "start_index": 0,
        "end_index": len(text),
    }
    cells, _ = validate_grounded_response(fake_response(text, metadata), request_data)
    assert all(c.rating == "Unverified" for c in cells.values())


@pytest.mark.parametrize(
    "uri,index",
    [
        ("javascript:alert(1)", 0),
        ("https://127.0.0.1/", 0),
        ("https://docs.example.com/", 999),
        ("https://docs.example.com/", -1),
    ],
)
def test_bad_metadata_is_rejected(grounded_fixture, request_data, uri, index):
    text, metadata = grounded_fixture
    metadata["grounding_chunks"][0]["web"]["uri"] = uri
    metadata["grounding_supports"][0]["grounding_chunk_indices"] = [index]
    cells, _ = validate_grounded_response(fake_response(text, metadata), request_data)
    assert cells["p0_f0"].rating == "Unverified"


def test_model_authored_citation_field_is_rejected(grounded_fixture, request_data):
    text, metadata = grounded_fixture
    data = json.loads(text)
    data["assessments"]["p0_f0"]["sources"] = ["https://invented.example.com/"]
    with pytest.raises(ValueError):
        validate_grounded_response(fake_response(json.dumps(data), metadata), request_data)


def test_model_url_in_explanation_is_rejected(grounded_fixture, request_data):
    text, metadata = grounded_fixture
    data = json.loads(text)
    data["assessments"]["p0_f0"]["explanation"] = "See https://invented.example.com for evidence."
    with pytest.raises(ValueError):
        validate_grounded_response(fake_response(json.dumps(data), metadata), request_data)


def test_incomplete_grid_rejected(grounded_fixture, request_data):
    text, metadata = grounded_fixture
    data = json.loads(text)
    del data["assessments"]["p1_f4"]
    with pytest.raises(ValueError, match="grid"):
        validate_grounded_response(fake_response(json.dumps(data), metadata), request_data)


def test_grounding_failure_preserves_editable_workspace(discovery_response, request_data):
    error = RuntimeError("sensitive key must never be displayed")
    error.code = 400
    service, call = researcher_with(discovery_response, error)
    result = service.analyze(request_data)
    assert len(result.discovery.features) == 5 and len(result.assessments) == 10
    assert all(a.rating == "Unverified" for a in result.assessments.values())
    assert "sensitive" not in " ".join(result.notices)
    assert "tools" in call.call_args_list[1].kwargs["config"]


def test_bad_research_json_fails_closed(discovery_response, request_data):
    service, _ = researcher_with(discovery_response, fake_response('{"assessments":'))
    result = service.analyze(request_data)
    assert all(a.rating == "Unverified" for a in result.assessments.values())


def test_custom_features_skip_discovery_call(request_data, grounded_fixture):
    text, metadata = grounded_fixture
    request = request_data.model_copy(
        update={"custom_features": ["Alpha", "Bravo", "Charlie", "Delta", "Echo"]}
    )
    service, call = researcher_with(fake_response(text, metadata))
    assert service.analyze(request).discovery.features[0].name == "Alpha"
    assert call.call_count == 1


def test_manual_workspace_needs_no_key_or_ai(request_data):
    request = request_data.model_copy(
        update={"custom_features": ["Alpha", "Bravo", "Charlie", "Delta", "Echo"]}
    )
    result = manual_analysis(request)
    assert result.mode == "Manual workspace" and result.model == "No AI call"
    with pytest.raises(ValueError):
        manual_analysis(request_data)


@pytest.mark.parametrize(
    "text", ['{"x": 1, "x": 2}', "[]", "not JSON", "```json\n{}", "{} trailing"]
)
def test_malformed_json_is_not_guessed(text):
    with pytest.raises(ValueError):
        clean_json(text)


def test_valid_json_fence_supported():
    assert json.loads(clean_json('```json\n{"ok": true}\n```')) == {"ok": True}


@pytest.mark.parametrize(
    "code,error_code", [(429, "quota"), (403, "key"), (404, "model"), (418, "provider")]
)
def test_errors_are_safe_and_bounded(code, error_code):
    error = RuntimeError("credential=SECRET")
    error.code = code
    service, call = researcher_with(error)
    with pytest.raises(ResearchError) as info:
        service._generate("test", schema=Insight)
    assert info.value.code == error_code and "SECRET" not in str(info.value)
    assert call.call_count == 1


@pytest.mark.parametrize("reason", ["API key not valid", "API key expired"])
def test_http_400_credentials_are_identified_without_leaking_details(reason, caplog):
    error = errors.ClientError(
        400, {"error": {"message": reason + ": credential=SECRET", "status": "INVALID_ARGUMENT"}}
    )
    service, call = researcher_with(error)
    with pytest.raises(ResearchError) as info:
        service._generate("private comparison", grounded=True)
    assert info.value.code == "key" and call.call_count == 1
    assert "credential_error=True" in caplog.text
    assert "SECRET" not in str(info.value) + caplog.text
    assert "private comparison" not in caplog.text


def test_unknown_failure_logs_only_safe_operator_metadata(caplog):
    service, _ = researcher_with(RuntimeError("secret-key and private prompt"))
    with pytest.raises(ResearchError):
        service._generate("private comparison", schema=Insight)
    assert "exception=RuntimeError" in caplog.text
    assert "secret-key" not in caplog.text and "private" not in caplog.text


def test_transient_retry_is_bounded(monkeypatch, discovery_response):
    monkeypatch.setattr("vantage.research.time.sleep", lambda _: None)
    service, call = researcher_with(httpx.ReadTimeout("test"), discovery_response)
    assert service._generate("test", schema=Insight) is discovery_response
    assert call.call_count == 2
    service, call = researcher_with(httpx.ReadTimeout("one"), httpx.ReadTimeout("two"))
    with pytest.raises(ResearchError, match="timed out"):
        service._generate("test", schema=Insight)
    assert call.call_count == 2


def test_server_error_retries_once(monkeypatch, discovery_response):
    monkeypatch.setattr("vantage.research.time.sleep", lambda _: None)
    error = RuntimeError("temporary")
    error.code = 503
    service, call = researcher_with(error, discovery_response)
    service._generate("test", schema=Insight)
    assert call.call_count == 2


def test_budget_window_and_missing_key():
    budget = CallBudget(1)
    budget.take(now=1)
    with pytest.raises(ResearchError, match="budget"):
        budget.take(now=2)
    budget.take(now=3601)
    with pytest.raises(ResearchError):
        GeminiResearcher("")


def test_strategic_insight_contract(demo):
    response = fake_response(
        json.dumps(
            {
                "strengths": "Reporting is rated Yes in this sample.",
                "neutral_observations": "Coverage varies and these products are fictional.",
                "critical_gaps_risks": "Validate integration needs before engineering investment.",
            }
        )
    )
    service, call = researcher_with(response)
    effective = effective_assessments(demo, {})
    roadmap = prioritize(demo, effective, [5] * 5, [3] * 5, [3] * 5)
    result = service.insights(demo, effective, [5] * 5, roadmap)
    assert "fictional" in result.neutral_observations
    assert call.call_count == 1 and "response_schema" in call.call_args.kwargs["config"]


def test_strategic_insights_reject_invented_url(demo):
    response = fake_response(
        json.dumps(
            {
                "strengths": "Reporting is rated Yes in this sample.",
                "neutral_observations": "See https://fabricated.example.com/ for proof.",
                "critical_gaps_risks": "Validate integration needs before investment.",
            }
        )
    )
    service, _ = researcher_with(response)
    effective = effective_assessments(demo, {})
    with pytest.raises(ResearchError, match="schema"):
        service.insights(
            demo, effective, [5] * 5, prioritize(demo, effective, [5] * 5, [3] * 5, [3] * 5)
        )
