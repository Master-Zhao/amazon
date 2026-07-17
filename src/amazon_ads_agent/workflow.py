"""Bounded orchestration for the five synthetic PoC workflow paths."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from .audit import AuditCollector
from .candidate_engine import generate_bid_candidates
from .config_loader import load_config, require_config
from .decimal_utils import decimal_to_string
from .evidence import evaluate_evidence
from .failure_analyzer import analyze_failure
from .metrics import calculate_metrics
from .models import ReasonerOutput, WorkflowResult
from .post_processor import build_completed, build_manual_intervention, build_plan
from .preflight import run_preflight
from .reasoner import Reasoner, ReasonerStub
from .runtime_validator import validate_runtime
from .schema_loader import validate_agent_output, validate_task_input


def _reasoner_context(task: dict[str, Any], acos: str, config: dict[str, Any]) -> dict[str, Any]:
    return {
        "entity_metrics": task["entity_metrics"],
        "target_acos": task["target_acos"],
        "acos": acos,
        "confidence": str(require_config(config, "analysis.confidence_threshold")),
        "rule_set_version": task["rule_set_version"],
    }


def run_workflow(
    task: dict[str, Any],
    *,
    reasoner_mode: str | None = None,
    reasoner: Reasoner | None = None,
    config: dict[str, Any] | None = None,
) -> WorkflowResult:
    """Run the synthetic keyword workflow and stop before any human approval."""

    rules = config or load_config()
    working_task = deepcopy(task)
    audit = AuditCollector(working_task)
    failures: list[dict[str, Any]] = []
    audit.record("task_loaded", None, "validating_data", "Synthetic task loaded.")
    validate_task_input(working_task)
    audit.record("schema_validated", "validating_data", "analyzing", "TaskInput Schema and cross-field validation passed.")

    if working_task["rule_set_version"] != rules["rule_set_version"]:
        raise ValueError("ERR_RULE_CONFIG_MISSING: task rule_set_version does not match loaded config")

    entity = working_task["entity_metrics"][0]
    metrics = calculate_metrics(entity)
    acos_text = "null" if metrics.acos is None else decimal_to_string(metrics.acos, places=6)
    audit.record("metrics_calculated", "analyzing", "analyzing", "Deterministic Decimal metrics calculated.", metadata={"acos": acos_text})
    evidence = evaluate_evidence(working_task, metrics, rules)
    audit.record(
        "evidence_evaluated",
        "analyzing",
        "analyzing" if evidence.outcome != "generate_candidates" else "generating_plan",
        f"Evidence outcome: {evidence.outcome}.",
        metadata={"analysis_days": evidence.analysis_days, "reason_count": len(evidence.reason_codes)},
    )

    if evidence.outcome in {"insufficient_evidence", "no_change_required"}:
        output = build_completed(working_task, evidence.outcome, evidence.reason_codes)
        validate_agent_output(output)
        audit.record(
            "completed_without_change",
            "analyzing",
            "completed",
            f"Completed with {evidence.outcome}; no preflight or approval was created.",
        )
        return WorkflowResult(output=output, audit_events=audit.events, failure_analyses=failures)

    candidates = generate_bid_candidates(entity["current_bid"], rules)
    audit.record(
        "candidates_generated",
        "generating_plan",
        "generating_plan",
        "Deterministic bid candidates generated.",
        plan_version=1,
        metadata={"candidate_count": len(candidates.values), "candidate_values": ",".join(candidates.values)},
    )
    selected_mode = reasoner_mode or working_task.get("test_fault", {}).get("reasoner_mode", "valid")
    active_reasoner: Reasoner = reasoner or ReasonerStub(selected_mode)
    plan_version = 1
    retry_count = 0
    fingerprints: list[str] = []
    feedback: dict[str, Any] | None = None

    while True:
        reasoned: ReasonerOutput = active_reasoner.select(candidates, _reasoner_context(working_task, acos_text, rules), feedback)
        plan = build_plan(working_task, metrics, candidates, reasoned, plan_version, retry_count)
        audit.record(
            "reasoner_completed",
            "generating_plan" if retry_count == 0 else "retrying",
            "validating_plan",
            "Reasoner Stub returned a candidate selection and explanation.",
            plan_version=plan_version,
            metadata={"model_config_id": str(require_config(rules, "reasoner.model_config_id"))},
        )
        validation = validate_runtime(plan, working_task, rules)
        if not validation.passed:
            assert validation.issue is not None
            issue = validation.issue
            audit.record(
                "runtime_validation_failed",
                "validating_plan",
                "retrying",
                issue.message,
                plan_version=plan_version,
                error_code=issue.error_code,
            )
            analysis = analyze_failure(
                working_task,
                issue,
                plan_version,
                retry_count,
                fingerprints,
                rules,
            )
            failures.append(analysis)
            fingerprints.append(analysis["error_fingerprint"])
            audit.record(
                "failure_analyzed",
                "retrying",
                "retrying" if analysis["retry_allowed"] else "manual_intervention_required",
                f"Failure next action: {analysis['next_action']}.",
                plan_version=plan_version,
                error_code=issue.error_code,
                metadata={"same_error_consecutive_count": analysis["same_error_consecutive_count"]},
            )
            if not analysis["retry_allowed"]:
                output = build_manual_intervention(working_task, issue, plan_version, retry_count)
                validate_agent_output(output)
                audit.record(
                    "manual_intervention_required",
                    "retrying",
                    "manual_intervention_required",
                    "Bounded automatic revision stopped without preflight or production write.",
                    plan_version=plan_version,
                    error_code=issue.error_code,
                )
                return WorkflowResult(output=output, audit_events=audit.events, failure_analyses=failures)

            retry_count += 1
            plan_version += 1
            working_task["attempt_id"] = f"attempt-{plan_version:04d}"
            audit.set_attempt_id(working_task["attempt_id"])
            feedback = analysis
            audit.record(
                "plan_revised",
                "retrying",
                "validating_plan",
                "Created a new pre-approval attempt and plan version.",
                plan_version=plan_version,
                metadata={"retry_count": retry_count},
            )
            continue

        audit.record(
            "runtime_validation_passed",
            "validating_plan",
            "preflighting",
            "Runtime Schema, reference, rule, and state validation passed.",
            plan_version=plan_version,
        )
        preflight = run_preflight(plan, rules)
        audit.record(
            "preflight_passed",
            "preflighting",
            "waiting_for_approval",
            "Local dry-run preflight passed with zero production writes.",
            plan_version=plan_version,
            metadata={"production_write_called": False},
        )
        plan["current_status"] = "waiting_for_approval"
        plan["runtime_validation"] = {"passed": True, "error_code": None, "failed_rule_ids": []}
        plan["execution_preflight"] = preflight
        validate_agent_output(plan)
        audit.record(
            "waiting_for_approval",
            "preflighting",
            "waiting_for_approval",
            "Plan frozen; automatic modification stopped before human approval.",
            plan_version=plan_version,
        )
        return WorkflowResult(output=plan, audit_events=audit.events, failure_analyses=failures)
