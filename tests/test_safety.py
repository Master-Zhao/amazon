"""Repository and runtime safety boundary tests."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from conftest import ROOT, load_example
from amazon_ads_agent.preflight import ProductionWriteForbidden, assert_production_write_forbidden
from amazon_ads_agent.workflow import run_workflow

SRC = ROOT / "src" / "amazon_ads_agent"


def _source_text() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in SRC.glob("*.py"))


def test_no_production_adapter_exists() -> None:
    assert not list(SRC.glob("*production*adapter*.py"))
    assert "class ProductionAdapter" not in _source_text()


def test_no_production_api_url_exists() -> None:
    text = _source_text().lower()
    assert "advertising-api.amazon" not in text
    assert "amazon ads api" not in text


def test_no_embedded_access_token_or_key_material() -> None:
    text = _source_text()
    assert re.search(r"AKIA[0-9A-Z]{16}", text) is None
    assert "Bearer eyJ" not in text
    assert "-----BEGIN PRIVATE KEY-----" not in text


def test_no_normal_true_production_write_assignment() -> None:
    text = _source_text()
    assert '"production_write_called": True' not in text
    assert "production_write_enabled = True" not in text


def test_forbidden_production_flag_raises() -> None:
    with pytest.raises(ProductionWriteForbidden):
        assert_production_write_forbidden(True)


def test_no_pause_delete_or_archive_action() -> None:
    text = _source_text()
    assert '"pause"' not in text
    assert '"delete"' not in text
    assert '"archive"' not in text


def test_business_source_does_not_call_float() -> None:
    assert "float(" not in _source_text()


def test_no_execution_method_without_approval() -> None:
    text = _source_text()
    assert "def execute(" not in text
    assert "def production_write(" not in text


def test_all_example_keywords_are_explicitly_synthetic() -> None:
    for path in (ROOT / "examples").glob("*.json"):
        task = load_example(path.name)
        assert "synthetic" in task["entity_metrics"][0]["keyword"].lower()


def test_config_is_fail_closed_and_dry_run_only() -> None:
    config = yaml.safe_load((ROOT / "config" / "poc-rules-v0.1.yaml").read_text(encoding="utf-8"))
    assert config["not_for_production"] is True
    assert config["runtime"]["production_write_enabled"] is False
    assert config["runtime"]["allowed_execution_modes"] == ["dry_run"]


def test_manual_intervention_never_reaches_approval() -> None:
    output = run_workflow(load_example("repeated-invalid-output.json"), reasoner_mode="always_invalid").output
    assert output["current_status"] == "manual_intervention_required"
    assert output["human_approval_required"] is False
    assert output["execution_preflight"]["production_write_called"] is False
