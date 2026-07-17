"""Offline Transport and LLMReasoner boundary tests."""

from __future__ import annotations

import json
import socket

import pytest

from amazon_ads_agent.reasoners.base import ReasonerInput
from amazon_ads_agent.reasoners.config import LLMReasonerConfig
from amazon_ads_agent.reasoners.errors import ReasonerError, ReasonerTransportError
from amazon_ads_agent.reasoners.llm import LLMReasoner
from amazon_ads_agent.reasoners.transport import FakeTransport, LLMTransportResponse, NotConfiguredTransport

FAKE_KEY = "test-only-not-a-real-key"


def _config(*, retries: int = 0) -> LLMReasonerConfig:
    return LLMReasonerConfig("llm", "test-model", FAKE_KEY, "https://model.invalid/v1", 30, retries)


def _input() -> ReasonerInput:
    return ReasonerInput.create(
        task_id="task-1", run_id="run-1", attempt_id="attempt-0001", data_snapshot_id="snapshot-1",
        plan_version=1, object_type="keyword", object_id="kw-1", optimization_goal="target_acos",
        requested_risk_profile="balanced",
        entity_metrics=[{"entity_id": "kw-1", "spend": "315.00", "sales": "900.00"}],
        calculated_metrics={"acos": "0.350000"}, candidate_values=("1.02", "1.08", "1.14"),
        constraints={"rule_set_version": "poc-rules-v0.1", "target_acos": "0.250000", "confidence": "0.85"},
        previous_failure=None,
    )


def _response(body: str | None = None, *, status: int = 200, request_id: str = "req-test-1") -> LLMTransportResponse:
    document = {
        "schema_version": "1.0", "decision": "select",
        "selected_value": "1.08", "reason": "offline test response",
        "evidence_paths": ["entity_metrics[0].spend", "entity_metrics[0].sales", "target_acos"],
        "risk_summary": "medium", "confidence": "0.840000",
    }
    return LLMTransportResponse(request_id, status, json.dumps(document) if body is None else body, {"input": 3})


def _error_code(reasoner: LLMReasoner) -> str:
    with pytest.raises(ReasonerError) as caught:
        reasoner.reason(_input())
    return caught.value.error_code


def test_fake_transport_records_call_and_last_request() -> None:
    transport = FakeTransport([_response()])
    LLMReasoner(_config(), transport).reason(_input())
    assert transport.call_count == 1 and transport.last_request is not None


def test_request_contains_model_timeout_and_metadata() -> None:
    transport = FakeTransport([_response()])
    LLMReasoner(_config(), transport).reason(_input())
    request = transport.last_request
    assert request is not None
    assert (request.model, request.timeout_seconds, request.request_metadata["attempt_id"]) == ("test-model", 30, "attempt-0001")


def test_request_uses_formal_repository_prompts() -> None:
    transport = FakeTransport([_response()])
    LLMReasoner(_config(), transport).reason(_input())
    request = transport.last_request
    assert request is not None
    assert "# Role" in request.payload["messages"][0]["content"]
    assert "Keyword Bid Optimization Task" in request.payload["messages"][1]["content"]
    assert request.payload["response_contract"] == "reasoner-output.schema.json"


def test_request_and_repr_do_not_contain_api_key() -> None:
    transport = FakeTransport([_response()])
    LLMReasoner(_config(), transport).reason(_input())
    assert FAKE_KEY not in repr(transport.last_request)


def test_valid_response_becomes_result() -> None:
    result = LLMReasoner(_config(), FakeTransport([_response()])).reason(_input())
    assert (result.selected_value, result.provider, result.model, result.request_id) == ("1.08", "llm", "test-model", "req-test-1")


def test_sensitive_or_malformed_request_id_is_rejected() -> None:
    assert _error_code(
        LLMReasoner(_config(), FakeTransport([_response(request_id="Bearer private value")]))
    ) == "ERR_LLM_RESPONSE_INVALID"


