"""Audit runner that orchestrates all checkers."""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Sequence

import yaml

from .boundary_checker import BoundaryChecker
from .config_checker import ConfigChecker, _load_config_files
from .models import AuditContext, AuditFinding, AuditReport, PromptFile, SchemaFile, SourceFile
from .prompt_checker import PromptChecker, _load_prompt_files
from .report_generator import AuditReportGenerator
from .rules import ALL_DEFAULT_RULES
from .source_scanner import SourceScanner, _load_source_files
from .registry import RuleRegistry


class AuditRunner:
    """Orchestrates security, compliance, and boundary audits."""

    def __init__(self, project_path: Path, rule_registry: RuleRegistry | None = None) -> None:
        self.project_path = project_path
        self.registry = rule_registry or create_default_registry()
        self._source_scanner = SourceScanner()
        self._config_checker = ConfigChecker()
        self._prompt_checker = PromptChecker()
        self._boundary_checker = BoundaryChecker()
        self._report_generator = AuditReportGenerator()
        self._context: AuditContext | None = None

    def _get_context(self) -> AuditContext:
        if self._context is None:
            self._context = AuditContext(project_path=self.project_path)
            self._context.source_files = _load_source_files(self.project_path)
            self._context.config_files = _load_config_files(self.project_path)
            self._context.prompt_files = _load_prompt_files(self.project_path)
            self._context.schema_files = self._load_schema_files(self.project_path)
        return self._context

    def _load_schema_files(self, project_path: Path) -> list[SchemaFile]:
        schema_dir = project_path / "schemas"
        if not schema_dir.is_dir():
            return []
        files: list[SchemaFile] = []
        for json_file in sorted(schema_dir.glob("*.json")):
            try:
                content = json_file.read_text(encoding="utf-8")
                parsed = json.loads(content)
                files.append(SchemaFile(path=str(json_file.relative_to(project_path)), content=content, parsed=parsed))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                continue
        return files

    def run_security_audit(self) -> tuple[AuditFinding, ...]:
        context = self._get_context()
        findings = self._source_scanner.check(context)
        prompt_findings = self._prompt_checker.check(context)
        return tuple(findings) + tuple(prompt_findings)

    def run_compliance_audit(self) -> tuple[AuditFinding, ...]:
        context = self._get_context()
        findings = self._config_checker.check(context)
        return tuple(findings)

    def run_boundary_audit(self) -> tuple[AuditFinding, ...]:
        context = self._get_context()
        findings = self._boundary_checker.check(context)
        return tuple(findings)

    def run_full_audit(self) -> AuditReport:
        security_findings = self.run_security_audit()
        compliance_findings = self.run_compliance_audit()
        boundary_findings = self.run_boundary_audit()
        return self._report_generator.generate_report(
            security_findings=security_findings,
            compliance_findings=compliance_findings,
            boundary_findings=boundary_findings,
            project_path=str(self.project_path),
        )


def create_default_registry() -> RuleRegistry:
    registry = RuleRegistry()
    registry.register_all(ALL_DEFAULT_RULES)
    return registry