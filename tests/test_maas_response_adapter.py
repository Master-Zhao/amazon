"""MaaS response adapter unit tests."""

from __future__ import annotations

import json

import pytest

from amazon_ads_agent.reasoners.errors import ReasonerResponseError
from amazon_ads_agent.reasoners.maas_response_adapter import adapt_maas_response


def _maas_body(**overrides) -> bytes:
    document = {
        "id": "maas-req-001",
        "choices": [{"message": {"content": json.dumps({"selected_value": "1.08"})}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }
    document.update(overrides)
    return json.dumps(document).encode()


def test_normal_maas_choices_response() -> None:
    result = adapt_maas_response(
        _maas_body(), {}, status_code=200, model="GLM-5.1", latency_ms=100, provider_name="maas",
    )
    assert result.body == json.dumps({"selected_value": "1.08"})
    assert result.provider == "maas"
    assert result.request_id == "maas-req-001"


def test_maas_output_text_format() -> None:
    body = json.dumps({
        "id": "maas-req-002",
        "output": {"text": json.dumps({"selected_value": "2.50"})},
        "usage": {"prompt_tokens": 20, "completion_tokens": 10, "total_tokens": 30},
    }).encode()
    result = adapt_maas_response(body, {}, status_code=200, model="GLM-5.1", latency_ms=100, provider_name="maas")
    assert result.body == json.dumps({"selected_value": "2.50"})


def test_maas_result_format() -> None:
    body = json.dumps({
        "id": "maas-req-003",
        "result": json.dumps({"selected_value": "3.00"}),
        "usage": {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
    }).encode()
    result = adapt_maas_response(body, {}, status_code=200, model="GLM-5.1", latency_ms=100, provider_name="maas")
    assert result.body == json.dumps({"selected_value": "3.00"})


def test_empty_response_rejected() -> None:
    with pytest.raises(ReasonerResponseError, match="ERR_LLM_PROVIDER_RESPONSE_EMPTY"):
        adapt_maas_response(b"", {}, status_code=200, model="GLM-5.1", latency_ms=100, provider_name="maas")


def test_invalid_json_rejected() -> None:
    with pytest.raises(ReasonerResponseError, match="ERR_LLM_PROVIDER_RESPONSE_INVALID"):
        adapt_maas_response(b"not-json", {}, status_code=200, model="GLM-5.1", latency_ms=100, provider_name="maas")


def test_non_object_rejected() -> None:
    with pytest.raises(ReasonerResponseError, match="ERR_LLM_PROVIDER_RESPONSE_INVALID"):
        adapt_maas_response(b"[]", {}, status_code=200, model="GLM-5.1", latency_ms=100, provider_name="maas")


def test_empty_content_rejected() -> None:
    body = json.dumps({"id": "req", "choices": [{"message": {"content": "  "}}]}).encode()
    with pytest.raises(ReasonerResponseError, match="ERR_LLM_PROVIDER_RESPONSE_EMPTY"):
        adapt_maas_response(body, {}, status_code=200, model="GLM-5.1", latency_ms=100, provider_name="maas")


def test_missing_content_path_rejected() -> None:
    body = json.dumps({"id": "req", "choices": [{"message": {}}]}).encode()
    with pytest.raises(ReasonerResponseError, match="ERR_LLM_PROVIDER_RESPONSE_INVALID"):
        adapt_maas_response(body, {}, status_code=200, model="GLM-5.1", latency_ms=100, provider_name="maas")


def test_usage_extracted_correctly() -> None:
    result = adapt_maas_response(
        _maas_body(), {}, status_code=200, model="GLM-5.1", latency_ms=100, provider_name="maas",
    )
    assert result.usage == {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}


def test_missing_usage_is_none() -> None:
    body = json.dumps({
        "id": "req", "choices": [{"message": {"content": "valid content"}}],
    }).encode()
    result = adapt_maas_response(body, {}, status_code=200, model="GLM-5.1", latency_ms=100, provider_name="maas")
    assert result.usage is None


def test_request_id_from_header() -> None:
    result = adapt_maas_response(
        _maas_body(), {"x-request-id": "header-id-001"}, status_code=200, model="GLM-5.1", latency_ms=100, provider_name="maas",
    )
    assert result.request_id == "header-id-001"


def test_request_id_fallback_to_local() -> None:
    body = json.dumps({"choices": [{"message": {"content": "valid"}}]}).encode()
    result = adapt_maas_response(body, {}, status_code=200, model="GLM-5.1", latency_ms=100, provider_name="maas")
    assert result.request_id.startswith("local-")