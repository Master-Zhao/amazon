"""Shared workflow helpers extracted from workflow.py and langgraph_workflow.py."""

from __future__ import annotations

import re
from typing import Any

from .config_loader import require_config
from .decimal_utils import decimal_to_string
from .models import ReasonerOutput
from .reasoners.base import ReasonerInput, ReasonerResult

_INDEXED_PATH = re.compile(r"^entity_metrics\[([0-9]+)\]\.([A-Za-z_][A-Za-z0-9_]*)$")


def resolve_evidence_value(task: dict[str, Any], metrics: Any, path: str) -> Any:
    if path in {"target_acos", "task_context.target_acos"}:
        return task["target_acos"]
    if path.startswith("calculated_metrics."):
        field = path.removeprefix("calculated_metrics.")
        value = getattr(metrics, field, None)
        return None if value is None else decimal_to_string(value, places=6)
    if path.startswith("entity_metrics."):
        return task["entity_metrics"][0].get(path.removeprefix("entity_metrics."))
    match = _INDEXED_PATH.fullmatch(path)
    if match:
        try:
            return task["entity_metrics"][int(match.group(1))][match.group(2)]
        except (IndexError, KeyError):
            return None
    return None


def build_reasoner_input(
    task: dict[str, Any],
    metrics: Any,
    acos: str,
    candidates: Any,
    rules: dict[str, Any],
    plan_version: int,
    previous_failure: dict[str, Any] | None,
) -> ReasonerInput:
    entity = task["entity_metrics"][0]
    return ReasonerInput.create(
        task_id=task["task_id"],
        run_id=task["run_id"],
        attempt_id=task["attempt_id"],
        data_snapshot_id=task["data_snapshot_id"],
        plan_version=plan_version,
        object_type=entity["entity_type"],
        object_id=entity["entity_id"],
        optimization_goal=task["optimization_goal"],
        requested_risk_profile=task["requested_risk_profile"],
        entity_metrics=task["entity_metrics"],
        calculated_metrics={
            "acos": acos,
            "ctr": None if metrics.ctr is None else decimal_to_string(metrics.ctr, places=6),
            "cpc": None if metrics.cpc is None else decimal_to_string(metrics.cpc, places=6),
            "cvr": None if metrics.cvr is None else decimal_to_string(metrics.cvr, places=6),
            "roas": None if metrics.roas is None else decimal_to_string(metrics.roas, places=6),
        },
        candidate_values=candidates.values,
        constraints={
            "rule_set_version": task["rule_set_version"],
            "target_acos": task["target_acos"],
            "confidence": str(require_config(rules, "analysis.confidence_threshold")),
            "max_decrease_ratio": str(require_config(rules, "keyword_bid.max_decrease_ratio")),
            "max_increase_ratio": str(require_config(rules, "keyword_bid.max_increase_ratio")),
            "min_bid": str(require_config(rules, "keyword_bid.min_bid")),
            "max_bid": str(require_config(rules, "keyword_bid.max_bid")),
            "bid_step": str(require_config(rules, "keyword_bid.bid_step")),
            "requested_risk_profile": task["requested_risk_profile"],
            "human_approval_required": True,
        },
        previous_failure=previous_failure,
    )


def legacy_output(
    task: dict[str, Any], metrics: Any, result: ReasonerResult, rules: dict[str, Any]
) -> ReasonerOutput:
    risk = result.risk_summary if result.risk_summary in {"low", "medium", "high"} else "medium"
    return ReasonerOutput(
        suggested_value=result.selected_value,
        reason=result.reason,
        evidence=tuple(
            {"path": path, "value": resolve_evidence_value(task, metrics, path)}
            for path in result.evidence_paths
        ),
        confidence=str(require_config(rules, "analysis.confidence_threshold")),
        risk_summary=risk,
    )