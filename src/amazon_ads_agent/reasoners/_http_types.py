"""Shared HTTP types and endpoint validation used by HTTP transports."""

from __future__ import annotations

import socket
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Mapping, Protocol
from urllib.parse import urlsplit

from .errors import ReasonerConfigurationError, ReasonerTimeoutError, ReasonerTransportError


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