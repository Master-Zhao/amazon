"""Secret-safe reports for actually executed real-model evaluation."""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence
from urllib.parse import urlsplit

from amazon_ads_agent.config_loader import load_config
from amazon_ads_agent.reasoners.prompt_builder import PromptBuilder

from .case_loader import EVALUATION_ROOT
from .models import EvaluationError, RealEvaluationRun
from .real_config import RealEvaluationConfig
from .real_metrics import evaluate_acceptance

REPO_ROOT = EVALUATION_ROOT.parent
PROMPT_ROOT = REPO_ROOT / "prompts"
SCHEMA_PATH = REPO_ROOT / "schemas" / "reasoner-output.schema.json"

_ALLOWED_SUBPROCESS_COMMANDS: frozenset[tuple[str, ...]] = frozenset({
    ("git", "rev-parse"),
})


def _safe_subprocess_run(command: Sequence[str], allowed_commands: frozenset[tuple[str, ...]]) -> str:
    cmd_tuple = tuple(command)
    if cmd_tuple[:2] not in allowed_commands:
        raise ValueError(f"Subprocess command not in whitelist: {command[0]}")
    try:
        return subprocess.run(
            list(command), check=True, capture_output=True, text=True, timeout=5
        ).stdout.strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def _git_commit() -> str:
    return _safe_subprocess_run(["git", "rev-parse", "HEAD"], _ALLOWED_SUBPROCESS_COMMANDS)


def _hashes() -> dict[str, str]:
    return {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(PROMPT_ROOT.glob("*.md"))
    }


def _schema_version() -> str:
    document = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return str(document.get("properties", {}).get("schema_version", {}).get("const", "unknown"))


def build_real_report(
    runs: list[RealEvaluationRun],
    summary: dict[str, object],
    *,
    model: str,
    base_url: str,
    budget: RealEvaluationConfig,
    smoke_case_ids: list[str],
    smoke_passed: bool,
    full_evaluation_executed: bool,
    generated_at: str | None = None,
    provider_name: str = "openai_compatible",
) -> dict[str, Any]:
    real_model_used = int(summary["actual_request_count"]) > 0
    acceptance = evaluate_acceptance(summary, executed=real_model_used)
    return {
        "evaluation_version": "poc-02-hour-04",
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git_commit": _git_commit(),
        "python_version": platform.python_version(),
        "provider": provider_name,
        "model": f"MaaS-{model}" if provider_name == "maas" else model,
        "base_url_host": urlsplit(base_url).netloc.rsplit("@", 1)[-1],
        "real_model_used": real_model_used,
        "prompt_version": PromptBuilder.TEMPLATE_VERSION,
        "prompt_hashes": _hashes(),
        "reasoner_schema_version": _schema_version(),
        "rule_set_version": load_config()["rule_set_version"],
        "evaluation_repetitions": budget.repetitions,
        "request_budget": budget.max_requests,
        "smoke_test": {"case_ids": smoke_case_ids, "passed": smoke_passed},
        "full_evaluation_executed": full_evaluation_executed,
        "summary": summary,
        "acceptance": acceptance,
        "runs": [run.to_dict() for run in runs],
        "disclaimer": "Real model outputs remain untrusted and no Amazon Ads production write exists.",
    }


def build_real_markdown(report: dict[str, Any]) -> str:
    summary, acceptance = report["summary"], report["acceptance"]
    lines = [
        "# PoC-02 Real Model Evaluation", "",
        f"- Execution status: `{acceptance['execution_status']}`",
        f"- Conclusion: `{acceptance['conclusion']}`",
        f"- Provider: `{report['provider']}`",
        f"- Model: `{report['model']}`",
        f"- Base URL host: `{report['base_url_host']}`",
        f"- Real model used: `{str(report['real_model_used']).lower()}`",
        f"- Git commit: `{report['git_commit']}`",
        f"- Generated at: `{report['generated_at']}`", "", "## Summary", "",
    ]
    for key, value in summary.items():
        lines.append(f"- {key}: `{str(value).lower() if isinstance(value, bool) else value}`")
    lines.extend(["", "## Runs", "", "| Run | Status | Requests | Agent revisions | Result |", "|---|---|---:|---:|---|"])
    for run in report["runs"]:
        lines.append(
            f"| {run['run_id']} | {run['terminal_status']} | {run['actual_request_count']} | "
            f"{run['agent_revision_count']} | {'PASS' if run['passed'] else 'FAIL'} |"
        )
    lines.extend([
        "", "## Safety boundary", "",
        "No Amazon Ads API, production adapter, Approval Service, or production write is present.",
        "Prompts, authorization headers, credentials, and raw provider envelopes are excluded.", "",
    ])
    return "\n".join(lines)


def write_real_reports(report: dict[str, Any], json_path: Path, markdown_path: Path) -> None:
    if json_path.exists() or markdown_path.exists():
        raise EvaluationError("ERR_EVALUATION_PATH_INVALID", "real model reports must not overwrite existing files")
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(build_real_markdown(report), encoding="utf-8")
