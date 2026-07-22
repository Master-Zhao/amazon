"""Base HTTP transport with shared logic for OpenAI-compatible and MaaS transports."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from time import monotonic_ns
from typing import Callable, Mapping

from .config import LLMReasonerConfig
from .errors import ReasonerConfigurationError, ReasonerTransportError
from ._http_types import HTTPClient, UrllibHTTPClient, _validate_endpoint
from .transport import LLMTransportRequest, LLMTransportResponse


class BaseHTTPTransport(ABC):
    """Abstract base for HTTP transports with shared budget, validation, and status mapping."""

    def __init__(
        self,
        config: LLMReasonerConfig,
        *,
        client: HTTPClient | None = None,
        max_requests: int = 60,
        clock: Callable[[], int] = monotonic_ns,
        provider_name: str | None = None,
        default_provider_name: str = "http",
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
        self._provider_name = provider_name or getattr(config, "provider_name", default_provider_name)
        self.actual_request_count = 0
        self.latencies_ms: list[int] = []
        self.usages: list[Mapping[str, int] | None] = []

    def _status_error(self, status: int) -> ReasonerTransportError:
        if status == 401:
            return ReasonerTransportError(
                "ERR_LLM_AUTHENTICATION_FAILED", "model service authentication failed",
                retryable=False, provider=self._provider_name,
            )
        if status == 403:
            return ReasonerTransportError(
                "ERR_LLM_PERMISSION_DENIED", "model service permission was denied",
                retryable=False, provider=self._provider_name,
            )
        if status == 429:
            return ReasonerTransportError(
                "ERR_LLM_RATE_LIMITED", "model service rate limit was reached",
                retryable=True, provider=self._provider_name,
            )
        if status in {500, 502, 503, 504}:
            return ReasonerTransportError(
                "ERR_LLM_SERVICE_UNAVAILABLE", "model service is temporarily unavailable",
                retryable=True, provider=self._provider_name,
            )
        return ReasonerTransportError(
            "ERR_LLM_REQUEST_REJECTED", "model service rejected the request",
            retryable=False, provider=self._provider_name,
        )

    def _validate_request(self, request: LLMTransportRequest) -> None:
        if self.actual_request_count >= self._max_requests:
            raise ReasonerTransportError(
                "ERR_REAL_EVALUATION_BUDGET_EXCEEDED", "real model request budget was exhausted",
                retryable=False, provider=self._provider_name,
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

    @abstractmethod
    def _build_payload(self, request: LLMTransportRequest) -> dict:
        ...

    @abstractmethod
    def _adapt_response(self, raw, elapsed: int, request: LLMTransportRequest) -> LLMTransportResponse:
        ...

    def complete(self, request: LLMTransportRequest) -> LLMTransportResponse:
        self._validate_request(request)
        payload = self._build_payload(request)
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
        response = self._adapt_response(raw, elapsed, request)
        self.usages.append(response.usage)
        return response