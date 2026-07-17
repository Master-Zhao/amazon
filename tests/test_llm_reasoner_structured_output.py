"""Strict JSON, Schema, revision, and Workflow tests using Fake Transport only."""

from __future__ import annotations

import json

import pytest

from conftest import load_example
from amazon_ads_agent.reasoners.base import ReasonerInput
from amazon_ads_agent.reasoners.config import LLMReasonerConfig
from amazon_ads_agent.reasoners.errors import ReasonerError
from amazon_ads_agent.reasoners.llm import LLMReasoner
from amazon_ads_agent.reasoners.transport import FakeTransport, LLMTransportResponse
from amazon_ads_agent.workflow import run_workflow

FAKE_KEY = "test-only-not-a-real-key"


def _config() -> LLMReasonerConfig:
    return LLMReasonerConfig("llm", "test-model", FAKE_KEY, "https://model.invalid/v1", 30, 0)


def _input(previous_failure: dict | None = None) -> ReasonerInput:
    return ReasonerInput.create(
        task_id="task-1", run_id="run-1", attempt_id="attempt-0001", data_snapshot_id="snapshot-1",
        plan_version=1, object_type="keyword", object_id="kw-1", optimization_goal="target_acos",
        requested_risk_profile="balanced",
        entity_metrics=[{"entity_type": "keyword", "entity_id": "kw-1", "keyword": "synthetic mouse", "current_bid": "1.20", "object_version": "etag-1", "impressions": 1000, "clicks": 50, "orders": 5, "spend": "40.00", "sales": "100.00", "currency": "USD"}],
        calculated_metrics={"acos": "0.400000", "ctr": "0.050000", "cpc": "0.800000", "cvr": "0.100000", "roas": "2.500000"},
        candidate_values=("1.02", "1.08", "1.14"),
        constraints={"rule_set_version": "poc-rules-v0.1", "target_acos": "0.250000", "human_approval_required": True},
        previous_failure=previous_failure,
    )


def _document(
    *, selected: object = "1.08", evidence: list[object] | None = None, confidence: object = "0.840000"
) -> dict:
    return {
        "schema_version": "1.0",
        "decision": "select",
        "selected_value": selected,
        "reason": "ACoS is above target, so a moderate bid decrease is selected.",
        "evidence_paths": evidence or ["calculated_metrics.acos", "task_context.target_acos"],
        "risk_summary": "The lower bid may reduce traffic and requires human approval.",
        "confidence": confidence,
    }


def _response(document: dict | None = None, *, body: str | None = None, request_id: str = "req-1") -> LLMTransportResponse:
    text = json.dumps(document or _document(), ensure_ascii=False) if body is None else body
    return LLMTransportResponse(request_id, 200, text, {})


def _error(body: str) -> ReasonerError:
    reasoner = LLMReasoner(_config(), FakeTransport([_response(body=body)]))
    with pytest.raises(ReasonerError) as caught:
        reasoner.reason(_input())
    return caught.value


def test_valid_json_converts_to_reasoner_result() -> None:
    result = LLMReasoner(_config(), FakeTransport([_response()])).reason(_input())
    assert result.selected_value == "1.08"
    assert result.model_confidence == "0.840000"
    assert result.provider == "llm" and result.model == "test-model" and result.request_id == "req-1"


@pytest.mark.parametrize(
    ("body", "code"),
    [
        ("", "ERR_LLM_RESPONSE_EMPTY"),
        ("plain text", "ERR_LLM_RESPONSE_INVALID"),
        ("```json\n{}\n```", "ERR_LLM_RESPONSE_INVALID"),
        ("Here is the answer:\n{}", "ERR_LLM_RESPONSE_INVALID"),
        ("{}\nThis is the answer.", "ERR_LLM_RESPONSE_INVALID"),
        ("{}{}", "ERR_LLM_RESPONSE_INVALID"),
        ('{"a":1,"a":2}', "ERR_LLM_RESPONSE_INVALID"),
        ('{"confidence":NaN}', "ERR_LLM_RESPONSE_INVALID"),
        (json.dumps([_document()]), "ERR_REASONER_OUTPUT_SCHEMA_FAILED"),
        (json.dumps({}), "ERR_REASONER_OUTPUT_SCHEMA_FAILED"),
    ],
)
def test_strict_response_rejections(body: str, code: str) -> None:
    assert _error(body).error_code == code


@pytest.mark.parametrize(
    ("mutation", "value"),
    [
        ("extra", True),
        ("selected_value", 1.08),
        ("confidence", 0.84),
        ("confidence", "1.2"),
        ("decision", "execute"),
    ],
)
def test_schema_rejects_untyped_or_extra_fields(mutation: str, value: object) -> None:
    document = _document()
    document[mutation] = value
    assert _error(json.dumps(document)).error_code == "ERR_REASONER_OUTPUT_SCHEMA_FAILED"


