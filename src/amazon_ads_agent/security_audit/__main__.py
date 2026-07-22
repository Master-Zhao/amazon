"""Allow running security audit as python -m amazon_ads_agent.security_audit."""

from __future__ import annotations

import sys

from .cli import audit_main

if __name__ == "__main__":
    sys.exit(audit_main())