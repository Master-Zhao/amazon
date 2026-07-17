"""Strict loader for repository-owned evaluation cases and fixtures."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from amazon_ads_agent.schema_loader import SchemaValidationError, validate_task_input

from .models import EvaluationCase, EvaluationError, EvaluationExpectation

EVALUATION_ROOT = Path(__file__).resolve().parent
CASE_ROOT = EVALUATION_ROOT / "cases"
EXPECTED_ROOT = EVALUATION_ROOT / "expected"
FIXTURE_ROOT = EVALUATION_ROOT / "fixtures"

CASE_FIELDS = {
    "evaluation_schema_version", "case_id", "name", "description", "provider", "real_model_used",
    "reasoner_mode", "task_input", "reasoner_input_overrides", "simulated_responses", "expectation_file", "tags",
}
EXPECTATION_FIELDS = {
    "expectation_schema_version", "case_id", "expected_terminal_status", "expected_completion_reason",
    "allowed_selected_values", "forbidden_selected_values", "required_evidence_paths_any",
    "forbidden_evidence_paths", "forbidden_output_fields", "expected_error_codes",
    "expected_first_json_passed", "expected_first_schema_passed", "expected_first_business_passed",
    "must_require_human_approval", "must_generate_manual_intervention_package",
    "must_not_call_preflight_on_failure", "production_write_called", "minimum_reasoner_calls",
    "maximum_reasoner_calls", "maximum_agent_revisions", "maximum_transport_retries", "same_error_stop_expected",
}
FIXTURE_FIELDS = {"fixture_schema_version", "test_only", "category", "responses"}
FIXTURE_ENTRY_FIELDS = {"classification", "body", "raw_body"}
FIXTURE_CLASSIFICATIONS = {"valid", "json_invalid", "schema_invalid", "business_invalid"}
DECIMAL_PATTERN = re.compile(r"^(0|[1-9][0-9]*)(\.[0-9]+)?$")
CASE_ID_PATTERN = re.compile(r"^CASE-[0-9]{3}$")
CASE_NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*$")


def _read_json(path: Path, *, missing_code: str, invalid_code: str) -> Any:
    if not path.is_file():
        raise EvaluationError(missing_code, f"required evaluation file is missing: {path.name}")
    try:
        content = path.read_text(encoding="utf-8")
        if not content.strip():
            raise ValueError("empty file")
        return json.loads(content)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise EvaluationError(invalid_code, f"evaluation JSON is invalid: {path.name}") from exc


def _safe_name(name: str, suffix: str) -> str:
    path = Path(name)
    if path.is_absolute() or path.name != name or ".." in path.parts or not name.endswith(suffix):
        raise EvaluationError("ERR_EVALUATION_PATH_INVALID", "evaluation path must be a repository-owned file name")
    return name


def _tuple_strings(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise EvaluationError("ERR_EVALUATION_EXPECTATION_INVALID", f"{field} must be a string array")
    return tuple(value)


def _evaluation_root(root: Path | None) -> Path:
    base = (root or EVALUATION_ROOT).resolve()
    if not base.is_relative_to(EVALUATION_ROOT.resolve()):
        raise EvaluationError("ERR_EVALUATION_PATH_INVALID", "evaluation input root must remain inside evaluation")
    return base


def _load_expectation(name: str, case_id: str, root: Path) -> EvaluationExpectation:
    safe = _safe_name(name, ".expected.json")
    raw = _read_json(root / "expected" / safe, missing_code="ERR_EVALUATION_EXPECTATION_NOT_FOUND", invalid_code="ERR_EVALUATION_EXPECTATION_INVALID")
    if not isinstance(raw, dict) or set(raw) != EXPECTATION_FIELDS:
        raise EvaluationError("ERR_EVALUATION_EXPECTATION_INVALID", "expectation fields do not match version 1.0")
    if raw["expectation_schema_version"] != "1.0":
        raise EvaluationError("ERR_EVALUATION_EXPECTATION_INVALID", "unsupported expectation version")
    if raw["case_id"] != case_id:
        raise EvaluationError("ERR_EVALUATION_CASE_ID_MISMATCH", "case and expectation identifiers differ")
    for field in ("allowed_selected_values", "forbidden_selected_values"):
        values = _tuple_strings(raw[field], field)
        if any(DECIMAL_PATTERN.fullmatch(item) is None for item in values):
            raise EvaluationError("ERR_EVALUATION_EXPECTATION_INVALID", f"{field} must contain Decimal strings")
    if raw["production_write_called"] is not False:
        raise EvaluationError("ERR_EVALUATION_EXPECTATION_INVALID", "production_write_called must be false")
    optional_bools = ("expected_first_json_passed", "expected_first_schema_passed", "expected_first_business_passed")
    required_bools = (
        "must_require_human_approval", "must_generate_manual_intervention_package",
        "must_not_call_preflight_on_failure", "same_error_stop_expected",
    )
    count_fields = (
        "minimum_reasoner_calls", "maximum_reasoner_calls", "maximum_agent_revisions",
        "maximum_transport_retries",
    )
    if any(raw[field] is not None and not isinstance(raw[field], bool) for field in optional_bools):
        raise EvaluationError("ERR_EVALUATION_EXPECTATION_INVALID", "first-attempt expectations must be booleans or null")
    if any(not isinstance(raw[field], bool) for field in required_bools):
        raise EvaluationError("ERR_EVALUATION_EXPECTATION_INVALID", "expectation flags must be booleans")
    if any(type(raw[field]) is not int or raw[field] < 0 for field in count_fields):
        raise EvaluationError("ERR_EVALUATION_EXPECTATION_INVALID", "expectation counters must be non-negative integers")
    if raw["minimum_reasoner_calls"] > raw["maximum_reasoner_calls"]:
        raise EvaluationError("ERR_EVALUATION_EXPECTATION_INVALID", "minimum Reasoner calls exceeds maximum")
    return EvaluationExpectation(
        **{
            **raw,
            "allowed_selected_values": _tuple_strings(raw["allowed_selected_values"], "allowed_selected_values"),
            "forbidden_selected_values": _tuple_strings(raw["forbidden_selected_values"], "forbidden_selected_values"),
            "required_evidence_paths_any": _tuple_strings(raw["required_evidence_paths_any"], "required_evidence_paths_any"),
            "forbidden_evidence_paths": _tuple_strings(raw["forbidden_evidence_paths"], "forbidden_evidence_paths"),
            "forbidden_output_fields": _tuple_strings(raw["forbidden_output_fields"], "forbidden_output_fields"),
            "expected_error_codes": _tuple_strings(raw["expected_error_codes"], "expected_error_codes"),
        }
    )


def _parse_case(raw: Any, root: Path) -> EvaluationCase:
    if not isinstance(raw, dict) or set(raw) != CASE_FIELDS:
        raise EvaluationError("ERR_EVALUATION_CASE_INVALID", "case fields do not match version 1.0")
    if raw["evaluation_schema_version"] != "1.0" or raw["provider"] not in {"fake", "stub"}:
        raise EvaluationError("ERR_EVALUATION_CASE_INVALID", "unsupported case version or provider")
    if raw["real_model_used"] is not False:
        raise EvaluationError("ERR_EVALUATION_CASE_INVALID", "real_model_used must be false")
    if not isinstance(raw["case_id"], str) or CASE_ID_PATTERN.fullmatch(raw["case_id"]) is None:
        raise EvaluationError("ERR_EVALUATION_CASE_INVALID", "case_id must use CASE-xxx")
    if not isinstance(raw["name"], str) or CASE_NAME_PATTERN.fullmatch(raw["name"]) is None:
        raise EvaluationError("ERR_EVALUATION_CASE_INVALID", "case name must be stable snake_case")
    if raw["reasoner_mode"] != "fake_sequence":
        raise EvaluationError("ERR_EVALUATION_CASE_INVALID", "reasoner_mode must be fake_sequence")
    if not isinstance(raw["description"], str) or not raw["description"].strip():
        raise EvaluationError("ERR_EVALUATION_CASE_INVALID", "case description is required")
    tags = _tuple_strings(raw["tags"], "tags")
    responses = _tuple_strings(raw["simulated_responses"], "simulated_responses")
    if not tags or not isinstance(raw["task_input"], dict) or raw["reasoner_input_overrides"] != {}:
        raise EvaluationError("ERR_EVALUATION_CASE_INVALID", "case task, tags, or overrides are invalid")
    try:
        validate_task_input(raw["task_input"])
    except SchemaValidationError as exc:
        raise EvaluationError("ERR_EVALUATION_CASE_INVALID", "case TaskInput failed the formal Schema") from exc
    expectation = _load_expectation(raw["expectation_file"], raw["case_id"], root)
    return EvaluationCase(
        **{**raw, "simulated_responses": responses, "tags": tags, "expectation": expectation}
    )


def load_case(name_or_id: str, root: Path | None = None) -> EvaluationCase:
    """Load one allow-scoped case by file name or CASE identifier."""

    base = _evaluation_root(root)
    if name_or_id.startswith("CASE-") and re.fullmatch(r"CASE-[0-9]{3}", name_or_id):
        matches = sorted((base / "cases").glob(f"case-{name_or_id[-3:]}-*.json"))
        if len(matches) != 1:
            raise EvaluationError("ERR_EVALUATION_CASE_NOT_FOUND", "requested evaluation case does not exist")
        path = matches[0]
    else:
        path = base / "cases" / _safe_name(name_or_id, ".json")
    raw = _read_json(path, missing_code="ERR_EVALUATION_CASE_NOT_FOUND", invalid_code="ERR_EVALUATION_CASE_INVALID")
    return _parse_case(raw, base)


def load_all_cases(root: Path | None = None) -> list[EvaluationCase]:
    """Load all cases and reject duplicate IDs, names, or orphan expectations."""

    base = _evaluation_root(root)
    cases = [load_case(path.name, base) for path in sorted((base / "cases").glob("case-*.json"))]
    ids = [case.case_id for case in cases]
    names = [case.name for case in cases]
    if len(ids) != len(set(ids)) or len(names) != len(set(names)):
        raise EvaluationError("ERR_EVALUATION_DUPLICATE_CASE_ID", "case_id and name must be globally unique")
    referenced = {case.expectation_file for case in cases}
    existing = {path.name for path in (base / "expected").glob("case-*.expected.json")}
    if referenced != existing:
        raise EvaluationError("ERR_EVALUATION_EXPECTATION_INVALID", "every case must have exactly one expectation")
    return cases


def load_fixture(name: str, root: Path | None = None) -> dict[str, Any]:
    """Load one strict, test-only response fixture collection."""

    base = _evaluation_root(root)
    safe = _safe_name(name, ".json")
    if safe not in {"valid-responses.json", "invalid-responses.json"}:
        raise EvaluationError("ERR_EVALUATION_PATH_INVALID", "fixture name is not allowed")
    raw = _read_json(base / "fixtures" / safe, missing_code="ERR_EVALUATION_FIXTURE_INVALID", invalid_code="ERR_EVALUATION_FIXTURE_INVALID")
    if not isinstance(raw, dict) or set(raw) != FIXTURE_FIELDS or raw["fixture_schema_version"] != "1.0" or raw["test_only"] is not True or not isinstance(raw["responses"], dict) or not raw["responses"]:
        raise EvaluationError("ERR_EVALUATION_FIXTURE_INVALID", "fixture fields do not match version 1.0")
    for key, entry in raw["responses"].items():
        if not isinstance(key, str) or not key or not isinstance(entry, dict):
            raise EvaluationError("ERR_EVALUATION_FIXTURE_INVALID", "fixture response entry is invalid")
        if not {"classification"} <= set(entry) <= FIXTURE_ENTRY_FIELDS:
            raise EvaluationError("ERR_EVALUATION_FIXTURE_INVALID", "fixture response fields are invalid")
        if entry["classification"] not in FIXTURE_CLASSIFICATIONS or (("body" in entry) == ("raw_body" in entry)):
            raise EvaluationError("ERR_EVALUATION_FIXTURE_INVALID", "fixture response classification or body is invalid")
        if "body" in entry and not isinstance(entry["body"], dict):
            raise EvaluationError("ERR_EVALUATION_FIXTURE_INVALID", "fixture body must be an object")
        if "raw_body" in entry and not isinstance(entry["raw_body"], str):
            raise EvaluationError("ERR_EVALUATION_FIXTURE_INVALID", "fixture raw_body must be text")
    return raw
