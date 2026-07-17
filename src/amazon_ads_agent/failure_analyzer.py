"""Stable failure fingerprinting and bounded revision decisions."""

from __future__ import annotations

from typing import Any

from .config_loader import require_config
from .models import ValidationIssue
from .post_processor import canonical_digest, utc_now
from .schema_loader import validate_failure_analysis

CORRECTABLE_CODES = {
    "ERR_SCHEMA_VALIDATION_FAILED",
    "ERR_CANDIDATE_OUT_OF_RANGE",
    "ERR_CURRENT_VALUE_MISMATCH",
    "ERR_OBJECT_VERSION_MISMATCH",
    "ERR_CHANGE_RATIO_EXCEEDED",
    "ERR_EVIDENCE_REFERENCE_INVALID",
    "ERR_STATE_TRANSITION_INVALID",
}


def analyze_failure(
    task: dict[str, Any],
    issue: ValidationIssue,
    plan_version: int,
    retry_count: int,
    prior_fingerprints: list[str],
    config: dict[str, Any],
) -> dict[str, Any]:
    """Create a schema-valid FailureAnalysis and decide whether to revise."""

    fingerprint = canonical_digest(
        {
            "error_code": issue.error_code,
            "failed_paths": sorted(issue.failed_paths),
            "rule_set_version": task["rule_set_version"],
            "actual_values": sorted(issue.actual_values),
        }
    )
    consecutive = 1
    for previous in reversed(prior_fingerprints):
        if previous != fingerprint:
            break
        consecutive += 1

    correctable = issue.error_code in CORRECTABLE_CODES
    max_revisions = require_config(config, "runtime.max_automatic_revisions")
    same_error_limit = require_config(config, "runtime.stop_on_same_error_consecutive_count")
    retry_allowed = correctable and retry_count < max_revisions and consecutive < same_error_limit
    category = "rule"
    if issue.error_code == "ERR_SCHEMA_VALIDATION_FAILED":
        category = "schema"
    elif issue.error_code in {"ERR_OBJECT_REFERENCE_INVALID", "ERR_CURRENT_VALUE_MISMATCH", "ERR_OBJECT_VERSION_MISMATCH"}:
        category = "data"
    elif issue.error_code in {"ERR_PRODUCTION_WRITE_FORBIDDEN", "ERR_STATE_TRANSITION_INVALID"}:
        category = "security"

    analysis = {
        "schema_version": "2.0",
        "task_id": task["task_id"],
        "run_id": task["run_id"],
        "attempt_id": task["attempt_id"],
        "plan_version": plan_version,
        "error_code": issue.error_code,
        "error_fingerprint": fingerprint,
        "error_category": category,
        "error_message": issue.message,
        "failed_rule_ids": list(issue.failed_rule_ids),
        "correctable": correctable,
        "retry_allowed": retry_allowed,
        "retry_count": retry_count,
        "same_error_consecutive_count": consecutive,
        "next_action": "revise_plan" if retry_allowed else "manual_intervention_required",
        "analyzed_at": utc_now(),
    }
    validate_failure_analysis(analysis)
    return analysis
