"""Environment-only LLM provider configuration with secret-safe repr."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Mapping

from .errors import ReasonerConfigurationError

ENV_LLM_PROVIDER = "LLM_PROVIDER"
ENV_LLM_MODEL = "LLM_MODEL"
ENV_LLM_API_KEY = "LLM_API_KEY"
ENV_LLM_BASE_URL = "LLM_BASE_URL"
ENV_LLM_TIMEOUT_SECONDS = "LLM_TIMEOUT_SECONDS"
ENV_LLM_MAX_RETRIES = "LLM_MAX_RETRIES"
LLM_ENVIRONMENT_VARIABLES = (
    ENV_LLM_PROVIDER,
    ENV_LLM_MODEL,
    ENV_LLM_API_KEY,
    ENV_LLM_BASE_URL,
    ENV_LLM_TIMEOUT_SECONDS,
    ENV_LLM_MAX_RETRIES,
)


def _parse_integer(raw: str, name: str, *, minimum: int) -> int:
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise ReasonerConfigurationError(
            "ERR_LLM_CONFIG_INVALID", f"{name} must be an integer", retryable=False, provider="llm"
        ) from exc
    if value < minimum:
        raise ReasonerConfigurationError(
            "ERR_LLM_CONFIG_INVALID", f"{name} must be at least {minimum}", retryable=False, provider="llm"
        )
    return value


@dataclass(frozen=True)
class LLMReasonerConfig:
    """Validated provider config; API key is excluded from repr and safe views."""

    provider: str = "stub"
    model: str | None = None
    api_key: str | None = field(default=None, repr=False)
    base_url: str | None = None
    timeout_seconds: int = 30
    max_retries: int = 1

    @classmethod
    def from_env(
        cls,
        environ: Mapping[str, str] | None = None,
        *,
        provider_override: str | None = None,
    ) -> "LLMReasonerConfig":
        """Load centralized environment variables without logging their values."""

        env = os.environ if environ is None else environ
        provider = (provider_override or env.get(ENV_LLM_PROVIDER, "stub")).strip().lower()
        if provider not in {"stub", "llm"}:
            raise ReasonerConfigurationError(
                "ERR_LLM_PROVIDER_UNSUPPORTED",
                "LLM_PROVIDER must be either stub or llm",
                retryable=False,
                provider=provider or "unknown",
            )
        timeout = _parse_integer(env.get(ENV_LLM_TIMEOUT_SECONDS, "30"), ENV_LLM_TIMEOUT_SECONDS, minimum=1)
        retries = _parse_integer(env.get(ENV_LLM_MAX_RETRIES, "1"), ENV_LLM_MAX_RETRIES, minimum=0)
        model = env.get(ENV_LLM_MODEL) or None
        api_key = env.get(ENV_LLM_API_KEY) or None
        base_url = env.get(ENV_LLM_BASE_URL) or None
        if provider == "llm":
            missing = [
                name
                for name, value in (
                    (ENV_LLM_MODEL, model),
                    (ENV_LLM_API_KEY, api_key),
                    (ENV_LLM_BASE_URL, base_url),
                )
                if not value
            ]
            if missing:
                raise ReasonerConfigurationError(
                    "ERR_LLM_CONFIG_MISSING",
                    f"missing required LLM configuration fields: {', '.join(missing)}",
                    retryable=False,
                    provider="llm",
                )
        return cls(provider, model, api_key, base_url, timeout, retries)

    def safe_description(self) -> dict[str, str | int | bool | None]:
        """Return non-sensitive metadata suitable for audit and diagnostics."""

        return {
            "provider": self.provider,
            "model": self.model,
            "base_url_configured": self.base_url is not None,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "api_key_configured": self.api_key is not None,
        }
