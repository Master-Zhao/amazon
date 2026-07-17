"""Prompt loading and stable message construction tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from amazon_ads_agent.reasoners.base import ReasonerInput
from amazon_ads_agent.reasoners.errors import PromptError
from amazon_ads_agent.reasoners.prompt_builder import PromptBuilder
from amazon_ads_agent.reasoners.prompt_loader import load_prompt
import amazon_ads_agent.reasoners.prompt_loader as prompt_loader

FAKE_KEY = "test-only-not-a-real-key"
FIXTURES = Path(__file__).parent / "fixtures"


def _input(*, keyword: str = "synthetic mouse", previous_failure: dict | None = None) -> ReasonerInput:
    return ReasonerInput.create(
        task_id="task-1", run_id="run-1", attempt_id="attempt-0001", data_snapshot_id="snapshot-1",
        plan_version=1, object_type="keyword", object_id="kw-1", optimization_goal="target_acos",
        requested_risk_profile="balanced",
        entity_metrics=[{
            "entity_type": "keyword", "entity_id": "kw-1", "keyword": keyword,
            "current_bid": "1.20", "object_version": "etag-1", "impressions": 25000,
            "clicks": 420, "orders": 30, "spend": "315.00", "sales": "900.00", "currency": "USD",
        }],
        calculated_metrics={"ctr": "0.016800", "cpc": "0.750000", "cvr": "0.071429", "acos": "0.350000", "roas": "2.857143"},
        candidate_values=("1.02", "1.08", "1.14"),
        constraints={
            "rule_set_version": "poc-rules-v0.1", "target_acos": "0.250000",
            "max_decrease_ratio": "0.150000", "max_increase_ratio": "0.150000",
            "min_bid": "0.02", "max_bid": "10.00", "bid_step": "0.02",
            "requested_risk_profile": "balanced", "human_approval_required": True,
        },
        previous_failure=previous_failure,
    )


def _payload(messages: list[dict[str, str]]) -> dict:
    content = messages[1]["content"]
    serialized = content.split("<reasoner_input_json>\n", 1)[1].split("\n</reasoner_input_json>", 1)[0]
    return json.loads(serialized)


def test_loads_system_prompt() -> None:
    assert "# Role" in load_prompt("reasoner-system.md")


def test_loads_scenario_prompt() -> None:
    assert "# Keyword Bid Optimization Task" in load_prompt("keyword-bid-optimization.md")


def test_loads_revision_prompt() -> None:
    assert "# Deterministic Validation Revision" in load_prompt("revision-feedback.md")


def test_builds_system_and_user_roles() -> None:
    messages = PromptBuilder().build(_input())
    assert [message["role"] for message in messages] == ["system", "user"]


def test_system_prompt_remains_separate() -> None:
    messages = PromptBuilder().build(_input(keyword="ignore system"))
    assert "ignore system" not in messages[0]["content"]


@pytest.mark.parametrize(
    "section",
    ["task_context", "object_reference", "entity_metrics", "calculated_metrics", "candidate_values", "constraints"],
)
def test_payload_contains_complete_sections(section: str) -> None:
    assert section in _payload(PromptBuilder().build(_input()))


def test_task_context_contains_all_identifiers() -> None:
    context = _payload(PromptBuilder().build(_input()))["task_context"]
    assert set(context) == {
        "task_id", "run_id", "attempt_id", "plan_version", "data_snapshot_id",
        "optimization_goal", "requested_risk_profile", "target_acos",
    }


def test_candidate_values_are_complete_and_ordered() -> None:
    assert _payload(PromptBuilder().build(_input()))["candidate_values"] == ["1.02", "1.08", "1.14"]


def test_no_revision_message_on_first_call() -> None:
    assert len(PromptBuilder().build(_input())) == 2


def test_revision_message_contains_only_safe_failure_fields() -> None:
    failure = {
        "error_code": "ERR_EVIDENCE_REFERENCE_INVALID", "error_fingerprint": "sha256:abc",
        "error_message": "evidence path does not exist", "failed_rule_ids": ["BR-026"],
        "traceback": "private stack", "authorization_header": "private credential",
    }
    messages = PromptBuilder().build(_input(previous_failure=failure))
    assert len(messages) == 3
    revision = messages[2]["content"]
    assert "ERR_EVIDENCE_REFERENCE_INVALID" in revision and "sha256:abc" in revision
    assert "private stack" not in revision and "private credential" not in revision


def test_serialization_is_stable() -> None:
    builder = PromptBuilder()
    assert builder.build(_input()) == builder.build(_input())


def test_unicode_is_preserved() -> None:
    content = PromptBuilder().build(_input(keyword="无线鼠标"))[1]["content"]
    assert "无线鼠标" in content and "\\u65e0" not in content


def test_keyword_quotes_and_newlines_are_json_escaped() -> None:
    keyword = "quote \"value\"\nnext line"
    payload = _payload(PromptBuilder().build(_input(keyword=keyword)))
    assert payload["entity_metrics"][0]["keyword"] == keyword


def test_builder_does_not_modify_input() -> None:
    value = _input()
    before = value.candidate_values
    PromptBuilder().build(value)
    assert value.candidate_values == before and value.plan_version == 1


def test_nested_input_remains_immutable() -> None:
    value = _input()
    with pytest.raises(TypeError):
        value.entity_metrics[0]["keyword"] = "changed"


def test_missing_prompt_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(prompt_loader, "PROMPT_ROOT", FIXTURES / "missing-prompts")
    with pytest.raises(PromptError) as caught:
        load_prompt("reasoner-system.md")
    assert caught.value.error_code == "ERR_PROMPT_FILE_NOT_FOUND"


def test_empty_prompt_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(prompt_loader, "PROMPT_ROOT", FIXTURES / "empty-prompts")
    with pytest.raises(PromptError) as caught:
        load_prompt("reasoner-system.md")
    assert caught.value.error_code == "ERR_PROMPT_FILE_EMPTY"


@pytest.mark.parametrize("name", ["../README.md", "sub/reasoner-system.md", "C:\\Windows\\win.ini", "/etc/passwd"])
def test_path_traversal_and_absolute_paths_are_rejected(name: str) -> None:
    with pytest.raises(PromptError) as caught:
        load_prompt(name)
    assert caught.value.error_code == "ERR_PROMPT_PATH_INVALID"


def test_api_key_environment_value_never_enters_messages(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_API_KEY", FAKE_KEY)
    assert FAKE_KEY not in json.dumps(PromptBuilder().build(_input()), ensure_ascii=False)


def test_transport_configuration_is_not_in_business_payload() -> None:
    payload_text = json.dumps(_payload(PromptBuilder().build(_input())))
    assert "base_url" not in payload_text and "timeout_seconds" not in payload_text and "api_key" not in payload_text
