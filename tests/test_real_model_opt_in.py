"""Double opt-in and real-evaluation budget tests."""

from __future__ import annotations

import pytest

from amazon_ads_agent.reasoners.config import LLMReasonerConfig
from amazon_ads_agent.reasoners.errors import ReasonerConfigurationError
from amazon_ads_agent.reasoners.provider import load_real_reasoner_config
from evaluation.models import EvaluationError
from evaluation.real_config import RealEvaluationConfig

FAKE_KEY = "test-only-not-a-real-key"


def _env(**overrides: str) -> dict[str, str]:
    values = {
        "LLM_PROVIDER": "llm", "LLM_REAL_CALL_ENABLED": "true", "LLM_MODEL": "test-model",
        "LLM_API_KEY": FAKE_KEY, "LLM_BASE_URL": "https://model.invalid/v1/chat/completions",
        "LLM_TIMEOUT_SECONDS": "5", "LLM_MAX_RETRIES": "1", "LLM_MAX_OUTPUT_TOKENS": "512",
    }
    values.update(overrides)
    return values


def test_default_real_call_is_disabled() -> None:
    assert LLMReasonerConfig.from_env({}).real_call_enabled is False


def test_environment_opt_in_without_cli_confirmation_fails() -> None:
    with pytest.raises(ReasonerConfigurationError) as caught:
        load_real_reasoner_config(cli_confirmed=False, environ=_env())
    assert caught.value.error_code == "ERR_REAL_MODEL_CONFIRMATION_REQUIRED"


def test_cli_confirmation_without_environment_opt_in_fails() -> None:
    with pytest.raises(ReasonerConfigurationError) as caught:
        load_real_reasoner_config(cli_confirmed=True, environ=_env(LLM_REAL_CALL_ENABLED="false"))
    assert caught.value.error_code == "ERR_REAL_MODEL_CALL_NOT_ENABLED"


def test_double_opt_in_loads_complete_config() -> None:
    config = load_real_reasoner_config(cli_confirmed=True, environ=_env())
    assert config.provider == "llm" and config.real_call_enabled is True
    assert config.max_output_tokens == 512


@pytest.mark.parametrize(
    ("missing", "code"),
    [
        ("LLM_MODEL", "ERR_LLM_MODEL_MISSING"),
        ("LLM_API_KEY", "ERR_LLM_API_KEY_MISSING"),
        ("LLM_BASE_URL", "ERR_LLM_BASE_URL_MISSING"),
    ],
)
def test_missing_real_configuration_fails_with_stable_code(missing: str, code: str) -> None:
    env = _env()
    del env[missing]
    with pytest.raises(ReasonerConfigurationError) as caught:
        load_real_reasoner_config(cli_confirmed=True, environ=env)
    assert caught.value.error_code == code
    assert FAKE_KEY not in str(caught.value)


@pytest.mark.parametrize("provider", ["", "stub", "fake", "unknown"])
def test_non_llm_provider_cannot_enable_real_calls(provider: str) -> None:
    with pytest.raises(ReasonerConfigurationError, match="ERR_REAL_MODEL_CALL_NOT_ENABLED"):
        load_real_reasoner_config(cli_confirmed=True, environ=_env(LLM_PROVIDER=provider))


@pytest.mark.parametrize("value", ["yes", "1", "truth", "enabled"])
def test_invalid_real_call_boolean_fails(value: str) -> None:
    with pytest.raises(ReasonerConfigurationError, match="ERR_REAL_MODEL_CALL_NOT_ENABLED"):
        load_real_reasoner_config(cli_confirmed=True, environ=_env(LLM_REAL_CALL_ENABLED=value))


def test_stub_mode_does_not_read_real_credentials() -> None:
    config = LLMReasonerConfig.from_env({"LLM_PROVIDER": "stub", "LLM_API_KEY": FAKE_KEY})
    assert config.api_key is None
    assert FAKE_KEY not in repr(config)


def test_stub_ignores_invalid_real_only_settings() -> None:
    config = LLMReasonerConfig.from_env({
        "LLM_PROVIDER": "stub", "LLM_REAL_CALL_ENABLED": "invalid", "LLM_MAX_OUTPUT_TOKENS": "invalid"
    })
    assert config.provider == "stub" and config.real_call_enabled is False


def test_real_budget_defaults_are_bounded() -> None:
    assert RealEvaluationConfig.from_env({}) == RealEvaluationConfig(60, 3, 1, 3)


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("REAL_EVALUATION_MAX_REQUESTS", "0"),
        ("REAL_EVALUATION_MAX_AGENT_REVISIONS", "4"),
        ("REAL_EVALUATION_MAX_TRANSPORT_RETRIES", "-1"),
        ("REAL_EVALUATION_REPETITIONS", "0"),
        ("REAL_EVALUATION_REPETITIONS", "1.5"),
    ],
)
def test_invalid_real_budget_fails_closed(name: str, value: str) -> None:
    with pytest.raises(EvaluationError, match="ERR_REAL_EVALUATION_CONFIG_INVALID"):
        RealEvaluationConfig.from_env({name: value})


def test_transport_retry_budget_is_enforced() -> None:
    with pytest.raises(EvaluationError, match="ERR_REAL_EVALUATION_CONFIG_INVALID"):
        RealEvaluationConfig(max_transport_retries=1).validate_transport_retries(2)


def test_transport_retry_budget_accepts_equal_value() -> None:
    RealEvaluationConfig(max_transport_retries=1).validate_transport_retries(1)
