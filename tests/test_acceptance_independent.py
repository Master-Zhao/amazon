"""Independent adversarial acceptance tests for the frozen PoC-01 boundary."""

from __future__ import annotations

import json
from copy import deepcopy

import pytest

from conftest import load_example
from amazon_ads_agent.cli import main
from amazon_ads_agent.config_loader import RuleConfigError
from amazon_ads_agent.models import CandidateSet, ReasonerOutput
from amazon_ads_agent.post_processor import calculate_plan_digest
from amazon_ads_agent.runtime_validator import (
    ERR_CANDIDATE_OUT_OF_RANGE,
    ERR_CURRENT_VALUE_MISMATCH,
    ERR_EVIDENCE_REFERENCE_INVALID,
    ERR_OBJECT_REFERENCE_INVALID,
    ERR_OBJECT_VERSION_MISMATCH,
    ERR_PLAN_DIGEST_MISMATCH,
    validate_runtime,
)
from amazon_ads_agent.workflow import run_workflow


def _validated_error(plan: dict, task: dict, config: dict) -> str:
    result = validate_runtime(plan, task, config)
    assert result.passed is False and result.issue is not None
    return result.issue.error_code


def _refresh_digest(plan: dict) -> None:
    plan["plan_digest"] = calculate_plan_digest(plan)


def test_out_of_candidate_value_is_rejected_before_preflight(valid_candidate_plan: dict, high_task: dict, config: dict) -> None:
    valid_candidate_plan["changes"][0]["suggested_value"] = "0.80"
    _refresh_digest(valid_candidate_plan)
    assert _validated_error(valid_candidate_plan, high_task, config) == ERR_CANDIDATE_OUT_OF_RANGE


def test_fabricated_object_is_rejected(valid_candidate_plan: dict, high_task: dict, config: dict) -> None:
    valid_candidate_plan["changes"][0]["object_id"] = "kw-9999"
    _refresh_digest(valid_candidate_plan)
    assert _validated_error(valid_candidate_plan, high_task, config) == ERR_OBJECT_REFERENCE_INVALID


def test_mismatched_current_value_is_rejected(valid_candidate_plan: dict, high_task: dict, config: dict) -> None:
    valid_candidate_plan["changes"][0]["expected_current_value"] = "1.30"
    _refresh_digest(valid_candidate_plan)
    assert _validated_error(valid_candidate_plan, high_task, config) == ERR_CURRENT_VALUE_MISMATCH


def test_mismatched_object_version_is_rejected(valid_candidate_plan: dict, high_task: dict, config: dict) -> None:
    valid_candidate_plan["changes"][0]["expected_object_version"] = "etag-v6"
    _refresh_digest(valid_candidate_plan)
    assert _validated_error(valid_candidate_plan, high_task, config) == ERR_OBJECT_VERSION_MISMATCH


def test_nonexistent_evidence_path_is_rejected(valid_candidate_plan: dict, high_task: dict, config: dict) -> None:
    valid_candidate_plan["changes"][0]["evidence"][0]["path"] = "entity_metrics[0].not_present"
    _refresh_digest(valid_candidate_plan)
    assert _validated_error(valid_candidate_plan, high_task, config) == ERR_EVIDENCE_REFERENCE_INVALID


class NeverCalledReasoner:
    """Proves config validation fails before untrusted reasoning starts."""

    def __init__(self) -> None:
        self.call_count = 0

    def select(self, candidates: CandidateSet, context: dict, feedback: dict | None = None) -> ReasonerOutput:
        self.call_count += 1
        raise AssertionError("Reasoner must not run when critical config is missing")


@pytest.mark.parametrize(
    ("section", "key"),
    [
        ("keyword_bid", "max_decrease_ratio"),
        ("keyword_bid", "bid_step"),
        ("keyword_bid", "min_bid"),
        ("keyword_bid", "max_bid"),
        ("runtime", "max_automatic_revisions"),
        ("runtime", "stop_on_same_error_consecutive_count"),
    ],
)
def test_missing_critical_config_fails_closed_before_reasoner(section: str, key: str, high_task: dict, config: dict) -> None:
    attacked = deepcopy(config)
    del attacked[section][key]
    reasoner = NeverCalledReasoner()
    with pytest.raises(RuleConfigError, match="ERR_RULE_CONFIG_MISSING"):
        run_workflow(high_task, config=attacked, reasoner=reasoner)
    assert reasoner.call_count == 0


def test_production_write_switch_attack_is_rejected(high_task: dict, config: dict) -> None:
    attacked = deepcopy(config)
    attacked["runtime"]["production_write_enabled"] = True
    with pytest.raises(RuleConfigError, match="ERR_PRODUCTION_WRITE_FORBIDDEN"):
        run_workflow(high_task, config=attacked)


