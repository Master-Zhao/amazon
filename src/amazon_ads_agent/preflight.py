"""Local dry-run request preflight with an unconditional no-write guard."""

from __future__ import annotations

from typing import Any

from .config_loader import require_config
from .decimal_utils import parse_decimal
from .post_processor import canonical_digest


class ProductionWriteForbidden(RuntimeError):
    """Raised whenever any caller requests a production write path."""


def assert_production_write_forbidden(production_write_called: bool) -> None:
    """Fail closed if a production write is reported or requested."""

    if production_write_called:
        raise ProductionWriteForbidden("ERR_PRODUCTION_WRITE_FORBIDDEN")


def run_preflight(plan: dict[str, Any], config: dict[str, Any], mode: str = "dry_run") -> dict[str, Any]:
    """Validate normalized local adapter request structure without I/O."""

    allowed_modes = require_config(config, "runtime.allowed_execution_modes")
    if mode not in allowed_modes or mode != "dry_run":
        raise ProductionWriteForbidden("only dry_run is supported")
    if require_config(config, "runtime.production_write_enabled") is not False:
        raise ProductionWriteForbidden("production write configuration must remain false")

    items: list[dict[str, str]] = []
    for change in plan["changes"]:
        before = parse_decimal(change["expected_current_value"])
        after = parse_decimal(change["suggested_value"])
        if before == after or change["suggested_value"] not in change["candidate_values"]:
            raise ValueError("preflight requires a real change from the candidate set")
        items.append(
            {
                "change_id": change["change_id"],
                "object_type": change["object_type"],
                "object_id": change["object_id"],
                "action": change["action"],
                "before": change["expected_current_value"],
                "after": change["suggested_value"],
            }
        )
    request = {"mode": "dry_run", "adapter": "local-preflight-stub-v0.1", "items": items}
    digest = canonical_digest(request)
    assert_production_write_forbidden(False)
    return {
        "passed": True,
        "preflight_id": f"preflight-{digest.removeprefix('sha256:')[:16]}",
        "mode": "dry_run",
        "request_digest": digest,
        "production_write_called": False,
    }
