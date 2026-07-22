"""LangGraph-based orchestration for the Amazon Ads Agent workflow.

Replaces the imperative while-loop in workflow.py with a declarative
StateGraph that models the same five synthetic PoC paths as explicit
nodes and conditional edges.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from .audit import AuditCollector
from .candidate_engine import generate_bid_candidates
from .config_loader import load_config, require_config, validate_config
from .decimal_utils import decimal_to_string
from .evidence import evaluate_evidence
from .failure_analyzer import analyze_failure
from .manual_intervention import build_manual_agent_output, build_manual_intervention_package
from .metrics import MetricsResult, calculate_metrics
from .models import CandidateSet, EvidenceDecision, ReasonerOutput, ValidationResult, ValidationIssue, WorkflowResult
from .post_processor import build_completed, build_plan
from .preflight import run_preflight
from .reasoners.base import Reasoner, ReasonerInput, ReasonerResult, adapt_reasoner
from .reasoners.config import LLMReasonerConfig
from .reasoners.errors import ReasonerError
from .reasoners.llm import LLMReasoner
from .reasoners.provider import create_reasoner, load_reasoner_config
from .reasoners.transport import LLMTransport, NotConfiguredTransport
from .reasoners.transport_router import create_transport
from .runtime_validator import validate_runtime
from .schema_loader import validate_agent_output, validate_task_input
from .workflow_shared import build_reasoner_input, legacy_output


class AgentState(TypedDict, total=False):
    task: dict[str, Any]
    rules: dict[str, Any]
    audit: AuditCollector
    failures: list[dict[str, Any]]
    metrics: MetricsResult | None
    acos_text: str
    evidence: EvidenceDecision | None
    candidates: CandidateSet | None
    active_reasoner: Reasoner | None
    provider_name: str
    model_name: str
    plan_version: int
    retry_count: int
    fingerprints: list[str]
    feedback: dict[str, Any] | None
    reasoner_result: ReasonerResult | None
    plan: dict[str, Any] | None
    validation: ValidationResult | None
    issue: ValidationIssue | None
    analysis: dict[str, Any] | None
    output: dict[str, Any] | None
    result: WorkflowResult | None
    reasoner_mode: str
    reasoner: Reasoner | None
    reasoner_provider: str | None
    reasoner_config: LLMReasonerConfig | None
    transport: LLMTransport | None
    config: dict[str, Any] | None


def _init_state(
    task: dict[str, Any],
    *,
    reasoner_mode: str | None = None,
    reasoner: Any | None = None,
    reasoner_provider: str | None = None,
    reasoner_config: LLMReasonerConfig | None = None,
    transport: LLMTransport | None = None,
    config: dict[str, Any] | None = None,
) -> AgentState:
    return AgentState(
        task=task,
        rules=None,
        audit=None,
        failures=[],
        metrics=None,
        acos_text="",
        evidence=None,
        candidates=None,
        active_reasoner=None,
        provider_name="",
        model_name="",
        plan_version=1,
        retry_count=0,
        fingerprints=[],
        feedback=None,
        reasoner_result=None,
        plan=None,
        validation=None,
        issue=None,
        analysis=None,
        output=None,
        result=None,
        reasoner_mode=reasoner_mode or "",
        reasoner=reasoner,
        reasoner_provider=reasoner_provider,
        reasoner_config=reasoner_config,
        transport=transport,
        config=config,
    )


def node_load_config(state: AgentState) -> dict[str, Any]:
    rules = validate_config(deepcopy(state["config"])) if state.get("config") is not None else load_config()
    return {"rules": rules}


def node_validate_input(state: AgentState) -> dict[str, Any]:
    working_task = deepcopy(state["task"])
    audit = AuditCollector(working_task)
    audit.record("task_loaded", None, "validating_data", "Synthetic task loaded.")
    validate_task_input(working_task)
    audit.record("schema_validated", "validating_data", "analyzing", "TaskInput Schema and cross-field validation passed.")
    rules = state["rules"]
    if working_task["rule_set_version"] != rules["rule_set_version"]:
        raise ValueError("ERR_RULE_CONFIG_MISSING: task rule_set_version does not match loaded config")
    return {"task": working_task, "audit": audit}


def node_calculate_metrics(state: AgentState) -> dict[str, Any]:
    entity = state["task"]["entity_metrics"][0]
    metrics = calculate_metrics(entity)
    acos_text = "null" if metrics.acos is None else decimal_to_string(metrics.acos, places=6)
    state["audit"].record("metrics_calculated", "analyzing", "analyzing", "Deterministic Decimal metrics calculated.", metadata={"acos": acos_text})
    return {"metrics": metrics, "acos_text": acos_text}


def node_evaluate_evidence(state: AgentState) -> dict[str, Any]:
    evidence = evaluate_evidence(state["task"], state["metrics"], state["rules"])
    state["audit"].record(
        "evidence_evaluated",
        "analyzing",
        "analyzing" if evidence.outcome != "generate_candidates" else "generating_plan",
        f"Evidence outcome: {evidence.outcome}.",
        metadata={"analysis_days": evidence.analysis_days, "reason_count": len(evidence.reason_codes)},
    )
    return {"evidence": evidence}


def node_complete_no_change(state: AgentState) -> dict[str, Any]:
    evidence = state["evidence"]
    output = build_completed(state["task"], evidence.outcome, evidence.reason_codes)
    validate_agent_output(output)
    state["audit"].record("completed_without_change", "analyzing", "completed", f"Completed with {evidence.outcome}; no preflight or approval was created.")
    return {
        "output": output,
        "result": WorkflowResult(output=output, audit_events=state["audit"].events, failure_analyses=state["failures"]),
    }


def node_generate_candidates(state: AgentState) -> dict[str, Any]:
    entity = state["task"]["entity_metrics"][0]
    candidates = generate_bid_candidates(entity["current_bid"], state["rules"])
    state["audit"].record(
        "candidates_generated",
        "generating_plan",
        "generating_plan",
        "Deterministic bid candidates generated.",
        plan_version=1,
        metadata={"candidate_count": len(candidates.values), "candidate_values": ",".join(candidates.values)},
    )
    return {"candidates": candidates}


def node_select_reasoner(state: AgentState) -> dict[str, Any]:
    rules = state["rules"]
    selected_mode = state.get("reasoner_mode") or state["task"].get("test_fault", {}).get("reasoner_mode", "valid")
    reasoner_override = state.get("reasoner")
    if reasoner_override is not None:
        active_reasoner: Reasoner = adapt_reasoner(reasoner_override)
        if isinstance(active_reasoner, LLMReasoner):
            provider_name = "llm"
            model_name = active_reasoner.config.model
        else:
            provider_name = "injected"
            model_name = type(reasoner_override).__name__
    else:
        provider_config = state.get("reasoner_config") or load_reasoner_config(provider_override=state.get("reasoner_provider"))
        transport_override = state.get("transport")
        if provider_config.provider == "llm" and transport_override is None and provider_config.real_call_enabled:
            transport_override = create_transport(provider_config)
        elif provider_config.provider == "llm" and transport_override is None:
            transport_override = NotConfiguredTransport()
        active_reasoner = create_reasoner(provider_config, transport=transport_override, stub_mode=selected_mode)
        provider_name = provider_config.provider
        model_name = provider_config.model if provider_config.provider == "llm" else str(require_config(rules, "reasoner.model_config_id"))
    state["audit"].record(
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
    return {"active_reasoner": active_reasoner, "provider_name": provider_name, "model_name": model_name, "reasoner_mode": selected_mode}


def node_reasoner_call(state: AgentState) -> dict[str, Any]:
    working_task = state["task"]
    metrics = state["metrics"]
    acos_text = state["acos_text"]
    candidates = state["candidates"]
    rules = state["rules"]
    plan_version = state["plan_version"]
    retry_count = state["retry_count"]
    feedback = state.get("feedback")
    active_reasoner = state["active_reasoner"]
    provider_name = state["provider_name"]
    model_name = state["model_name"]
    audit = state["audit"]

    reasoner_input = build_reasoner_input(working_task, metrics, acos_text, candidates, rules, plan_version, feedback)

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
        result = active_reasoner.reason(reasoner_input)
    except ReasonerError as error:
        return _handle_reasoner_error(state, error)

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
        legacy_output(working_task, metrics, result, rules),
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
    return {"reasoner_result": result, "plan": plan, "issue": None}


def _handle_reasoner_error(state: AgentState, error: ReasonerError) -> dict[str, Any]:
    audit = state["audit"]
    active_reasoner = state["active_reasoner"]
    model_name = state["model_name"]
    plan_version = state["plan_version"]
    retry_count = state["retry_count"]
    rules = state["rules"]
    working_task = state["task"]
    fingerprints = list(state["fingerprints"])
    failures = list(state["failures"])

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
    package = build_manual_intervention_package(working_task, failures, audit.events, rules)
    output = build_manual_agent_output(working_task, issue, package["manual_intervention_package_id"], plan_version, retry_count)
    validate_agent_output(output)
    return {
        "issue": issue,
        "analysis": analysis,
        "failures": failures,
        "fingerprints": fingerprints,
        "output": output,
        "result": WorkflowResult(output=output, audit_events=audit.events, failure_analyses=failures, manual_intervention_package=package),
    }


def node_validate_runtime(state: AgentState) -> dict[str, Any]:
    plan = state["plan"]
    working_task = state["task"]
    rules = state["rules"]
    audit = state["audit"]
    plan_version = state["plan_version"]
    retry_count = state["retry_count"]
    fingerprints = list(state["fingerprints"])
    failures = list(state["failures"])

    validation = validate_runtime(plan, working_task, rules)
    if validation.passed:
        return {"validation": validation, "issue": None, "analysis": None}

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

    if analysis["retry_allowed"]:
        new_retry_count = retry_count + 1
        new_plan_version = plan_version + 1
        working_task = deepcopy(working_task)
        working_task["attempt_id"] = f"attempt-{new_plan_version:04d}"
        audit.set_attempt_id(working_task["attempt_id"])
        audit.record("plan_revised", "retrying", "validating_plan", "Created a new pre-approval attempt and plan version.", plan_version=new_plan_version, metadata={"retry_count": new_retry_count})
        return {
            "validation": validation,
            "issue": issue,
            "analysis": analysis,
            "failures": failures,
            "fingerprints": fingerprints,
            "task": working_task,
            "plan_version": new_plan_version,
            "retry_count": new_retry_count,
            "feedback": analysis,
        }

    audit.record("manual_intervention_required", "retrying", "manual_intervention_required", "Bounded automatic revision stopped without preflight or production write.", plan_version=plan_version, error_code=issue.error_code)
    package = build_manual_intervention_package(working_task, failures, audit.events, rules)
    output = build_manual_agent_output(working_task, issue, package["manual_intervention_package_id"], plan_version, retry_count)
    validate_agent_output(output)
    return {
        "validation": validation,
        "issue": issue,
        "analysis": analysis,
        "failures": failures,
        "fingerprints": fingerprints,
        "output": output,
        "result": WorkflowResult(output=output, audit_events=audit.events, failure_analyses=failures, manual_intervention_package=package),
    }


def node_preflight(state: AgentState) -> dict[str, Any]:
    audit = state["audit"]
    plan_version = state["plan_version"]
    plan = state["plan"]
    rules = state["rules"]

    audit.record("runtime_validation_passed", "validating_plan", "preflighting", "Runtime Schema, reference, rule, and state validation passed.", plan_version=plan_version)
    preflight_result = run_preflight(plan, rules)
    audit.record("preflight_passed", "preflighting", "waiting_for_approval", "Local dry-run preflight passed with zero production writes.", plan_version=plan_version, metadata={"production_write_called": False})
    plan = dict(plan)
    plan["current_status"] = "waiting_for_approval"
    plan["runtime_validation"] = {"passed": True, "error_code": None, "failed_rule_ids": []}
    plan["execution_preflight"] = preflight_result
    validate_agent_output(plan)
    audit.record("waiting_for_approval", "preflighting", "waiting_for_approval", "Plan frozen; automatic modification stopped before human approval.", plan_version=plan_version)
    return {
        "plan": plan,
        "output": plan,
        "result": WorkflowResult(output=plan, audit_events=audit.events, failure_analyses=state["failures"]),
    }



def route_after_evidence(state: AgentState) -> str:
    outcome = state["evidence"].outcome
    if outcome in {"insufficient_evidence", "no_change_required"}:
        return "complete_no_change"
    return "generate_candidates"


def route_after_validation(state: AgentState) -> str:
    if state["validation"].passed:
        return "preflight"
    if state.get("result") is not None:
        return END
    return "reasoner_call"


def route_after_reasoner(state: AgentState) -> str:
    if state.get("issue") is not None and state.get("result") is not None:
        return END
    return "validate_runtime"


def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("load_config", node_load_config)
    graph.add_node("validate_input", node_validate_input)
    graph.add_node("calculate_metrics", node_calculate_metrics)
    graph.add_node("evaluate_evidence", node_evaluate_evidence)
    graph.add_node("complete_no_change", node_complete_no_change)
    graph.add_node("generate_candidates", node_generate_candidates)
    graph.add_node("select_reasoner", node_select_reasoner)
    graph.add_node("reasoner_call", node_reasoner_call)
    graph.add_node("validate_runtime", node_validate_runtime)
    graph.add_node("preflight", node_preflight)

    graph.set_entry_point("load_config")
    graph.add_edge("load_config", "validate_input")
    graph.add_edge("validate_input", "calculate_metrics")
    graph.add_edge("calculate_metrics", "evaluate_evidence")

    graph.add_conditional_edges("evaluate_evidence", route_after_evidence, {
        "complete_no_change": "complete_no_change",
        "generate_candidates": "generate_candidates",
    })
    graph.add_edge("complete_no_change", END)

    graph.add_edge("generate_candidates", "select_reasoner")
    graph.add_edge("select_reasoner", "reasoner_call")

    graph.add_conditional_edges("reasoner_call", route_after_reasoner, {
        END: END,
        "validate_runtime": "validate_runtime",
    })

    graph.add_conditional_edges("validate_runtime", route_after_validation, {
        "preflight": "preflight",
        "reasoner_call": "reasoner_call",
        END: END,
    })

    graph.add_edge("preflight", END)

    return graph


def run_langgraph_workflow(
    task: dict[str, Any],
    *,
    reasoner_mode: str | None = None,
    reasoner: Any | None = None,
    reasoner_provider: str | None = None,
    reasoner_config: LLMReasonerConfig | None = None,
    transport: LLMTransport | None = None,
    config: dict[str, Any] | None = None,
) -> WorkflowResult:
    graph = build_graph()
    compiled = graph.compile()
    initial = _init_state(
        task,
        reasoner_mode=reasoner_mode,
        reasoner=reasoner,
        reasoner_provider=reasoner_provider,
        reasoner_config=reasoner_config,
        transport=transport,
        config=config,
    )
    final = compiled.invoke(initial)
    return final["result"]
