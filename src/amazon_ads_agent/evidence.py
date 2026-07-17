"""Configured evidence sufficiency and high-ACoS decision gate."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from .config_loader import require_config
from .decimal_utils import parse_decimal
from .models import EvidenceDecision, MetricsResult


def evaluate_evidence(task: dict[str, Any], metrics: MetricsResult, config: dict[str, Any]) -> EvidenceDecision:
    """Classify a task as insufficient, no-change, or candidate-generating."""

    start = date.fromisoformat(task["date_range"]["start"])
    end = date.fromisoformat(task["date_range"]["end"])
    analysis_days = (end - start).days + 1
    entity = task["entity_metrics"][0]
    minimum_days = require_config(config, "analysis.minimum_analysis_days")
    min_clicks = require_config(config, "analysis.min_clicks")
    min_orders = require_config(config, "analysis.min_orders")
    configured_target = parse_decimal(require_config(config, "analysis.target_acos"))
    input_target = parse_decimal(task["target_acos"])

    insufficiencies: list[str] = []
    if analysis_days < minimum_days:
        insufficiencies.append("ANALYSIS_WINDOW_TOO_SHORT")
    if entity["clicks"] < min_clicks:
        insufficiencies.append("CLICKS_BELOW_MINIMUM")
    if entity["orders"] < min_orders:
        insufficiencies.append("ORDERS_BELOW_MINIMUM")
    if parse_decimal(entity["sales"]) <= Decimal("0") or metrics.acos is None:
        insufficiencies.append("ACOS_UNAVAILABLE")
    if input_target != configured_target:
        insufficiencies.append("TARGET_ACOS_CONFIG_MISMATCH")
    if insufficiencies:
        return EvidenceDecision("insufficient_evidence", tuple(insufficiencies), analysis_days)
    if metrics.acos <= configured_target:
        return EvidenceDecision("no_change_required", ("ACOS_NOT_ABOVE_TARGET",), analysis_days)
    return EvidenceDecision("generate_candidates", ("ACOS_ABOVE_TARGET",), analysis_days)
