"""Fixed dataset integrity and safety tests."""

from __future__ import annotations

import json
import re
from decimal import Decimal, InvalidOperation

import pytest

from evaluation.case_loader import CASE_ROOT, EXPECTED_ROOT, load_all_cases, load_case


EXPECTED_IDS = {f"CASE-{number:03d}" for number in range(1, 13)}


def test_exact_fixed_case_set_exists() -> None:
    assert {case.case_id for case in load_all_cases()} == EXPECTED_IDS


@pytest.mark.parametrize("case_id", sorted(EXPECTED_IDS))
def test_fixed_case_is_machine_judgeable(case_id: str) -> None:
    case = load_case(case_id)
    assert case.description.strip()
    assert case.tags
    assert case.expectation.expected_terminal_status
    assert (EXPECTED_ROOT / case.expectation_file).is_file()


def test_all_cases_are_offline_fake_only() -> None:
    assert all(case.provider in {"fake", "stub"} and case.real_model_used is False for case in load_all_cases())


def test_all_expectations_forbid_production_write() -> None:
    assert all(case.expectation.production_write_called is False for case in load_all_cases())


def test_dataset_contains_no_credentials_or_production_urls() -> None:
    text = "\n".join(path.read_text(encoding="utf-8") for path in [*CASE_ROOT.glob("*.json"), *EXPECTED_ROOT.glob("*.json")]).lower()
    assert re.search(r"sk-[a-z0-9]{20,}", text) is None
    assert "authorization" not in text
    assert "https://advertising-api.amazon" not in text


@pytest.mark.parametrize("case_id", sorted(EXPECTED_IDS))
def test_candidate_values_are_decimal_strings(case_id: str) -> None:
    expectation = load_case(case_id).expectation
    for value in expectation.allowed_selected_values + expectation.forbidden_selected_values:
        assert isinstance(value, str)
        try:
            Decimal(value)
        except InvalidOperation:
            pytest.fail(f"not a Decimal string: {value}")


def test_case_003_has_one_allowed_candidate() -> None:
    assert len(load_case("CASE-003").expectation.allowed_selected_values) == 1


def test_case_004_never_calls_reasoner() -> None:
    expected = load_case("CASE-004").expectation
    assert expected.minimum_reasoner_calls == expected.maximum_reasoner_calls == 0


@pytest.mark.parametrize("case_id", ["CASE-009", "CASE-011"])
def test_revision_case_allows_exactly_one_revision(case_id: str) -> None:
    assert load_case(case_id).expectation.maximum_agent_revisions == 1


def test_case_012_requires_bounded_manual_intervention() -> None:
    expected = load_case("CASE-012").expectation
    assert expected.must_generate_manual_intervention_package
    assert expected.same_error_stop_expected
    assert expected.maximum_reasoner_calls == 2


def test_case_006_forbids_injected_value() -> None:
    assert "100" in load_case("CASE-006").expectation.forbidden_selected_values


def test_case_007_preserves_human_approval() -> None:
    assert load_case("CASE-007").expectation.must_require_human_approval


def test_case_json_is_plain_data_not_executable_code() -> None:
    for path in CASE_ROOT.glob("*.json"):
        assert isinstance(json.loads(path.read_text(encoding="utf-8")), dict)
        assert path.suffix == ".json"
