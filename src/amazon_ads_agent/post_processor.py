"""Deterministic normalization, versioning, and plan freezing."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from .decimal_utils import decimal_to_string, parse_decimal, percentage_change
from .models import CandidateSet, MetricsResult, ReasonerOutput, ValidationIssue


def utc_now() -> str:
    """Return an RFC 3339 UTC timestamp."""

    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def canonical_digest(payload: Any) -> str:
    """Hash normalized JSON with stable key ordering and no display whitespace."""

    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def _change_id(task_id: str, object_id: str) -> str:
    digest = hashlib.sha256(f"{task_id}|{object_id}|update_bid".encode("utf-8")).hexdigest()
    return f"chg-{digest[:16]}"


def build_plan(
    task: dict[str, Any],
    metrics: MetricsResult,
    candidates: CandidateSet,
    reasoner_output: ReasonerOutput,
    plan_version: int,
    retry_count: int,
) -> dict[str, Any]:
    """Create an immutable candidate plan without accepting it as valid."""

    entity = task["entity_metrics"][0]
    current = parse_decimal(entity["current_bid"])
    suggested = parse_decimal(reasoner_output.suggested_value)
    ratio = percentage_change(current, suggested)
    change = {
        "change_id": _change_id(task["task_id"], entity["entity_id"]),
        "object_type": "keyword",
        "object_id": entity["entity_id"],
        "action": "update_bid",
        "expected_current_value": entity["current_bid"],
        "expected_object_version": entity["object_version"],
        "candidate_values": list(candidates.values),
        "suggested_value": reasoner_output.suggested_value,
        "change_ratio": decimal_to_string(ratio, places=12),
        "reason": reasoner_output.reason,
        "evidence": [dict(item) for item in reasoner_output.evidence],
        "confidence": reasoner_output.confidence,
        "change_risk_level": reasoner_output.risk_summary,
    }
    digest_fields = {
        "task_id": task["task_id"],
        "run_id": task["run_id"],
        "plan_version": plan_version,
        "data_snapshot_id": task["data_snapshot_id"],
        "rule_set_version": task["rule_set_version"],
        "changes": [
            {
                key: change[key]
                for key in (
                    "change_id", "object_type", "object_id", "action",
                    "expected_current_value", "expected_object_version",
                    "suggested_value", "change_ratio", "change_risk_level",
                )
            }
        ],
    }
    return {
        "schema_version": "2.0",
        "task_id": task["task_id"],
        "run_id": task["run_id"],
        "attempt_id": task["attempt_id"],
        "current_status": "validating_plan",
        "completion_reason": None,
        "analysis_summary": reasoner_output.reason,
        "issues": [
            {
                "issue_id": "issue-acos-above-target",
                "type": "acos_above_target",
                "evidence_paths": ["entity_metrics[0].spend", "entity_metrics[0].sales", "target_acos"],
            }
        ],
        "plan_version": plan_version,
        "rule_set_version": task["rule_set_version"],
        "data_snapshot_id": task["data_snapshot_id"],
        "plan_digest": canonical_digest(digest_fields),
        "changes": [change],
        "calculated_risk_level": reasoner_output.risk_summary,
        "runtime_validation": None,
        "execution_preflight": None,
        "retry_count": retry_count,
        "human_approval_required": True,
        "generated_at": utc_now(),
    }


def build_completed(task: dict[str, Any], completion_reason: str, reason_codes: tuple[str, ...]) -> dict[str, Any]:
    """Build a no-change terminal result that skips validation and preflight."""

    summary = "证据不足，未生成广告修改。" if completion_reason == "insufficient_evidence" else "数据充分但 ACoS 未触发调整规则。"
    return {
        "schema_version": "2.0",
        "task_id": task["task_id"],
        "run_id": task["run_id"],
        "attempt_id": task["attempt_id"],
        "current_status": "completed",
        "completion_reason": completion_reason,
        "analysis_summary": summary,
        "issues": [
            {"issue_id": f"issue-{index + 1}", "type": code.lower(), "evidence_paths": []}
            for index, code in enumerate(reason_codes)
        ],
        "plan_version": 0,
        "rule_set_version": task["rule_set_version"],
        "data_snapshot_id": task["data_snapshot_id"],
        "plan_digest": None,
        "changes": [],
        "calculated_risk_level": "low",
        "runtime_validation": None,
        "execution_preflight": None,
        "retry_count": 0,
        "human_approval_required": False,
        "generated_at": utc_now(),
    }


def build_manual_intervention(
    task: dict[str, Any], issue: ValidationIssue, plan_version: int, retry_count: int
) -> dict[str, Any]:
    """Build the isolated PoC failure terminal described in ISSUE-001."""

    return {
        "schema_version": "2.0",
        "task_id": task["task_id"],
        "run_id": task["run_id"],
        "attempt_id": task["attempt_id"],
        "current_status": "manual_intervention_required",
        "completion_reason": None,
        "analysis_summary": f"自动修订已停止：{issue.error_code}，{issue.message}",
        "issues": [
            {
                "issue_id": "issue-manual-intervention",
                "type": issue.error_code.lower(),
                "evidence_paths": list(issue.failed_paths),
            }
        ],
        "plan_version": plan_version,
        "rule_set_version": task["rule_set_version"],
        "data_snapshot_id": task["data_snapshot_id"],
        "plan_digest": None,
        "changes": [],
        "calculated_risk_level": "high",
        "runtime_validation": {
            "passed": False,
            "error_code": issue.error_code,
            "failed_rule_ids": list(issue.failed_rule_ids),
        },
        "execution_preflight": {
            "passed": False,
            "preflight_id": None,
            "mode": "dry_run",
            "request_digest": None,
            "production_write_called": False,
        },
        "retry_count": retry_count,
        "human_approval_required": False,
        "generated_at": utc_now(),
    }
