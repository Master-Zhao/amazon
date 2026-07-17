"""Reasoner Stub candidate-selection contract."""

from amazon_ads_agent.candidate_engine import generate_bid_candidates
from amazon_ads_agent.reasoner import ReasonerStub


def _context(high_task: dict, config: dict) -> dict:
    return {
        "entity_metrics": high_task["entity_metrics"],
        "target_acos": high_task["target_acos"],
        "acos": "0.350000",
        "confidence": config["analysis"]["confidence_threshold"],
    }


def test_valid_mode_selects_from_candidates(high_task: dict, config: dict) -> None:
    candidates = generate_bid_candidates("1.20", config)
    output = ReasonerStub("valid").select(candidates, _context(high_task, config))
    assert output.suggested_value == "1.08"
    assert output.suggested_value in candidates.values


def test_invalid_once_is_invalid_then_valid(high_task: dict, config: dict) -> None:
    candidates = generate_bid_candidates("1.20", config)
    reasoner = ReasonerStub("invalid_once")
    assert reasoner.select(candidates, _context(high_task, config)).suggested_value == "0.80"
    assert reasoner.select(candidates, _context(high_task, config), {"error": "feedback"}).suggested_value in candidates.values


def test_always_invalid_repeats_same_value(high_task: dict, config: dict) -> None:
    candidates = generate_bid_candidates("1.20", config)
    reasoner = ReasonerStub("always_invalid")
    values = [reasoner.select(candidates, _context(high_task, config)).suggested_value for _ in range(2)]
    assert values == ["0.80", "0.80"]
