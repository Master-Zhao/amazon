"""Safe structured errors for Reasoner configuration and service boundaries."""

from __future__ import annotations


class ReasonerError(RuntimeError):
    """Base error whose string form is always safe to log."""

    def __init__(self, error_code: str, safe_message: str, *, retryable: bool, provider: str) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message
        self.retryable = retryable
        self.provider = provider

    def __str__(self) -> str:
        return f"{self.error_code}: {self.safe_message}"


class ReasonerConfigurationError(ReasonerError):
    """Non-retryable provider configuration error."""


class ReasonerTransportError(ReasonerError):
    """Retryable or terminal model-service transport error."""


class ReasonerTimeoutError(ReasonerTransportError):
    """Model-service timeout."""


class ReasonerResponseError(ReasonerError):
    """Non-retryable empty or malformed service response."""


class PromptError(ReasonerConfigurationError):
    """Fail-closed prompt loading or path validation error."""


class ReasonerOutputSchemaError(ReasonerResponseError):
    """Reasoner output Schema loading or validation error."""

    def __init__(
        self,
        error_code: str,
        safe_message: str,
        *,
        field_path: str = "$",
    ) -> None:
        super().__init__(error_code, safe_message, retryable=False, provider="llm")
        self.field_path = field_path


class ReasonerRetriesExhaustedError(ReasonerTransportError):
    """Network/service retry budget exhausted inside one agent attempt."""
