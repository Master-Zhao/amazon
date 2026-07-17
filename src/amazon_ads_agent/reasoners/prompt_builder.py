"""Stable, injection-resistant message construction for Reasoner transport calls."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from .base import ReasonerInput, to_plain_data
from .prompt_loader import load_prompt

PromptLoader = Callable[[str], str]


def _stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _safe_previous_failure(previous_failure: Any) -> dict[str, Any]:
    failure = to_plain_data(previous_failure)
    return {
        "error_code": str(failure.get("error_code", "ERR_UNKNOWN")),
        "error_fingerprint": str(failure.get("error_fingerprint", "sha256:unknown")),
        "safe_message": str(failure.get("safe_message", failure.get("error_message", "validation failed"))),
        "failed_rule_ids": [str(item) for item in failure.get("failed_rule_ids", [])],
    }


class PromptBuilder:
    """Build fixed-role messages while keeping all task strings in JSON data."""

    TEMPLATE_VERSION = "reasoner-prompt-v1.0"

    def __init__(self, loader: PromptLoader = load_prompt) -> None:
        self._loader = loader

    def build(self, reasoner_input: ReasonerInput) -> list[dict[str, str]]:
        """Return stable Transport messages without mutating the input."""

        system_prompt = self._loader("reasoner-system.md")
        scenario_prompt = self._loader("keyword-bid-optimization.md")
        plain = to_plain_data(reasoner_input)
        payload = {
            "task_context": {
                "task_id": plain["task_id"],
                "run_id": plain["run_id"],
                "attempt_id": plain["attempt_id"],
                "plan_version": plain["plan_version"],
                "data_snapshot_id": plain["data_snapshot_id"],
                "optimization_goal": plain["optimization_goal"],
                "requested_risk_profile": plain["requested_risk_profile"],
                "target_acos": plain["constraints"].get("target_acos"),
            },
            "object_reference": {
                "object_type": plain["object_type"],
                "object_id": plain["object_id"],
            },
            "entity_metrics": plain["entity_metrics"],
            "calculated_metrics": plain["calculated_metrics"],
            "candidate_values": plain["candidate_values"],
            "constraints": plain["constraints"],
        }
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"{scenario_prompt}\n\n<reasoner_input_json>\n{_stable_json(payload)}\n</reasoner_input_json>",
            },
        ]
        if reasoner_input.previous_failure is not None:
            revision_prompt = self._loader("revision-feedback.md")
            safe_failure = _safe_previous_failure(reasoner_input.previous_failure)
            messages.append(
                {
                    "role": "user",
                    "content": (
                        f"{revision_prompt}\n\n<previous_failure_json>\n"
                        f"{_stable_json(safe_failure)}\n</previous_failure_json>"
                    ),
                }
            )
        return messages


ReasonerPromptBuilder = PromptBuilder
