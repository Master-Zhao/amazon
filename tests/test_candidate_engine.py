"""Candidate range, step, ordering, and deduplication tests."""

from copy import deepcopy
from decimal import Decimal

from amazon_ads_agent.candidate_engine import generate_bid_candidates
from amazon_ads_agent.decimal_utils import parse_decimal


def test_one_twenty_generates_expected_candidates(config: dict) -> None:
    assert generate_bid_candidates("1.20", config).values == ("1.02", "1.08", "1.14")


def test_candidates_do_not_exceed_fifteen_percent(config: dict) -> None:
    for value in generate_bid_candidates("1.20", config).values:
        assert (Decimal("1.20") - parse_decimal(value)) / Decimal("1.20") <= Decimal("0.15")


def test_candidates_match_bid_step(config: dict) -> None:
    step = Decimal(config["keyword_bid"]["bid_step"])
    assert all(parse_decimal(value) / step == (parse_decimal(value) / step).to_integral_value() for value in generate_bid_candidates("1.20", config).values)


def test_candidates_respect_minimum(config: dict) -> None:
    minimum = parse_decimal(config["keyword_bid"]["min_bid"])
    assert all(parse_decimal(value) >= minimum for value in generate_bid_candidates("0.10", config).values)


def test_candidates_respect_maximum(config: dict) -> None:
    maximum = parse_decimal(config["keyword_bid"]["max_bid"])
    assert all(parse_decimal(value) <= maximum for value in generate_bid_candidates("5.00", config).values)


def test_candidates_are_deduplicated(config: dict) -> None:
    modified = deepcopy(config)
    modified["keyword_bid"]["candidate_change_ratios"].append("-0.100000")
    values = generate_bid_candidates("1.20", modified).values
    assert len(values) == len(set(values))
