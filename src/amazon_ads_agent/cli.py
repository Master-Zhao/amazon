"""Command-line interface for local synthetic PoC runs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .config_loader import RuleConfigError
from .schema_loader import SchemaValidationError
from .workflow import run_workflow


def build_parser() -> argparse.ArgumentParser:
    """Create the stable command-line parser."""

    parser = argparse.ArgumentParser(description="Run the synthetic Amazon Ads keyword agent PoC.")
    parser.add_argument("input", type=Path, help="Path to a synthetic TaskInput JSON file")
    parser.add_argument(
        "--reasoner-mode",
        choices=("valid", "invalid_once", "always_invalid"),
        default=None,
        help="Explicit test-only Reasoner Stub mode",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run one workflow and print a protocol envelope to stdout."""

    args = build_parser().parse_args(argv)
    try:
        task = json.loads(args.input.read_text(encoding="utf-8"))
        if not isinstance(task, dict):
            raise SchemaValidationError("TaskInput root must be an object")
        result = run_workflow(task, reasoner_mode=args.reasoner_mode)
    except (FileNotFoundError, json.JSONDecodeError, SchemaValidationError) as exc:
        print(f"INPUT_ERROR: {exc}", file=sys.stderr)
        return 2
    except (RuleConfigError, ValueError, RuntimeError) as exc:
        print(f"INTERNAL_ERROR: {exc}", file=sys.stderr)
        return 4

    for event in result.audit_events:
        marker = f" [{event['error_code']}]" if event["error_code"] else ""
        print(f"{event['step_id']} {event['event_type']} -> {event['status_after']}{marker}", file=sys.stderr)
    payload = {
        "agent_output": result.output,
        "manual_intervention_package": result.manual_intervention_package,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 3 if result.output["current_status"] == "manual_intervention_required" else 0
