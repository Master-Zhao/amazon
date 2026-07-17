"""HTTP Mock tests for the one OpenAI-compatible protocol."""

from __future__ import annotations

import json
import socket
import urllib.error
from collections.abc import Mapping

import pytest

from amazon_ads_agent.reasoners.config import LLMReasonerConfig
from amazon_ads_agent.reasoners.errors import (
    ReasonerConfigurationError,
    ReasonerResponseError,
    ReasonerRetriesExhaustedError,
    ReasonerTimeoutError,
    ReasonerTransportError,
)
from amazon_ads_agent.reasoners.http_transport import HTTPResponse, OpenAICompatibleHTTPTransport, UrllibHTTPClient
from amazon_ads_agent.reasoners.llm import LLMReasoner
from amazon_ads_agent.reasoners.transport import LLMTransportRequest
from amazon_ads_agent.workflow import run_workflow

FAKE_KEY = "test-only-not-a-real-key"


class MockClient:
    def __init__(self, outcomes: list[HTTPResponse | Exception]) -> None:
        self.outcomes = list(outcomes)
        self.calls: list[tuple[str, Mapping[str, str], bytes, int]] = []

    def post(self, url: str, headers: Mapping[str, str], body: bytes, timeout_seconds: int) -> HTTPResponse:
        self.calls.append((url, headers, body, timeout_seconds))
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def _config(*, retries: int = 0, base_url: str = "https://model.invalid/v1/chat/completions") -> LLMReasonerConfig:
    return LLMReasonerConfig("llm", "test-model", FAKE_KEY, base_url, 5, retries, True, 512)


def _request() -> LLMTransportRequest:
    return LLMTransportRequest(
        "test-model", "https://model.invalid/v1/chat/completions", 5,
        {"messages": [{"role": "user", "content": "synthetic"}]},
        {"task_id": "task", "run_id": "run", "attempt_id": "attempt-0001", "plan_version": 1},
    )


def _reasoner_content(value: str = "1.08") -> str:
    return json.dumps({
        "schema_version": "1.0", "decision": "select", "selected_value": value,
        "reason": "synthetic model selection", "evidence_paths": ["calculated_metrics.acos", "task_context.target_acos"],
        "risk_summary": "human approval remains required", "confidence": "0.800000",
    })


