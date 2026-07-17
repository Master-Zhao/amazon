"""Bounded orchestration for the five synthetic PoC workflow paths."""

from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

from .audit import AuditCollector
from .candidate_engine import generate_bid_candidates
from .config_loader import load_config, require_config, validate_config
from .decimal_utils import decimal_to_string
from .evidence import evaluate_evidence
from .failure_analyzer import analyze_failure
from .manual_intervention import build_manual_agent_output, build_manual_intervention_package
from .metrics import calculate_metrics
from .models import ReasonerOutput, ValidationIssue, WorkflowResult
from .post_processor import build_completed, build_plan
from .preflight import run_preflight
from .reasoners.base import Reasoner, ReasonerInput, ReasonerResult, adapt_reasoner
from .reasoners.config import LLMReasonerConfig
from .reasoners.errors import ReasonerError
from .reasoners.llm import LLMReasoner
from .reasoners.provider import create_reasoner, load_reasoner_config
from .reasoners.transport import LLMTransport
from .runtime_validator import validate_runtime
from .schema_loader import validate_agent_output, validate_task_input

_INDEXED_PATH = re.compile(r"^entity_metrics\[([0-9]+)\]\.([A-Za-z_][A-Za-z0-9_]*)$")


def _resolve_evidence_value(task: dict[str, Any], metrics: Any, path: str) -> Any:
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


