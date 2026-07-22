"""Base checker abstraction for all audit checkers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence

from .models import AuditContext, AuditFinding, AuditRule


class BaseChecker(ABC):
    """Abstract base class for audit checkers."""

    @property
    @abstractmethod
    def category(self) -> str:
        ...

    @abstractmethod
    def check(self, context: AuditContext) -> Sequence[AuditFinding]:
        ...

    def _create_finding(
        self,
        rule: AuditRule,
        status: str,
        file_path: str | None = None,
        line_number: int | None = None,
        description: str = "",
        evidence: str = "",
        remediation: str = "",
    ) -> AuditFinding:
        return AuditFinding(
            rule_id=rule.rule_id,
            category=rule.category,
            severity=rule.severity,
            status=status,
            file_path=file_path,
            line_number=line_number,
            description=description or rule.description,
            evidence=evidence,
            remediation=remediation,
        )