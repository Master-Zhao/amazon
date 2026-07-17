"""Draft 2020-12 Schema loading and deterministic semantic validation."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError, ValidationError

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_ROOT = REPOSITORY_ROOT / "schemas"


class SchemaValidationError(ValueError):
    """Raised with a stable code when schema or cross-field validation fails."""

    error_code = "ERR_SCHEMA_VALIDATION_FAILED"


def load_schema(name: str, schema_root: Path | None = None) -> dict[str, Any]:
    """Load and self-check one repository-owned JSON Schema."""

    root = schema_root or SCHEMA_ROOT
    path = root / name
    if not path.is_file():
        raise SchemaValidationError(f"missing Schema: {name}")
    try:
        schema = json.loads(path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
    except (json.JSONDecodeError, SchemaError) as exc:
        raise SchemaValidationError(f"invalid Schema {name}: {exc}") from exc
    return schema


def validate_document(document: dict[str, Any], schema_name: str) -> None:
    """Validate a document and reject unknown or incorrectly formatted fields."""

    schema = load_schema(schema_name)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(document), key=lambda error: list(error.absolute_path))
    if errors:
        first = errors[0]
        path = ".".join(str(part) for part in first.absolute_path) or "$"
        raise SchemaValidationError(f"{schema_name}:{path}: {first.message}")


def validate_task_input(document: dict[str, Any]) -> None:
    """Validate TaskInput Schema plus standard-Schema cross-field invariants."""

    validate_document(document, "task-input.schema.json")
    metrics = document["entity_metrics"]
    entity_ids = [item["entity_id"] for item in metrics]
    if len(entity_ids) != len(set(entity_ids)):
        raise SchemaValidationError("entity_metrics.entity_id values must be unique")
    for index, item in enumerate(metrics):
        if item["clicks"] > item["impressions"]:
            raise SchemaValidationError(f"entity_metrics.{index}.clicks cannot exceed impressions")
        if item["orders"] > item["clicks"]:
            raise SchemaValidationError(f"entity_metrics.{index}.orders cannot exceed clicks")
    start = date.fromisoformat(document["date_range"]["start"])
    end = date.fromisoformat(document["date_range"]["end"])
    if end < start:
        raise SchemaValidationError("date_range.end cannot precede date_range.start")


def validate_agent_output(document: dict[str, Any]) -> None:
    """Validate an intermediate or terminal PoC AgentOutput."""

    validate_document(document, "agent-output.schema.json")


def validate_failure_analysis(document: dict[str, Any]) -> None:
    """Validate a bounded revision FailureAnalysis record."""

    validate_document(document, "failure-analysis.schema.json")


def validate_audit_event(document: dict[str, Any]) -> None:
    """Validate one append-only audit event."""

    validate_document(document, "audit-event.schema.json")