def _reasoner_input(
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


def _legacy_output(
    task: dict[str, Any], metrics: Any, result: ReasonerResult, rules: dict[str, Any]
) -> ReasonerOutput:
    risk = result.risk_summary if result.risk_summary in {"low", "medium", "high"} else "medium"
    return ReasonerOutput(
        suggested_value=result.selected_value,
        reason=result.reason,
        evidence=tuple(
            {"path": path, "value": _resolve_evidence_value(task, metrics, path)}
            for path in result.evidence_paths
        ),
        confidence=str(require_config(rules, "analysis.confidence_threshold")),
        risk_summary=risk,
    )


def _manual_result(
    task: dict[str, Any],
    issue: ValidationIssue,
    failures: list[dict[str, Any]],
    audit: AuditCollector,
    rules: dict[str, Any],
    plan_version: int,
    retry_count: int,
) -> WorkflowResult:
    package = build_manual_intervention_package(task, failures, audit.events, rules)
    output = build_manual_agent_output(
        task, issue, package["manual_intervention_package_id"], plan_version, retry_count
    )
    validate_agent_output(output)
    return WorkflowResult(
        output=output,
        audit_events=audit.events,
        failure_analyses=failures,
        manual_intervention_package=package,
    )


def run_workflow(
    task: dict[str, Any],
    *,
    reasoner_mode: str | None = None,
    reasoner: Any | None = None,
    reasoner_provider: str | None = None,
    reasoner_config: LLMReasonerConfig | None = None,
    transport: LLMTransport | None = None,
    config: dict[str, Any] | None = None,
) -> WorkflowResult:
    """Run the synthetic keyword workflow and stop before any human approval."""

    rules = validate_config(deepcopy(config)) if config is not None else load_config()
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
        audit.record("completed_without_change", "analyzing", "completed", f"Completed with {evidence.outcome}; no preflight or approval was created.")
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
    if reasoner is not None:
        active_reasoner: Reasoner = adapt_reasoner(reasoner)
        if isinstance(active_reasoner, LLMReasoner):
            provider_name = "llm"
            model_name = active_reasoner.config.model
        else:
            provider_name = "injected"
            model_name = type(reasoner).__name__
    else:
        provider_config = reasoner_config or load_reasoner_config(provider_override=reasoner_provider)
        active_reasoner = create_reasoner(provider_config, transport=transport, stub_mode=selected_mode)
        provider_name = provider_config.provider
        model_name = provider_config.model if provider_config.provider == "llm" else str(require_config(rules, "reasoner.model_config_id"))
    audit.record(
        "reasoner_provider_selected",
        "generating_plan",
        "generating_plan",
        "Configured Reasoner Provider selected.",
        plan_version=1,
        metadata={
            "provider": provider_name,
            "model": model_name,
            "transport_retry_count": 0,
            "agent_revision_count": 0,
        },
    )
    plan_version = 1
    retry_count = 0
    fingerprints: list[str] = []
    feedback: dict[str, Any] | None = None

    while True:
        if provider_name == "llm":
            audit.record(
                "llm_request_started",
                "generating_plan" if retry_count == 0 else "retrying",
                "generating_plan",
                "Injected LLM Transport request started.",
                plan_version=plan_version,
                metadata={"provider": "llm", "model": model_name, "agent_revision_count": retry_count},
            )
        try:
            result = active_reasoner.reason(
                _reasoner_input(working_task, metrics, acos_text, candidates, rules, plan_version, feedback)
            )
        except ReasonerError as error:
            transport_retries = int(getattr(active_reasoner, "last_transport_retry_count", 0))
            prompt_metadata = dict(getattr(active_reasoner, "last_prompt_metadata", {}))
            if prompt_metadata:
                audit.record(
                    "reasoner_prompt_built",
                    "generating_plan" if retry_count == 0 else "retrying",
                    "generating_plan",
                    "Formal Reasoner messages were built from repository templates.",
                    plan_version=plan_version,
                    metadata=prompt_metadata,
                )
            if bool(getattr(active_reasoner, "last_response_received", False)):
                audit.record(
                    "reasoner_response_received",
                    "generating_plan",
                    "generating_plan",
                    "A model response body was received for strict local validation.",
                    plan_version=plan_version,
                    metadata={"provider": "llm", "model": model_name},
                )
            schema_path = getattr(active_reasoner, "last_schema_field_path", None)
            if error.error_code == "ERR_REASONER_OUTPUT_SCHEMA_FAILED":
                audit.record(
                    "reasoner_schema_validation_failed",
                    "generating_plan",
                    "manual_intervention_required",
                    "Reasoner output failed the independent Schema.",
                    plan_version=plan_version,
                    error_code=error.error_code,
                    metadata={"field_path": schema_path or "$", "schema_version": "1.0"},
                )
            audit.record(
                "llm_request_failed",
                "generating_plan" if retry_count == 0 else "retrying",
                "manual_intervention_required",
                error.safe_message,
                plan_version=plan_version,
                error_code=error.error_code,
                metadata={
                    "provider": error.provider,
                    "model": model_name,
                    "transport_retry_count": transport_retries,
                    "agent_revision_count": retry_count,
                },
            )
            issue = ValidationIssue(error.error_code, error.safe_message, failed_paths=("reasoner",))
            analysis = analyze_failure(working_task, issue, plan_version, retry_count, fingerprints, rules)
            failures.append(analysis)
            fingerprints.append(analysis["error_fingerprint"])
            audit.record(
                "failure_analyzed",
                "generating_plan" if retry_count == 0 else "retrying",
                "manual_intervention_required",
                f"Failure next action: {analysis['next_action']}.",
                plan_version=plan_version,
                error_code=issue.error_code,
                metadata={"same_error_consecutive_count": analysis["same_error_consecutive_count"]},
            )
            audit.record(
                "manual_intervention_required",
                "generating_plan" if retry_count == 0 else "retrying",
                "manual_intervention_required",
                "Reasoner service failed; no preflight or production write was attempted.",
                plan_version=plan_version,
                error_code=issue.error_code,
            )
            return _manual_result(working_task, issue, failures, audit, rules, plan_version, retry_count)

        transport_retries = int(getattr(active_reasoner, "last_transport_retry_count", 0))
        if provider_name == "llm":
            audit.record(
                "reasoner_prompt_built",
                "generating_plan" if retry_count == 0 else "retrying",
                "generating_plan",
                "Formal Reasoner messages were built from repository templates.",
                plan_version=plan_version,
                metadata=dict(getattr(active_reasoner, "last_prompt_metadata", {})),
            )
            audit.record(
                "reasoner_response_received",
                "generating_plan",
                "generating_plan",
                "A model response body was received for strict local validation.",
                plan_version=plan_version,
                metadata={"provider": "llm", "model": result.model, "request_id": result.request_id},
            )
            audit.record(
                "reasoner_response_parsed",
                "generating_plan",
                "generating_plan",
                "The response was exactly one strict JSON object.",
                plan_version=plan_version,
                metadata={"provider": "llm", "request_id": result.request_id},
            )
            audit.record(
                "reasoner_schema_validation_passed",
                "generating_plan",
                "generating_plan",
                "Reasoner output passed Schema 1.0; business validation is still required.",
                plan_version=plan_version,
                metadata={"schema_version": "1.0", "request_id": result.request_id},
            )
            if bool(getattr(active_reasoner, "last_prompt_metadata", {}).get("revision_template_added")):
                audit.record(
                    "reasoner_revision_feedback_added",
                    "retrying",
                    "generating_plan",
                    "Safe deterministic failure feedback was added to the revision prompt.",
                    plan_version=plan_version,
                    metadata={"previous_failure_included": True},
                )
            if transport_retries:
                audit.record(
                    "llm_transport_retry",
                    "generating_plan" if retry_count == 0 else "retrying",
                    "generating_plan",
                    "Model transport retry completed inside the current agent attempt.",
                    plan_version=plan_version,
                    metadata={
                        "transport_retry_count": transport_retries,
                        "agent_revision_count": retry_count,
                    },
                )
            audit.record(
                "llm_request_succeeded",
                "generating_plan" if retry_count == 0 else "retrying",
                "generating_plan",
                "Injected LLM Transport returned a parseable Provider result.",
                plan_version=plan_version,
                metadata={
                    "provider": result.provider,
                    "model": result.model,
                    "request_id": result.request_id,
                    "transport_retry_count": transport_retries,
                    "agent_revision_count": retry_count,
                },
            )
        plan = build_plan(
            working_task,
            metrics,
            candidates,
            _legacy_output(working_task, metrics, result, rules),
            plan_version,
            retry_count,
        )
        audit.record(
            "reasoner_completed",
            "generating_plan" if retry_count == 0 else "retrying",
            "validating_plan",
            "Reasoner returned an untrusted candidate selection and explanation.",
            plan_version=plan_version,
            metadata={
                "provider": result.provider,
                "model": result.model,
                "request_id": result.request_id,
                "transport_retry_count": transport_retries,
                "agent_revision_count": retry_count,
            },
        )
        validation = validate_runtime(plan, working_task, rules)
        if not validation.passed:
            assert validation.issue is not None
            issue = validation.issue
            audit.record("runtime_validation_failed", "validating_plan", "retrying", issue.message, plan_version=plan_version, error_code=issue.error_code)
            analysis = analyze_failure(working_task, issue, plan_version, retry_count, fingerprints, rules)
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
                audit.record("manual_intervention_required", "retrying", "manual_intervention_required", "Bounded automatic revision stopped without preflight or production write.", plan_version=plan_version, error_code=issue.error_code)
                return _manual_result(working_task, issue, failures, audit, rules, plan_version, retry_count)

            retry_count += 1
            plan_version += 1
            working_task["attempt_id"] = f"attempt-{plan_version:04d}"
            audit.set_attempt_id(working_task["attempt_id"])
            feedback = analysis
            audit.record("plan_revised", "retrying", "validating_plan", "Created a new pre-approval attempt and plan version.", plan_version=plan_version, metadata={"retry_count": retry_count})
            continue

        audit.record("runtime_validation_passed", "validating_plan", "preflighting", "Runtime Schema, reference, rule, and state validation passed.", plan_version=plan_version)
        preflight = run_preflight(plan, rules)
        audit.record("preflight_passed", "preflighting", "waiting_for_approval", "Local dry-run preflight passed with zero production writes.", plan_version=plan_version, metadata={"production_write_called": False})
        plan["current_status"] = "waiting_for_approval"
        plan["runtime_validation"] = {"passed": True, "error_code": None, "failed_rule_ids": []}
        plan["execution_preflight"] = preflight
        validate_agent_output(plan)
        audit.record("waiting_for_approval", "preflighting", "waiting_for_approval", "Plan frozen; automatic modification stopped before human approval.", plan_version=plan_version)
        return WorkflowResult(output=plan, audit_events=audit.events, failure_analyses=failures)
