"""Evaluator checks and formal Workflow integration tests."""

from __future__ import annotations

from copy import deepcopy

import pytest

from evaluation.case_loader import load_all_cases, load_case
from evaluation.evaluator import build_checks, evaluate_case, evaluate_cases


def _observation(case_id: str = "CASE-001") -> tuple:
    case = load_case(case_id)
    result = evaluate_case(case)
    source_id = case.task_input["entity_metrics"][0]["entity_id"]
    return case, {
        "first_attempt_json_passed": result.first_attempt_json_passed,
        "first_attempt_schema_passed": result.first_attempt_schema_passed,
        "first_attempt_business_passed": result.first_attempt_business_passed,
        "selected_value": result.selected_value,
        "evidence_paths": result.evidence_paths,
        "object_ids": (source_id,) if result.selected_value else (),
        "human_approval_required": case.expectation.must_require_human_approval,
        "production_write_called": False,
        "agent_revision_count": result.agent_revision_count,
        "transport_retry_count": result.transport_retry_count,
        "same_error_consecutive_count": 2 if case.expectation.same_error_stop_expected else 0,
        "terminal_status": result.terminal_status,
        "completion_reason": result.completion_reason,
        "reasoner_call_count": result.reasoner_call_count,
        "preflight_call_count": result.preflight_call_count,
        "manual_intervention_generated": result.manual_intervention_generated,
        "error_codes": result.error_codes,
        "output": {"production_write_called": False},
        "real_model_used": False,
    }


@pytest.mark.parametrize("case_id", [f"CASE-{number:03d}" for number in range(1, 13)])
def test_every_fixed_case_passes(case_id: str) -> None:
    result = evaluate_case(load_case(case_id))
    assert result.passed, [check.check_id for check in result.checks if not check.passed]


def test_all_cases_evaluate_in_order() -> None:
    results = evaluate_cases(load_all_cases())
    assert [result.case_id for result in results] == [f"CASE-{number:03d}" for number in range(1, 13)]


@pytest.mark.parametrize(
    ("field", "bad_value", "check_id"),
    [
        ("selected_value", "0.80", "selected_value_in_candidates"),
        ("object_ids", ("kw-9999",), "object_reference_valid"),
        ("evidence_paths", ("calculated_metrics.profit_margin",), "evidence_paths_valid"),
        ("human_approval_required", False, "human_approval_preserved"),
        ("production_write_called", True, "production_write_not_called"),
        ("terminal_status", "completed", "terminal_status_expected"),
        ("reasoner_call_count", 0, "reasoner_call_count_expected"),
        ("reasoner_call_count", 3, "reasoner_call_count_expected"),
        ("agent_revision_count", 2, "revision_limit_respected"),
        ("transport_retry_count", 1, "retry_counters_separated"),
        ("preflight_call_count", 0, "preflight_called_only_after_validation"),
        ("manual_intervention_generated", True, "manual_intervention_expected"),
        ("real_model_used", True, "real_model_not_used"),
    ],
)
def test_machine_check_detects_violation(field: str, bad_value: object, check_id: str) -> None:
    case, observation = _observation()
    observation[field] = bad_value
    checks = {check.check_id: check for check in build_checks(case, observation)}
    assert not checks[check_id].passed
    assert checks[check_id].error_code


def test_forbidden_output_field_detected() -> None:
    case, observation = _observation()
    observation["output"] = {"approval_id": "forbidden"}
    checks = {check.check_id: check for check in build_checks(case, observation)}
    assert not checks["forbidden_output_fields_absent"].passed


def test_case_004_reasoner_and_preflight_are_zero() -> None:
    result = evaluate_case(load_case("CASE-004"))
    assert result.reasoner_call_count == result.preflight_call_count == 0


def test_case_009_invalid_evidence_revises_successfully() -> None:
    result = evaluate_case(load_case("CASE-009"))
    assert result.error_codes == ("ERR_EVIDENCE_REFERENCE_INVALID",)
    assert result.agent_revision_count == 1 and result.reasoner_call_count == 2 and result.passed


def test_case_011_candidate_violation_revises_successfully() -> None:
    result = evaluate_case(load_case("CASE-011"))
    assert result.candidate_violation_detected and result.agent_revision_count == 1 and result.passed


def test_case_012_stops_after_same_error_twice() -> None:
    result = evaluate_case(load_case("CASE-012"))
    assert result.reasoner_call_count == 2
    assert result.manual_intervention_generated
    assert result.terminal_status == "manual_intervention_required"


def test_check_ids_are_stable_and_unique() -> None:
    result = evaluate_case(load_case("CASE-001"))
    ids = [check.check_id for check in result.checks]
    assert len(ids) == len(set(ids)) == 18
