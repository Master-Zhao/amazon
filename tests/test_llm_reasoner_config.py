"""Environment configuration and credential-safety tests."""

from __future__ import annotations

import pytest

from amazon_ads_agent.reasoners.config import LLMReasonerConfig, LLM_ENVIRONMENT_VARIABLES
from amazon_ads_agent.reasoners.errors import ReasonerConfigurationError

FAKE_KEY = "test-only-not-a-real-key"


def _llm_env(**overrides: str) -> dict[str, str]:
    values = {
        "LLM_PROVIDER": "llm",
        "LLM_MODEL": "test-model",
        "LLM_API_KEY": FAKE_KEY,
        "LLM_BASE_URL": "https://model.invalid/v1",
        "LLM_TIMEOUT_SECONDS": "30",
        "LLM_MAX_RETRIES": "1",
    }
    values.update(overrides)
    return values


def test_default_provider_is_stub() -> None:
    config = LLMReasonerConfig.from_env({})
    assert config.provider == "stub"


def test_stub_does_not_require_key() -> None:
    assert LLMReasonerConfig.from_env({"LLM_PROVIDER": "stub"}).api_key is None


def test_llm_complete_config_is_loaded() -> None:
    config = LLMReasonerConfig.from_env(_llm_env())
    assert (config.provider, config.model, config.timeout_seconds, config.max_retries) == ("llm", "test-model", 30, 1)


def test_provider_override_has_precedence() -> None:
    assert LLMReasonerConfig.from_env({"LLM_PROVIDER": "llm"}, provider_override="stub").provider == "stub"


@pytest.mark.parametrize("provider", ["unknown", "", "openai", "STUBB"])
def test_unsupported_provider_fails(provider: str) -> None:
    with pytest.raises(ReasonerConfigurationError) as caught:
        LLMReasonerConfig.from_env({"LLM_PROVIDER": provider})
    assert caught.value.error_code == "ERR_LLM_PROVIDER_UNSUPPORTED"


@pytest.mark.parametrize("missing", ["LLM_MODEL", "LLM_API_KEY", "LLM_BASE_URL"])
def test_llm_missing_required_field_fails(missing: str) -> None:
    env = _llm_env()
    del env[missing]
    with pytest.raises(ReasonerConfigurationError) as caught:
        LLMReasonerConfig.from_env(env)
    assert caught.value.error_code == "ERR_LLM_CONFIG_MISSING"
    assert FAKE_KEY not in str(caught.value)


@pytest.mark.parametrize("raw", ["0", "-1", "1.5", "nope"])
def test_timeout_must_be_positive_integer(raw: str) -> None:
    with pytest.raises(ReasonerConfigurationError) as caught:
        LLMReasonerConfig.from_env(_llm_env(LLM_TIMEOUT_SECONDS=raw))
    assert caught.value.error_code == "ERR_LLM_CONFIG_INVALID"


@pytest.mark.parametrize("raw", ["-1", "1.5", "nope"])
def test_retries_must_be_non_negative_integer(raw: str) -> None:
    with pytest.raises(ReasonerConfigurationError) as caught:
        LLMReasonerConfig.from_env(_llm_env(LLM_MAX_RETRIES=raw))
    assert caught.value.error_code == "ERR_LLM_CONFIG_INVALID"


def test_zero_retries_is_valid() -> None:
    assert LLMReasonerConfig.from_env(_llm_env(LLM_MAX_RETRIES="0")).max_retries == 0


def test_api_key_is_absent_from_repr_and_safe_description() -> None:
    config = LLMReasonerConfig.from_env(_llm_env())
    assert FAKE_KEY not in repr(config)
    assert FAKE_KEY not in repr(config.safe_description())
    assert config.safe_description()["api_key_configured"] is True


def test_environment_names_are_centralized() -> None:
    assert set(LLM_ENVIRONMENT_VARIABLES) == {
        "LLM_PROVIDER", "LLM_MODEL", "LLM_API_KEY", "LLM_BASE_URL", "LLM_TIMEOUT_SECONDS", "LLM_MAX_RETRIES",
        "LLM_REAL_CALL_ENABLED", "LLM_MAX_OUTPUT_TOKENS", "LLM_PROVIDER_NAME",
    }


def test_llm_provider_name_defaults_to_glm() -> None:
    config = LLMReasonerConfig.from_env(_llm_env())
    assert config.provider_name == "glm"


def test_llm_provider_name_from_env() -> None:
    config = LLMReasonerConfig.from_env(_llm_env(LLM_PROVIDER_NAME="custom_provider"))
    assert config.provider_name == "custom_provider"


def test_stub_provider_name_defaults_to_glm() -> None:
    config = LLMReasonerConfig.from_env({"LLM_PROVIDER": "stub"})
    assert config.provider_name == "glm"


def test_safe_description_includes_provider_name() -> None:
    config = LLMReasonerConfig.from_env(_llm_env())
    desc = config.safe_description()
    assert "provider_name" in desc
    assert desc["provider_name"] == "glm"
