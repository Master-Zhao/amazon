"""Evaluation CLI behavior and isolation tests."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from evaluation import run_evaluation
from evaluation.case_loader import load_case
from evaluation.evaluator import evaluate_case


RESULTS = Path(__file__).resolve().parents[1] / "evaluation" / "results"


def _paths(name: str) -> tuple[Path, Path]:
    return RESULTS / f"custom-{name}.json", RESULTS / f"custom-{name}.md"


def _cleanup(*paths: Path) -> None:
    for path in paths:
        path.unlink(missing_ok=True)


def test_cli_runs_all_cases_and_generates_both_reports() -> None:
    json_path, md_path = _paths("all-test")
    try:
        assert run_evaluation.main(["--output", str(json_path), "--markdown-output", str(md_path)]) == 0
        assert json_path.is_file() and md_path.is_file()
        assert json.loads(json_path.read_text(encoding="utf-8"))["summary"]["total_cases"] == 12
    finally:
        _cleanup(json_path, md_path)


@pytest.mark.parametrize("case_id", ["CASE-004", "CASE-006", "CASE-011", "CASE-012"])
def test_cli_runs_single_case(case_id: str) -> None:
    json_path, md_path = _paths(case_id.lower())
    try:
        assert run_evaluation.main(["--case", case_id, "--output", str(json_path), "--markdown-output", str(md_path)]) == 0
        assert json.loads(json_path.read_text(encoding="utf-8"))["cases"][0]["case_id"] == case_id
    finally:
        _cleanup(json_path, md_path)


def test_missing_case_returns_exit_2(capsys: pytest.CaptureFixture[str]) -> None:
    assert run_evaluation.main(["--case", "CASE-999"]) == 2
    assert "ERR_EVALUATION_CASE_NOT_FOUND" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("argument", "path"),
    [("--output", "../outside.json"), ("--markdown-output", "README.md"), ("--output", "evaluation/results/bad.md")],
)
def test_unsafe_output_path_returns_exit_2(argument: str, path: str) -> None:
    assert run_evaluation.main([argument, path]) == 2


def test_evaluation_failure_returns_exit_3(monkeypatch: pytest.MonkeyPatch) -> None:
    failed = replace(evaluate_case(load_case("CASE-001")), passed=False, final_attempt_passed=False)
    monkeypatch.setattr(run_evaluation, "evaluate_cases", lambda cases: [failed])
    monkeypatch.setattr(run_evaluation, "write_reports", lambda *args: None)
    assert run_evaluation.main([]) == 3


def test_internal_error_returns_exit_4(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(run_evaluation, "evaluate_cases", lambda cases: (_ for _ in ()).throw(RuntimeError("safe")))
    assert run_evaluation.main([]) == 4


def test_cli_does_not_require_model_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.setattr(run_evaluation, "write_reports", lambda *args: None)
    assert run_evaluation.main(["--case", "CASE-001"]) == 0


def test_cli_creates_nested_output_directory() -> None:
    directory = RESULTS / "custom-cli-nested"
    json_path, md_path = directory / "report.json", directory / "report.md"
    try:
        assert run_evaluation.main(["--case", "CASE-001", "--output", str(json_path), "--markdown-output", str(md_path)]) == 0
        assert json_path.is_file() and md_path.is_file()
    finally:
        _cleanup(json_path, md_path)
        directory.rmdir()


def test_cli_never_opens_network(monkeypatch: pytest.MonkeyPatch) -> None:
    import socket

    monkeypatch.setattr(socket, "create_connection", lambda *args, **kwargs: pytest.fail("network access attempted"))
    monkeypatch.setattr(run_evaluation, "write_reports", lambda *args: None)
    assert run_evaluation.main(["--case", "CASE-001"]) == 0


def test_repeated_runs_have_identical_summary(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[dict] = []
    monkeypatch.setattr(run_evaluation, "write_reports", lambda report, *args: captured.append(report))
    assert run_evaluation.main(["--case", "CASE-011"]) == 0
    assert run_evaluation.main(["--case", "CASE-011"]) == 0
    assert captured[0]["summary"] == captured[1]["summary"]
    assert captured[0]["cases"] == captured[1]["cases"]


def test_cli_stdout_never_contains_prompt(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(run_evaluation, "write_reports", lambda *args: None)
    assert run_evaluation.main(["--case", "CASE-006"]) == 0
    output = capsys.readouterr().out.lower()
    assert "system prompt" not in output and "messages" not in output
