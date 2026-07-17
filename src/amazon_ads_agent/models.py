"""Typed value objects shared by the deterministic PoC modules."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class MetricsResult:
    """Deterministically calculated keyword performance metrics."""

    ctr: Decimal | None
    cpc: Decimal | None
    cvr: Decimal | None
    acos: Decimal | None
    roas: Decimal | None
    reason_codes: dict[str, str | None]


@dataclass(frozen=True)
class EvidenceDecision:
    """Evidence gate decision made before candidate generation."""

    outcome: str
    reason_codes: tuple[str, ...]
    analysis_days: int


@dataclass(frozen=True)
class CandidateSet:
    """Immutable deterministic bid candidate collection."""

    values: tuple[str, ...]
    rule_set_version: str


@dataclass(frozen=True)
class ReasonerOutput:
    """Untrusted selection and explanation returned by a Reasoner."""

    suggested_value: str
    reason: str
    evidence: tuple[dict[str, str | int | None], ...]
    confidence: str
    risk_summary: str


@dataclass(frozen=True)
class ValidationIssue:
    """Stable runtime validation failure."""

    error_code: str
    message: str
    failed_rule_ids: tuple[str, ...] = ()
    failed_paths: tuple[str, ...] = ()
    actual_values: tuple[str, ...] = ()


@dataclass(frozen=True)
class ValidationResult:
    """Runtime validation outcome."""

    passed: bool
    issue: ValidationIssue | None = None


@dataclass
class WorkflowResult:
    """Workflow output with separately inspectable audit and failure evidence."""

    output: dict[str, Any]
    audit_events: list[dict[str, Any]] = field(default_factory=list)
    failure_analyses: list[dict[str, Any]] = field(default_factory=list)
    manual_intervention_package: dict[str, Any] | None = None
