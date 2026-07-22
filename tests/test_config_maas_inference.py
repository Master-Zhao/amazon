"""Config provider_name auto-inference tests for MaaS endpoints."""

from __future__ import annotations

from amazon_ads_agent.reasoners.config import LLMReasonerConfig

FAKE_KEY = "test-only-not-a-real-key"


def _env(**overrides) -> dict[str, str]:
    values = {
        "LLM_PROVIDER": "llm",
        "LLM_REAL_CALL_ENABLED": "true",
        "LLM_MODEL": "GLM-5.1",
        "LLM_API_KEY": FAKE_KEY,
        "LLM_BASE_URL": "https://api.modelarts-maas.com/plan/v2",
        "LLM_TIMEOUT_SECONDS": "5",
        "LLM_MAX_RETRIES": "1",
        "LLM_MAX_OUTPUT_TOKENS": "512",
    }
    values.update(overrides)
    return values


def test_maas_endpoint_auto_infers_provider_name() -> None:
    config = LLMReasonerConfig.from_env(_env())
    assert config.provider_name == "maas"


def test_non_maas_endpoint_defaults_to_glm() -> None:
    config = LLMReasonerConfig.from_env(_env(LLM_BASE_URL="https://open.bigmodel.cn/api/paas/v4/chat/completions"))
    assert config.provider_name == "glm"


def test_explicit_provider_name_overrides_auto_inference() -> None:
    config = LLMReasonerConfig.from_env(_env(LLM_PROVIDER_NAME="custom_provider"))
    assert config.provider_name == "custom_provider"


def test_explicit_glm_overrides_maas_inference() -> None:
    config = LLMReasonerConfig.from_env(_env(LLM_PROVIDER_NAME="glm"))
    assert config.provider_name == "glm"


def test_stub_mode_not_affected_by_maas_inference() -> None:
    config = LLMReasonerConfig.from_env({"LLM_PROVIDER": "stub"})
    assert config.provider_name == "glm"


def test_maas_endpoint_with_empty_provider_name_uses_inference() -> None:
    config = LLMReasonerConfig.from_env(_env(LLM_PROVIDER_NAME=""))
    assert config.provider_name == "maas"