"""Small secret-redaction helpers for model-service diagnostics."""

from __future__ import annotations

import re
from urllib.parse import urlsplit

_SENSITIVE = re.compile(
    r"(?i)(api[_ -]?key|bearer(?: token)?|authorization|access_token|refresh_token|secret|password)"
    r"\s*[:=]\s*(?:bearer\s+)?[^\s,;]+"
)
_BEARER = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~-]+")


def redact_sensitive(value: str) -> str:
    """Redact common credential assignments without retaining their values."""

    redacted = _SENSITIVE.sub(lambda match: f"{match.group(1)}=[REDACTED]", value)
    return _BEARER.sub("Bearer [REDACTED]", redacted)


def safe_base_url_host(value: str) -> str:
    """Return only the non-sensitive host and optional port."""

    parsed = urlsplit(value)
    return parsed.netloc.rsplit("@", 1)[-1]
