"""Central Reasoner Provider factory."""

from __future__ import annotations

import os
from typing import Mapping

from .base import Reasoner
from .config import (
    ENV_LLM_API_KEY,
    ENV_LLM_BASE_URL,
    ENV_LLM_MODEL,
    ENV_LLM_PROVIDER,

    ENV_LLM_REAL_CALL_ENABLED,
    LLMReasonerConfig,
)
from .errors import ReasonerConfigurationError
from .llm import LLMReasoner
from .stub import ReasonerStub
from .transport import LLMTransport, NotConfiguredTransport


def load_reasoner_config(*, provider_override: str | None = None) -> LLMReasonerConfig:
    """Load and validate Provider environment configuration in one boundary."""

    return LLMReasonerConfig.from_env(provider_override=provider_override)


def load_real_reasoner_config(
    *, cli_confirmed: bool, environ: Mapping[str, str] | None = None
) -> LLMReasonerConfig:
    """Validate both real-call opt-ins before any HTTP Transport can be created."""

    env = os.environ if environ is None else environ
    if not cli_confirmed:
        raise ReasonerConfigurationError(
            "ERR_REAL_MODEL_CONFIRMATION_REQUIRED", "--confirm-real-model is required",
            retryable=False, provider="llm",
        )
    if env.get(ENV_LLM_PROVIDER, "").strip().lower() != "llm":
        raise ReasonerConfigurationError(
            "ERR_REAL_MODEL_CALL_NOT_ENABLED", "LLM_PROVIDER=llm is required for real model calls",
            retryable=False, provider="llm",
        )
    enabled = env.get(ENV_LLM_REAL_CALL_ENABLED, "").strip().lower()
    if enabled not in {"true", "false", ""}:
        raise ReasonerConfigurationError(
            "ERR_REAL_MODEL_CALL_NOT_ENABLED", "LLM_REAL_CALL_ENABLED must be true or false",
            retryable=False, provider="llm",
        )
    if enabled != "true":
        raise ReasonerConfigurationError(
            "ERR_REAL_MODEL_CALL_NOT_ENABLED", "LLM_REAL_CALL_ENABLED=true is required",
            retryable=False, provider="llm",
        )
    for name, code in (
        (ENV_LLM_MODEL, "ERR_LLM_MODEL_MISSING"),
        (ENV_LLM_API_KEY, "ERR_LLM_API_KEY_MISSING"),
        (ENV_LLM_BASE_URL, "ERR_LLM_BASE_URL_MISSING"),
    ):
        if not env.get(name, "").strip():
            raise ReasonerConfigurationError(code, f"{name} is required", retryable=False, provider="llm")
    return LLMReasonerConfig.from_env(env)


def create_reasoner(
    config: LLMReasonerConfig,
    *,
    transport: LLMTransport | None = None,
    stub_mode: str = "valid",
) -> Reasoner:
    """Create exactly the configured provider without silent fallback."""

    if config.provider == "stub":
        return ReasonerStub(stub_mode)
    if config.provider == "llm":
        if not config.model or not config.api_key or not config.base_url:
            raise ReasonerConfigurationError(
                "ERR_LLM_CONFIG_MISSING",
                "LLM provider configuration is incomplete",
                retryable=False,
                provider="llm",
            )
        return LLMReasoner(config, transport or NotConfiguredTransport())
    raise ReasonerConfigurationError(
        "ERR_LLM_PROVIDER_UNSUPPORTED",
        "unsupported Reasoner Provider",
        retryable=False,
        provider=config.provider,
    )
