"""Secret-safe JSON and Markdown report tests."""

from __future__ import annotations

import json
from datetime import datetime

from evaluation.case_loader import load_all_cases
from evaluation.evaluator import evaluate_cases
from evaluation.metrics import calculate_summary
from evaluation.report import EVALUATION_VERSION, build_json_report, build_markdown_report


def _report():
    results = evaluate_cases(load_all_cases())
    return build_json_report(
        results, calculate_summary(results),
        generated_at="2026-07-17T09:00:00+08:00", git_commit="a" * 40,
    )


def test_json_report_serializes() -> None:
    assert json.loads(json.dumps(_report()))["summary"]["total_cases"] == 12


def test_report_has_reproducibility_metadata() -> None:
    report = _report()
    assert report["evaluation_version"] == EVALUATION_VERSION
    assert report["git_commit"] == "a" * 40
    assert report["python_version"]
    assert datetime.fromisoformat(report["generated_at"]).tzinfo is not None


def test_report_is_explicitly_fake_only() -> None:
    report = _report()
    assert report["provider"] == "fake"
    assert report["real_model_used"] is False
    assert "real-model" in report["disclaimer"]


def test_report_has_summary_and_each_case() -> None:
    report = _report()
    assert report["summary"]["case_pass_rate"] == "1.000000"
    assert [case["case_id"] for case in report["cases"]] == [f"CASE-{number:03d}" for number in range(1, 13)]


def test_markdown_report_contains_metadata_and_metrics() -> None:
    markdown = build_markdown_report(_report())
    assert "# Deterministic Reasoner Evaluation Report" in markdown
    assert "Provider: `fake`" in markdown
    assert "Real model used: `false`" in markdown
    assert "Case pass rate: `1.000000`" in markdown


def test_markdown_report_contains_all_cases() -> None:
    markdown = build_markdown_report(_report())
    assert all(f"CASE-{number:03d}" in markdown for number in range(1, 13))


def test_report_excludes_secrets_prompts_and_raw_responses() -> None:
    rendered = json.dumps(_report(), ensure_ascii=False).lower()
    for forbidden in ("api_key", "authorization", "bearer ", "system_prompt", "raw_response", "messages"):
        assert forbidden not in rendered


def test_report_ratios_remain_strings() -> None:
    summary = _report()["summary"]
    assert all(isinstance(summary[key], str) for key in summary if key.endswith("rate"))


def test_no_failed_checks_section_is_explicit() -> None:
    assert "No failed checks." in build_markdown_report(_report())

