"""Deterministic keyword bid candidate generation."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from .config_loader import require_config
from .decimal_utils import decimal_to_string, parse_decimal, round_to_step, step_decimal_places
from .models import CandidateSet


class CandidateGenerationError(ValueError):
    """Raised when a safe deterministic candidate set cannot be generated."""


def generate_bid_candidates(current_bid_value: str, config: dict[str, Any]) -> CandidateSet:
    """Generate sorted, deduplicated, bounded bid candidates from config ratios."""

    current_bid = parse_decimal(current_bid_value)
    minimum = parse_decimal(require_config(config, "keyword_bid.min_bid"))
    maximum = parse_decimal(require_config(config, "keyword_bid.max_bid"))
    step = parse_decimal(require_config(config, "keyword_bid.bid_step"))
    max_decrease = parse_decimal(require_config(config, "keyword_bid.max_decrease_ratio"))
    ratios = require_config(config, "keyword_bid.candidate_change_ratios")
    scale = step_decimal_places(step)
    values: set[str] = set()

    for ratio_value in ratios:
        ratio = parse_decimal(ratio_value)
        if ratio >= Decimal("0") or abs(ratio) > max_decrease:
            continue
        candidate = round_to_step(current_bid * (Decimal("1") + ratio), step)
        if candidate < minimum or candidate > maximum or candidate == current_bid:
            continue
        actual_decrease = (current_bid - candidate) / current_bid
        if actual_decrease > max_decrease:
            continue
        values.add(decimal_to_string(candidate, places=scale))

    ordered = tuple(sorted(values, key=parse_decimal))
    if not ordered:
        raise CandidateGenerationError("deterministic candidate set is empty")
    return CandidateSet(values=ordered, rule_set_version=str(config["rule_set_version"]))
