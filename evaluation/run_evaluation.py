"""CLI for deterministic Fake-only Reasoner evaluation."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evaluation.case_loader import EVALUATION_ROOT, load_all_cases, load_case
from evaluation.evaluator import evaluate_cases
from evaluation.metrics import calculate_summary
from evaluation.models import EvaluationError
from evaluation.report import build_json_report, write_reports
from evaluation.real_config import RealEvaluationConfig
from evaluation.real_evaluator import evaluate_real_cases
from evaluation.real_metrics import calculate_real_summary
from evaluation.real_report import build_real_report, write_real_reports
from amazon_ads_agent.reasoners.errors import ReasonerError
from amazon_ads_agent.reasoners.http_transport import OpenAICompatibleHTTPTransport
from amazon_ads_agent.reasoners.provider import load_real_reasoner_config

RESULTS_ROOT = EVALUATION_ROOT / "results"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run offline Fake or explicitly enabled real-model evaluation.")
    parser.add_argument("--provider", choices=("fake", "stub", "real"), default="fake")
    parser.add_argument("--confirm-real-model", action="store_true")
    parser.add_argument("--case", dest="case_id", help="Run one CASE-xxx identifier")
    parser.add_argument("--output", type=Path, help="JSON report path under evaluation/results")
    parser.add_argument("--markdown-output", type=Path, help="Markdown report path under evaluation/results")
    return parser


def _safe_output(path: Path, suffix: str) -> Path:
    resolved = (Path.cwd() / path).resolve() if not path.is_absolute() else path.resolve()
    root = RESULTS_ROOT.resolve()
    if resolved.suffix.lower() != suffix or not resolved.is_relative_to(root):
        raise EvaluationError("ERR_EVALUATION_PATH_INVALID", "report output must remain under evaluation/results")
    inputs = [EVALUATION_ROOT / "cases", EVALUATION_ROOT / "expected", EVALUATION_ROOT / "fixtures"]
    if any(resolved.is_relative_to(item.resolve()) for item in inputs):
        raise EvaluationError("ERR_EVALUATION_PATH_INVALID", "report output cannot overwrite evaluation inputs")
    return resolved


def _real_output_paths(output: Path | None, markdown_output: Path | None) -> tuple[Path, Path]:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    json_path = _safe_output(output or RESULTS_ROOT / f"real-model-{stamp}.json", ".json")
    markdown_path = _safe_output(markdown_output or RESULTS_ROOT / f"real-model-{stamp}.md", ".md")
    if not json_path.name.startswith("real-model-") or not markdown_path.name.startswith("real-model-"):
        raise EvaluationError("ERR_EVALUATION_PATH_INVALID", "real reports must use the real-model- filename prefix")
    if json_path.name in {"latest.json", "latest.md"} or markdown_path.name in {"latest.json", "latest.md"}:
        raise EvaluationError("ERR_EVALUATION_PATH_INVALID", "real reports cannot overwrite Fake latest reports")
    if json_path.exists() or markdown_path.exists():
        raise EvaluationError("ERR_EVALUATION_PATH_INVALID", "real model reports must not overwrite existing files")
    return json_path, markdown_path


def _run_real(args: argparse.Namespace) -> int:
    reasoner_config = load_real_reasoner_config(cli_confirmed=args.confirm_real_model)
    budget = RealEvaluationConfig.from_env()
    budget.validate_transport_retries(reasoner_config.max_retries)
    json_path, markdown_path = _real_output_paths(args.output, args.markdown_output)
    transport = OpenAICompatibleHTTPTransport(reasoner_config, max_requests=budget.max_requests)
    if args.case_id:
        selected = [load_case(args.case_id)]
        runs = evaluate_real_cases(
            selected,
            reasoner_config=reasoner_config,
            transport=transport,
            budget=budget,
            repetitions=1,
            controlled_case_011=args.case_id == "CASE-011",
        )
        smoke_ids = [args.case_id]
        smoke_passed = bool(runs) and all(run.passed for run in runs)
        full_executed = False
        expected_runs = 1
    else:
        smoke_ids = ["CASE-001", "CASE-006", "CASE-011"]
        smoke_cases = [load_case(case_id) for case_id in smoke_ids]
        smoke_runs = evaluate_real_cases(
            smoke_cases,
            reasoner_config=reasoner_config,
            transport=transport,
            budget=budget,
            repetitions=1,
            controlled_case_011=True,
        )
        smoke_passed = len(smoke_runs) == 3 and all(run.passed for run in smoke_runs)
        full_runs = []
        if smoke_passed:
            full_runs = evaluate_real_cases(
                load_all_cases(),
                reasoner_config=reasoner_config,
                transport=transport,
                budget=budget,
                repetitions=budget.repetitions,
            )
        runs = smoke_runs + full_runs
        full_executed = smoke_passed
        expected_runs = 3 + (12 * budget.repetitions if smoke_passed else 0)
    summary = calculate_real_summary(runs, expected_runs=expected_runs, request_budget=budget.max_requests)
    report = build_real_report(
        runs,
        summary,
        model=str(reasoner_config.model),
        base_url=str(reasoner_config.base_url),
        budget=budget,
        smoke_case_ids=smoke_ids,
        smoke_passed=smoke_passed,
        full_evaluation_executed=full_executed,
    )
    write_real_reports(report, json_path, markdown_path)
    acceptance = report["acceptance"]
    print(
        f"provider=openai_compatible real_model_used={str(report['real_model_used']).lower()} total_runs={summary['total_runs']} "
        f"passed_runs={summary['passed_runs']} requests={summary['actual_request_count']} "
        f"conclusion={acceptance['conclusion']}"
    )
    return 0 if acceptance["conclusion"] in {"PASS", "PASS WITH KNOWN LIMITATIONS"} else 3


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.provider == "real":
            return _run_real(args)
        if args.confirm_real_model:
            raise EvaluationError(
                "ERR_REAL_MODEL_CONFIRMATION_REQUIRED", "--confirm-real-model is valid only with --provider real"
            )
        cases = [load_case(args.case_id)] if args.case_id else load_all_cases()
        json_path = _safe_output(args.output or RESULTS_ROOT / "latest.json", ".json")
        markdown_path = _safe_output(args.markdown_output or RESULTS_ROOT / "latest.md", ".md")
        results = evaluate_cases(cases)
        summary = calculate_summary(results)
        report = build_json_report(results, summary, provider=args.provider)
        write_reports(report, json_path, markdown_path)
    except (EvaluationError, ReasonerError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"EVALUATION_INTERNAL_ERROR: {type(exc).__name__}", file=sys.stderr)
        return 4
    print(
        f"provider={args.provider} real_model_used=false total={summary.total_cases} "
        f"passed={summary.passed_cases} failed={summary.failed_cases} "
        f"production_write_violations={summary.production_write_violation_count}"
    )
    return 0 if summary.failed_cases == 0 else 3


if __name__ == "__main__":
    raise SystemExit(main())
