"""Runtime Schema, reference, rule, and state validation."""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any

from .candidate_engine import generate_bid_candidates
from .config_loader import require_config
from .decimal_utils import decimal_to_string, parse_decimal, percentage_change
from .metrics import calculate_metrics
from .models import ValidationIssue, ValidationResult
from .post_processor import calculate_plan_digest
from .schema_loader import SchemaValidationError, validate_agent_output

ERR_SCHEMA_VALIDATION_FAILED = "ERR_SCHEMA_VALIDATION_FAILED"
ERR_OBJECT_REFERENCE_INVALID = "ERR_OBJECT_REFERENCE_INVALID"
ERR_CANDIDATE_OUT_OF_RANGE = "ERR_CANDIDATE_OUT_OF_RANGE"
ERR_CURRENT_VALUE_MISMATCH = "ERR_CURRENT_VALUE_MISMATCH"
ERR_OBJECT_VERSION_MISMATCH = "ERR_OBJECT_VERSION_MISMATCH"
ERR_CHANGE_RATIO_EXCEEDED = "ERR_CHANGE_RATIO_EXCEEDED"
ERR_EVIDENCE_REFERENCE_INVALID = "ERR_EVIDENCE_REFERENCE_INVALID"
ERR_RULE_CONFIG_MISSING = "ERR_RULE_CONFIG_MISSING"
ERR_STATE_TRANSITION_INVALID = "ERR_STATE_TRANSITION_INVALID"
ERR_PRODUCTION_WRITE_FORBIDDEN = "ERR_PRODUCTION_WRITE_FORBIDDEN"
ERR_PLAN_DIGEST_MISMATCH = "ERR_PLAN_DIGEST_MISMATCH"

_INDEXED_PATH = re.compile(r"^entity_metrics\[([0-9]+)\]\.([A-Za-z_][A-Za-z0-9_]*)$")


def _failed(code: str, message: str, rules: tuple[str, ...] = (), paths: tuple[str, ...] = (), values: tuple[str, ...] = ()) -> ValidationResult:
    return ValidationResult(False, ValidationIssue(code, message, rules, paths, values))


def _resolve_evidence(task: dict[str, Any], path: str) -> Any:
    if path in {"target_acos", "task_context.target_acos"}:
        return task["target_acos"]
    if path.startswith("entity_metrics."):
        return task["entity_metrics"][0][path.removeprefix("entity_metrics.")]
    if path.startswith("calculated_metrics."):
        field = path.removeprefix("calculated_metrics.")
        calculated = calculate_metrics(task["entity_metrics"][0])
        if not hasattr(calculated, field):
            raise KeyError(path)
        value = getattr(calculated, field)
        return None if value is None else decimal_to_string(value, places=6)
    match = _INDEXED_PATH.fullmatch(path)
    if not match:
        raise KeyError(path)
    index = int(match.group(1))
    field = match.group(2)
    return task["entity_metrics"][index][field]


