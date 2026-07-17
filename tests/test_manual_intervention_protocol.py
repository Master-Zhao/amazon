"""V0.2.1 ManualInterventionPackage Schema and state protocol tests."""

from __future__ import annotations

from copy import deepcopy

import pytest

from conftest import load_example
from amazon_ads_agent.schema_loader import (
    SchemaValidationError,
    validate_agent_output,
    validate_manual_intervention_package,
)
from amazon_ads_agent.workflow import run_workflow


@pytest.fixture
def manual_result():
    return run_workflow(load_example("repeated-invalid-output.json"), reasoner_mode="always_invalid")


@pytest.fixture
def valid_package(manual_result) -> dict:
    assert manual_result.manual_intervention_package is not None
    return deepcopy(manual_result.manual_intervention_package)


def test_valid_manual_intervention_package_passes(valid_package: dict) -> None:
    validate_manual_intervention_package(valid_package)


def test_missing_package_id_is_rejected(valid_package: dict) -> None:
    del valid_package["manual_intervention_package_id"]
    with pytest.raises(SchemaValidationError):
        validate_manual_intervention_package(valid_package)


def test_production_write_true_is_rejected(valid_package: dict) -> None:
    valid_package["production_write_called"] = True
    with pytest.raises(SchemaValidationError):
        validate_manual_intervention_package(valid_package)


def test_nonterminal_original_run_is_rejected(valid_package: dict) -> None:
    valid_package["original_run_terminal"] = False
    with pytest.raises(SchemaValidationError):
        validate_manual_intervention_package(valid_package)


def test_incomplete_attempt_history_is_rejected(valid_package: dict) -> None:
    del valid_package["attempt_history"][0]["error_fingerprint"]
    with pytest.raises(SchemaValidationError):
        validate_manual_intervention_package(valid_package)


def test_unknown_package_field_is_rejected(valid_package: dict) -> None:
    valid_package["unknown"] = "rejected"
    with pytest.raises(SchemaValidationError):
        validate_manual_intervention_package(valid_package)


def test_created_at_without_timezone_is_rejected(valid_package: dict) -> None:
    valid_package["created_at"] = "2026-07-17T12:00:00"
    with pytest.raises(SchemaValidationError):
        validate_manual_intervention_package(valid_package)


def test_manual_agent_output_references_package_and_has_no_preflight(manual_result) -> None:
    output = manual_result.output
    package = manual_result.manual_intervention_package
    validate_agent_output(output)
    assert package is not None
    assert output["manual_intervention_package_id"] == package["manual_intervention_package_id"]
    assert output["execution_preflight"] is None
    assert output["human_approval_required"] is False


def test_manual_agent_output_without_package_reference_is_rejected(manual_result) -> None:
    output = deepcopy(manual_result.output)
    output["manual_intervention_package_id"] = None
    with pytest.raises(SchemaValidationError):
        validate_agent_output(output)


def test_waiting_plan_cannot_reference_manual_package() -> None:
    output = run_workflow(load_example("high-acos-keyword.json")).output
    output["manual_intervention_package_id"] = "mip-0123456789abcdef"
    with pytest.raises(SchemaValidationError):
        validate_agent_output(output)


def test_attempt_history_matches_failure_analyses(manual_result) -> None:
    package = manual_result.manual_intervention_package
    assert package is not None
    assert len(package["attempt_history"]) == len(manual_result.failure_analyses) == 2
    assert [item["error_fingerprint"] for item in package["attempt_history"]] == [
        failure["error_fingerprint"] for failure in manual_result.failure_analyses
    ]
    assert package["original_run_terminal"] is True
    assert package["recovery_constraints"]["new_run_id_required"] is True


def test_package_references_terminal_audit_event(manual_result) -> None:
    package = manual_result.manual_intervention_package
    assert package is not None
    terminal_event = manual_result.audit_events[-1]
    assert terminal_event["event_type"] == "manual_intervention_required"
    assert terminal_event["event_id"] in package["audit_event_ids"]
