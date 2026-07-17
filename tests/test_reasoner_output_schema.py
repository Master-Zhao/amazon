"""Positive and adversarial tests for Reasoner Output Schema 1.0."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from amazon_ads_agent.reasoners.errors import ReasonerOutputSchemaError
from amazon_ads_agent.reasoners.output_schema import (
    load_reasoner_output_schema,
    validate_reasoner_output,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _valid() -> dict:
    return {
        "schema_version": "1.0",
        "decision": "select",
        "selected_value": "1.08",
        "reason": "ACoS is above target, so the moderate decrease is selected.",
        "evidence_paths": ["calculated_metrics.acos", "task_context.target_acos"],
        "risk_summary": "A lower bid may reduce traffic and requires human approval.",
        "confidence": "0.840000",
    }


def _assert_schema_failure(document: object) -> None:
    with pytest.raises(ReasonerOutputSchemaError) as caught:
        validate_reasoner_output(document)
    assert caught.value.error_code == "ERR_REASONER_OUTPUT_SCHEMA_FAILED"
    assert caught.value.field_path


def test_valid_output_passes_without_coercion() -> None:
    document = _valid()
    assert validate_reasoner_output(document) is document


def test_schema_is_draft_2020_12_and_self_valid() -> None:
    schema = load_reasoner_output_schema()
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    Draft202012Validator.check_schema(schema)


def test_schema_closes_unknown_fields() -> None:
    assert load_reasoner_output_schema()["additionalProperties"] is False


@pytest.mark.parametrize(
    "field",
    ["schema_version", "decision", "selected_value", "reason", "evidence_paths", "risk_summary", "confidence"],
)
def test_required_fields_are_enforced(field: str) -> None:
    document = _valid()
    del document[field]
    _assert_schema_failure(document)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("schema_version", "2.0"),
        ("decision", "execute"),
        ("selected_value", 1.08),
        ("selected_value", "USD 1.08"),
        ("confidence", 0.84),
        ("confidence", "-0.1"),
        ("confidence", "1.1"),
        ("reason", ""),
        ("reason", "          "),
        ("risk_summary", ""),
        ("risk_summary", "   "),
        ("evidence_paths", []),
        ("evidence_paths", ["target_acos", "target_acos"]),
        ("evidence_paths", [""]),
        ("evidence_paths", ["   "]),
    ],
)
def test_invalid_typed_or_bounded_values_are_rejected(field: str, value: object) -> None:
    document = _valid()
    document[field] = value
    _assert_schema_failure(document)


@pytest.mark.parametrize(
    "field",
    [
        "action",
        "change_id",
        "plan_digest",
        "approval_id",
        "execute_now",
        "execution_status",
        "production_write_called",
        "object_id",
        "object_version",
        "candidate_values",
        "rule_set_version",
        "data_snapshot_id",
    ],
)
def test_privileged_or_extra_fields_are_rejected(field: str) -> None:
    document = _valid()
    document[field] = False if field in {"execute_now", "production_write_called"} else "forbidden"
    _assert_schema_failure(document)


def test_array_root_is_rejected() -> None:
    _assert_schema_failure([_valid()])


def test_missing_schema_file_fails_closed() -> None:
    with pytest.raises(ReasonerOutputSchemaError) as caught:
        load_reasoner_output_schema(FIXTURES / "missing-schema")
    assert caught.value.error_code == "ERR_REASONER_SCHEMA_NOT_FOUND"


def test_invalid_schema_file_fails_closed() -> None:
    with pytest.raises(ReasonerOutputSchemaError) as caught:
        load_reasoner_output_schema(FIXTURES / "invalid-reasoner-schema")
    assert caught.value.error_code == "ERR_REASONER_SCHEMA_INVALID"


def test_validation_does_not_modify_document() -> None:
    document = _valid()
    before = deepcopy(document)
    validate_reasoner_output(document)
    assert document == before