@pytest.mark.parametrize(
    ("body", "code"),
    [
        ("", "ERR_LLM_RESPONSE_EMPTY"),
        ("not-json", "ERR_LLM_RESPONSE_INVALID"),
        ("{}", "ERR_REASONER_OUTPUT_SCHEMA_FAILED"),
        ('{"selected_value": 108, "reason": "x", "evidence_paths": ["target_acos"], "risk_summary": "medium"}', "ERR_REASONER_OUTPUT_SCHEMA_FAILED"),
        ('{"selected_value": "abc", "reason": "x", "evidence_paths": ["target_acos"], "risk_summary": "medium"}', "ERR_REASONER_OUTPUT_SCHEMA_FAILED"),
        ('{"selected_value": "1.08", "reason": "x", "evidence_paths": [], "risk_summary": "medium"}', "ERR_REASONER_OUTPUT_SCHEMA_FAILED"),
        ('{"selected_value": "1.08", "reason": "x", "evidence_paths": [1], "risk_summary": "medium"}', "ERR_REASONER_OUTPUT_SCHEMA_FAILED"),
        ('{"selected_value": "1.08", "reason": "x", "evidence_paths": ["target_acos"], "risk_summary": "medium", "object_id": "fabricated"}', "ERR_REASONER_OUTPUT_SCHEMA_FAILED"),
    ],
)
def test_invalid_response_shapes_fail(body: str, code: str) -> None:
    assert _error_code(LLMReasoner(_config(), FakeTransport([_response(body)]))) == code


def test_timeout_without_retry_is_distinct() -> None:
    assert _error_code(LLMReasoner(_config(), FakeTransport([TimeoutError("private detail")]))) == "ERR_LLM_TIMEOUT"


def test_transport_failure_without_retry_is_distinct() -> None:
    error = ReasonerTransportError("ERR_LLM_TRANSPORT_FAILED", "safe failure", retryable=True, provider="llm")
    assert _error_code(LLMReasoner(_config(), FakeTransport([error]))) == "ERR_LLM_TRANSPORT_FAILED"


def test_client_error_is_not_retried() -> None:
    transport = FakeTransport([_response(status=400), _response()])
    assert _error_code(LLMReasoner(_config(retries=2), transport)) == "ERR_LLM_TRANSPORT_FAILED"
    assert transport.call_count == 1


def test_server_error_retries_then_succeeds() -> None:
    transport = FakeTransport([_response(status=503), _response()])
    reasoner = LLMReasoner(_config(retries=1), transport)
    result = reasoner.reason(_input())
    assert result.selected_value == "1.08"
    assert transport.call_count == 2
    assert reasoner.last_transport_retry_count == 1


def test_retry_exhaustion_has_stable_error() -> None:
    transport = FakeTransport([TimeoutError(), TimeoutError()])
    reasoner = LLMReasoner(_config(retries=1), transport)
    assert _error_code(reasoner) == "ERR_LLM_RETRIES_EXHAUSTED"
    assert transport.call_count == 2


def test_reasoner_call_count_excludes_transport_retries() -> None:
    reasoner = LLMReasoner(_config(retries=1), FakeTransport([TimeoutError(), _response()]))
    reasoner.reason(_input())
    assert reasoner.call_count == 1


def test_input_nested_state_is_immutable() -> None:
    value = _input()
    with pytest.raises(TypeError):
        value.constraints["target_acos"] = "0.10"


def test_candidate_values_are_immutable_and_unchanged() -> None:
    value = _input()
    before = value.candidate_values
    LLMReasoner(_config(), FakeTransport([_response()])).reason(value)
    assert value.candidate_values == before
    with pytest.raises(AttributeError):
        value.candidate_values.append("2.00")


def test_no_default_transport_uses_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("network access attempted")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    assert _error_code(LLMReasoner(_config(), NotConfiguredTransport())) == "ERR_LLM_TRANSPORT_FAILED"