def validate_runtime(plan: dict[str, Any], task: dict[str, Any], config: dict[str, Any]) -> ValidationResult:
    """Validate an untrusted plan against its source snapshot and rule config."""

    preflight = plan.get("execution_preflight")
    if isinstance(preflight, dict) and preflight.get("production_write_called") is not False:
        return _failed(ERR_PRODUCTION_WRITE_FORBIDDEN, "production_write_called must be false", paths=("execution_preflight.production_write_called",))
    try:
        validate_agent_output(plan)
    except SchemaValidationError as exc:
        return _failed(ERR_SCHEMA_VALIDATION_FAILED, str(exc), paths=("$",))

    calculated_digest = calculate_plan_digest(plan)
    if plan["plan_digest"] != calculated_digest:
        return _failed(
            ERR_PLAN_DIGEST_MISMATCH,
            "plan_digest does not match the immutable V0.2.1 plan fields",
            paths=("plan_digest",),
            values=(str(plan["plan_digest"]), calculated_digest),
        )

    if plan["rule_set_version"] != task["rule_set_version"] or plan["rule_set_version"] != config["rule_set_version"]:
        return _failed(ERR_RULE_CONFIG_MISSING, "rule_set_version does not match loaded config", paths=("rule_set_version",))
    if plan["data_snapshot_id"] != task["data_snapshot_id"]:
        return _failed(ERR_OBJECT_REFERENCE_INVALID, "data_snapshot_id mismatch", paths=("data_snapshot_id",))
    if plan["current_status"] != "validating_plan":
        return _failed(ERR_STATE_TRANSITION_INVALID, "candidate plan must be in validating_plan", paths=("current_status",))

    entities = {entity["entity_id"]: entity for entity in task["entity_metrics"]}
    change_ids: set[str] = set()
    max_decrease = parse_decimal(require_config(config, "keyword_bid.max_decrease_ratio"))
    step = parse_decimal(require_config(config, "keyword_bid.bid_step"))

    for index, change in enumerate(plan["changes"]):
        prefix = f"changes[{index}]"
        if change["change_id"] in change_ids:
            return _failed(ERR_OBJECT_REFERENCE_INVALID, "duplicate change_id", paths=(f"{prefix}.change_id",))
        change_ids.add(change["change_id"])
        if change["object_type"] != "keyword" or change["action"] != "update_bid":
            return _failed(ERR_OBJECT_REFERENCE_INVALID, "unsupported object/action combination", paths=(prefix,))
        entity = entities.get(change["object_id"])
        if entity is None:
            return _failed(ERR_OBJECT_REFERENCE_INVALID, "object_id is not in the input snapshot", paths=(f"{prefix}.object_id",))

        expected_candidates = generate_bid_candidates(entity["current_bid"], config).values
        if tuple(change["candidate_values"]) != expected_candidates or change["suggested_value"] not in expected_candidates:
            return _failed(
                ERR_CANDIDATE_OUT_OF_RANGE,
                "suggested value must belong to the immutable Candidate Engine set",
                rules=("BR-022",),
                paths=(f"{prefix}.suggested_value", f"{prefix}.candidate_values"),
                values=(change["suggested_value"],),
            )
        if parse_decimal(change["expected_current_value"]) != parse_decimal(entity["current_bid"]):
            return _failed(ERR_CURRENT_VALUE_MISMATCH, "expected current bid differs from snapshot", paths=(f"{prefix}.expected_current_value",))
        if change["expected_object_version"] != entity["object_version"]:
            return _failed(ERR_OBJECT_VERSION_MISMATCH, "expected object version differs from snapshot", paths=(f"{prefix}.expected_object_version",))

        current = parse_decimal(entity["current_bid"])
        suggested = parse_decimal(change["suggested_value"])
        actual_ratio = percentage_change(current, suggested)
        ratio_string = decimal_to_string(actual_ratio, places=12)
        if change["change_ratio"] != ratio_string or abs(actual_ratio) > max_decrease:
            return _failed(ERR_CHANGE_RATIO_EXCEEDED, "change ratio is inconsistent or exceeds configured limit", rules=("BR-019", "BR-023"), paths=(f"{prefix}.change_ratio",))
        if (suggested / step) != (suggested / step).to_integral_value():
            return _failed(ERR_CHANGE_RATIO_EXCEEDED, "suggested bid does not match configured step", rules=("BR-024",), paths=(f"{prefix}.suggested_value",))

        for evidence_index, evidence in enumerate(change["evidence"]):
            try:
                actual = _resolve_evidence(task, evidence["path"])
            except (KeyError, IndexError):
                return _failed(ERR_EVIDENCE_REFERENCE_INVALID, "evidence path does not exist", rules=("BR-026",), paths=(f"{prefix}.evidence[{evidence_index}].path",))
            if actual != evidence["value"]:
                return _failed(ERR_EVIDENCE_REFERENCE_INVALID, "evidence value differs from snapshot", rules=("BR-026",), paths=(f"{prefix}.evidence[{evidence_index}].value",))
        confidence = parse_decimal(change["confidence"])
        if confidence < Decimal("0") or confidence > Decimal("1"):
            return _failed(ERR_SCHEMA_VALIDATION_FAILED, "confidence is outside [0, 1]", paths=(f"{prefix}.confidence",))

    if not plan["human_approval_required"]:
        return _failed(ERR_STATE_TRANSITION_INVALID, "a change plan must require human approval", paths=("human_approval_required",))
    return ValidationResult(True)
