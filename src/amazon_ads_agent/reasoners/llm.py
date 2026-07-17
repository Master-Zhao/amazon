"""Strict structured-output LLM Reasoner using an injected offline-safe Transport."""

from __future__ import annotations

import json
import re
from typing import Any

from .base import ReasonerInput, ReasonerResult
from .config import LLMReasonerConfig
from .errors import (
    ReasonerResponseError,
    ReasonerRetriesExhaustedError,
    ReasonerTimeoutError,
    ReasonerTransportError,
)
from .output_schema import validate_reasoner_output
from .prompt_builder import PromptBuilder
from .transport import LLMTransport, LLMTransportRequest, LLMTransportResponse


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-standard JSON constant: {value}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    document: dict[str, Any] = {}
    for key, value in pairs:
        if key in document:
            raise ValueError("duplicate JSON object key")
        document[key] = value
    return document


class LLMReasoner:
    """Build formal messages, call Transport, and strictly validate pure JSON."""

    def __init__(
        self,
        config: LLMReasonerConfig,
        transport: LLMTransport,
        *,
        prompt_builder: PromptBuilder | None = None,
    ) -> None:
        self.config = config
        self.transport = transport
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.call_count = 0
        self.last_transport_retry_count = 0
        self.last_prompt_metadata: dict[str, str | bool] = {}
        self.last_response_received = False
        self.last_schema_field_path: str | None = None
        self.attempt_history: list[dict[str, Any]] = []
        self.response_metadata: list[dict[str, Any]] = []

    def _request(self, reasoner_input: ReasonerInput) -> LLMTransportRequest:
        messages = self.prompt_builder.build(reasoner_input)
        self.last_prompt_metadata = {
            "template_version": self.prompt_builder.TEMPLATE_VERSION,
            "system_template": "reasoner-system.md",
            "scenario_template": "keyword-bid-optimization.md",
            "revision_template_added": reasoner_input.previous_failure is not None,
        }
        return LLMTransportRequest(
            model=str(self.config.model),
            base_url=str(self.config.base_url),
            timeout_seconds=self.config.timeout_seconds,
            payload={
                "messages": messages,
                "response_contract": "reasoner-output.schema.json",
            },
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
            document = json.loads(
                response.body,
                object_pairs_hook=_unique_object,
                parse_constant=_reject_constant,
            )
        except (json.JSONDecodeError, ValueError) as exc:
            raise ReasonerResponseError(
                "ERR_LLM_RESPONSE_INVALID",
                "model service response is not one strict JSON object",
                retryable=False,
                provider="llm",
            ) from exc
        validated = validate_reasoner_output(document)
        return ReasonerResult(
            selected_value=validated["selected_value"],
            reason=validated["reason"],
            evidence_paths=tuple(validated["evidence_paths"]),
            risk_summary=validated["risk_summary"],
            provider="llm",
            model="",
            request_id=response.request_id,
            model_confidence=validated["confidence"],
        )

    def reason(self, reasoner_input: ReasonerInput) -> ReasonerResult:
        """Perform one reasoning call; service retries remain inside this call."""

        self.call_count += 1
        self.last_response_received = False
        self.last_schema_field_path = None
        request = self._request(reasoner_input)
        try:
            response = self._complete_with_retries(request)
        except ReasonerTransportError:
            self.attempt_history.append({"json_passed": False, "schema_passed": False, "response_received": False})
            raise
        self.last_response_received = True
        self.response_metadata.append(
            {
                "request_id": response.request_id,
                "latency_ms": response.latency_ms,
                "usage": None if response.usage is None else dict(response.usage),
                "provider": response.provider,
                "model": response.model,
            }
        )
        try:
            parsed = self._parse(response)
        except ReasonerResponseError as exc:
            self.last_schema_field_path = getattr(exc, "field_path", None)
            json_passed = exc.error_code not in {"ERR_LLM_RESPONSE_EMPTY", "ERR_LLM_RESPONSE_INVALID"}
            self.attempt_history.append(
                {"json_passed": json_passed, "schema_passed": False, "response_received": True}
            )
            raise
        self.attempt_history.append({"json_passed": True, "schema_passed": True, "response_received": True})
        return ReasonerResult(
            selected_value=parsed.selected_value,
            reason=parsed.reason,
            evidence_paths=parsed.evidence_paths,
            risk_summary=parsed.risk_summary,
            provider="llm",
            model=str(self.config.model),
            request_id=parsed.request_id,
            model_confidence=parsed.model_confidence,
        )