def _response(
    status: int = 200, *, content: str | None = None, usage: object = "default",
    request_id: str = "provider-request-1",
) -> HTTPResponse:
    document: dict[str, object] = {
        "id": request_id, "choices": [{"message": {"content": content or _reasoner_content()}}],
    }
    if usage == "default":
        document["usage"] = {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
    elif usage is not None:
        document["usage"] = usage
    return HTTPResponse(status, {"x-request-id": request_id}, json.dumps(document).encode())


def test_200_extracts_body_request_id_usage_and_metadata() -> None:
    transport = OpenAICompatibleHTTPTransport(_config(), client=MockClient([_response()]))
    result = transport.complete(_request())
    assert result.status_code == 200 and result.body == _reasoner_content()
    assert result.request_id == "provider-request-1"
    assert result.usage == {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
    assert result.provider == "openai_compatible" and result.model == "test-model"


def test_missing_usage_is_preserved_as_none() -> None:
    result = OpenAICompatibleHTTPTransport(_config(), client=MockClient([_response(usage=None)])).complete(_request())
    assert result.usage is None


def test_request_protocol_is_explicit_and_deterministic() -> None:
    client = MockClient([_response()])
    OpenAICompatibleHTTPTransport(_config(), client=client).complete(_request())
    url, headers, body, timeout = client.calls[0]
    payload = json.loads(body)
    assert url == "https://model.invalid/v1/chat/completions" and timeout == 5
    assert headers["Content-Type"] == "application/json"
    assert headers["Authorization"] == f"Bearer {FAKE_KEY}"
    assert payload == {
        "model": "test-model", "messages": [{"role": "user", "content": "synthetic"}],
        "temperature": 0, "response_format": {"type": "json_object"}, "max_tokens": 512,
    }


@pytest.mark.parametrize(
    ("status", "code", "retryable"),
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
def test_http_status_mapping(status: int, code: str, retryable: bool) -> None:
    with pytest.raises(ReasonerTransportError) as caught:
        OpenAICompatibleHTTPTransport(_config(), client=MockClient([HTTPResponse(status, {}, b"private")])).complete(_request())
    assert caught.value.error_code == code and caught.value.retryable is retryable
    assert "private" not in str(caught.value) and FAKE_KEY not in str(caught.value)


@pytest.mark.parametrize("status", [429, 500, 503])
def test_retryable_status_then_success(status: int) -> None:
    client = MockClient([HTTPResponse(status, {}, b""), _response()])
    transport = OpenAICompatibleHTTPTransport(_config(retries=1), client=client)
    response = LLMReasoner(_config(retries=1), transport)._complete_with_retries(_request())
    assert response.status_code == 200 and len(client.calls) == 2


@pytest.mark.parametrize("status", [429, 500, 503])
def test_retryable_status_exhaustion_is_bounded(status: int) -> None:
    client = MockClient([HTTPResponse(status, {}, b""), HTTPResponse(status, {}, b"")])
    with pytest.raises(ReasonerRetriesExhaustedError):
        LLMReasoner(_config(retries=1), OpenAICompatibleHTTPTransport(_config(), client=client))._complete_with_retries(_request())
    assert len(client.calls) == 2


@pytest.mark.parametrize(
    ("body", "code"),
    [
        (b"", "ERR_LLM_PROVIDER_RESPONSE_EMPTY"),
        (b"not-json", "ERR_LLM_PROVIDER_RESPONSE_INVALID"),
        (b"[]", "ERR_LLM_PROVIDER_RESPONSE_INVALID"),
        (b'{"choices":[]}', "ERR_LLM_PROVIDER_RESPONSE_INVALID"),
        (b'{"choices":[{"message":{}}]}', "ERR_LLM_PROVIDER_RESPONSE_INVALID"),
        (b'{"choices":[{"message":{"content":""}}]}', "ERR_LLM_PROVIDER_RESPONSE_EMPTY"),
    ],
)
def test_invalid_provider_response_fails_closed(body: bytes, code: str) -> None:
    with pytest.raises(ReasonerResponseError) as caught:
        OpenAICompatibleHTTPTransport(_config(), client=MockClient([HTTPResponse(200, {}, body)])).complete(_request())
    assert caught.value.error_code == code


@pytest.mark.parametrize("usage", [{}, {"prompt_tokens": -1}, {"prompt_tokens": "1"}, {"unknown": 1}, []])
def test_invalid_usage_fails_closed(usage: object) -> None:
    with pytest.raises(ReasonerResponseError, match="ERR_LLM_PROVIDER_USAGE_INVALID"):
        OpenAICompatibleHTTPTransport(_config(), client=MockClient([_response(usage=usage)])).complete(_request())


def test_latency_uses_monotonic_integer_milliseconds() -> None:
    ticks = iter([1_000_000, 8_000_000])
    transport = OpenAICompatibleHTTPTransport(_config(), client=MockClient([_response()]), clock=lambda: next(ticks))
    assert transport.complete(_request()).latency_ms == 7
    assert transport.latencies_ms == [7]


def test_request_budget_stops_before_extra_http_call() -> None:
    client = MockClient([_response(), _response()])
    transport = OpenAICompatibleHTTPTransport(_config(), client=client, max_requests=1)
    transport.complete(_request())
    with pytest.raises(ReasonerTransportError, match="ERR_REAL_EVALUATION_BUDGET_EXCEEDED"):
        transport.complete(_request())
    assert len(client.calls) == 1


@pytest.mark.parametrize("base_url", ["ftp://model.invalid", "http://model.invalid", "https://user:pass@model.invalid"])
def test_unsafe_endpoint_is_rejected(base_url: str) -> None:
    with pytest.raises(ReasonerConfigurationError, match="ERR_LLM_BASE_URL_INVALID"):
        OpenAICompatibleHTTPTransport(_config(base_url=base_url), client=MockClient([]))


def test_loopback_http_endpoint_is_allowed_for_local_mocking() -> None:
    config = _config(base_url="http://127.0.0.1:8080/v1")
    transport = OpenAICompatibleHTTPTransport(config, client=MockClient([]))
    assert "test-only" not in repr(transport)


def test_urllib_client_maps_socket_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: (_ for _ in ()).throw(socket.timeout()))
    with pytest.raises(ReasonerTimeoutError, match="ERR_LLM_TIMEOUT"):
        UrllibHTTPClient().post("https://model.invalid", {}, b"{}", 1)


def test_urllib_client_maps_url_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "urllib.request.urlopen", lambda *args, **kwargs: (_ for _ in ()).throw(urllib.error.URLError("private"))
    )
    with pytest.raises(ReasonerTransportError, match="ERR_LLM_TRANSPORT_FAILED") as caught:
        UrllibHTTPClient().post("https://model.invalid", {}, b"{}", 1)
    assert "private" not in str(caught.value)


def test_transport_retry_does_not_change_agent_versions(high_task: dict) -> None:
    client = MockClient([HTTPResponse(503, {}, b""), _response()])
    config = _config(retries=1)
    result = run_workflow(
        high_task, reasoner_config=config,
        transport=OpenAICompatibleHTTPTransport(config, client=client),
    )
    assert result.output["plan_version"] == 1
    assert result.output["attempt_id"] == "attempt-0001"
    assert result.output["retry_count"] == 0
    assert len(client.calls) == 2
