"""Strict real-evaluation budgets loaded only for explicit real mode."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping

from evaluation.models import EvaluationError

ENV_MAX_REQUESTS = "REAL_EVALUATION_MAX_REQUESTS"
ENV_MAX_AGENT_REVISIONS = "REAL_EVALUATION_MAX_AGENT_REVISIONS"
ENV_MAX_TRANSPORT_RETRIES = "REAL_EVALUATION_MAX_TRANSPORT_RETRIES"
ENV_REPETITIONS = "REAL_EVALUATION_REPETITIONS"


def _integer(env: Mapping[str, str], name: str, default: str, minimum: int, maximum: int) -> int:
    try:
        value = int(env.get(name, default))
    except (TypeError, ValueError) as exc:
        raise EvaluationError("ERR_REAL_EVALUATION_CONFIG_INVALID", f"{name} must be an integer") from exc
    if value < minimum or value > maximum:
        raise EvaluationError(
            "ERR_REAL_EVALUATION_CONFIG_INVALID", f"{name} must be between {minimum} and {maximum}"
        )
    return value


@dataclass(frozen=True)
class RealEvaluationConfig:
    max_requests: int = 60
    max_agent_revisions: int = 3
    max_transport_retries: int = 1
    repetitions: int = 3

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "RealEvaluationConfig":
        env = os.environ if environ is None else environ
        return cls(
            max_requests=_integer(env, ENV_MAX_REQUESTS, "60", 1, 1000),
            max_agent_revisions=_integer(env, ENV_MAX_AGENT_REVISIONS, "3", 0, 3),
            max_transport_retries=_integer(env, ENV_MAX_TRANSPORT_RETRIES, "1", 0, 10),
            repetitions=_integer(env, ENV_REPETITIONS, "3", 1, 10),
        )

    def validate_transport_retries(self, configured_retries: int) -> None:
        if configured_retries > self.max_transport_retries:
            raise EvaluationError(
                "ERR_REAL_EVALUATION_CONFIG_INVALID",
                "LLM_MAX_RETRIES exceeds REAL_EVALUATION_MAX_TRANSPORT_RETRIES",
            )

    def to_dict(self) -> dict[str, int]:
        return {
            "max_requests": self.max_requests,
            "max_agent_revisions": self.max_agent_revisions,
            "max_transport_retries": self.max_transport_retries,
            "repetitions": self.repetitions,
        }

