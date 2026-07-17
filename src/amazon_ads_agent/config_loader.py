"""Fail-closed loader for the versioned PoC rule set."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .decimal_utils import parse_decimal

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = REPOSITORY_ROOT / "config" / "poc-rules-v0.1.yaml"


class RuleConfigError(ValueError):
    """Raised when required versioned configuration is absent or unsafe."""


def _require(mapping: dict[str, Any], path: str) -> Any:
    current: Any = mapping
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise RuleConfigError(f"ERR_RULE_CONFIG_MISSING: {path}")
        current = current[part]
    return current


def load_config(path: Path | None = None) -> dict[str, Any]:
    """Load and validate the complete, explicitly non-production PoC config."""

    config_path = path or DEFAULT_CONFIG_PATH
    if not config_path.is_file():
        raise RuleConfigError(f"ERR_RULE_CONFIG_MISSING: {config_path}")
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise RuleConfigError("configuration root must be an object")

    required = (
        "schema_version", "environment", "not_for_production", "rule_set_version",
        "analysis.minimum_analysis_days", "analysis.min_clicks", "analysis.min_orders",
        "analysis.target_acos", "analysis.confidence_threshold",
        "keyword_bid.max_decrease_ratio", "keyword_bid.max_increase_ratio",
        "keyword_bid.min_bid", "keyword_bid.max_bid", "keyword_bid.bid_step",
        "keyword_bid.candidate_change_ratios", "strategy.default_profile",
        "strategy.balanced.min_confidence", "strategy.balanced.approval_level",
        "runtime.max_automatic_revisions", "runtime.stop_on_same_error_consecutive_count",
        "runtime.production_write_enabled", "runtime.allowed_execution_modes",
        "reasoner.provider", "reasoner.model_config_id",
    )
    for key in required:
        _require(raw, key)

    if raw["environment"] != "poc" or raw["not_for_production"] is not True:
        raise RuleConfigError("PoC configuration must be explicitly marked not for production")
    if _require(raw, "runtime.production_write_enabled") is not False:
        raise RuleConfigError("production writes must be disabled")
    if _require(raw, "runtime.allowed_execution_modes") != ["dry_run"]:
        raise RuleConfigError("dry_run must be the only execution mode")
    if _require(raw, "reasoner.provider") != "stub":
        raise RuleConfigError("the PoC accepts only the explicit Reasoner Stub")

    decimal_paths = (
        "analysis.target_acos", "analysis.confidence_threshold",
        "keyword_bid.max_decrease_ratio", "keyword_bid.max_increase_ratio",
        "keyword_bid.min_bid", "keyword_bid.max_bid", "keyword_bid.bid_step",
        "strategy.balanced.min_confidence",
    )
    for key in decimal_paths:
        parse_decimal(_require(raw, key))
    ratios = _require(raw, "keyword_bid.candidate_change_ratios")
    if not isinstance(ratios, list) or not ratios:
        raise RuleConfigError("candidate_change_ratios must be a non-empty list")
    for ratio in ratios:
        parse_decimal(ratio)

    for key in (
        "analysis.minimum_analysis_days", "analysis.min_clicks", "analysis.min_orders",
        "runtime.max_automatic_revisions", "runtime.stop_on_same_error_consecutive_count",
    ):
        value = _require(raw, key)
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise RuleConfigError(f"{key} must be a positive integer")
    return raw


def require_config(config: dict[str, Any], path: str) -> Any:
    """Read a required config field without fallback inference."""

    return _require(config, path)
