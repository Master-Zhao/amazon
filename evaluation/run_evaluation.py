"""CLI for deterministic Fake-only Reasoner evaluation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evaluation.case_loader import EVALUATION_ROOT, load_all_cases, load_case
from evaluation.evaluator import evaluate_cases
from evaluation.metrics import calculate_summary
from evaluation.models import EvaluationError
from evaluation.report import build_json_report, write_reports

RESULTS_ROOT = EVALUATION_ROOT / "results"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run deterministic Fake-only Reasoner evaluation.")
    parser.add_argument("--case", dest="case_id", help="Run one CASE-xxx identifier")
    parser.add_argument("--output", type=Path, default=RESULTS_ROOT / "latest.json", help="JSON report path under evaluation/results")
    parser.add_argument("--markdown-output", type=Path, default=RESULTS_ROOT / "latest.md", help="Markdown report path under evaluation/results")
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


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        cases = [load_case(args.case_id)] if args.case_id else load_all_cases()
        json_path = _safe_output(args.output, ".json")
        markdown_path = _safe_output(args.markdown_output, ".md")
        results = evaluate_cases(cases)
        summary = calculate_summary(results)
        report = build_json_report(results, summary)
        write_reports(report, json_path, markdown_path)
    except EvaluationError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"EVALUATION_INTERNAL_ERROR: {type(exc).__name__}", file=sys.stderr)
        return 4
    print(
        f"provider=fake real_model_used=false total={summary.total_cases} "
        f"passed={summary.passed_cases} failed={summary.failed_cases} "
        f"production_write_violations={summary.production_write_violation_count}"
    )
    return 0 if summary.failed_cases == 0 else 3


if __name__ == "__main__":
    raise SystemExit(main())
