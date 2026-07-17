"""Central Reasoner Provider factory."""

from __future__ import annotations

from .base import Reasoner
from .config import LLMReasonerConfig
from .errors import ReasonerConfigurationError
from .llm import LLMReasoner
from .stub import ReasonerStub
from .transport import LLMTransport, NotConfiguredTransport


def load_reasoner_config(*, provider_override: str | None = None) -> LLMReasonerConfig:
    """Load and validate Provider environment configuration in one boundary."""

    return LLMReasonerConfig.from_env(provider_override=provider_override)


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
