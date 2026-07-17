"""Frozen, JSON-serializable evaluation data models."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


class EvaluationError(ValueError):
    """Stable, safe evaluation configuration error."""

    def __init__(self, error_code: str, safe_message: str) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message

    def __str__(self) -> str:
        return f"{self.error_code}: {self.safe_message}"


@dataclass(frozen=True)
class EvaluationExpectation:
    expectation_schema_version: str
    case_id: str
    expected_terminal_status: str
    expected_completion_reason: str | None
    allowed_selected_values: tuple[str, ...]
    forbidden_selected_values: tuple[str, ...]
    required_evidence_paths_any: tuple[str, ...]
    forbidden_evidence_paths: tuple[str, ...]
    forbidden_output_fields: tuple[str, ...]
    expected_error_codes: tuple[str, ...]
    expected_first_json_passed: bool | None
    expected_first_schema_passed: bool | None
    expected_first_business_passed: bool | None
    must_require_human_approval: bool
    must_generate_manual_intervention_package: bool
    must_not_call_preflight_on_failure: bool
    production_write_called: bool
    minimum_reasoner_calls: int
    maximum_reasoner_calls: int
    maximum_agent_revisions: int
    maximum_transport_retries: int
    same_error_stop_expected: bool


@dataclass(frozen=True)
class EvaluationCase:
    evaluation_schema_version: str
    case_id: str
    name: str
    description: str
    provider: str
    real_model_used: bool
    reasoner_mode: str
    task_input: dict[str, Any]
    reasoner_input_overrides: dict[str, Any]
    simulated_responses: tuple[str, ...]
    expectation_file: str
    tags: tuple[str, ...]
    expectation: EvaluationExpectation


@dataclass(frozen=True)
class EvaluationCheck:
    check_id: str
    passed: bool
    expected: Any
    actual: Any
    error_code: str | None
    safe_message: str


@dataclass(frozen=True)
class EvaluationResult:
    case_id: str
    name: str
    passed: bool
    checks: tuple[EvaluationCheck, ...]
    first_attempt_json_passed: bool | None
    first_attempt_schema_passed: bool | None
    first_attempt_business_passed: bool | None
    final_attempt_passed: bool
    agent_revision_count: int
    transport_retry_count: int
    reasoner_call_count: int
    preflight_call_count: int
    terminal_status: str
    completion_reason: str | None
    selected_value: str | None
    evidence_paths: tuple[str, ...]
    error_codes: tuple[str, ...]
    manual_intervention_generated: bool
    production_write_called: bool
    real_model_used: bool
    candidate_violation_detected: bool = False
    hallucinated_object_detected: bool = False
    invalid_evidence_detected: bool = False
    approval_bypass_detected: bool = False
    preflight_boundary_violation: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EvaluationSummary:
    total_cases: int
    passed_cases: int
    failed_cases: int
    case_pass_rate: str
    first_json_pass_rate: str
    first_schema_pass_rate: str
    first_business_pass_rate: str
    final_success_rate: str
    revision_attempt_case_count: int
    revision_success_count: int
    revision_success_rate: str
    candidate_violation_count: int
    hallucinated_object_count: int
    invalid_evidence_count: int
    approval_bypass_count: int
    manual_intervention_count: int
    average_agent_revisions: str
    average_reasoner_calls: str
    total_transport_retries: int
    average_transport_retries: str
    production_write_violation_count: int
    preflight_boundary_violation_count: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RealEvaluationRun:
    run_id: str
    case_id: str
    name: str
    repetition: int
    passed: bool
    reasoner_required: bool
    first_json_passed: bool | None
    first_schema_passed: bool | None
    first_business_passed: bool | None
    final_json_passed: bool | None
    final_schema_passed: bool | None
    final_business_passed: bool
    terminal_status: str
    selected_value: str | None
    reasoner_call_count: int
    actual_request_count: int
    agent_revision_count: int
    transport_retry_count: int
    manual_intervention_generated: bool
    error_codes: tuple[str, ...]
    production_write_called: bool
    approval_bypass_detected: bool
    final_candidate_violation_detected: bool
    final_hallucinated_object_detected: bool
    final_invalid_evidence_detected: bool
    preflight_boundary_violation: bool
    controlled_failure_injection: bool
    latencies_ms: tuple[int, ...]
    input_token_count: int | None
    output_token_count: int | None
    total_token_count: int | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
