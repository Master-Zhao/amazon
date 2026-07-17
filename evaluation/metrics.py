"""Exact Decimal metrics for deterministic evaluation results."""

from __future__ import annotations

from decimal import Decimal
from typing import Iterable

from amazon_ads_agent.decimal_utils import decimal_to_string

from .models import EvaluationResult, EvaluationSummary


def _ratio(numerator: int, denominator: int) -> str:
    value = Decimal("0") if denominator == 0 else Decimal(numerator) / Decimal(denominator)
    return decimal_to_string(value, places=6)


def _average(values: Iterable[int], count: int) -> str:
    total = sum(values)
    return _ratio(total, count)


def calculate_summary(results: list[EvaluationResult]) -> EvaluationSummary:
    """Aggregate outcomes without floats or division-by-zero behavior."""

    total = len(results)
    passed = sum(item.passed for item in results)
    attempted = [item for item in results if item.first_attempt_json_passed is not None]
    revisions = [item for item in results if item.first_attempt_business_passed is False and item.agent_revision_count > 0]
    revision_success = sum(item.passed and item.terminal_status == "waiting_for_approval" for item in revisions)
    return EvaluationSummary(
        total_cases=total,
        passed_cases=passed,
        failed_cases=total - passed,
        case_pass_rate=_ratio(passed, total),
        first_json_pass_rate=_ratio(sum(item.first_attempt_json_passed is True for item in attempted), len(attempted)),
        first_schema_pass_rate=_ratio(sum(item.first_attempt_schema_passed is True for item in attempted), len(attempted)),
        first_business_pass_rate=_ratio(sum(item.first_attempt_business_passed is True for item in attempted), len(attempted)),
        final_success_rate=_ratio(sum(item.final_attempt_passed for item in results), total),
        revision_attempt_case_count=len(revisions),
        revision_success_count=revision_success,
        revision_success_rate=_ratio(revision_success, len(revisions)),
        candidate_violation_count=sum(item.candidate_violation_detected for item in results),
        hallucinated_object_count=sum(item.hallucinated_object_detected for item in results),
        invalid_evidence_count=sum(item.invalid_evidence_detected for item in results),
        approval_bypass_count=sum(item.approval_bypass_detected for item in results),
        manual_intervention_count=sum(item.manual_intervention_generated for item in results),
        average_agent_revisions=_average((item.agent_revision_count for item in results), total),
        average_reasoner_calls=_average((item.reasoner_call_count for item in results), total),
        total_transport_retries=sum(item.transport_retry_count for item in results),
        average_transport_retries=_average((item.transport_retry_count for item in results), total),
        production_write_violation_count=sum(item.production_write_called for item in results),
        preflight_boundary_violation_count=sum(item.preflight_boundary_violation for item in results),
    )
