"""Strict adapter for one OpenAI-compatible chat-completions response protocol."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any
from uuid import uuid4

from .errors import ReasonerResponseError
from .transport import LLMTransportResponse

_REQUEST_ID = re.compile(r"[A-Za-z0-9._:-]{1,128}")
_USAGE_KEYS = ("prompt_tokens", "completion_tokens", "total_tokens")


def _error(code: str, message: str, *, provider_name: str = "openai_compatible") -> ReasonerResponseError:
    return ReasonerResponseError(code, message, retryable=False, provider=provider_name)


def _request_id(document: Mapping[str, Any], headers: Mapping[str, str]) -> str:
    normalized = {str(key).lower(): value for key, value in headers.items()}
    candidates = (normalized.get("x-request-id"), document.get("id"))
    for candidate in candidates:
        if isinstance(candidate, str) and _REQUEST_ID.fullmatch(candidate):
            return candidate
    return f"local-{uuid4().hex}"


def _usage(value: Any) -> Mapping[str, int] | None:
    if value is None:
        return None
    if not isinstance(value, dict) or not value or any(key not in _USAGE_KEYS for key in value):
        raise _error("ERR_LLM_PROVIDER_USAGE_INVALID", "model provider usage is invalid")
    if any(type(item) is not int or item < 0 for item in value.values()):
        raise _error("ERR_LLM_PROVIDER_USAGE_INVALID", "model provider usage is invalid")
    return {key: value[key] for key in _USAGE_KEYS if key in value}


def adapt_openai_compatible_response(
    raw_body: bytes,
    headers: Mapping[str, str],
    *,
    status_code: int,
    model: str,
    latency_ms: int,
    provider_name: str = "openai_compatible",
) -> LLMTransportResponse:
    """Extract exactly one assistant content string without repairing it."""

    if not raw_body:
        raise _error("ERR_LLM_PROVIDER_RESPONSE_EMPTY", "model provider returned an empty response", provider_name=provider_name)
    try:
        document = json.loads(raw_body.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise _error("ERR_LLM_PROVIDER_RESPONSE_INVALID", "model provider response is not valid JSON", provider_name=provider_name) from exc
    if not isinstance(document, dict):
        raise _error("ERR_LLM_PROVIDER_RESPONSE_INVALID", "model provider response must be an object", provider_name=provider_name)
    choices = document.get("choices")
    if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
        raise _error("ERR_LLM_PROVIDER_RESPONSE_INVALID", "model provider must return exactly one choice", provider_name=provider_name)
    message = choices[0].get("message")
    content = message.get("content") if isinstance(message, dict) else None
    if not isinstance(content, str):
        raise _error("ERR_LLM_PROVIDER_RESPONSE_INVALID", "model provider response content path is missing", provider_name=provider_name)
    if not content.strip():
        raise _error("ERR_LLM_PROVIDER_RESPONSE_EMPTY", "model provider returned empty assistant content", provider_name=provider_name)
    return LLMTransportResponse(
        request_id=_request_id(document, headers),
        status_code=status_code,
        body=content,
        usage=_usage(document.get("usage")),
        latency_ms=latency_ms,
        provider=provider_name,
        model=model,
    )
