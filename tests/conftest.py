"""Shared synthetic fixtures for the PoC test suite."""

from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from amazon_ads_agent.candidate_engine import generate_bid_candidates
from amazon_ads_agent.config_loader import load_config
from amazon_ads_agent.decimal_utils import decimal_to_string
from amazon_ads_agent.metrics import calculate_metrics
from amazon_ads_agent.post_processor import build_plan
from amazon_ads_agent.reasoner import ReasonerStub


def load_example(name: str) -> dict[str, Any]:
    """Load one repository-owned synthetic TaskInput."""

    return json.loads((ROOT / "examples" / name).read_text(encoding="utf-8"))


@pytest.fixture
def config() -> dict[str, Any]:
    return load_config()


@pytest.fixture
def high_task() -> dict[str, Any]:
    return load_example("high-acos-keyword.json")


@pytest.fixture
def valid_candidate_plan(high_task: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    task = deepcopy(high_task)
    metrics = calculate_metrics(task["entity_metrics"][0])
    candidates = generate_bid_candidates(task["entity_metrics"][0]["current_bid"], config)
    reasoner = ReasonerStub("valid")
    context = {
        "entity_metrics": task["entity_metrics"],
        "target_acos": task["target_acos"],
        "acos": decimal_to_string(metrics.acos, places=6),
        "confidence": config["analysis"]["confidence_threshold"],
    }
    selected = reasoner.select(candidates, context)
    return build_plan(task, metrics, candidates, selected, 1, 0)
