"""Model-service transport protocol and deterministic offline transports."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol

from .errors import ReasonerTransportError


@dataclass(frozen=True)
class LLMTransportRequest:
    """Credential-free request passed to an injected model transport."""

    model: str
    base_url: str
    timeout_seconds: int
    payload: Mapping[str, Any]
    request_metadata: Mapping[str, str | int | bool | None]


@dataclass(frozen=True)
class LLMTransportResponse:
    """Raw model-service response; business parsing happens elsewhere."""

    request_id: str
    status_code: int
    body: str
    usage: Mapping[str, int] = field(default_factory=dict)


class LLMTransport(Protocol):
    """Transport-only model service boundary."""

    def complete(self, request: LLMTransportRequest) -> LLMTransportResponse:
        """Return a raw response or raise a structured transport error."""


class FakeTransport:
    """Programmable offline transport that records calls and never uses network."""

    def __init__(self, outcomes: list[LLMTransportResponse | Exception] | None = None) -> None:
        self._outcomes = list(outcomes or [])
        self.call_count = 0
        self.last_request: LLMTransportRequest | None = None

    def complete(self, request: LLMTransportRequest) -> LLMTransportResponse:
        self.call_count += 1
        self.last_request = request
        if not self._outcomes:
            raise ReasonerTransportError(
                "ERR_LLM_TRANSPORT_FAILED",
                "Fake Transport has no programmed response",
                retryable=False,
                provider="llm",
            )
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class NotConfiguredTransport:
    """Fail-closed placeholder; it cannot access network."""

    def complete(self, request: LLMTransportRequest) -> LLMTransportResponse:
        raise ReasonerTransportError(
            "ERR_LLM_TRANSPORT_FAILED",
            "no LLM Transport implementation was injected",
            retryable=False,
            provider="llm",
        )
