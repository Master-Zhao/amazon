"""Immutable Reasoner contract shared by Stub and LLM providers."""

from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from types import MappingProxyType
from typing import Any, Mapping, Protocol, cast

from ..models import CandidateSet, ReasonerOutput


def freeze(value: Any) -> Any:
    """Recursively freeze JSON-like data without changing scalar values."""

    if isinstance(value, Mapping):
        return MappingProxyType({str(key): freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(freeze(item) for item in value)
    return value


def to_plain_data(value: Any) -> Any:
    """Convert frozen JSON-like data into detached plain containers."""

    if is_dataclass(value) and not isinstance(value, type):
        return {item.name: to_plain_data(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, Mapping):
        return {str(key): to_plain_data(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [to_plain_data(item) for item in value]
    return value


@dataclass(frozen=True)
class ReasonerInput:
    """Read-only provider input; it never carries credentials."""

    task_id: str
    run_id: str
    attempt_id: str
    data_snapshot_id: str
    plan_version: int
    object_type: str
    object_id: str
    optimization_goal: str
    requested_risk_profile: str
    entity_metrics: tuple[Mapping[str, Any], ...]
    calculated_metrics: Mapping[str, Any]
    candidate_values: tuple[str, ...]
    constraints: Mapping[str, Any]
    previous_failure: Mapping[str, Any] | None = None

    @classmethod
    def create(cls, **values: Any) -> "ReasonerInput":
        """Build an input with recursively immutable nested containers."""

        values["entity_metrics"] = tuple(freeze(item) for item in values["entity_metrics"])
        values["calculated_metrics"] = freeze(values["calculated_metrics"])
        values["candidate_values"] = tuple(values["candidate_values"])
        values["constraints"] = freeze(values["constraints"])
        if values.get("previous_failure") is not None:
            values["previous_failure"] = freeze(values["previous_failure"])
        return cls(**values)


@dataclass(frozen=True)
class ReasonerResult:
    """Untrusted provider selection and explanation, not a validated plan."""

    selected_value: str
    reason: str
    evidence_paths: tuple[str, ...]
    risk_summary: str
    provider: str
    model: str
    request_id: str
    model_confidence: str | None = None


class Reasoner(Protocol):
    """Unified provider contract used by Workflow."""

    def reason(self, reasoner_input: ReasonerInput) -> ReasonerResult:
        """Return an untrusted selection without changing workflow state."""

        ...


class LegacyReasonerAdapter:
    """Adapt pre-PoC-02 `select` implementations to the unified contract."""

    def __init__(self, legacy_reasoner: Any) -> None:
        self._legacy_reasoner = legacy_reasoner

    @property
    def call_count(self) -> int:
        return int(getattr(self._legacy_reasoner, "call_count", 0))

    def reason(self, reasoner_input: ReasonerInput) -> ReasonerResult:
        candidates = CandidateSet(
            values=reasoner_input.candidate_values,
            rule_set_version=str(reasoner_input.constraints["rule_set_version"]),
        )
        context = {
            "entity_metrics": to_plain_data(reasoner_input.entity_metrics),
            "target_acos": reasoner_input.constraints["target_acos"],
            "acos": reasoner_input.calculated_metrics["acos"],
            "confidence": reasoner_input.constraints["confidence"],
        }
        feedback = None if reasoner_input.previous_failure is None else to_plain_data(reasoner_input.previous_failure)
        legacy: ReasonerOutput = self._legacy_reasoner.select(candidates, context, feedback)
        return ReasonerResult(
            selected_value=legacy.suggested_value,
            reason=legacy.reason,
            evidence_paths=tuple(str(item["path"]) for item in legacy.evidence),
            risk_summary=legacy.risk_summary,
            provider="legacy-adapter",
            model=type(self._legacy_reasoner).__name__,
            request_id=f"legacy-request-{self.call_count:04d}",
        )


def adapt_reasoner(reasoner: Any) -> Reasoner:
    """Return a unified Reasoner while preserving legacy test injection."""

    if callable(getattr(reasoner, "reason", None)):
        return cast(Reasoner, reasoner)
    if callable(getattr(reasoner, "select", None)):
        return LegacyReasonerAdapter(reasoner)
    raise TypeError("reasoner must implement reason() or the legacy select() contract")
