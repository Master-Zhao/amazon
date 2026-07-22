"""MaaS Provider Identity chain tests: provider_name from Config to Transport to Response to Report."""

from __future__ import annotations

import json

import pytest

from amazon_ads_agent.reasoners.config import LLMReasonerConfig
from amazon_ads_agent.reasoners.http_transport import HTTPResponse
from amazon_ads_agent.reasoners.maas_transport import MaaSHTTPTransport
from amazon_ads_agent.reasoners.transport import LLMTransportRequest
from amazon_ads_agent.reasoners.transport_router import create_transport
from evaluation.real_report import build_real_report
from evaluation.real_config import RealEvaluationConfig

FAKE_KEY = "test-only-not-a-real-key"
MAAS_BASE_URL = "https://api.modelarts-maas.com/plan/v2"


class MockClient:
    def __init__(self, outcomes: list[HTTPResponse | Exception]) -> None:
        self.outcomes = list(outcomes)

    def post(self, url, headers, body, timeout_seconds):
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def _maas_response() -> HTTPResponse:
    document = {
        "id": "maas-req-1",
        "choices": [{"message": {"content": json.dumps({
            "schema_version": "1.0", "decision": "select", "selected_value": "1.08",
            "reason": "synthetic", "evidence_paths": ["calculated_metrics.acos"],
            "risk_summary": "low", "confidence": "0.800000",
        })}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }
    return HTTPResponse(200, {"x-request-id": "maas-req-1"}, json.dumps(document).encode())


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


def test_maas_provider_name_from_config_to_transport() -> None:
    config = LLMReasonerConfig("llm", "GLM-5.1", FAKE_KEY, MAAS_BASE_URL, 5, 0, True, 512, "maas")
    transport = create_transport(config, client=MockClient([_maas_response()]))
    request = LLMTransportRequest(
        "GLM-5.1", MAAS_BASE_URL, 5,
        {"messages": [{"role": "user", "content": "test"}]},
        {"task_id": "task"},
    )
    result = transport.complete(request)
    assert result.provider == "maas"


def test_maas_provider_name_from_config_to_report() -> None:
    config = LLMReasonerConfig("llm", "GLM-5.1", FAKE_KEY, MAAS_BASE_URL, 5, 0, True, 512, "maas")
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
    assert report["provider"] == "maas"
    assert report["model"] == "MaaS-GLM-5.1"


def test_glm_provider_name_not_prefixed_in_report() -> None:
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
    assert report["model"] == "glm-4-flash"


def test_transport_isolation_maas_vs_openai() -> None:
    from amazon_ads_agent.reasoners.http_transport import OpenAICompatibleHTTPTransport
    maas_config = LLMReasonerConfig("llm", "GLM-5.1", FAKE_KEY, MAAS_BASE_URL, 5, 0, True, 512, "maas")
    openai_config = LLMReasonerConfig("llm", "test-model", FAKE_KEY, "https://open.bigmodel.cn/api/paas/v4/chat/completions", 5, 0, True, 512, "glm")
    maas_transport = MaaSHTTPTransport(maas_config, client=MockClient([_maas_response()]))
    openai_transport = OpenAICompatibleHTTPTransport(openai_config, client=MockClient([_maas_response()]))
    assert maas_transport.actual_request_count == 0
    assert openai_transport.actual_request_count == 0
    assert maas_transport._provider_name == "maas"
    assert openai_transport._provider_name == "glm"