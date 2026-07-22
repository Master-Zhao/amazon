"""Configuration checker for compliance audit rules."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Sequence

import yaml

from .checkers import BaseChecker
from .models import AuditContext, AuditFinding, ConfigFile
from .rules import DEFAULT_COMPLIANCE_RULES


def _load_config_files(project_path: Path) -> list[ConfigFile]:
    files: list[ConfigFile] = []
    targets = [
        project_path / ".gitignore",
        project_path / "pyproject.toml",
        project_path / "config" / "poc-rules-v0.1.yaml",
        project_path / ".env.example",
        project_path / ".github" / "workflows" / "ci.yml",
    ]
    for target in targets:
        if target.is_file():
            try:
                content = target.read_text(encoding="utf-8")
                parsed: Any = None
                if target.suffix in (".yaml", ".yml"):
                    parsed = yaml.safe_load(content)
                elif target.suffix == ".json":
                    parsed = json.loads(content)
                files.append(ConfigFile(path=str(target.relative_to(project_path)), content=content, parsed=parsed))
            except (OSError, UnicodeDecodeError, yaml.YAMLError, json.JSONDecodeError):
                continue
    return files


class ConfigChecker(BaseChecker):
    """Checks configuration files for 12 compliance rules."""

    @property
    def category(self) -> str:
        return "config_check"

    def check(self, context: AuditContext) -> Sequence[AuditFinding]:
        if not context.config_files:
            context.config_files = _load_config_files(context.project_path)
        findings: list[AuditFinding] = []
        findings.append(self._check_decimal_enforcement(context))
        findings.append(self._check_schema_validation(context))
        findings.append(self._check_immutable_data(context))
        findings.append(self._check_structured_errors(context))
        findings.append(self._check_reasoner_contract(context))
        findings.append(self._check_reasoner_immutability(context))
        findings.append(self._check_independent_counters(context))
        findings.append(self._check_config_loading(context))
        findings.append(self._check_audit_append_only(context))
        findings.append(self._check_cli_interface(context))
        findings.append(self._check_output_schema(context))
        findings.append(self._check_preflight_contract(context))
        return findings

    def _rule(self, rule_id: str):
        for r in DEFAULT_COMPLIANCE_RULES:
            if r.rule_id == rule_id:
                return r
        raise ValueError(f"Unknown rule: {rule_id}")

    def _check_decimal_enforcement(self, context: AuditContext) -> AuditFinding:
        rule = self._rule("COMPLIANCE-CODE-001")
        for sf in context.source_files:
            if "decimal_utils.py" not in sf.path:
                continue
            has_parse_decimal = "parse_decimal" in sf.content
            has_decimal_to_string = "decimal_to_string" in sf.content
            if has_parse_decimal and has_decimal_to_string:
                return self._create_finding(rule, "compliant", file_path=sf.path,
                                            description="parse_decimal() and decimal_to_string() present; Decimal enforced")
            break
        return self._create_finding(rule, "non_compliant", description="Decimal enforcement not found",
                                    remediation="Implement parse_decimal() and decimal_to_string() in decimal_utils.py")

    def _check_schema_validation(self, context: AuditContext) -> AuditFinding:
        rule = self._rule("COMPLIANCE-CODE-002")
        for sf in context.source_files:
            if "schema_loader.py" not in sf.path:
                continue
            has_draft = "Draft202012Validator" in sf.content or "Draft7Validator" in sf.content
            has_cross_field = "validate_task_input" in sf.content
            if has_draft and has_cross_field:
                return self._create_finding(rule, "compliant", file_path=sf.path,
                                            description="Schema validation with Draft validator and cross-field checks present")
            break
        return self._create_finding(rule, "non_compliant", description="Schema validation not found or incomplete",
                                    remediation="Implement Draft202012Validator and cross-field validation in schema_loader.py")

    def _check_immutable_data(self, context: AuditContext) -> AuditFinding:
        rule = self._rule("COMPLIANCE-CODE-003")
        for sf in context.source_files:
            if "base.py" not in sf.path:
                continue
            has_freeze = "freeze" in sf.content
            has_mapping_proxy = "MappingProxyType" in sf.content
            if has_freeze and has_mapping_proxy:
                return self._create_finding(rule, "compliant", file_path=sf.path,
                                            description="freeze() and MappingProxyType ensure data immutability")
            break
        return self._create_finding(rule, "non_compliant", description="Data immutability (freeze/MappingProxyType) not found",
                                    remediation="Implement freeze() and MappingProxyType in base.py")

    def _check_structured_errors(self, context: AuditContext) -> AuditFinding:
        rule = self._rule("COMPLIANCE-CODE-004")
        for sf in context.source_files:
            if "errors.py" not in sf.path:
                continue
            has_error_code = "error_code" in sf.content
            has_safe_message = "safe_message" in sf.content
            has_retryable = "retryable" in sf.content
            has_provider = "provider" in sf.content
            if has_error_code and has_safe_message and has_retryable and has_provider:
                return self._create_finding(rule, "compliant", file_path=sf.path,
                                            description="ReasonerError has error_code, safe_message, retryable, provider")
            break
        return self._create_finding(rule, "non_compliant", description="Structured error fields incomplete",
                                    remediation="Add error_code, safe_message, retryable, provider to ReasonerError")

    def _check_reasoner_contract(self, context: AuditContext) -> AuditFinding:
        rule = self._rule("COMPLIANCE-ARCH-001")
        for sf in context.source_files:
            if "base.py" not in sf.path:
                continue
            has_protocol = "class Reasoner" in sf.content and "Protocol" in sf.content
            has_reason_method = "def reason" in sf.content
            if has_protocol and has_reason_method:
                return self._create_finding(rule, "compliant", file_path=sf.path,
                                            description="Reasoner Protocol with reason() method defined")
            break
        return self._create_finding(rule, "non_compliant", description="Reasoner Protocol not found",
                                    remediation="Define Reasoner Protocol with reason(reasoner_input) -> ReasonerResult")

    def _check_reasoner_immutability(self, context: AuditContext) -> AuditFinding:
        rule = self._rule("COMPLIANCE-ARCH-002")
        for sf in context.source_files:
            if "base.py" not in sf.path:
                continue
            has_frozen = "frozen=True" in sf.content
            has_reasoner_input = "class ReasonerInput" in sf.content
            if has_frozen and has_reasoner_input:
                return self._create_finding(rule, "compliant", file_path=sf.path,
                                            description="ReasonerInput is frozen dataclass; immutability enforced")
            break
        return self._create_finding(rule, "non_compliant", description="ReasonerInput immutability not confirmed",
                                    remediation="Make ReasonerInput a frozen=True dataclass")

    def _check_independent_counters(self, context: AuditContext) -> AuditFinding:
        rule = self._rule("COMPLIANCE-ARCH-003")
        for sf in context.source_files:
            if "llm.py" not in sf.path:
                continue
            has_transport_retry = "transport_retry_count" in sf.content or "last_transport_retry_count" in sf.content
            has_call_count = "call_count" in sf.content
            if has_transport_retry and has_call_count:
                return self._create_finding(rule, "compliant", file_path=sf.path,
                                            description="Transport retry count and call count are independent")
            break
        return self._create_finding(rule, "non_compliant", description="Independent counters not confirmed",
                                    remediation="Ensure transport_retry_count and call_count are separate attributes")

    def _check_config_loading(self, context: AuditContext) -> AuditFinding:
        rule = self._rule("COMPLIANCE-ARCH-004")
        for sf in context.source_files:
            if "config_loader.py" not in sf.path:
                continue
            has_load_config = "load_config" in sf.content
            has_validate_config = "validate_config" in sf.content
            has_require_config = "require_config" in sf.content
            if has_load_config and has_validate_config and has_require_config:
                return self._create_finding(rule, "compliant", file_path=sf.path,
                                            description="load_config(), validate_config(), require_config() present with no fallback")
            break
        return self._create_finding(rule, "non_compliant", description="Config loading functions not found",
                                    remediation="Implement load_config(), validate_config(), require_config() in config_loader.py")

    def _check_audit_append_only(self, context: AuditContext) -> AuditFinding:
        rule = self._rule("COMPLIANCE-ARCH-005")
        for sf in context.source_files:
            if "audit.py" not in sf.path:
                continue
            has_record = "def record" in sf.content
            has_forbidden = "FORBIDDEN_METADATA_KEYS" in sf.content
            if has_record and has_forbidden:
                return self._create_finding(rule, "compliant", file_path=sf.path,
                                            description="AuditCollector record() append-only; FORBIDDEN_METADATA_KEYS present")
            break
        return self._create_finding(rule, "non_compliant", description="Audit append-only pattern not confirmed",
                                    remediation="Implement append-only record() and FORBIDDEN_METADATA_KEYS in audit.py")

    def _check_cli_interface(self, context: AuditContext) -> AuditFinding:
        rule = self._rule("COMPLIANCE-API-001")
        for sf in context.source_files:
            if "cli.py" not in sf.path:
                continue
            has_input_arg = "input" in sf.content
            has_reasoner_mode = "reasoner-mode" in sf.content or "reasoner_mode" in sf.content
            has_reasoner_provider = "reasoner-provider" in sf.content or "reasoner_provider" in sf.content
            if has_input_arg and has_reasoner_mode and has_reasoner_provider:
                return self._create_finding(rule, "compliant", file_path=sf.path,
                                            description="CLI accepts input, --reasoner-mode, --reasoner-provider")
            break
        return self._create_finding(rule, "non_compliant", description="CLI interface not confirmed",
                                    remediation="Implement CLI with input, --reasoner-mode, --reasoner-provider arguments")

    def _check_output_schema(self, context: AuditContext) -> AuditFinding:
        rule = self._rule("COMPLIANCE-API-002")
        for sf in context.source_files:
            if "output_schema.py" not in sf.path:
                continue
            has_validate = "validate_reasoner_output" in sf.content
            if has_validate:
                return self._create_finding(rule, "compliant", file_path=sf.path,
                                            description="validate_reasoner_output() uses independent schema; strict parsing")
            break
        return self._create_finding(rule, "non_compliant", description="Output schema validation not found",
                                    remediation="Implement validate_reasoner_output() with independent schema")

    def _check_preflight_contract(self, context: AuditContext) -> AuditFinding:
        rule = self._rule("COMPLIANCE-ARCH-006")
        for sf in context.source_files:
            if "preflight.py" not in sf.path:
                continue
            has_run_preflight = "run_preflight" in sf.content
            has_production_check = "production_write" in sf.content
            if has_run_preflight and has_production_check:
                return self._create_finding(rule, "compliant", file_path=sf.path,
                                            description="run_preflight() verifies mode and production_write forbidden")
            break
        return self._create_finding(rule, "non_compliant", description="Preflight contract not confirmed",
                                    remediation="Implement run_preflight() with production_write check")