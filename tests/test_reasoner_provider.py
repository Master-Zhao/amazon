"""Provider factory and Workflow integration tests."""

from __future__ import annotations

import json

import pytest

from amazon_ads_agent.reasoners.config import LLMReasonerConfig
from amazon_ads_agent.reasoners.errors import ReasonerConfigurationError, ReasonerTransportError
from amazon_ads_agent.reasoners.llm import LLMReasoner
from amazon_ads_agent.reasoners.provider import create_reasoner, load_reasoner_config
from amazon_ads_agent.reasoners.stub import ReasonerStub
from amazon_ads_agent.reasoners.transport import FakeTransport, LLMTransportResponse
from amazon_ads_agent.workflow import run_workflow

FAKE_KEY = "test-only-not-a-real-key"


def _config(*, retries: int = 0) -> LLMReasonerConfig:
    return LLMReasonerConfig("llm", "test-model", FAKE_KEY, "https://model.invalid/v1", 30, retries)


def _response(value: str = "1.08", *, extra: dict[str, str] | None = None) -> LLMTransportResponse:
    body = {
        "schema_version": "1.0",
        "decision": "select",
        "selected_value": value,
        "reason": "offline Fake Transport selection",
        "evidence_paths": ["entity_metrics[0].spend", "entity_metrics[0].sales", "target_acos"],
        "risk_summary": "human approval required",
        "confidence": "0.840000",
    }
    body.update(extra or {})
    return LLMTransportResponse("request-offline-1", 200, json.dumps(body), {})


def test_factory_creates_stub_without_key() -> None:
    assert isinstance(create_reasoner(LLMReasonerConfig()), ReasonerStub)


def test_provider_layer_loads_default_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    assert load_reasoner_config().provider == "stub"


def test_factory_passes_stub_mode() -> None:
    reasoner = create_reasoner(LLMReasonerConfig(), stub_mode="always_invalid")
    assert isinstance(reasoner, ReasonerStub) and reasoner.mode == "always_invalid"


def test_stub_factory_does_not_call_transport() -> None:
    transport = FakeTransport([])
    create_reasoner(LLMReasonerConfig(), transport=transport)
    assert transport.call_count == 0


def test_factory_creates_llm_with_injected_transport() -> None:
    transport = FakeTransport([_response()])
    reasoner = create_reasoner(_config(), transport=transport)
    assert isinstance(reasoner, LLMReasoner) and reasoner.transport is transport


@pytest.mark.parametrize("missing", ["model", "api_key", "base_url"])
def test_factory_rejects_incomplete_llm(missing: str) -> None:
    values = {"provider": "llm", "model": "test-model", "api_key": FAKE_KEY, "base_url": "https://model.invalid"}
    values[missing] = None
    with pytest.raises(ReasonerConfigurationError) as caught:
        create_reasoner(LLMReasonerConfig(**values))
    assert caught.value.error_code == "ERR_LLM_CONFIG_MISSING"


def test_factory_rejects_unknown_provider_without_fallback() -> None:
    with pytest.raises(ReasonerConfigurationError) as caught:
        create_reasoner(LLMReasonerConfig(provider="other"))
    assert caught.value.error_code == "ERR_LLM_PROVIDER_UNSUPPORTED"


def test_default_workflow_uses_stub(high_task: dict) -> None:
    result = run_workflow(high_task, reasoner_config=LLMReasonerConfig())
    selected = next(event for event in result.audit_events if event["event_type"] == "reasoner_provider_selected")
    assert selected["metadata"]["provider"] == "stub"


def test_explicit_stub_provider_runs(high_task: dict) -> None:
    result = run_workflow(high_task, reasoner_provider="stub")
    assert result.output["current_status"] == "waiting_for_approval"


def test_llm_fake_transport_reaches_waiting_for_approval(high_task: dict) -> None:
    transport = FakeTransport([_response()])
    result = run_workflow(high_task, reasoner_config=_config(), transport=transport)
    assert result.output["current_status"] == "waiting_for_approval"
    assert result.output["human_approval_required"] is True
    assert result.output["execution_preflight"]["production_write_called"] is False
    assert transport.call_count == 1


def test_llm_outside_candidate_is_rejected_then_revised(high_task: dict) -> None:
    transport = FakeTransport([_response("0.80"), _response("1.08")])
    result = run_workflow(high_task, reasoner_config=_config(), transport=transport)
    assert result.output["current_status"] == "waiting_for_approval"
    assert result.output["plan_version"] == 2 and result.output["retry_count"] == 1
    assert result.failure_analyses[0]["error_code"] == "ERR_CANDIDATE_OUT_OF_RANGE"


def test_llm_fabricated_object_field_fails_closed(high_task: dict) -> None:
    result = run_workflow(high_task, reasoner_config=_config(), transport=FakeTransport([_response(extra={"object_id": "fabricated"})]))
    assert result.output["current_status"] == "manual_intervention_required"
    assert result.output["runtime_validation"]["error_code"] == "ERR_REASONER_OUTPUT_SCHEMA_FAILED"
    assert result.output["execution_preflight"] is None


def test_llm_service_error_never_enters_preflight(high_task: dict) -> None:
    error = ReasonerTransportError("ERR_LLM_TRANSPORT_FAILED", "safe service error", retryable=False, provider="llm")
    result = run_workflow(high_task, reasoner_config=_config(), transport=FakeTransport([error]))
    assert result.output["current_status"] == "manual_intervention_required"
    assert result.output["plan_version"] == 1 and result.output["retry_count"] == 0
    assert "preflight_passed" not in {event["event_type"] for event in result.audit_events}


def test_transport_retry_does_not_change_agent_versions(high_task: dict) -> None:
    result = run_workflow(
        high_task,
        reasoner_config=_config(retries=1),
        transport=FakeTransport([TimeoutError(), _response()]),
    )
    assert (result.output["plan_version"], result.output["retry_count"], result.output["attempt_id"]) == (1, 0, "attempt-0001")
    retry_event = next(event for event in result.audit_events if event["event_type"] == "llm_transport_retry")
    assert retry_event["metadata"] == {"transport_retry_count": 1, "agent_revision_count": 0}


def test_audit_metadata_has_provider_model_request_but_no_key(high_task: dict) -> None:
    result = run_workflow(high_task, reasoner_config=_config(), transport=FakeTransport([_response()]))
    audit_text = json.dumps(result.audit_events)
    assert FAKE_KEY not in audit_text
    assert '"provider": "llm"' in audit_text and '"request_id": "request-offline-1"' in audit_text


def test_llm_configuration_error_never_initializes_transport(high_task: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "llm")
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    transport = FakeTransport([_response()])
    with pytest.raises(ReasonerConfigurationError):
        run_workflow(high_task, transport=transport)
    assert transport.call_count == 0
