"""V0.2.1 terminal AgentOutput and ManualInterventionPackage builders."""

from __future__ import annotations

from typing import Any

from .config_loader import require_config
from .models import ValidationIssue
from .post_processor import canonical_digest, utc_now
from .schema_loader import validate_manual_intervention_package


def _stop_reason(last_failure: dict[str, Any], config: dict[str, Any]) -> str:
    if last_failure["same_error_consecutive_count"] >= require_config(
        config, "runtime.stop_on_same_error_consecutive_count"
    ):
        return "same_error_repeated"
    if last_failure["retry_count"] >= require_config(config, "runtime.max_automatic_revisions"):
        return "maximum_revisions_reached"
    if last_failure["error_code"] == "ERR_RULE_CONFIG_MISSING":
        return "rule_config_missing"
    if last_failure["error_code"] == "ERR_STATE_TRANSITION_INVALID":
        return "invalid_state_transition"
    if last_failure["error_code"] == "ERR_PRODUCTION_WRITE_FORBIDDEN":
        return "internal_safety_guard"
    return "uncorrectable_validation_failure"


def build_manual_intervention_package(
    task: dict[str, Any],
    failures: list[dict[str, Any]],
    audit_events: list[dict[str, Any]],
    config: dict[str, Any],
) -> dict[str, Any]:
    """Build and validate immutable material for explicit future human recovery."""

    if not failures:
        raise ValueError("manual intervention requires at least one FailureAnalysis")
    if not audit_events:
        raise ValueError("manual intervention requires audit evidence")
    latest = failures[-1]
    identity = canonical_digest(
        {
            "task_id": task["task_id"],
            "run_id": task["run_id"],
            "data_snapshot_id": task["data_snapshot_id"],
            "latest_attempt_id": latest["attempt_id"],
            "latest_plan_version": latest["plan_version"],
            "fingerprints": [failure["error_fingerprint"] for failure in failures],
        }
    )
    package = {
        "schema_version": "2.0.1",
        "manual_intervention_package_id": f"mip-{identity.removeprefix('sha256:')[:16]}",
        "task_id": task["task_id"],
        "run_id": task["run_id"],
        "data_snapshot_id": task["data_snapshot_id"],
        "latest_attempt_id": latest["attempt_id"],
        "latest_plan_version": latest["plan_version"],
        "stop_reason": _stop_reason(latest, config),
        "last_error_code": latest["error_code"],
        "last_error_fingerprint": latest["error_fingerprint"],
        "last_error_message": latest["error_message"],
        "retry_count": latest["retry_count"],
        "same_error_consecutive_count": latest["same_error_consecutive_count"],
        "attempt_history": [
            {
                "attempt_id": failure["attempt_id"],
                "plan_version": failure["plan_version"],
                "error_code": failure["error_code"],
                "error_fingerprint": failure["error_fingerprint"],
                "correctable": failure["correctable"],
                "occurred_at": failure["analyzed_at"],
            }
            for failure in failures
        ],
        "audit_event_ids": [event["event_id"] for event in audit_events],
        "recovery_constraints": {
            "human_explicit_recovery_required": True,
            "new_run_id_required": True,
            "failed_plan_reuse_forbidden": True,
            "old_approval_reuse_forbidden": True,
            "automatic_replay_forbidden": True,
            "input_and_config_revalidation_required": True,
        },
        "original_run_terminal": True,
        "production_write_called": False,
        "created_at": utc_now(),
    }
    validate_manual_intervention_package(package)
    return package


def build_manual_agent_output(
    task: dict[str, Any],
    issue: ValidationIssue,
    package_id: str,
    plan_version: int,
    retry_count: int,
) -> dict[str, Any]:
    """Represent terminal state while keeping failure material in its own package."""

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
        "execution_preflight": None,
        "retry_count": retry_count,
        "human_approval_required": False,
        "manual_intervention_package_id": package_id,
        "generated_at": utc_now(),
    }
