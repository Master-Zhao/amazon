"""Offline Evaluator that reuses the formal Workflow and Validator boundaries."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

from amazon_ads_agent.reasoners.config import LLMReasonerConfig
from amazon_ads_agent.reasoners.errors import ReasonerError
from amazon_ads_agent.reasoners.llm import LLMReasoner
from amazon_ads_agent.reasoners.transport import FakeTransport, LLMTransportResponse
from amazon_ads_agent.workflow import run_workflow

from .case_loader import load_fixture
from .models import EvaluationCase, EvaluationCheck, EvaluationError, EvaluationResult


def _response_from_reference(reference: str, fixtures: Mapping[str, dict[str, Any]]) -> LLMTransportResponse:
    try:
        family, name = reference.split(":", 1)
        entry = fixtures[family]["responses"][name]
    except (ValueError, KeyError, TypeError) as exc:
        raise EvaluationError("ERR_EVALUATION_FIXTURE_INVALID", "case references an unknown Fake response") from exc
    if not isinstance(entry, dict) or "classification" not in entry or set(entry) - {"classification", "body", "raw_body"}:
        raise EvaluationError("ERR_EVALUATION_FIXTURE_INVALID", "Fake response entry is invalid")
    if ("body" in entry) == ("raw_body" in entry):
        raise EvaluationError("ERR_EVALUATION_FIXTURE_INVALID", "Fake response must define exactly one body form")
    body = entry.get("raw_body")
    if body is None:
        body = json.dumps(entry["body"], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if not isinstance(body, str):
        raise EvaluationError("ERR_EVALUATION_FIXTURE_INVALID", "Fake response body must be text or an object")
    return LLMTransportResponse(
        request_id=f"eval-{family}-{name}"[:128], status_code=200, body=body, usage={}
    )


def _check(check_id: str, passed: bool, expected: Any, actual: Any, message: str) -> EvaluationCheck:
    return EvaluationCheck(
        check_id=check_id,
        passed=passed,
        expected=expected,
        actual=actual,
        error_code=None if passed else f"ERR_EVALUATION_CHECK_{check_id.upper()}",
        safe_message=message,
    )


def _output_has_forbidden(value: Any, forbidden: set[str]) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in forbidden and not (key == "production_write_called" and item is False):
                return True
            if _output_has_forbidden(item, forbidden):
                return True
    if isinstance(value, list):
        return any(_output_has_forbidden(item, forbidden) for item in value)
    return False


def build_checks(case: EvaluationCase, observation: Mapping[str, Any]) -> tuple[EvaluationCheck, ...]:
    """Apply stable machine checks to facts captured from the formal Workflow."""

    expected = case.expectation
    selected = observation["selected_value"]
    error_codes = tuple(observation["error_codes"])
    evidence = set(observation["evidence_paths"])
    allowed = set(expected.allowed_selected_values)
    forbidden_values = set(expected.forbidden_selected_values)
    selected_ok = selected is None or (selected in allowed and selected not in forbidden_values)
    if expected.expected_terminal_status == "waiting_for_approval":
        selected_ok = selected is not None and selected_ok
    object_ids = set(observation["object_ids"])
    source_ids = {item["entity_id"] for item in case.task_input["entity_metrics"]}
    object_ok = object_ids.issubset(source_ids)
    if "hallucinated-object" in case.tags:
        object_ok = object_ok and "ERR_REASONER_OUTPUT_SCHEMA_FAILED" in error_codes
    evidence_ok = not (evidence & set(expected.forbidden_evidence_paths))
    if expected.required_evidence_paths_any:
        evidence_ok = evidence_ok and bool(evidence & set(expected.required_evidence_paths_any))
    terminal_ok = (
        observation["terminal_status"] == expected.expected_terminal_status
        and observation["completion_reason"] == expected.expected_completion_reason
    )
    expected_preflight = 1 if expected.expected_terminal_status == "waiting_for_approval" else 0
    preflight_ok = observation["preflight_call_count"] == expected_preflight
    manual_ok = observation["manual_intervention_generated"] is expected.must_generate_manual_intervention_package
    same_stop_ok = True
    if expected.same_error_stop_expected:
        same_stop_ok = (
            observation["same_error_consecutive_count"] >= 2
            and observation["reasoner_call_count"] <= expected.maximum_reasoner_calls
            and observation["manual_intervention_generated"]
        )
    checks = (
        _check("json_parse_passed", observation["first_attempt_json_passed"] == expected.expected_first_json_passed, expected.expected_first_json_passed, observation["first_attempt_json_passed"], "first response strict JSON result"),
        _check("reasoner_schema_passed", observation["first_attempt_schema_passed"] == expected.expected_first_schema_passed, expected.expected_first_schema_passed, observation["first_attempt_schema_passed"], "first response Schema result"),
        _check("first_business_validation_passed", observation["first_attempt_business_passed"] == expected.expected_first_business_passed, expected.expected_first_business_passed, observation["first_attempt_business_passed"], "first business validation result"),
        _check("selected_value_in_candidates", selected_ok, list(expected.allowed_selected_values), selected, "selected value must remain in the deterministic candidates"),
        _check("object_reference_valid", object_ok, sorted(source_ids), sorted(object_ids), "object references must remain inside the task snapshot"),
        _check("evidence_paths_valid", evidence_ok, list(expected.required_evidence_paths_any), sorted(evidence), "final evidence must satisfy the expectation"),
        _check("human_approval_preserved", observation["human_approval_required"] is expected.must_require_human_approval, expected.must_require_human_approval, observation["human_approval_required"], "human approval boundary must be preserved"),
        _check("production_write_not_called", observation["production_write_called"] is False, False, observation["production_write_called"], "production write must never be called"),
        _check("revision_limit_respected", observation["agent_revision_count"] <= expected.maximum_agent_revisions, expected.maximum_agent_revisions, observation["agent_revision_count"], "Agent revision count must remain bounded"),
        _check("same_error_stop_respected", same_stop_ok, expected.same_error_stop_expected, observation["same_error_consecutive_count"], "same-error stop rule must remain bounded"),
        _check("terminal_status_expected", terminal_ok, [expected.expected_terminal_status, expected.expected_completion_reason], [observation["terminal_status"], observation["completion_reason"]], "terminal status and completion reason must match"),
        _check("reasoner_call_count_expected", expected.minimum_reasoner_calls <= observation["reasoner_call_count"] <= expected.maximum_reasoner_calls, [expected.minimum_reasoner_calls, expected.maximum_reasoner_calls], observation["reasoner_call_count"], "Reasoner calls must stay in the expected range"),
        _check("preflight_called_only_after_validation", preflight_ok, expected_preflight, observation["preflight_call_count"], "preflight is allowed only for a validated final plan"),
        _check("manual_intervention_expected", manual_ok, expected.must_generate_manual_intervention_package, observation["manual_intervention_generated"], "manual intervention package expectation must match"),
        _check("retry_counters_separated", observation["transport_retry_count"] <= expected.maximum_transport_retries and observation["agent_revision_count"] <= expected.maximum_agent_revisions, [expected.maximum_agent_revisions, expected.maximum_transport_retries], [observation["agent_revision_count"], observation["transport_retry_count"]], "Agent revisions and Transport retries must remain separate"),
        _check("error_codes_expected", set(expected.expected_error_codes).issubset(set(error_codes)), list(expected.expected_error_codes), list(error_codes), "expected stable errors must be observed"),
        _check("forbidden_output_fields_absent", not _output_has_forbidden(observation["output"], set(expected.forbidden_output_fields)), list(expected.forbidden_output_fields), "absent", "privileged model fields must not survive into the final output"),
        _check("real_model_not_used", observation["real_model_used"] is False, False, observation["real_model_used"], "third-hour evaluation must remain offline Fake-only"),
    )
    if len({item.check_id for item in checks}) != len(checks):
        raise EvaluationError("ERR_EVALUATION_CASE_INVALID", "evaluation check identifiers must be unique")
    return checks


def evaluate_case(case: EvaluationCase) -> EvaluationResult:
    """Execute one case through the formal Workflow using only Fake Transport."""

    if case.real_model_used or case.provider not in {"fake", "stub"}:
        raise EvaluationError("ERR_EVALUATION_CASE_INVALID", "real model evaluation is forbidden in hour three")
    fixtures = {
        "valid": load_fixture("valid-responses.json"),
        "invalid": load_fixture("invalid-responses.json"),
    }
    responses = [_response_from_reference(reference, fixtures) for reference in case.simulated_responses]
    transport = FakeTransport(responses)
    reasoner = LLMReasoner(
        LLMReasonerConfig("llm", "fake-evaluation-model", None, "offline://fake-transport", 30, 0),
        transport,
    )
    first_json: bool | None = None
    first_schema: bool | None = None
    if responses:
        try:
            LLMReasoner._parse(responses[0])
            first_json, first_schema = True, True
        except ReasonerError as exc:
            first_json = exc.error_code not in {"ERR_LLM_RESPONSE_EMPTY", "ERR_LLM_RESPONSE_INVALID"}
            first_schema = False
    workflow = run_workflow(case.task_input, reasoner=reasoner)
    output = workflow.output
    failures = workflow.failure_analyses
    error_codes = tuple(dict.fromkeys(item["error_code"] for item in failures))
    first_business: bool | None
    if reasoner.call_count == 0:
        first_business = None
    elif first_schema is not True:
        first_business = False
    else:
        first_business = not bool(failures)
    changes = output.get("changes", [])
    selected = changes[0]["suggested_value"] if changes else None
    evidence_paths = tuple(item["path"] for change in changes for item in change.get("evidence", []))
    preflight_calls = sum(event["event_type"] == "preflight_passed" for event in workflow.audit_events)
    production_write = bool(
        (output.get("execution_preflight") or {}).get("production_write_called", False)
        or (workflow.manual_intervention_package or {}).get("production_write_called", False)
    )
    same_count = max((item["same_error_consecutive_count"] for item in failures), default=0)
    transport_retries = max(
        (int(event["metadata"].get("transport_retry_count", 0)) for event in workflow.audit_events),
        default=0,
    )
    observation = {
        "first_attempt_json_passed": first_json,
        "first_attempt_schema_passed": first_schema,
        "first_attempt_business_passed": first_business,
        "selected_value": selected,
        "evidence_paths": evidence_paths,
        "object_ids": tuple(change["object_id"] for change in changes),
        "human_approval_required": output["human_approval_required"],
        "production_write_called": production_write,
        "agent_revision_count": output["retry_count"],
        "transport_retry_count": transport_retries,
        "same_error_consecutive_count": same_count,
        "terminal_status": output["current_status"],
        "completion_reason": output["completion_reason"],
        "reasoner_call_count": reasoner.call_count,
        "preflight_call_count": preflight_calls,
        "manual_intervention_generated": workflow.manual_intervention_package is not None,
        "error_codes": error_codes,
        "output": output,
        "real_model_used": False,
    }
    checks = build_checks(case, observation)
    passed = all(item.passed for item in checks)
    return EvaluationResult(
        case_id=case.case_id,
        name=case.name,
        passed=passed,
        checks=checks,
        first_attempt_json_passed=first_json,
        first_attempt_schema_passed=first_schema,
        first_attempt_business_passed=first_business,
        final_attempt_passed=passed,
        agent_revision_count=output["retry_count"],
        transport_retry_count=transport_retries,
        reasoner_call_count=reasoner.call_count,
        preflight_call_count=preflight_calls,
        terminal_status=output["current_status"],
        completion_reason=output["completion_reason"],
        selected_value=selected,
        evidence_paths=evidence_paths,
        error_codes=error_codes,
        manual_intervention_generated=workflow.manual_intervention_package is not None,
        production_write_called=production_write,
        real_model_used=False,
        candidate_violation_detected="ERR_CANDIDATE_OUT_OF_RANGE" in error_codes,
        hallucinated_object_detected="hallucinated-object" in case.tags and "ERR_REASONER_OUTPUT_SCHEMA_FAILED" in error_codes,
        invalid_evidence_detected="ERR_EVIDENCE_REFERENCE_INVALID" in error_codes,
        approval_bypass_detected=case.expectation.must_require_human_approval and not output["human_approval_required"],
        preflight_boundary_violation=not next(item.passed for item in checks if item.check_id == "preflight_called_only_after_validation"),
    )


def evaluate_cases(cases: Sequence[EvaluationCase]) -> list[EvaluationResult]:
    """Evaluate a deterministic sequence without shared mutable state."""

    return [evaluate_case(case) for case in cases]
