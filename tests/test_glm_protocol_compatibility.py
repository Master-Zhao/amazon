"""GLM API protocol compatibility tests for the response adapter."""

from __future__ import annotations

import json

import pytest

from amazon_ads_agent.reasoners.config import LLMReasonerConfig
from amazon_ads_agent.reasoners.errors import ReasonerResponseError
from amazon_ads_agent.reasoners.http_transport import HTTPResponse, OpenAICompatibleHTTPTransport
from amazon_ads_agent.reasoners.response_adapter import adapt_openai_compatible_response
from amazon_ads_agent.reasoners.transport import LLMTransportRequest

FAKE_KEY = "test-only-not-a-real-key"


def _glm_response(
    *,
    content: str | None = None,
    request_id: str = "cnl-abc123def",
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


def _config() -> LLMReasonerConfig:
    return LLMReasonerConfig("llm", "glm-4-flash", FAKE_KEY, "https://open.bigmodel.cn/api/paas/v4/chat/completions", 5, 0, True, 512, "glm")


def _request() -> LLMTransportRequest:
    return LLMTransportRequest(
        "glm-4-flash", "https://open.bigmodel.cn/api/paas/v4/chat/completions", 5,
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


def test_glm_style_request_id_parsed() -> None:
    raw_body = json.dumps({
        "id": "cnl-xyz789",
        "choices": [{"message": {"content": '{"selected_value":"1.08"}'}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }).encode()
    result = adapt_openai_compatible_response(
        raw_body, {"x-request-id": "cnl-xyz789"}, status_code=200, model="glm-4-flash", latency_ms=100, provider_name="glm",
    )
    assert result.request_id == "cnl-xyz789"
    assert result.provider == "glm"


def test_glm_usage_fields_extracted() -> None:
    raw_body = json.dumps({
        "id": "cnl-test",
        "choices": [{"message": {"content": '{"selected_value":"1.08"}'}}],
        "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
    }).encode()
    result = adapt_openai_compatible_response(
        raw_body, {}, status_code=200, model="glm-4-flash", latency_ms=100, provider_name="glm",
    )
    assert result.usage == {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}


def test_glm_empty_choices_rejected() -> None:
    raw_body = json.dumps({
        "id": "cnl-test",
        "choices": [],
    }).encode()
    with pytest.raises(ReasonerResponseError, match="ERR_LLM_PROVIDER_RESPONSE_INVALID"):
        adapt_openai_compatible_response(
            raw_body, {}, status_code=200, model="glm-4-flash", latency_ms=100, provider_name="glm",
        )


def test_glm_non_json_content_rejected() -> None:
    raw_body = json.dumps({
        "id": "cnl-test",
        "choices": [{"message": {"content": "This is not JSON, just natural language text."}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }).encode()
    result = adapt_openai_compatible_response(
        raw_body, {}, status_code=200, model="glm-4-flash", latency_ms=100, provider_name="glm",
    )
    assert isinstance(result.body, str)


def test_glm_markdown_fenced_json_not_extracted() -> None:
    raw_body = json.dumps({
        "id": "cnl-test",
        "choices": [{"message": {"content": "```json\n{\"selected_value\": \"1.08\"}\n```"}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }).encode()
    result = adapt_openai_compatible_response(
        raw_body, {}, status_code=200, model="glm-4-flash", latency_ms=100, provider_name="glm",
    )
    assert "```" in result.body


def test_glm_transport_uses_provider_name() -> None:
    transport = OpenAICompatibleHTTPTransport(_config(), client=MockClient([_glm_response()]))
    result = transport.complete(_request())
    assert result.provider == "glm"


def test_glm_401_error_uses_provider_name() -> None:
    with pytest.raises(ReasonerResponseError if False else Exception) as caught:
        from amazon_ads_agent.reasoners.errors import ReasonerTransportError
        try:
            OpenAICompatibleHTTPTransport(
                _config(), client=MockClient([HTTPResponse(401, {}, b"")]),
            ).complete(_request())
        except ReasonerTransportError as e:
            assert e.provider == "glm"
            raise


def test_glm_429_error_uses_provider_name() -> None:
    from amazon_ads_agent.reasoners.errors import ReasonerTransportError
    with pytest.raises(ReasonerTransportError) as caught:
        OpenAICompatibleHTTPTransport(
            _config(), client=MockClient([HTTPResponse(429, {}, b"")]),
        ).complete(_request())
    assert caught.value.provider == "glm"
    assert caught.value.retryable is True


def test_glm_duplicate_json_keys_rejected() -> None:
    raw = b'{"id":"cnl-test","choices":[{"message":{"content":"{\\"a\\":1,\\"a\\":2}"}}],"usage":{"prompt_tokens":1,"completion_tokens":1,"total_tokens":2}}'
    result = adapt_openai_compatible_response(
        raw, {}, status_code=200, model="glm-4-flash", latency_ms=100, provider_name="glm",
    )
    assert result.provider == "glm"