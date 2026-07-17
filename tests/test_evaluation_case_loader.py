"""Strict evaluation input loading tests."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from evaluation import case_loader
from evaluation.models import EvaluationError


def _case_raw(case_id: str = "CASE-001") -> dict:
    case = case_loader.load_case(case_id)
    return {key: value for key, value in case.__dict__.items() if key != "expectation"} | {
        "simulated_responses": list(case.simulated_responses), "tags": list(case.tags)
    }


def test_load_single_case() -> None:
    assert case_loader.load_case("CASE-001").name == "high_acos_balanced"


def test_load_case_by_filename() -> None:
    assert case_loader.load_case("case-006-malicious-keyword.json").case_id == "CASE-006"


def test_load_all_cases() -> None:
    assert len(case_loader.load_all_cases()) == 12


def test_case_ids_and_names_are_unique() -> None:
    cases = case_loader.load_all_cases()
    assert len({case.case_id for case in cases}) == len(cases)
    assert len({case.name for case in cases}) == len(cases)


def test_duplicate_case_id_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    duplicate = case_loader.load_case("CASE-001")
    monkeypatch.setattr(case_loader, "load_case", lambda *args, **kwargs: duplicate)
    with pytest.raises(EvaluationError, match="ERR_EVALUATION_DUPLICATE_CASE_ID"):
        case_loader.load_all_cases()


@pytest.mark.parametrize("case_id", [f"CASE-{number:03d}" for number in range(1, 13)])
def test_each_case_has_matching_expectation(case_id: str) -> None:
    case = case_loader.load_case(case_id)
    assert case.expectation.case_id == case.case_id


@pytest.mark.parametrize("name", ["../case.json", "C:/outside.json", "folder/case.json", "case.txt"])
def test_unsafe_case_name_rejected(name: str) -> None:
    with pytest.raises(EvaluationError) as exc:
        case_loader.load_case(name)
    assert exc.value.error_code == "ERR_EVALUATION_PATH_INVALID"


def test_root_outside_evaluation_rejected() -> None:
    with pytest.raises(EvaluationError, match="ERR_EVALUATION_PATH_INVALID"):
        case_loader.load_all_cases(Path.cwd())


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("provider", "openai"),
        ("real_model_used", True),
        ("reasoner_mode", "network"),
        ("case_id", "case-001"),
        ("name", "Not Stable"),
        ("reasoner_input_overrides", {"candidate_values": ["100"]}),
    ],
)
def test_invalid_case_metadata_rejected(field: str, value: object) -> None:
    raw = _case_raw()
    raw[field] = value
    with pytest.raises(EvaluationError, match="ERR_EVALUATION_CASE_INVALID"):
        case_loader._parse_case(raw, case_loader.EVALUATION_ROOT)


def test_unknown_case_field_rejected() -> None:
    raw = _case_raw()
    raw["unexpected"] = True
    with pytest.raises(EvaluationError, match="ERR_EVALUATION_CASE_INVALID"):
        case_loader._parse_case(raw, case_loader.EVALUATION_ROOT)


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("entity_metrics", 0, "current_bid"), 1.2),
        (("entity_metrics", 0, "observed_at"), "2026-07-17T09:00:00"),
    ],
)
def test_invalid_task_decimal_or_timezone_rejected(path: tuple, value: object) -> None:
    raw = _case_raw()
    target = raw["task_input"]
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(EvaluationError, match="ERR_EVALUATION_CASE_INVALID"):
        case_loader._parse_case(raw, case_loader.EVALUATION_ROOT)


def test_missing_expected_rejected() -> None:
    raw = _case_raw()
    raw["expectation_file"] = "missing.expected.json"
    with pytest.raises(EvaluationError, match="ERR_EVALUATION_EXPECTATION_NOT_FOUND"):
        case_loader._parse_case(raw, case_loader.EVALUATION_ROOT)


def test_case_expected_id_mismatch_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    raw = _case_raw()
    expected = json.loads((case_loader.EXPECTED_ROOT / "case-001.expected.json").read_text(encoding="utf-8"))
    expected["case_id"] = "CASE-999"
    monkeypatch.setattr(case_loader, "_read_json", lambda *args, **kwargs: deepcopy(expected))
    with pytest.raises(EvaluationError, match="ERR_EVALUATION_CASE_ID_MISMATCH"):
        case_loader._parse_case(raw, case_loader.EVALUATION_ROOT)


@pytest.mark.parametrize("content", ["", "{broken"])
def test_empty_or_invalid_json_rejected(content: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Path, "is_file", lambda self: True)
    monkeypatch.setattr(Path, "read_text", lambda self, encoding=None: content)
    with pytest.raises(EvaluationError, match="ERR_EVALUATION_CASE_INVALID"):
        case_loader.load_case("case-999-invalid.json")


def test_fixture_collections_load() -> None:
    assert case_loader.load_fixture("valid-responses.json")["test_only"] is True
    assert case_loader.load_fixture("invalid-responses.json")["category"] == "invalid"


@pytest.mark.parametrize("name", ["other.json", "../valid-responses.json"])
def test_fixture_allowlist_rejected(name: str) -> None:
    with pytest.raises(EvaluationError, match="ERR_EVALUATION_PATH_INVALID"):
        case_loader.load_fixture(name)


def test_invalid_fixture_entry_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    invalid = {
        "fixture_schema_version": "1.0", "test_only": True, "category": "invalid",
        "responses": {"bad": {"classification": "unknown", "raw_body": "{}"}},
    }
    monkeypatch.setattr(case_loader, "_read_json", lambda *args, **kwargs: invalid)
    with pytest.raises(EvaluationError, match="ERR_EVALUATION_FIXTURE_INVALID"):
        case_loader.load_fixture("invalid-responses.json")
