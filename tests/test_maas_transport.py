"""MaaS HTTP Transport unit tests."""

from __future__ import annotations

import json

import pytest

from amazon_ads_agent.reasoners.config import LLMReasonerConfig
from amazon_ads_agent.reasoners.errors import ReasonerTransportError
from amazon_ads_agent.reasoners.http_transport import HTTPResponse
from amazon_ads_agent.reasoners.maas_transport import MaaSHTTPTransport
from amazon_ads_agent.reasoners.transport import LLMTransportRequest

FAKE_KEY = "test-only-not-a-real-key"
MAAS_BASE_URL = "https://api.modelarts-maas.com/plan/v2"


def _config() -> LLMReasonerConfig:
    return LLMReasonerConfig("llm", "GLM-5.1", FAKE_KEY, MAAS_BASE_URL, 5, 0, True, 512, "maas")


def _request() -> LLMTransportRequest:
    return LLMTransportRequest(
        "GLM-5.1", MAAS_BASE_URL, 5,
        {"messages": [{"role": "user", "content": "synthetic"}]},
        {"task_id": "task", "run_id": "run", "attempt_id": "attempt-0001", "plan_version": 1},
    )


class MockClient:
    def __init__(self, outcomes: list[HTTPResponse | Exception]) -> None:
        self.outcomes = list(outcomes)

    def post(self, url, headers, body, timeout_seconds):
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def _maas_response(
    *,
    content: str | None = None,
    request_id: str = "maas-req-001",
    usage: dict | None = None,
    status: int = 200,
) -> HTTPResponse:
    document: dict = {
        "id": request_id,
        "choices": [{"message": {"content": content or json.dumps({
            "schema_version": "1.0", "decision": "select", "selected_value": "1.08",
            "reason": "synthetic", "evidence_paths": ["calculated_metrics.acos"],
            "risk_summary": "low", "confidence": "0.800000",
        })}}],
    }
    if usage is not None:
        document["usage"] = usage
    else:
        document["usage"] = {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
    return HTTPResponse(status, {"x-request-id": request_id}, json.dumps(document).encode())


def test_200_extracts_body_request_id_usage_and_metadata() -> None:
    transport = MaaSHTTPTransport(_config(), client=MockClient([_maas_response()]))
    result = transport.complete(_request())
    assert result.provider == "maas" and result.model == "GLM-5.1"
    assert result.request_id == "maas-req-001"
    assert result.usage == {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}


@pytest.mark.parametrize(
    ("status", "error_code", "retryable"),
    [
        (400, "ERR_LLM_REQUEST_REJECTED", False),
        (401, "ERR_LLM_AUTHENTICATION_FAILED", False),
        (403, "ERR_LLM_PERMISSION_DENIED", False),
        (404, "ERR_LLM_REQUEST_REJECTED", False),
        (429, "ERR_LLM_RATE_LIMITED", True),
        (500, "ERR_LLM_SERVICE_UNAVAILABLE", True),
        (502, "ERR_LLM_SERVICE_UNAVAILABLE", True),
        (503, "ERR_LLM_SERVICE_UNAVAILABLE", True),
        (504, "ERR_LLM_SERVICE_UNAVAILABLE", True),
    ],
)
def test_http_status_mapping(status: int, error_code: str, retryable: bool) -> None:
    transport = MaaSHTTPTransport(_config(), client=MockClient([HTTPResponse(status, {}, b"")]))
    with pytest.raises(ReasonerTransportError) as caught:
        transport.complete(_request())
    assert caught.value.error_code == error_code
    assert caught.value.retryable == retryable
    assert caught.value.provider == "maas"


def test_request_budget_stops_before_extra_http_call() -> None:
    transport = MaaSHTTPTransport(_config(), client=MockClient([_maas_response()]), max_requests=1)
    transport.complete(_request())
    with pytest.raises(ReasonerTransportError, match="ERR_REAL_EVALUATION_BUDGET_EXCEEDED"):
        transport.complete(_request())


def test_repr_does_not_contain_api_key() -> None:
    transport = MaaSHTTPTransport(_config(), client=MockClient([_maas_response()]))
    assert FAKE_KEY not in repr(transport)


def test_incomplete_config_raises() -> None:
    with pytest.raises(Exception, match="ERR_LLM_CONFIG_MISSING"):
        MaaSHTTPTransport(LLMReasonerConfig("llm"), client=MockClient([]))


def test_latency_uses_monotonic_integer_milliseconds() -> None:
    class TickClock:
        def __init__(self):
            self._values = [1_000_000_000_000, 1_000_500_000_000]
            self._idx = 0
        def __call__(self):
            v = self._values[self._idx]
            self._idx += 1
            return v
    transport = MaaSHTTPTransport(
        _config(), client=MockClient([_maas_response()]),
        clock=TickClock(),
    )
    transport.complete(_request())
    assert transport.latencies_ms == [500]