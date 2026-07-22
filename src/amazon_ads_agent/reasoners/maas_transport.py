"""Explicitly enabled Huawei Cloud ModelArts MaaS HTTP transport."""

from __future__ import annotations

from .base_http_transport import BaseHTTPTransport
from .config import LLMReasonerConfig
from .maas_response_adapter import adapt_maas_response
from .transport import LLMTransportRequest, LLMTransportResponse


class MaaSHTTPTransport(BaseHTTPTransport):
    """Huawei Cloud ModelArts MaaS API transport; no provider guessing or fallback."""

    def __init__(self, config: LLMReasonerConfig, **kwargs) -> None:
        super().__init__(config, default_provider_name="maas", **kwargs)

    def __repr__(self) -> str:
        return (
            f"MaaSHTTPTransport(model={self._config.model!r}, "
            f"base_url_configured=True, max_requests={self._max_requests})"
        )

    def _build_payload(self, request: LLMTransportRequest) -> dict:
        return {
            "model": request.model,
            "messages": request.payload.get("messages"),
            "temperature": 0,
            "max_tokens": self._config.max_output_tokens,
        }

    def _adapt_response(self, raw, elapsed: int, request: LLMTransportRequest) -> LLMTransportResponse:
        return adapt_maas_response(
            raw.body, raw.headers, status_code=raw.status_code, model=request.model, latency_ms=elapsed,
            provider_name=self._provider_name,
        )
