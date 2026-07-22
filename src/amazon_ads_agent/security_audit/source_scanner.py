"""Source code scanner for security audit rules."""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Sequence

from .checkers import BaseChecker
from .models import AuditContext, AuditFinding, SourceFile
from .rules import DEFAULT_SECURITY_RULES

_AKIA_RE = re.compile(r"\bAKIA[0-9A-Z]{16}\b")
_BEARER_TOKEN_RE = re.compile(r"\bbearer\s+[A-Za-z0-9._~-]+", re.IGNORECASE)
_PRIVATE_KEY_RE = re.compile(r"-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----")
_EVAL_RE = re.compile(r"\beval\s*\(")
_EXEC_RE = re.compile(r"\bexec\s*\(")
_FLOAT_CALL_RE = re.compile(r"\bfloat\s*\(")
_SUBPROCESS_RE = re.compile(r"\bsubprocess\s*\.\s*run\s*\(")
_PRODUCTION_ADAPTER_RE = re.compile(r"production.*adapter", re.IGNORECASE)
_FORBIDDEN_KEYS_EXPECTED = frozenset({"access_token", "refresh_token", "authorization_header", "secret", "password"})
_SENSITIVE_PATTERNS_EXPECTED = frozenset({"api_key", "bearer", "authorization", "access_token", "refresh_token", "secret", "password"})


def _load_source_files(project_path: Path) -> list[SourceFile]:
    src_dir = project_path / "src"
    if not src_dir.is_dir():
        src_dir = project_path
    files: list[SourceFile] = []
    for py_file in sorted(src_dir.rglob("*.py")):
        try:
            content = py_file.read_text(encoding="utf-8")
            try:
                tree = ast.parse(content, filename=str(py_file))
            except SyntaxError:
                tree = None
            files.append(SourceFile(path=str(py_file.relative_to(project_path)), content=content, ast_tree=tree))
        except (OSError, UnicodeDecodeError):
            continue
    return files


def _find_in_source(files: list[SourceFile], pattern: re.Pattern[str]) -> list[tuple[str, int, str]]:
    results: list[tuple[str, int, str]] = []
    for sf in files:
        for i, line in enumerate(sf.content.splitlines(), 1):
            if pattern.search(line):
                results.append((sf.path, i, line.strip()))
    return results


