"""Transport router: select MaaS or OpenAI-compatible transport by endpoint domain."""

from __future__ import annotations

from urllib.parse import urlsplit

from .config import LLMReasonerConfig
from .http_transport import HTTPClient, OpenAICompatibleHTTPTransport
from .transport import LLMTransport

_MAAS_HOST = "api.modelarts-maas.com"


def is_maas_endpoint(base_url: str) -> bool:
    try:
        parsed = urlsplit(base_url)
        return bool(parsed.hostname and _MAAS_HOST in parsed.hostname)
    except Exception:
        return False


def create_transport(
    config: LLMReasonerConfig,
    *,
    client: HTTPClient | None = None,
    max_requests: int = 60,
    provider_name: str | None = None,
) -> LLMTransport:
    effective_name = provider_name or config.provider_name
    if is_maas_endpoint(config.base_url or ""):
        from .maas_transport import MaaSHTTPTransport
        return MaaSHTTPTransport(config, client=client, max_requests=max_requests, provider_name=effective_name)
    return OpenAICompatibleHTTPTransport(config, client=client, max_requests=max_requests, provider_name=effective_name)