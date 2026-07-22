"""Transport routing and MaaS endpoint detection tests."""

from __future__ import annotations

import pytest

from amazon_ads_agent.reasoners.config import LLMReasonerConfig
from amazon_ads_agent.reasoners.http_transport import OpenAICompatibleHTTPTransport
from amazon_ads_agent.reasoners.maas_transport import MaaSHTTPTransport
from amazon_ads_agent.reasoners.transport_router import create_transport, is_maas_endpoint

FAKE_KEY = "test-only-not-a-real-key"


class TestIsMaaSEndpoint:
    def test_maas_endpoint_returns_true(self) -> None:
        assert is_maas_endpoint("https://api.modelarts-maas.com/plan/v2") is True

    def test_maas_endpoint_with_path(self) -> None:
        assert is_maas_endpoint("https://api.modelarts-maas.com/v1/chat/completions") is True

    def test_non_maas_endpoint_returns_false(self) -> None:
        assert is_maas_endpoint("https://open.bigmodel.cn/api/paas/v4/chat/completions") is False

    def test_localhost_returns_false(self) -> None:
        assert is_maas_endpoint("http://localhost:8080/v1") is False

    def test_empty_string_returns_false(self) -> None:
        assert is_maas_endpoint("") is False

    def test_invalid_url_returns_false(self) -> None:
        assert is_maas_endpoint("not-a-url") is False

    def test_none_like_returns_false(self) -> None:
        assert is_maas_endpoint("://missing-scheme") is False


class TestCreateTransport:
    def _maas_config(self) -> LLMReasonerConfig:
        return LLMReasonerConfig(
            "llm", "GLM-5.1", FAKE_KEY,
            "https://api.modelarts-maas.com/plan/v2", 5, 0, True, 512, "maas",
        )

    def _openai_config(self) -> LLMReasonerConfig:
        return LLMReasonerConfig(
            "llm", "test-model", FAKE_KEY,
            "https://open.bigmodel.cn/api/paas/v4/chat/completions", 5, 0, True, 512, "glm",
        )

    def test_maas_endpoint_creates_maas_transport(self) -> None:
        transport = create_transport(self._maas_config())
        assert isinstance(transport, MaaSHTTPTransport)

    def test_openai_endpoint_creates_openai_transport(self) -> None:
        transport = create_transport(self._openai_config())
        assert isinstance(transport, OpenAICompatibleHTTPTransport)

    def test_maas_transport_provider_name(self) -> None:
        transport = create_transport(self._maas_config())
        assert transport._provider_name == "maas"

    def test_openai_transport_provider_name(self) -> None:
        transport = create_transport(self._openai_config())
        assert transport._provider_name == "glm"

    def test_explicit_provider_name_overrides(self) -> None:
        transport = create_transport(self._maas_config(), provider_name="custom")
        assert transport._provider_name == "custom"