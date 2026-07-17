"""Explicitly enabled OpenAI-compatible JSON HTTP transport."""

from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass
from time import monotonic_ns
from typing import Callable, Mapping, Protocol
from urllib.parse import urlsplit

from .config import LLMReasonerConfig
from .errors import ReasonerConfigurationError, ReasonerTimeoutError, ReasonerTransportError
from .response_adapter import adapt_openai_compatible_response
from .transport import LLMTransportRequest, LLMTransportResponse


@dataclass(frozen=True)
class HTTPResponse:
    status_code: int
    headers: Mapping[str, str]
    body: bytes


class HTTPClient(Protocol):
    def post(self, url: str, headers: Mapping[str, str], body: bytes, timeout_seconds: int) -> HTTPResponse:
        """Send one JSON POST and return a raw, business-agnostic response."""


class UrllibHTTPClient:
    """Minimal standard-library client used only after explicit opt-in."""

    def post(self, url: str, headers: Mapping[str, str], body: bytes, timeout_seconds: int) -> HTTPResponse:
        request = urllib.request.Request(url, data=body, headers=dict(headers), method="POST")
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                return HTTPResponse(response.status, dict(response.headers.items()), response.read())
        except urllib.error.HTTPError as exc:
            return HTTPResponse(exc.code, dict(exc.headers.items()) if exc.headers else {}, b"")
        except (TimeoutError, socket.timeout) as exc:
            raise ReasonerTimeoutError(
                "ERR_LLM_TIMEOUT", "model service request timed out", retryable=True, provider="openai_compatible"
            ) from exc
        except (urllib.error.URLError, OSError) as exc:
            raise ReasonerTransportError(
                "ERR_LLM_TRANSPORT_FAILED", "model service transport failed", retryable=True,
                provider="openai_compatible",
            ) from exc


def _validate_endpoint(value: str) -> None:
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise ReasonerConfigurationError(
            "ERR_LLM_BASE_URL_INVALID", "LLM_BASE_URL must be a credential-free HTTP endpoint",
            retryable=False, provider="llm",
        )
    if parsed.scheme == "http" and parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise ReasonerConfigurationError(
            "ERR_LLM_BASE_URL_INVALID", "non-local real model endpoints must use HTTPS",
            retryable=False, provider="llm",
        )


class OpenAICompatibleHTTPTransport:
    """One explicit chat-completions protocol; no provider guessing or fallback."""

    def __init__(
        self,
        config: LLMReasonerConfig,
        *,
        client: HTTPClient | None = None,
        max_requests: int = 60,
        clock: Callable[[], int] = monotonic_ns,
    ) -> None:
        if not config.model or not config.api_key or not config.base_url:
            raise ReasonerConfigurationError(
                "ERR_LLM_CONFIG_MISSING", "real model HTTP configuration is incomplete",
                retryable=False, provider="llm",
            )
        _validate_endpoint(config.base_url)
        if type(max_requests) is not int or max_requests < 1:
            raise ReasonerConfigurationError(
                "ERR_REAL_EVALUATION_CONFIG_INVALID", "request budget must be a positive integer",
                retryable=False, provider="llm",
            )
        self._config = config
        self._client = client or UrllibHTTPClient()
        self._max_requests = max_requests
        self._clock = clock
        self.actual_request_count = 0
        self.latencies_ms: list[int] = []
        self.usages: list[Mapping[str, int] | None] = []

    def __repr__(self) -> str:
        return (
            f"OpenAICompatibleHTTPTransport(model={self._config.model!r}, "
            f"base_url_configured=True, max_requests={self._max_requests})"
        )

    def _status_error(self, status: int) -> ReasonerTransportError:
        if status == 401:
            return ReasonerTransportError(
                "ERR_LLM_AUTHENTICATION_FAILED", "model service authentication failed",
                retryable=False, provider="openai_compatible",
            )
        if status == 403:
            return ReasonerTransportError(
                "ERR_LLM_PERMISSION_DENIED", "model service permission was denied",
                retryable=False, provider="openai_compatible",
            )
        if status == 429:
            return ReasonerTransportError(
                "ERR_LLM_RATE_LIMITED", "model service rate limit was reached",
                retryable=True, provider="openai_compatible",
            )
        if status in {500, 502, 503, 504}:
            return ReasonerTransportError(
                "ERR_LLM_SERVICE_UNAVAILABLE", "model service is temporarily unavailable",
                retryable=True, provider="openai_compatible",
            )
        return ReasonerTransportError(
            "ERR_LLM_REQUEST_REJECTED", "model service rejected the request",
            retryable=False, provider="openai_compatible",
        )

    def complete(self, request: LLMTransportRequest) -> LLMTransportResponse:
        if self.actual_request_count >= self._max_requests:
            raise ReasonerTransportError(
                "ERR_REAL_EVALUATION_BUDGET_EXCEEDED", "real model request budget was exhausted",
                retryable=False, provider="openai_compatible",
            )
        if request.model != self._config.model or request.base_url != self._config.base_url:
            raise ReasonerConfigurationError(
                "ERR_LLM_CONFIG_INVALID", "transport request does not match validated configuration",
                retryable=False, provider="llm",
            )
        messages = request.payload.get("messages")
        if not isinstance(messages, list):
            raise ReasonerConfigurationError(
                "ERR_LLM_CONFIG_INVALID", "transport messages payload is invalid",
                retryable=False, provider="llm",
            )
        payload = {
            "model": request.model,
            "messages": messages,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "max_tokens": self._config.max_output_tokens,
        }
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self._config.api_key}"}
        encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.actual_request_count += 1
        started = self._clock()
        try:
            raw = self._client.post(str(self._config.base_url), headers, encoded, request.timeout_seconds)
        finally:
            elapsed = max(0, (self._clock() - started) // 1_000_000)
            self.latencies_ms.append(elapsed)
        if raw.status_code < 200 or raw.status_code >= 300:
            raise self._status_error(raw.status_code)
        response = adapt_openai_compatible_response(
            raw.body, raw.headers, status_code=raw.status_code, model=request.model, latency_ms=elapsed
        )
        self.usages.append(response.usage)
        return response