@pytest.mark.parametrize(
    "field",
    [
        "suggested_value",
        "candidate_values",
        "reason",
        "evidence",
        "expected_current_value",
        "expected_object_version",
    ],
)
def test_old_digest_reuse_is_rejected_for_every_frozen_field(
    field: str, valid_candidate_plan: dict, high_task: dict, config: dict
) -> None:
    change = valid_candidate_plan["changes"][0]
    old_digest = valid_candidate_plan["plan_digest"]
    if field == "suggested_value":
        change[field] = "1.14"
    elif field == "candidate_values":
        change[field] = ["1.02", "1.08", "1.14", "1.20"]
    elif field == "reason":
        change[field] = f"{change[field]} tampered"
    elif field == "evidence":
        change[field][0]["value"] = "316.00"
    elif field == "expected_current_value":
        change[field] = "1.30"
    else:
        change[field] = "etag-v6"
    assert valid_candidate_plan["plan_digest"] == old_digest
    assert _validated_error(valid_candidate_plan, high_task, config) == ERR_PLAN_DIGEST_MISMATCH


class CountingValidReasoner:
    """Independent counter proving a frozen valid plan is not revised again."""

    def __init__(self) -> None:
        self.call_count = 0

    def select(self, candidates: CandidateSet, context: dict, feedback: dict | None = None) -> ReasonerOutput:
        self.call_count += 1
        entity = context["entity_metrics"][0]
        return ReasonerOutput(
            candidates.values[1],
            "independent valid selection",
            (
                {"path": "entity_metrics[0].spend", "value": entity["spend"]},
                {"path": "entity_metrics[0].sales", "value": entity["sales"]},
                {"path": "target_acos", "value": context["target_acos"]},
            ),
            context["confidence"],
            "medium",
        )


def test_success_freezes_attempt_and_stops_reasoner() -> None:
    reasoner = CountingValidReasoner()
    result = run_workflow(load_example("high-acos-keyword.json"), reasoner=reasoner)
    assert result.output["current_status"] == "waiting_for_approval"
    assert result.output["plan_version"] == 1
    assert result.output["attempt_id"] == "attempt-0001"
    assert reasoner.call_count == 1
    assert result.manual_intervention_package is None


class ChangingInvalidReasoner:
    """Produces distinct invalid fingerprints until the configured maximum."""

    def __init__(self) -> None:
        self.call_count = 0

    def select(self, candidates: CandidateSet, context: dict, feedback: dict | None = None) -> ReasonerOutput:
        selected = ("0.80", "0.79", "0.78", "0.77")[self.call_count]
        self.call_count += 1
        entity = context["entity_metrics"][0]
        return ReasonerOutput(
            selected,
            "independent changing invalid value",
            (
                {"path": "entity_metrics[0].spend", "value": entity["spend"]},
                {"path": "entity_metrics[0].sales", "value": entity["sales"]},
                {"path": "target_acos", "value": context["target_acos"]},
            ),
            context["confidence"],
            "medium",
        )


def test_maximum_revision_stop_creates_package_without_preflight() -> None:
    reasoner = ChangingInvalidReasoner()
    result = run_workflow(load_example("high-acos-keyword.json"), reasoner=reasoner)
    assert result.output["current_status"] == "manual_intervention_required"
    assert result.output["plan_version"] == 4
    assert result.output["retry_count"] == 3
    assert result.output["execution_preflight"] is None
    assert "preflight_passed" not in {event["event_type"] for event in result.audit_events}
    assert reasoner.call_count == 4
    assert result.manual_intervention_package is not None
    assert result.manual_intervention_package["stop_reason"] == "maximum_revisions_reached"


def test_same_error_twice_stops_and_cli_returns_three(capsys) -> None:
    exit_code = main(["examples/repeated-invalid-output.json", "--reasoner-mode", "always_invalid"])
    captured = capsys.readouterr()
    envelope = json.loads(captured.out)
    output = envelope["agent_output"]
    package = envelope["manual_intervention_package"]
    assert exit_code == 3
    assert output["current_status"] == "manual_intervention_required"
    assert output["human_approval_required"] is False
    assert output["execution_preflight"] is None
    assert output["manual_intervention_package_id"] == package["manual_intervention_package_id"]
    assert package["same_error_consecutive_count"] == 2
    assert package["stop_reason"] == "same_error_repeated"
    assert package["production_write_called"] is False
    assert captured.err.count("reasoner_completed") == 2
    assert "preflight_passed" not in captured.err
