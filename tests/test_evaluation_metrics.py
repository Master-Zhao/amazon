"""Exact Decimal evaluation metric tests."""

from __future__ import annotations

from dataclasses import replace

from evaluation.case_loader import load_all_cases
from evaluation.evaluator import evaluate_cases
from evaluation.metrics import calculate_summary


def _results():
    return evaluate_cases(load_all_cases())


def test_empty_result_set_is_safe() -> None:
    summary = calculate_summary([])
    assert summary.total_cases == 0
    assert summary.case_pass_rate == "0.000000"
    assert summary.average_reasoner_calls == "0.000000"


def test_all_pass_rate_is_exact_decimal_string() -> None:
    summary = calculate_summary(_results())
    assert summary.case_pass_rate == "1.000000"
    assert isinstance(summary.case_pass_rate, str)


def test_partial_pass_rate_is_exact() -> None:
    results = _results()[:2]
    results[0] = replace(results[0], passed=False, final_attempt_passed=False)
    summary = calculate_summary(results)
    assert summary.case_pass_rate == "0.500000"
    assert summary.final_success_rate == "0.500000"


def test_all_failed_rate_is_zero() -> None:
    results = [replace(item, passed=False, final_attempt_passed=False) for item in _results()[:2]]
    assert calculate_summary(results).case_pass_rate == "0.000000"


def test_first_attempt_rates_are_correct() -> None:
    summary = calculate_summary(_results())
    assert summary.first_json_pass_rate == "1.000000"
    assert summary.first_schema_pass_rate == "0.900000"
    assert summary.first_business_pass_rate == "0.600000"


def test_revision_success_rate_is_exact() -> None:
    summary = calculate_summary(_results())
    assert summary.revision_attempt_case_count == 3
    assert summary.revision_success_count == 2
    assert summary.revision_success_rate == "0.666667"


def test_violation_counts_are_detected() -> None:
    summary = calculate_summary(_results())
    assert summary.candidate_violation_count == 2
    assert summary.hallucinated_object_count == 1
    assert summary.invalid_evidence_count == 1
    assert summary.approval_bypass_count == 0


def test_manual_intervention_count_is_correct() -> None:
    assert calculate_summary(_results()).manual_intervention_count == 2


def test_agent_and_transport_counters_are_separate() -> None:
    summary = calculate_summary(_results())
    assert summary.average_agent_revisions == "0.250000"
    assert summary.total_transport_retries == 0
    assert summary.average_transport_retries == "0.000000"


def test_average_reasoner_calls_is_exact() -> None:
    assert calculate_summary(_results()).average_reasoner_calls == "1.083333"


def test_production_and_preflight_violations_are_zero() -> None:
    summary = calculate_summary(_results())
    assert summary.production_write_violation_count == 0
    assert summary.preflight_boundary_violation_count == 0


def test_production_violation_is_counted() -> None:
    results = _results()[:1]
    results[0] = replace(results[0], production_write_called=True)
    assert calculate_summary(results).production_write_violation_count == 1

