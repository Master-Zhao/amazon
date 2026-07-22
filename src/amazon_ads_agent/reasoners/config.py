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
ENV_LLM_REAL_CALL_ENABLED = "LLM_REAL_CALL_ENABLED"
ENV_LLM_MAX_OUTPUT_TOKENS = "LLM_MAX_OUTPUT_TOKENS"
ENV_LLM_PROVIDER_NAME = "LLM_PROVIDER_NAME"
LLM_ENVIRONMENT_VARIABLES = (
    ENV_LLM_PROVIDER,
    ENV_LLM_MODEL,
    ENV_LLM_API_KEY,
    ENV_LLM_BASE_URL,
    ENV_LLM_TIMEOUT_SECONDS,
    ENV_LLM_MAX_RETRIES,
    ENV_LLM_REAL_CALL_ENABLED,
    ENV_LLM_MAX_OUTPUT_TOKENS,
    ENV_LLM_PROVIDER_NAME,
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
    real_call_enabled: bool = False
    max_output_tokens: int = 1024
    provider_name: str = "glm"

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
        if provider == "stub":
            return cls(provider="stub", provider_name="glm")
        timeout = _parse_integer(env.get(ENV_LLM_TIMEOUT_SECONDS, "30"), ENV_LLM_TIMEOUT_SECONDS, minimum=1)
        retries = _parse_integer(env.get(ENV_LLM_MAX_RETRIES, "1"), ENV_LLM_MAX_RETRIES, minimum=0)
        real_call_raw = env.get(ENV_LLM_REAL_CALL_ENABLED, "false").strip().lower()
        if real_call_raw not in {"true", "false"}:
            raise ReasonerConfigurationError(
                "ERR_REAL_MODEL_CALL_NOT_ENABLED",
                "LLM_REAL_CALL_ENABLED must be true or false",
                retryable=False,
                provider="llm",
            )
        max_output_tokens = _parse_integer(
            env.get(ENV_LLM_MAX_OUTPUT_TOKENS, "1024"), ENV_LLM_MAX_OUTPUT_TOKENS, minimum=1
        )
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
        explicit_provider_name = (env.get(ENV_LLM_PROVIDER_NAME) or "").strip()
        if explicit_provider_name:
            provider_name = explicit_provider_name
        else:
            from .transport_router import is_maas_endpoint
            provider_name = "maas" if is_maas_endpoint(base_url or "") else "glm"
        return cls(provider, model, api_key, base_url, timeout, retries, real_call_raw == "true", max_output_tokens, provider_name)

    def safe_description(self) -> dict[str, str | int | bool | None]:
        """Return non-sensitive metadata suitable for audit and diagnostics."""

        return {
            "provider": self.provider,
            "model": self.model,
            "base_url_configured": self.base_url is not None,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "real_call_enabled": self.real_call_enabled,
            "max_output_tokens": self.max_output_tokens,
            "api_key_configured": self.api_key is not None,
            "provider_name": self.provider_name,
        }
