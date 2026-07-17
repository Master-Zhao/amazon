"""Runtime Validator reference, candidate, rule, and safety checks."""

from copy import deepcopy

from amazon_ads_agent.runtime_validator import (
    ERR_CANDIDATE_OUT_OF_RANGE,
    ERR_CURRENT_VALUE_MISMATCH,
    ERR_EVIDENCE_REFERENCE_INVALID,
    ERR_OBJECT_REFERENCE_INVALID,
    ERR_OBJECT_VERSION_MISMATCH,
    ERR_PRODUCTION_WRITE_FORBIDDEN,
    ERR_SCHEMA_VALIDATION_FAILED,
    validate_runtime,
)


def test_valid_candidate_plan_passes(valid_candidate_plan: dict, high_task: dict, config: dict) -> None:
    assert validate_runtime(valid_candidate_plan, high_task, config).passed is True


def test_candidate_outside_set_is_rejected(valid_candidate_plan: dict, high_task: dict, config: dict) -> None:
    valid_candidate_plan["changes"][0]["suggested_value"] = "0.80"
    result = validate_runtime(valid_candidate_plan, high_task, config)
    assert result.issue is not None and result.issue.error_code == ERR_CANDIDATE_OUT_OF_RANGE


def test_nonexistent_object_is_rejected(valid_candidate_plan: dict, high_task: dict, config: dict) -> None:
    valid_candidate_plan["changes"][0]["object_id"] = "kw-not-in-snapshot"
    result = validate_runtime(valid_candidate_plan, high_task, config)
    assert result.issue is not None and result.issue.error_code == ERR_OBJECT_REFERENCE_INVALID


def test_current_value_mismatch_is_rejected(valid_candidate_plan: dict, high_task: dict, config: dict) -> None:
    valid_candidate_plan["changes"][0]["expected_current_value"] = "1.21"
    result = validate_runtime(valid_candidate_plan, high_task, config)
    assert result.issue is not None and result.issue.error_code == ERR_CURRENT_VALUE_MISMATCH


def test_object_version_mismatch_is_rejected(valid_candidate_plan: dict, high_task: dict, config: dict) -> None:
    valid_candidate_plan["changes"][0]["expected_object_version"] = "wrong-version"
    result = validate_runtime(valid_candidate_plan, high_task, config)
    assert result.issue is not None and result.issue.error_code == ERR_OBJECT_VERSION_MISMATCH


def test_bad_evidence_path_is_rejected(valid_candidate_plan: dict, high_task: dict, config: dict) -> None:
    valid_candidate_plan["changes"][0]["evidence"][0]["path"] = "entity_metrics[0].unknown"
    result = validate_runtime(valid_candidate_plan, high_task, config)
    assert result.issue is not None and result.issue.error_code == ERR_EVIDENCE_REFERENCE_INVALID


def test_change_plan_requires_human_approval(valid_candidate_plan: dict, high_task: dict, config: dict) -> None:
    valid_candidate_plan["human_approval_required"] = False
    result = validate_runtime(valid_candidate_plan, high_task, config)
    assert result.passed is False
    assert result.issue is not None and result.issue.error_code == ERR_SCHEMA_VALIDATION_FAILED


def test_production_write_true_gets_specific_safety_error(valid_candidate_plan: dict, high_task: dict, config: dict) -> None:
    valid_candidate_plan["execution_preflight"] = {
        "passed": True,
        "preflight_id": "unsafe",
        "mode": "dry_run",
        "request_digest": None,
        "production_write_called": True,
    }
    result = validate_runtime(valid_candidate_plan, high_task, config)
    assert result.issue is not None and result.issue.error_code == ERR_PRODUCTION_WRITE_FORBIDDEN


def test_candidate_values_cannot_be_modified_with_suggestion(valid_candidate_plan: dict, high_task: dict, config: dict) -> None:
    changed = deepcopy(valid_candidate_plan)
    changed["changes"][0]["candidate_values"] = ["0.80"]
    changed["changes"][0]["suggested_value"] = "0.80"
    result = validate_runtime(changed, high_task, config)
    assert result.issue is not None and result.issue.error_code == ERR_CANDIDATE_OUT_OF_RANGE
