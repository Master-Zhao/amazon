"""Immutable audit data models and credential-redaction helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence
from uuid import uuid4

_SENSITIVE_PATTERNS = re.compile(
    r"(?i)(api[_-]?key|bearer(?:\s+token)?|authorization|access_token|refresh_token|secret|password)"
    r"\s*[:=]\s*(?:bearer\s+)?[^\s,;]+"
)
_BEARER_PATTERN = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~-]+")
_AKIA_PATTERN = re.compile(r"\bAKIA[0-9A-Z]{16}\b")


def redact_evidence(value: str) -> str:
    """Redact credential patterns from evidence strings."""

    redacted = _SENSITIVE_PATTERNS.sub(lambda m: f"{m.group(1)}=[REDACTED]", value)
    redacted = _BEARER_PATTERN.sub("Bearer [REDACTED]", redacted)
    redacted = _AKIA_PATTERN.sub("AKIA[REDACTED]", redacted)
    return redacted


@dataclass(frozen=True)
class AuditRule:
    """Declarative definition of a single audit check."""

    rule_id: str
    category: str
    severity: str
    description: str
    check_function: str

    def __post_init__(self) -> None:
        valid_severities = ("critical", "high", "medium", "low")
        if self.severity not in valid_severities:
            raise ValueError(f"severity must be one of {valid_severities}, got {self.severity!r}")
        valid_categories = ("security", "compliance", "boundary")
        if self.category not in valid_categories:
            raise ValueError(f"category must be one of {valid_categories}, got {self.category!r}")


@dataclass(frozen=True)
class AuditFinding:
    """Result of applying a single audit rule to a target."""

    rule_id: str
    category: str
    severity: str
    status: str
    file_path: str | None = None
    line_number: int | None = None
    description: str = ""
    evidence: str = ""
    remediation: str = ""

    def __post_init__(self) -> None:
        valid_statuses = ("compliant", "non_compliant", "not_applicable", "partial", "clear", "unclear", "violated")
        if self.status not in valid_statuses:
            raise ValueError(f"status must be one of {valid_statuses}, got {self.status!r}")
        object.__setattr__(self, "evidence", redact_evidence(self.evidence))


@dataclass(frozen=True)
class AuditSummary:
    """Aggregate counts across all audit findings."""

    total_rules: int = 0
    compliant_count: int = 0
    non_compliant_count: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0


@dataclass(frozen=True)
class PotentialImprovement:
    """A non-blocking improvement suggestion identified during audit."""

    improvement_id: str
    severity: str
    description: str
    affected_files: tuple[str, ...] = ()
    remediation: str = ""


@dataclass(frozen=True)
class AuditReport:
    """Complete audit report with findings, summary, and improvements."""

    report_id: str
    generated_at: str
    project_path: str
    security_findings: tuple[AuditFinding, ...] = ()
    compliance_findings: tuple[AuditFinding, ...] = ()
    boundary_findings: tuple[AuditFinding, ...] = ()
    summary: AuditSummary = field(default_factory=AuditSummary)
    potential_improvements: tuple[PotentialImprovement, ...] = ()


@dataclass
class SourceFile:
    """A loaded Python source file with its AST."""

    path: str
    content: str
    ast_tree: Any = None


@dataclass
class ConfigFile:
    """A loaded configuration file."""

    path: str
    content: str
    parsed: Any = None


@dataclass
class PromptFile:
    """A loaded prompt template file."""

    path: str
    content: str


@dataclass
class SchemaFile:
    """A loaded JSON Schema file."""

    path: str
    content: str
    parsed: Any = None


@dataclass
class AuditContext:
    """All files and metadata needed to run an audit."""

    project_path: Path
    source_files: list[SourceFile] = field(default_factory=list)
    config_files: list[ConfigFile] = field(default_factory=list)
    prompt_files: list[PromptFile] = field(default_factory=list)
    schema_files: list[SchemaFile] = field(default_factory=list)


def create_report_id() -> str:
    return f"audit-{uuid4().hex[:12]}"


def create_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()