def test_schema_error_message_does_not_echo_response() -> None:
    document = _document()
    document["execute_now"] = "private-response-marker"
    error = _error(json.dumps(document))
    assert "private-response-marker" not in str(error)


def test_schema_failure_does_not_enter_runtime_validator() -> None:
    result = run_workflow(
        load_example("high-acos-keyword.json"), reasoner_config=_config(),
        transport=FakeTransport([_response(body="```json\n{}\n```")]),
    )
    events = {event["event_type"] for event in result.audit_events}
    assert "runtime_validation_failed" not in events and "runtime_validation_passed" not in events
    assert "preflight_passed" not in events


def test_valid_schema_output_enters_runtime_validator() -> None:
    result = run_workflow(load_example("high-acos-keyword.json"), reasoner_config=_config(), transport=FakeTransport([_response()]))
    events = {event["event_type"] for event in result.audit_events}
    assert "reasoner_schema_validation_passed" in events
    assert "runtime_validation_passed" in events


def test_outside_candidate_is_rejected_by_runtime_then_revised() -> None:
    transport = FakeTransport([_response(_document(selected="0.80")), _response()])
    result = run_workflow(load_example("high-acos-keyword.json"), reasoner_config=_config(), transport=transport)
    assert result.failure_analyses[0]["error_code"] == "ERR_CANDIDATE_OUT_OF_RANGE"
    assert result.output["current_status"] == "waiting_for_approval" and result.output["plan_version"] == 2


def test_invalid_evidence_is_rejected_by_runtime_then_revised() -> None:
    invalid = _document(evidence=["calculated_metrics.not_real"])
    transport = FakeTransport([_response(invalid), _response()])
    result = run_workflow(load_example("high-acos-keyword.json"), reasoner_config=_config(), transport=transport)
    assert result.failure_analyses[0]["error_code"] == "ERR_EVIDENCE_REFERENCE_INVALID"
    assert result.output["current_status"] == "waiting_for_approval"


def test_valid_result_waits_for_approval_without_more_calls() -> None:
    transport = FakeTransport([_response(), _response()])
    result = run_workflow(load_example("high-acos-keyword.json"), reasoner_config=_config(), transport=transport)
    assert result.output["current_status"] == "waiting_for_approval"
    assert result.output["human_approval_required"] is True
    assert result.output["execution_preflight"]["production_write_called"] is False
    assert transport.call_count == 1


def test_second_request_contains_safe_previous_failure() -> None:
    transport = FakeTransport([_response(_document(selected="0.80")), _response()])
    result = run_workflow(load_example("high-acos-keyword.json"), reasoner_config=_config(), transport=transport)
    assert result.output["current_status"] == "waiting_for_approval"
    request = transport.last_request
    assert request is not None and len(request.payload["messages"]) == 3
    revision = request.payload["messages"][2]["content"]
    assert "ERR_CANDIDATE_OUT_OF_RANGE" in revision and "previous_failure_json" in revision
    assert "authorization_header" not in revision and FAKE_KEY not in revision


def test_revision_does_not_change_candidates_object_or_workflow_versions() -> None:
    transport = FakeTransport([_response(_document(selected="0.80")), _response()])
    result = run_workflow(load_example("high-acos-keyword.json"), reasoner_config=_config(), transport=transport)
    request = transport.last_request
    assert request is not None
    user = request.payload["messages"][1]["content"]
    assert '"candidate_values":["1.02","1.08","1.14"]' in user
    assert '"object_id":"kw-high-acos-001"' in user
    assert request.request_metadata["plan_version"] == 2
    assert request.request_metadata["attempt_id"] == "attempt-0002"
    assert result.output["retry_count"] == 1


def test_same_business_error_twice_enters_manual_intervention() -> None:
    invalid = _response(_document(selected="0.80"))
    transport = FakeTransport([invalid, invalid])
    result = run_workflow(load_example("high-acos-keyword.json"), reasoner_config=_config(), transport=transport)
    assert result.output["current_status"] == "manual_intervention_required"
    assert result.manual_intervention_package is not None
    assert result.manual_intervention_package["same_error_consecutive_count"] == 2
    assert "preflight_passed" not in {event["event_type"] for event in result.audit_events}
    assert transport.call_count == 2


def test_audit_never_contains_prompt_response_or_key() -> None:
    result = run_workflow(load_example("high-acos-keyword.json"), reasoner_config=_config(), transport=FakeTransport([_response()]))
    text = json.dumps(result.audit_events, ensure_ascii=False)
    assert FAKE_KEY not in text
    assert "ACoS is above target" not in text
    assert "reasoner_input_json" not in text


def test_model_confidence_does_not_override_deterministic_plan_confidence() -> None:
    result = run_workflow(
        load_example("high-acos-keyword.json"), reasoner_config=_config(),
        transport=FakeTransport([_response(_document(confidence="0.120000"))]),
    )
    assert result.output["changes"][0]["confidence"] != "0.120000"