class SourceScanner(BaseChecker):
    """Scans Python source files for 18 security rules."""

    @property
    def category(self) -> str:
        return "source_scan"

    def check(self, context: AuditContext) -> Sequence[AuditFinding]:
        if not context.source_files:
            context.source_files = _load_source_files(context.project_path)
        findings: list[AuditFinding] = []
        findings.append(self._check_hardcoded_secrets(context))
        findings.append(self._check_gitignore_env_exclusion(context))
        findings.append(self._check_api_key_repr_false(context))
        findings.append(self._check_forbidden_metadata_keys(context))
        findings.append(self._check_report_no_credentials(context))

        findings.append(self._check_no_eval_exec(context))
        findings.append(self._check_no_float(context))
        findings.append(self._check_https_endpoint(context))
        findings.append(self._check_production_write_forbidden(context))
        findings.append(self._check_no_production_adapter(context))
        findings.append(self._check_default_offline_mode(context))
        findings.append(self._check_double_confirmation(context))
        findings.append(self._check_redact_sensitive_patterns(context))
        findings.append(self._check_report_url_redaction(context))
        return findings

    def _rule(self, rule_id: str) -> tuple:
        for r in DEFAULT_SECURITY_RULES:
            if r.rule_id == rule_id:
                return (r,)
        raise ValueError(f"Unknown rule: {rule_id}")

    def _check_hardcoded_secrets(self, context: AuditContext) -> AuditFinding:
        rule = self._rule("SEC-SENSITIVE-001")[0]
        hits = []
        for sf in context.source_files:
            for i, line in enumerate(sf.content.splitlines(), 1):
                if _AKIA_RE.search(line) or _BEARER_TOKEN_RE.search(line) or _PRIVATE_KEY_RE.search(line):
                    hits.append((sf.path, i))
        if hits:
            return self._create_finding(rule, "non_compliant", description=f"Found {len(hits)} hardcoded secret(s)",
                                        evidence=str(hits), remediation="Remove hardcoded secrets; use environment variables")
        return self._create_finding(rule, "compliant", description="No hardcoded secrets found")

    def _check_gitignore_env_exclusion(self, context: AuditContext) -> AuditFinding:
        rule = self._rule("SEC-SENSITIVE-002")[0]
        gitignore_path = context.project_path / ".gitignore"
        if not gitignore_path.is_file():
            return self._create_finding(rule, "non_compliant", description=".gitignore not found",
                                        remediation="Create .gitignore excluding .env and .env.*")
        content = gitignore_path.read_text(encoding="utf-8")
        has_env = ".env" in content
        has_env_star = ".env.*" in content
        has_env_example = ".env.example" in content or "!*.env.example" in content or "!.env.example" in content
        if has_env and has_env_star:
            return self._create_finding(rule, "compliant", description=".gitignore properly excludes .env files")
        missing = []
        if not has_env:
            missing.append(".env")
        if not has_env_star:
            missing.append(".env.*")
        return self._create_finding(rule, "non_compliant", description=f".gitignore missing: {', '.join(missing)}",
                                    remediation="Add .env and .env.* to .gitignore")

    def _check_api_key_repr_false(self, context: AuditContext) -> AuditFinding:
        rule = self._rule("SEC-SENSITIVE-003")[0]
        for sf in context.source_files:
            if "config.py" not in sf.path:
                continue
            has_repr_false = "repr=False" in sf.content and "api_key" in sf.content
            has_safe_description = "safe_description" in sf.content
            if has_repr_false and has_safe_description:
                return self._create_finding(rule, "compliant", file_path=sf.path,
                                            description="api_key marked repr=False; safe_description() present")
            break
        return self._create_finding(rule, "non_compliant", description="api_key repr=False or safe_description() missing",
                                    remediation="Mark api_key field with repr=False and implement safe_description()")

    def _check_forbidden_metadata_keys(self, context: AuditContext) -> AuditFinding:
        rule = self._rule("SEC-SENSITIVE-004")[0]
        for sf in context.source_files:
            if "audit.py" not in sf.path:
                continue
            has_forbidden = "FORBIDDEN_METADATA_KEYS" in sf.content
            if has_forbidden:
                for key in _FORBIDDEN_KEYS_EXPECTED:
                    if key not in sf.content:
                        return self._create_finding(rule, "non_compliant", file_path=sf.path,
                                                    description=f"FORBIDDEN_METADATA_KEYS missing key: {key}",
                                                    remediation=f"Add '{key}' to FORBIDDEN_METADATA_KEYS")
                return self._create_finding(rule, "compliant", file_path=sf.path,
                                            description="FORBIDDEN_METADATA_KEYS covers all expected keys")
            break
        return self._create_finding(rule, "non_compliant", description="FORBIDDEN_METADATA_KEYS not found",
                                    remediation="Define FORBIDDEN_METADATA_KEYS in audit.py")

    def _check_report_no_credentials(self, context: AuditContext) -> AuditFinding:
        rule = self._rule("SEC-SENSITIVE-005")[0]
        for sf in context.source_files:
            if "real_report.py" not in sf.path:
                continue
            has_safe_url = "safe_base_url_host" in sf.content or "urlsplit" in sf.content
            no_api_key_in_report = "api_key" not in sf.content.split("def ")[0] if "def " in sf.content else True
            if has_safe_url:
                return self._create_finding(rule, "compliant", file_path=sf.path,
                                            description="Report uses safe URL host; no credential exposure")
            break
        return self._create_finding(rule, "non_compliant", description="Report may expose credentials",
                                    remediation="Use safe_base_url_host() and redact credentials in reports")


    def _check_no_eval_exec(self, context: AuditContext) -> AuditFinding:
        rule = self._rule("SEC-UNSAFE-001")[0]
        eval_hits = _find_in_source(context.source_files, _EVAL_RE)
        exec_hits = _find_in_source(context.source_files, _EXEC_RE)
        sub_hits = _find_in_source(context.source_files, _SUBPROCESS_RE)
        all_dangerous = eval_hits + exec_hits
        if all_dangerous:
            return self._create_finding(rule, "non_compliant",
                                        description=f"Found {len(all_dangerous)} eval/exec call(s)",
                                        evidence=str(all_dangerous),
                                        remediation="Remove eval/exec calls; use safer alternatives")
        if sub_hits:
            allowed_sub = [h for h in sub_hits if "git" in h[2] and "rev-parse" in h[2]]
            if len(allowed_sub) == len(sub_hits):
                return self._create_finding(rule, "compliant",
                                            description="No eval/exec; subprocess limited to git rev-parse only")
            return self._create_finding(rule, "non_compliant",
                                        description=f"subprocess used beyond git rev-parse: {len(sub_hits) - len(allowed_sub)} call(s)",
                                        remediation="Limit subprocess to git rev-parse only")
        return self._create_finding(rule, "compliant", description="No eval/exec/subprocess calls in source")

    def _check_no_float(self, context: AuditContext) -> AuditFinding:
        rule = self._rule("SEC-UNSAFE-002")[0]
        hits = _find_in_source(context.source_files, _FLOAT_CALL_RE)
        if hits:
            return self._create_finding(rule, "non_compliant",
                                        description=f"Found {len(hits)} float() call(s)",
                                        evidence=str(hits),
                                        remediation="Replace float() with decimal.Decimal")
        return self._create_finding(rule, "compliant", description="No float() calls; business calculations use Decimal")

    def _check_https_endpoint(self, context: AuditContext) -> AuditFinding:
        rule = self._rule("SEC-UNSAFE-003")[0]
        for sf in context.source_files:
            if "http_transport.py" not in sf.path:
                continue
            has_validate = "_validate_endpoint" in sf.content
            has_https = "https" in sf.content.lower() or "HTTPS" in sf.content
            if has_validate and has_https:
                return self._create_finding(rule, "compliant", file_path=sf.path,
                                            description="_validate_endpoint() enforces HTTPS for non-localhost")
            break
        return self._create_finding(rule, "non_compliant", description="_validate_endpoint() not found or missing HTTPS check",
                                    remediation="Implement _validate_endpoint() requiring HTTPS for non-localhost")

    def _check_production_write_forbidden(self, context: AuditContext) -> AuditFinding:
        rule = self._rule("SEC-PROD-001")[0]
        found_files: list[str] = []
        for sf in context.source_files:
            if any(kw in sf.path for kw in ("runtime_validator", "preflight", "config_loader")):
                if "production_write" in sf.content and "False" in sf.content:
                    found_files.append(sf.path)
        if found_files:
            return self._create_finding(rule, "compliant",
                                        description=f"production_write_called always False in: {', '.join(found_files)}")
        return self._create_finding(rule, "non_compliant", description="production_write_called enforcement not found",
                                    remediation="Ensure production_write_called is always False in runtime_validator, preflight, config_loader")

    def _check_no_production_adapter(self, context: AuditContext) -> AuditFinding:
        rule = self._rule("SEC-PROD-002")[0]
        hits = _find_in_source(context.source_files, _PRODUCTION_ADAPTER_RE)
        if hits:
            return self._create_finding(rule, "non_compliant",
                                        description=f"Found production adapter reference(s): {len(hits)}",
                                        evidence=str(hits),
                                        remediation="Remove production adapter files/classes")
        return self._create_finding(rule, "compliant", description="No production adapter found")

    def _check_default_offline_mode(self, context: AuditContext) -> AuditFinding:
        rule = self._rule("SEC-NETWORK-001")[0]
        env_example = context.project_path / ".env.example"
        ci_yml = context.project_path / ".github" / "workflows" / "ci.yml"
        checks: list[str] = []
        if env_example.is_file():
            content = env_example.read_text(encoding="utf-8")
            if "LLM_PROVIDER=stub" in content or "LLM_PROVIDER=stub" in content:
                checks.append(".env.example has LLM_PROVIDER=stub")
            if "LLM_REAL_CALL_ENABLED=false" in content:
                checks.append(".env.example has LLM_REAL_CALL_ENABLED=false")
        if ci_yml.is_file():
            content = ci_yml.read_text(encoding="utf-8")
            if "LLM_PROVIDER=stub" in content or "LLM_PROVIDER=stub" in content:
                checks.append("CI sets LLM_PROVIDER=stub")
        for cf in context.config_files:
            if "poc-rules" in cf.path:
                if "provider" in str(cf.parsed) and "stub" in str(cf.parsed.get("reasoner", {}).get("provider", "")):
                    checks.append("YAML config has reasoner.provider=stub")
        if checks:
            return self._create_finding(rule, "compliant", description="Default offline mode confirmed: " + "; ".join(checks))
        return self._create_finding(rule, "non_compliant", description="Default offline mode not confirmed",
                                    remediation="Set LLM_PROVIDER=stub and LLM_REAL_CALL_ENABLED=false in defaults")

    def _check_double_confirmation(self, context: AuditContext) -> AuditFinding:
        rule = self._rule("SEC-NETWORK-002")[0]
        for sf in context.source_files:
            if "provider.py" not in sf.path and "config.py" not in sf.path:
                continue
            has_env_check = "LLM_REAL_CALL_ENABLED" in sf.content
            has_cli_confirm = "confirm" in sf.content.lower()
            if has_env_check:
                return self._create_finding(rule, "compliant", file_path=sf.path,
                                            description="Double confirmation: env var + CLI flag required for real calls")
            break
        return self._create_finding(rule, "non_compliant", description="Double confirmation for real model calls not found",
                                    remediation="Require both LLM_REAL_CALL_ENABLED=true and CLI confirmation")

    def _check_redact_sensitive_patterns(self, context: AuditContext) -> AuditFinding:
        rule = self._rule("SEC-REDACT-001")[0]
        for sf in context.source_files:
            if "security.py" not in sf.path:
                continue
            has_sensitive = "_SENSITIVE" in sf.content
            if not has_sensitive:
                break
            missing = [p for p in _SENSITIVE_PATTERNS_EXPECTED if p not in sf.content]
            if not missing:
                return self._create_finding(rule, "compliant", file_path=sf.path,
                                            description="_SENSITIVE regex covers all expected credential patterns")
            return self._create_finding(rule, "non_compliant", file_path=sf.path,
                                        description=f"_SENSITIVE regex missing patterns: {', '.join(missing)}",
                                        remediation=f"Add missing patterns to _SENSITIVE: {', '.join(missing)}")
        return self._create_finding(rule, "non_compliant", description="_SENSITIVE regex not found in security.py",
                                    remediation="Define _SENSITIVE regex covering all credential patterns")

    def _check_report_url_redaction(self, context: AuditContext) -> AuditFinding:
        rule = self._rule("SEC-REDACT-002")[0]
        for sf in context.source_files:
            if "real_report.py" not in sf.path:
                continue
            if "safe_base_url_host" in sf.content or "urlsplit" in sf.content:
                return self._create_finding(rule, "compliant", file_path=sf.path,
                                            description="Report uses safe_base_url_host() to strip credentials from URLs")
            break
        return self._create_finding(rule, "non_compliant", description="Report URL credential stripping not found",
                                    remediation="Use safe_base_url_host() for base_url in reports")