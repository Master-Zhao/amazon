"""Provider Identity chain tests: provider_name from Config to Transport to Response to Report."""

from __future__ import annotations

import json

import pytest

from amazon_ads_agent.reasoners.config import LLMReasonerConfig
from amazon_ads_agent.reasoners.http_transport import HTTPResponse, OpenAICompatibleHTTPTransport
from amazon_ads_agent.reasoners.response_adapter import adapt_openai_compatible_response
from amazon_ads_agent.reasoners.transport import LLMTransportRequest
from evaluation.real_report import build_real_report
from evaluation.real_config import RealEvaluationConfig
from evaluation.models import RealEvaluationRun

FAKE_KEY = "test-only-not-a-real-key"


class MockClient:
    def __init__(self, outcomes: list[HTTPResponse | Exception]) -> None:
        self.outcomes = list(outcomes)

    def post(self, url, headers, body, timeout_seconds):
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def _response(status: int = 200, *, content: str | None = None) -> HTTPResponse:
    document = {
        "id": "req-1",
        "choices": [{"message": {"content": content or json.dumps({
            "schema_version": "1.0", "decision": "select", "selected_value": "1.08",
            "reason": "synthetic", "evidence_paths": ["calculated_metrics.acos"],
            "risk_summary": "low", "confidence": "0.800000",
        })}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }
    return HTTPResponse(status, {"x-request-id": "req-1"}, json.dumps(document).encode())


def test_provider_name_from_config_to_transport() -> None:
    config = LLMReasonerConfig("llm", "glm-4-flash", FAKE_KEY, "https://open.bigmodel.cn/api/paas/v4/chat/completions", 5, 0, True, 512, "glm")
    transport = OpenAICompatibleHTTPTransport(config, client=MockClient([_response()]))
    request = LLMTransportRequest(
        "glm-4-flash", "https://open.bigmodel.cn/api/paas/v4/chat/completions", 5,
        {"messages": [{"role": "user", "content": "test"}]},
        {"task_id": "task"},
    )
    result = transport.complete(request)
    assert result.provider == "glm"


def _safety_summary(**overrides) -> dict:
    base = {
        "actual_request_count": 1,
        "total_runs": 0,
        "passed_runs": 0,
        "production_write_violation_count": 0,
        "approval_bypass_count": 0,
        "final_candidate_violation_count": 0,
        "final_hallucinated_object_count": 0,
        "final_invalid_evidence_count": 0,
        "preflight_boundary_violation_count": 0,
        "amazon_ads_api_call_count": 0,
        "credential_leak_count": 0,
        "final_json_pass_rate": "1.000000",
        "final_schema_pass_rate": "1.000000",
        "final_business_pass_rate": "1.000000",
        "first_json_pass_rate": "1.000000",
        "first_schema_pass_rate": "1.000000",
        "first_business_pass_rate": "1.000000",
        "final_success_rate": "1.000000",
        "revision_success_rate": "1.000000",
        "manual_intervention_rate": "0.000000",
        "sample_complete": True,
        "reasoner_run_count": 1,
    }
    base.update(overrides)
    return base


def test_provider_name_from_config_to_report() -> None:
    config = LLMReasonerConfig("llm", "glm-4-flash", FAKE_KEY, "https://open.bigmodel.cn/api/paas/v4/chat/completions", 5, 0, True, 512, "glm")
    budget = RealEvaluationConfig.from_env()
    report = build_real_report(
        [], _safety_summary(),
        model=config.model or "",
        base_url=config.base_url or "",
        budget=budget,
        smoke_case_ids=["CASE-001"],
        smoke_passed=True,
        full_evaluation_executed=False,
        provider_name=config.provider_name,
    )
    assert report["provider"] == "glm"


def test_provider_name_env_override() -> None:
    config = LLMReasonerConfig.from_env({
        "LLM_PROVIDER": "llm",
        "LLM_MODEL": "glm-4-flash",
        "LLM_API_KEY": FAKE_KEY,
        "LLM_BASE_URL": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        "LLM_PROVIDER_NAME": "custom_glm",
    })
    assert config.provider_name == "custom_glm"


def test_provider_name_default_backward_compat() -> None:
    raw_body = json.dumps({
        "id": "req-1",
        "choices": [{"message": {"content": '{"selected_value":"1.08"}'}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }).encode()
    result = adapt_openai_compatible_response(
        raw_body, {}, status_code=200, model="test-model", latency_ms=100,
    )
    assert result.provider == "openai_compatible"


def test_provider_name_explicit_in_adapter() -> None:
    raw_body = json.dumps({
        "id": "req-1",
        "choices": [{"message": {"content": '{"selected_value":"1.08"}'}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }).encode()
    result = adapt_openai_compatible_response(
        raw_body, {}, status_code=200, model="glm-4-flash", latency_ms=100, provider_name="glm",
    )
    assert result.provider == "glm"


def test_report_default_provider_name_backward_compat() -> None:
    budget = RealEvaluationConfig.from_env()
    report = build_real_report(
        [], _safety_summary(actual_request_count=0),
        model="test-model",
        base_url="https://model.invalid/v1",
        budget=budget,
        smoke_case_ids=[],
        smoke_passed=False,
        full_evaluation_executed=False,
    )
    assert report["provider"] == "openai_compatible"