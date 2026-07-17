"""Draft 2020-12 validation for the independent Reasoner output contract."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from ..schema_loader import SCHEMA_ROOT
from .errors import ReasonerOutputSchemaError

SCHEMA_NAME = "reasoner-output.schema.json"


def load_reasoner_output_schema(schema_root: Path | None = None) -> dict[str, Any]:
    """Load and self-check the repository-owned Reasoner output Schema."""

    path = (schema_root or SCHEMA_ROOT) / SCHEMA_NAME
    if not path.is_file():
        raise ReasonerOutputSchemaError(
            "ERR_REASONER_SCHEMA_NOT_FOUND", "Reasoner output Schema is missing"
        )
    try:
        schema = json.loads(path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
    except (OSError, UnicodeError, json.JSONDecodeError, SchemaError) as exc:
        raise ReasonerOutputSchemaError(
            "ERR_REASONER_SCHEMA_INVALID", "Reasoner output Schema is invalid"
        ) from exc
    return schema


def validate_reasoner_output(document: Any, schema_root: Path | None = None) -> dict[str, Any]:
    """Validate without coercion and return the same typed document."""

    schema = load_reasoner_output_schema(schema_root)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(document), key=lambda error: list(error.absolute_path))
    if errors:
        first = errors[0]
        field_path = ".".join(str(part) for part in first.absolute_path) or "$"
        raise ReasonerOutputSchemaError(
            "ERR_REASONER_OUTPUT_SCHEMA_FAILED",
            f"Reasoner output failed Schema validation at {field_path}",
            field_path=field_path,
        )
    assert isinstance(document, dict)
    return document
