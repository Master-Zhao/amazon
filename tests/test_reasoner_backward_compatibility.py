"""PoC-01 compatibility and unchanged five-scenario behavior."""

from __future__ import annotations

import json

import pytest

from conftest import load_example
from amazon_ads_agent.candidate_engine import generate_bid_candidates
from amazon_ads_agent.cli import main
from amazon_ads_agent.reasoner import Reasoner, ReasonerInput, ReasonerResult, ReasonerStub
from amazon_ads_agent.reasoners.stub import ReasonerStub as LayeredReasonerStub
from amazon_ads_agent.workflow import run_workflow


def _context(high_task: dict, config: dict) -> dict:
    return {
        "entity_metrics": high_task["entity_metrics"], "target_acos": high_task["target_acos"],
        "acos": "0.350000", "confidence": config["analysis"]["confidence_threshold"],
    }


def test_old_public_import_reexports_layered_stub() -> None:
    assert ReasonerStub is LayeredReasonerStub


def test_old_public_types_remain_importable() -> None:
    assert Reasoner is not None and ReasonerInput is not None and ReasonerResult is not None


def test_old_select_signature_still_works(high_task: dict, config: dict) -> None:
    candidates = generate_bid_candidates("1.20", config)
    assert ReasonerStub().select(candidates, _context(high_task, config)).suggested_value == "1.08"


@pytest.mark.parametrize(
    ("mode", "expected"),
    [("valid", ["1.08"]), ("invalid_once", ["0.80", "1.08"]), ("always_invalid", ["0.80", "0.80"])],
)
def test_stub_mode_semantics_are_unchanged(mode: str, expected: list[str], high_task: dict, config: dict) -> None:
    reasoner = ReasonerStub(mode)
    candidates = generate_bid_candidates("1.20", config)
    actual = [reasoner.select(candidates, _context(high_task, config), {"feedback": True}).suggested_value for _ in expected]
    assert actual == expected


@pytest.mark.parametrize(
    ("example", "mode", "status", "plan_version", "retry_count"),
    [
        ("high-acos-keyword.json", None, "waiting_for_approval", 1, 0),
        ("insufficient-evidence.json", None, "completed", 0, 0),
        ("no-change-required.json", None, "completed", 0, 0),
        ("invalid-reasoner-output.json", "invalid_once", "waiting_for_approval", 2, 1),
        ("repeated-invalid-output.json", "always_invalid", "manual_intervention_required", 2, 1),
    ],
)
def test_five_example_terminal_states_are_unchanged(
    example: str, mode: str | None, status: str, plan_version: int, retry_count: int
) -> None:
    result = run_workflow(load_example(example), reasoner_mode=mode)
    assert (result.output["current_status"], result.output["plan_version"], result.output["retry_count"]) == (
        status, plan_version, retry_count
    )


def test_invalid_once_still_performs_one_agent_revision() -> None:
    result = run_workflow(load_example("invalid-reasoner-output.json"), reasoner_mode="invalid_once")
    assert sum(event["event_type"] == "plan_revised" for event in result.audit_events) == 1
    assert sum(event["event_type"] == "reasoner_completed" for event in result.audit_events) == 2


def test_always_invalid_still_creates_manual_package() -> None:
    result = run_workflow(load_example("repeated-invalid-output.json"), reasoner_mode="always_invalid")
    assert result.manual_intervention_package is not None
    assert result.manual_intervention_package["same_error_consecutive_count"] == 2
    assert result.manual_intervention_package["production_write_called"] is False


def test_old_cli_command_still_succeeds(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["examples/high-acos-keyword.json"]) == 0
    assert json.loads(capsys.readouterr().out)["agent_output"]["current_status"] == "waiting_for_approval"


def test_old_cli_reasoner_mode_still_succeeds(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["examples/invalid-reasoner-output.json", "--reasoner-mode", "invalid_once"]) == 0
    assert json.loads(capsys.readouterr().out)["agent_output"]["plan_version"] == 2


def test_cli_explicit_stub_provider_succeeds(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["examples/high-acos-keyword.json", "--reasoner-provider", "stub"]) == 0
    assert json.loads(capsys.readouterr().out)["agent_output"]["current_status"] == "waiting_for_approval"


def test_cli_rejects_llm_and_stub_mode_conflict(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["examples/high-acos-keyword.json", "--reasoner-provider", "llm", "--reasoner-mode", "valid"]) == 4
    assert "ERR_LLM_CONFIG_INVALID" in capsys.readouterr().err


def test_waiting_plan_remains_dry_run_only() -> None:
    output = run_workflow(load_example("high-acos-keyword.json")).output
    assert output["human_approval_required"] is True
    assert output["execution_preflight"]["mode"] == "dry_run"
    assert output["execution_preflight"]["production_write_called"] is False
