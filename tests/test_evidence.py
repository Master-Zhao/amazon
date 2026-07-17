"""Evidence sufficiency and no-change routing."""

from conftest import load_example
from amazon_ads_agent.evidence import evaluate_evidence
from amazon_ads_agent.metrics import calculate_metrics


def _outcome(name: str, config: dict) -> str:
    task = load_example(name)
    metrics = calculate_metrics(task["entity_metrics"][0])
    return evaluate_evidence(task, metrics, config).outcome


def test_high_acos_requires_candidates(config: dict) -> None:
    assert _outcome("high-acos-keyword.json", config) == "generate_candidates"


def test_short_window_or_low_clicks_is_insufficient(config: dict) -> None:
    assert _outcome("insufficient-evidence.json", config) == "insufficient_evidence"


def test_acos_at_or_below_target_needs_no_change(config: dict) -> None:
    assert _outcome("no-change-required.json", config) == "no_change_required"


def test_target_config_mismatch_fails_closed(high_task: dict, config: dict) -> None:
    high_task["target_acos"] = "0.300000"
    metrics = calculate_metrics(high_task["entity_metrics"][0])
    decision = evaluate_evidence(high_task, metrics, config)
    assert decision.outcome == "insufficient_evidence"
    assert "TARGET_ACOS_CONFIG_MISMATCH" in decision.reason_codes
