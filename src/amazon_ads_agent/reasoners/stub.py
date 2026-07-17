"""Offline Reasoner Stub with unified and legacy-compatible interfaces."""

from __future__ import annotations

from typing import Any

from ..models import CandidateSet, ReasonerOutput
from .base import ReasonerInput, ReasonerResult, to_plain_data


class ReasonerStub:
    """Deterministic test Stub; it is not a model or external API."""

    MODES = {"valid", "invalid_once", "always_invalid"}

    def __init__(self, mode: str = "valid") -> None:
        if mode not in self.MODES:
            raise ValueError(f"unsupported Reasoner Stub mode: {mode}")
        self.mode = mode
        self.call_count = 0

    def _legacy_select(
        self,
        candidates: CandidateSet,
        context: dict[str, Any],
        feedback: dict[str, Any] | None,
    ) -> ReasonerOutput:
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

    def reason(self, reasoner_input: ReasonerInput) -> ReasonerResult:
        """Select through the unified immutable input contract."""

        legacy = self._legacy_select(
            CandidateSet(reasoner_input.candidate_values, str(reasoner_input.constraints["rule_set_version"])),
            {
                "entity_metrics": to_plain_data(reasoner_input.entity_metrics),
                "target_acos": reasoner_input.constraints["target_acos"],
                "acos": reasoner_input.calculated_metrics["acos"],
                "confidence": reasoner_input.constraints["confidence"],
            },
            None if reasoner_input.previous_failure is None else to_plain_data(reasoner_input.previous_failure),
        )
        return ReasonerResult(
            selected_value=legacy.suggested_value,
            reason=legacy.reason,
            evidence_paths=tuple(str(item["path"]) for item in legacy.evidence),
            risk_summary=legacy.risk_summary,
            provider="stub",
            model="reasoner-stub-v0.1",
            request_id=f"stub-request-{self.call_count:04d}",
        )

    def select(
        self,
        candidates: CandidateSet,
        context: dict[str, Any],
        feedback: dict[str, Any] | None = None,
    ) -> ReasonerOutput:
        """Preserve the pre-PoC-02 public import and call signature."""

        return self._legacy_select(candidates, context, feedback)
