"""Secret-safe JSON and Markdown evaluation report generation."""

from __future__ import annotations

import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import EvaluationResult, EvaluationSummary

EVALUATION_VERSION = "poc-02-hour-03"


def _git_commit() -> str:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True, timeout=5
        )
        value = completed.stdout.strip()
        return value if value else "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def build_json_report(
    results: list[EvaluationResult],
    summary: EvaluationSummary,
    *,
    generated_at: str | None = None,
    git_commit: str | None = None,
) -> dict[str, Any]:
    """Build a JSON-safe report without prompts, credentials, or raw responses."""

    return {
        "evaluation_version": EVALUATION_VERSION,
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git_commit": git_commit or _git_commit(),
        "python_version": platform.python_version(),
        "provider": "fake",
        "real_model_used": False,
        "disclaimer": "Fake Transport only; results do not represent real-model answer quality.",
        "summary": summary.to_dict(),
        "cases": [result.to_dict() for result in results],
    }


def build_markdown_report(report: dict[str, Any]) -> str:
    """Render a deterministic human-readable report from safe JSON facts."""

    summary = report["summary"]
    lines = [
        "# Deterministic Reasoner Evaluation Report",
        "",
        "> 本报告使用 Stub 或 Fake Transport。`real_model_used=false`。结果不代表真实大模型回答质量。",
        "",
        f"- Generated at: `{report['generated_at']}`",
        f"- Git commit: `{report['git_commit']}`",
        f"- Python: `{report['python_version']}`",
        f"- Provider: `{report['provider']}`",
        f"- Real model used: `{str(report['real_model_used']).lower()}`",
        "",
        "## Summary",
        "",
    ]
    labels = (
        ("Total cases", "total_cases"), ("Passed cases", "passed_cases"), ("Failed cases", "failed_cases"),
        ("Case pass rate", "case_pass_rate"), ("First JSON pass rate", "first_json_pass_rate"),
        ("First Schema pass rate", "first_schema_pass_rate"), ("First business pass rate", "first_business_pass_rate"),
        ("Final success rate", "final_success_rate"), ("Revision success rate", "revision_success_rate"),
        ("Candidate violations detected", "candidate_violation_count"), ("Hallucinated objects detected", "hallucinated_object_count"),
        ("Invalid evidence detected", "invalid_evidence_count"), ("Approval bypass violations", "approval_bypass_count"),
        ("Manual interventions", "manual_intervention_count"), ("Average Agent revisions", "average_agent_revisions"),
        ("Average Reasoner calls", "average_reasoner_calls"), ("Total Transport retries", "total_transport_retries"),
        ("Production write violations", "production_write_violation_count"),
        ("Preflight boundary violations", "preflight_boundary_violation_count"),
    )
    lines.extend(f"- {label}: `{summary[key]}`" for label, key in labels)
    lines.extend(["", "## Cases", "", "| Case | Status | Calls | Revisions | Result |", "|---|---|---:|---:|---|"])
    for case in report["cases"]:
        lines.append(
            f"| {case['case_id']} {case['name']} | {case['terminal_status']} | "
            f"{case['reasoner_call_count']} | {case['agent_revision_count']} | {'PASS' if case['passed'] else 'FAIL'} |"
        )
    failed = [case for case in report["cases"] if not case["passed"]]
    lines.extend(["", "## Failed checks", ""])
    if not failed:
        lines.append("No failed checks.")
    for case in failed:
        lines.append(f"### {case['case_id']} {case['name']}")
        for check in case["checks"]:
            if not check["passed"]:
                lines.append(f"- `{check['check_id']}`: {check['safe_message']}")
    lines.extend([
        "", "## Known limitations", "",
        "This is a fixed offline dataset using predefined Fake responses. It does not measure real-model latency, cost, or answer quality.",
        "No Amazon Ads API, Approval Service, production adapter, or production write is present.",
        "",
    ])
    return "\n".join(lines)


def write_reports(report: dict[str, Any], json_path: Path, markdown_path: Path) -> None:
    """Write both reports as UTF-8 after the caller validates output paths."""

    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(build_markdown_report(report), encoding="utf-8")
