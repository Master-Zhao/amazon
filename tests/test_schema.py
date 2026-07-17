"""Draft 2020-12 Schema and semantic input validation tests."""

from __future__ import annotations

from copy import deepcopy

import pytest

from conftest import load_example
from amazon_ads_agent.schema_loader import (
    SchemaValidationError,
    validate_agent_output,
    validate_audit_event,
    validate_failure_analysis,
    validate_task_input,
)
from amazon_ads_agent.workflow import run_workflow


def test_valid_task_input_passes(high_task: dict) -> None:
    validate_task_input(high_task)


def test_unknown_input_field_is_rejected(high_task: dict) -> None:
    high_task["unknown"] = "rejected"
    with pytest.raises(SchemaValidationError):
        validate_task_input(high_task)


def test_decimal_json_number_is_rejected(high_task: dict) -> None:
    high_task["entity_metrics"][0]["spend"] = 315.0
    with pytest.raises(SchemaValidationError):
        validate_task_input(high_task)


def test_clicks_cannot_exceed_impressions(high_task: dict) -> None:
    high_task["entity_metrics"][0]["clicks"] = 25001
    with pytest.raises(SchemaValidationError, match="clicks"):
        validate_task_input(high_task)


def test_orders_cannot_exceed_clicks(high_task: dict) -> None:
    high_task["entity_metrics"][0]["orders"] = 421
    with pytest.raises(SchemaValidationError, match="orders"):
        validate_task_input(high_task)


def test_non_keyword_object_is_rejected(high_task: dict) -> None:
    high_task["entity_metrics"][0]["entity_type"] = "campaign"
    with pytest.raises(SchemaValidationError):
        validate_task_input(high_task)


def test_agent_output_invalid_state_combination_is_rejected(high_task: dict) -> None:
    output = run_workflow(high_task).output
    output["current_status"] = "completed"
    with pytest.raises(SchemaValidationError):
        validate_agent_output(output)


def test_failure_analysis_is_schema_valid() -> None:
    result = run_workflow(load_example("invalid-reasoner-output.json"), reasoner_mode="invalid_once")
    validate_failure_analysis(result.failure_analyses[0])


def test_audit_event_is_schema_valid(high_task: dict) -> None:
    result = run_workflow(high_task)
    validate_audit_event(result.audit_events[0])


def test_date_time_without_offset_is_rejected(high_task: dict) -> None:
    high_task["measurement_at"] = "2026-07-14T23:59:59"
    with pytest.raises(SchemaValidationError):
        validate_task_input(high_task)
