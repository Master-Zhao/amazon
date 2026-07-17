"""Restricted Reasoner protocol and an explicitly synthetic test Stub."""

from __future__ import annotations

from typing import Any, Protocol

from .models import CandidateSet, ReasonerOutput


class Reasoner(Protocol):
    """Select and explain one value without changing deterministic candidates."""

    def select(self, candidates: CandidateSet, context: dict[str, Any], feedback: dict[str, Any] | None = None) -> ReasonerOutput:
        """Return an untrusted selection for deterministic post-processing."""


class ReasonerStub:
    """Test-only deterministic Stub; it is not a model or external API."""

    MODES = {"valid", "invalid_once", "always_invalid"}

    def __init__(self, mode: str = "valid") -> None:
        if mode not in self.MODES:
            raise ValueError(f"unsupported Reasoner Stub mode: {mode}")
        self.mode = mode
        self.call_count = 0

    def select(self, candidates: CandidateSet, context: dict[str, Any], feedback: dict[str, Any] | None = None) -> ReasonerOutput:
        """Choose the middle candidate, with explicit fault-injection modes."""

        self.call_count += 1
        inject_invalid = self.mode == "always_invalid" or (self.mode == "invalid_once" and self.call_count == 1)
        suggested = "0.80" if inject_invalid else candidates.values[len(candidates.values) // 2]
        suffix = " 已根据运行期反馈重新选择。" if feedback else ""
        entity = context["entity_metrics"][0]
        return ReasonerOutput(
            suggested_value=suggested,
            reason=(
                f"ACoS {context['acos']} 高于目标 {context['target_acos']}；"
                f"Reasoner Stub 选择确定性候选集合中的中间值。{suffix}"
            ),
            evidence=(
                {"path": "entity_metrics[0].spend", "value": entity["spend"]},
                {"path": "entity_metrics[0].sales", "value": entity["sales"]},
                {"path": "target_acos", "value": context["target_acos"]},
            ),
            confidence=context["confidence"],
            risk_summary="medium",
        )
