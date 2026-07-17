"""LLM Reasoner engineering skeleton using an injected offline-safe Transport."""

from __future__ import annotations

import json
import re
from typing import Any

from .base import ReasonerInput, ReasonerResult, to_plain_data
from .config import LLMReasonerConfig
from .errors import (
    ReasonerResponseError,
    ReasonerRetriesExhaustedError,
    ReasonerTimeoutError,
    ReasonerTransportError,
)
from .transport import LLMTransport, LLMTransportRequest, LLMTransportResponse

PLACEHOLDER_SYSTEM_MESSAGE = "provider-contract-placeholder"
PLACEHOLDER_NOTICE = (
    "This message only verifies Provider and Transport integration; "
    "it is not the formal model prompt."
)


class LLMReasoner:
    """Convert immutable inputs to raw Transport calls and parse test JSON."""

    def __init__(self, config: LLMReasonerConfig, transport: LLMTransport) -> None:
        self.config = config
        self.transport = transport
        self.call_count = 0
        self.last_transport_retry_count = 0

    def _request(self, reasoner_input: ReasonerInput) -> LLMTransportRequest:
        payload = {
            "messages": [
                {"role": "system", "content": PLACEHOLDER_SYSTEM_MESSAGE},
                {
                    "role": "user",
                    "content": json.dumps(to_plain_data(reasoner_input), ensure_ascii=False, sort_keys=True),
                },
            ],
            "notice": PLACEHOLDER_NOTICE,
        }
        return LLMTransportRequest(
            model=str(self.config.model),
            base_url=str(self.config.base_url),
            timeout_seconds=self.config.timeout_seconds,
            payload=payload,
            request_metadata={
                "task_id": reasoner_input.task_id,
                "run_id": reasoner_input.run_id,
                "attempt_id": reasoner_input.attempt_id,
                "plan_version": reasoner_input.plan_version,
            },
        )

    def _complete_with_retries(self, request: LLMTransportRequest) -> LLMTransportResponse:
        self.last_transport_retry_count = 0
        last_error: ReasonerTransportError | None = None
        for attempt in range(self.config.max_retries + 1):
            try:
                response = self.transport.complete(request)
                if response.status_code >= 500:
                    raise ReasonerTransportError(
                        "ERR_LLM_TRANSPORT_FAILED",
                        "model service returned a temporary server error",
                        retryable=True,
                        provider="llm",
                    )
                if response.status_code >= 400:
                    raise ReasonerTransportError(
                        "ERR_LLM_TRANSPORT_FAILED",
                        "model service rejected the request",
                        retryable=False,
                        provider="llm",
                    )
                return response
            except TimeoutError as exc:
                last_error = ReasonerTimeoutError(
                    "ERR_LLM_TIMEOUT", "model service request timed out", retryable=True, provider="llm"
                )
                last_error.__cause__ = exc
            except ReasonerTimeoutError as exc:
                last_error = exc
            except ReasonerTransportError as exc:
                last_error = exc
            except OSError as exc:
                last_error = ReasonerTransportError(
                    "ERR_LLM_TRANSPORT_FAILED", "model service transport failed", retryable=True, provider="llm"
                )
                last_error.__cause__ = exc
            if last_error is not None and (not last_error.retryable or attempt >= self.config.max_retries):
                break
            self.last_transport_retry_count += 1

        assert last_error is not None
        if self.config.max_retries > 0 and last_error.retryable:
            raise ReasonerRetriesExhaustedError(
                "ERR_LLM_RETRIES_EXHAUSTED",
                f"model service retries exhausted after {self.last_transport_retry_count} retries",
                retryable=False,
                provider="llm",
            ) from last_error
        raise last_error

    @staticmethod
    def _parse(response: LLMTransportResponse) -> ReasonerResult:
        if re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", response.request_id) is None:
            raise ReasonerResponseError(
                "ERR_LLM_RESPONSE_INVALID", "model service request_id is invalid", retryable=False, provider="llm"
            )
        if not response.body.strip():
            raise ReasonerResponseError(
                "ERR_LLM_RESPONSE_EMPTY", "model service returned an empty response", retryable=False, provider="llm"
            )
        try:
            document: Any = json.loads(response.body)
        except json.JSONDecodeError as exc:
            raise ReasonerResponseError(
                "ERR_LLM_RESPONSE_INVALID", "model service response is not valid JSON", retryable=False, provider="llm"
            ) from exc
        required = {"selected_value", "reason", "evidence_paths", "risk_summary"}
        if not isinstance(document, dict) or set(document) != required:
            raise ReasonerResponseError(
                "ERR_LLM_RESPONSE_INVALID",
                "model service response fields do not match the Provider contract",
                retryable=False,
                provider="llm",
            )
        if not isinstance(document["selected_value"], str) or re.fullmatch(
            r"^(0|[1-9][0-9]*)(\.[0-9]+)?$", document["selected_value"]
        ) is None:
            raise ReasonerResponseError(
                "ERR_LLM_RESPONSE_INVALID", "selected_value must be a Decimal string", retryable=False, provider="llm"
            )
        if not isinstance(document["reason"], str) or not isinstance(document["risk_summary"], str):
            raise ReasonerResponseError(
                "ERR_LLM_RESPONSE_INVALID", "reason and risk_summary must be strings", retryable=False, provider="llm"
            )
        paths = document["evidence_paths"]
        if not isinstance(paths, list) or not paths or not all(isinstance(path, str) for path in paths):
            raise ReasonerResponseError(
                "ERR_LLM_RESPONSE_INVALID", "evidence_paths must be a non-empty string array", retryable=False, provider="llm"
            )
        return ReasonerResult(
            selected_value=document["selected_value"],
            reason=document["reason"],
            evidence_paths=tuple(paths),
            risk_summary=document["risk_summary"],
            provider="llm",
            model="",
            request_id=response.request_id,
        )

    def reason(self, reasoner_input: ReasonerInput) -> ReasonerResult:
        """Perform one agent reasoning call with internal service retries only."""

        self.call_count += 1
        response = self._complete_with_retries(self._request(reasoner_input))
        parsed = self._parse(response)
        return ReasonerResult(
            selected_value=parsed.selected_value,
            reason=parsed.reason,
            evidence_paths=parsed.evidence_paths,
            risk_summary=parsed.risk_summary,
            provider="llm",
            model=str(self.config.model),
            request_id=parsed.request_id,
        )
