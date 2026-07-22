"""End-to-end LangGraph workflow tests mirroring test_workflow.py."""

from __future__ import annotations

import socket
import subprocess

from conftest import load_example
from amazon_ads_agent.models import CandidateSet, ReasonerOutput
from amazon_ads_agent.langgraph_workflow import run_langgraph_workflow


def test_langgraph_high_acos_waits_for_approval() -> None:
    output = run_langgraph_workflow(load_example("high-acos-keyword.json")).output
    assert output["current_status"] == "waiting_for_approval"
    assert output["human_approval_required"] is True
    assert output["changes"][0]["suggested_value"] == "1.08"


def test_langgraph_insufficient_evidence_completes_without_change() -> None:
    output = run_langgraph_workflow(load_example("insufficient-evidence.json")).output
    assert (output["current_status"], output["completion_reason"]) == ("completed", "insufficient_evidence")
    assert output["changes"] == [] and output["human_approval_required"] is False


def test_langgraph_no_change_required_completes_without_change() -> None:
    output = run_langgraph_workflow(load_example("no-change-required.json")).output
    assert (output["current_status"], output["completion_reason"]) == ("completed", "no_change_required")
    assert output["changes"] == [] and output["execution_preflight"] is None


def test_langgraph_invalid_once_revises_then_succeeds() -> None:
    result = run_langgraph_workflow(load_example("invalid-reasoner-output.json"), reasoner_mode="invalid_once")
    assert result.output["current_status"] == "waiting_for_approval"
    assert len(result.failure_analyses) == 1
    assert result.failure_analyses[0]["next_action"] == "revise_plan"


def test_langgraph_plan_version_increments_after_revision() -> None:
    output = run_langgraph_workflow(load_example("invalid-reasoner-output.json"), reasoner_mode="invalid_once").output
    assert output["plan_version"] == 2 and output["retry_count"] == 1


def test_langgraph_attempt_id_changes_after_revision() -> None:
    task = load_example("invalid-reasoner-output.json")
    original = task["attempt_id"]
    output = run_langgraph_workflow(task, reasoner_mode="invalid_once").output
    assert output["attempt_id"] != original


def test_langgraph_same_error_twice_stops_automatic_revision() -> None:
    result = run_langgraph_workflow(load_example("repeated-invalid-output.json"), reasoner_mode="always_invalid")
    assert result.output["current_status"] == "manual_intervention_required"
    assert result.failure_analyses[-1]["same_error_consecutive_count"] == 2
    assert result.failure_analyses[-1]["retry_allowed"] is False


class ChangingInvalidReasoner:
    def __init__(self) -> None:
        self.call_count = 0

    def select(self, candidates: CandidateSet, context: dict, feedback: dict | None = None) -> ReasonerOutput:
        values = ("0.80", "0.79", "0.78", "0.77")
        selected = values[self.call_count]
        self.call_count += 1
        entity = context["entity_metrics"][0]
        return ReasonerOutput(
            selected,
            "test-only changing invalid candidate",
            (
                {"path": "entity_metrics[0].spend", "value": entity["spend"]},
                {"path": "entity_metrics[0].sales", "value": entity["sales"]},
                {"path": "target_acos", "value": context["target_acos"]},
            ),
            context["confidence"],
            "medium",
        )


def test_langgraph_automatic_revisions_never_exceed_three() -> None:
    reasoner = ChangingInvalidReasoner()
    result = run_langgraph_workflow(load_example("high-acos-keyword.json"), reasoner=reasoner)
    assert result.output["current_status"] == "manual_intervention_required"
    assert result.output["retry_count"] == 3
    assert result.output["plan_version"] == 4
    assert reasoner.call_count == 4


class CountingValidReasoner:
    def __init__(self) -> None:
        self.call_count = 0

    def select(self, candidates: CandidateSet, context: dict, feedback: dict | None = None) -> ReasonerOutput:
        self.call_count += 1
        entity = context["entity_metrics"][0]
        return ReasonerOutput(
            candidates.values[1],
            "valid counted selection",
            (
                {"path": "entity_metrics[0].spend", "value": entity["spend"]},
                {"path": "entity_metrics[0].sales", "value": entity["sales"]},
                {"path": "target_acos", "value": context["target_acos"]},
            ),
            context["confidence"],
            "medium",
        )


def test_langgraph_validation_success_stops_further_reasoner_calls() -> None:
    reasoner = CountingValidReasoner()
    result = run_langgraph_workflow(load_example("high-acos-keyword.json"), reasoner=reasoner)
    assert result.output["current_status"] == "waiting_for_approval"
    assert reasoner.call_count == 1


def test_langgraph_preflight_passes_without_production_write() -> None:
    preflight = run_langgraph_workflow(load_example("high-acos-keyword.json")).output["execution_preflight"]
    assert preflight["passed"] is True
    assert preflight["production_write_called"] is False


def test_langgraph_every_terminal_path_keeps_production_write_false_or_absent() -> None:
    cases = (
        ("high-acos-keyword.json", "valid"),
        ("insufficient-evidence.json", "valid"),
        ("no-change-required.json", "valid"),
        ("invalid-reasoner-output.json", "invalid_once"),
        ("repeated-invalid-output.json", "always_invalid"),
    )
    for filename, mode in cases:
        preflight = run_langgraph_workflow(load_example(filename), reasoner_mode=mode).output["execution_preflight"]
        assert preflight is None or preflight["production_write_called"] is False


def test_langgraph_workflow_does_not_access_network(monkeypatch) -> None:
    def blocked_socket(*args, **kwargs):
        raise AssertionError("network access is forbidden")

    monkeypatch.setattr(socket, "socket", blocked_socket)
    assert run_langgraph_workflow(load_example("high-acos-keyword.json")).output["current_status"] == "waiting_for_approval"


def test_langgraph_workflow_does_not_start_development_tests(monkeypatch) -> None:
    def blocked_process(*args, **kwargs):
        raise AssertionError("runtime test process is forbidden")

    monkeypatch.setattr(subprocess, "run", blocked_process)
    monkeypatch.setattr(subprocess, "Popen", blocked_process)
    assert run_langgraph_workflow(load_example("high-acos-keyword.json")).output["current_status"] == "waiting_for_approval"


def test_langgraph_key_workflow_steps_are_audited() -> None:
    events = {event["event_type"] for event in run_langgraph_workflow(load_example("invalid-reasoner-output.json"), reasoner_mode="invalid_once").audit_events}
    required = {
        "task_loaded", "schema_validated", "metrics_calculated", "evidence_evaluated",
        "candidates_generated", "reasoner_completed", "runtime_validation_failed",
        "failure_analyzed", "plan_revised", "runtime_validation_passed",
        "preflight_passed", "waiting_for_approval",
    }
    assert required <= events


def test_langgraph_audit_step_ids_are_unique() -> None:
    events = run_langgraph_workflow(load_example("high-acos-keyword.json")).audit_events
    assert len({event["step_id"] for event in events}) == len(events)