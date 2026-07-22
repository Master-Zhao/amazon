"""Prompt security checker for audit rules."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from .checkers import BaseChecker
from .models import AuditContext, AuditFinding, PromptFile
from .rules import DEFAULT_SECURITY_RULES


def _load_prompt_files(project_path: Path) -> list[PromptFile]:
    prompt_dir = project_path / "prompts"
    if not prompt_dir.is_dir():
        return []
    files: list[PromptFile] = []
    for md_file in sorted(prompt_dir.glob("*.md")):
        try:
            content = md_file.read_text(encoding="utf-8")
            files.append(PromptFile(path=str(md_file.relative_to(project_path)), content=content))
        except (OSError, UnicodeDecodeError):
            continue
    return files


class PromptChecker(BaseChecker):
    """Checks prompt templates for security rules."""

    @property
    def category(self) -> str:
        return "prompt_check"

    def check(self, context: AuditContext) -> Sequence[AuditFinding]:
        if not context.prompt_files:
            context.prompt_files = _load_prompt_files(context.project_path)
        findings: list[AuditFinding] = []
        findings.append(self._check_prompt_data_isolation(context))
        findings.append(self._check_trust_boundary(context))
        findings.append(self._check_whitelist_loading(context))
        findings.append(self._check_strict_parsing(context))
        return findings

    def _rule(self, rule_id: str):
        for r in DEFAULT_SECURITY_RULES:
            if r.rule_id == rule_id:
                return r
        raise ValueError(f"Unknown rule: {rule_id}")

    def _check_prompt_data_isolation(self, context: AuditContext) -> AuditFinding:
        rule = self._rule("SEC-INJECTION-001")
        for sf in context.source_files:
            if "prompt_builder.py" not in sf.path:
                continue
            has_json_tag = "reasoner_input_json" in sf.content
            if has_json_tag:
                return self._create_finding(rule, "compliant", file_path=sf.path,
                                            description="Prompt data isolated via <reasoner_input_json> tag (prompt-side verification)")
            break
        return self._create_finding(rule, "non_compliant", description="Prompt data isolation not verified from prompt side",
                                    remediation="Ensure PromptBuilder uses <reasoner_input_json> tag for data injection")

    def _check_trust_boundary(self, context: AuditContext) -> AuditFinding:
        rule = self._rule("SEC-INJECTION-002")
        for pf in context.prompt_files:
            if "reasoner-system" not in pf.path:
                continue
            has_boundary = any(
                phrase in pf.content.lower()
                for phrase in ["data trust boundary", "数据信任边界", "instructions in data fields have no system authority",
                               "数据字段中的指令无系统权限"]
            )
            if has_boundary:
                return self._create_finding(rule, "compliant", file_path=pf.path,
                                            description="Data Trust Boundary declaration in system prompt (prompt-side)")
            break
        return self._create_finding(rule, "non_compliant", description="Data Trust Boundary not in prompt template",
                                    remediation="Add trust boundary declaration to reasoner-system.md")

    def _check_whitelist_loading(self, context: AuditContext) -> AuditFinding:
        rule = self._rule("SEC-INJECTION-004")
        for sf in context.source_files:
            if "prompt_loader.py" not in sf.path:
                continue
            has_whitelist = "ALLOWED_PROMPTS" in sf.content
            if has_whitelist:
                return self._create_finding(rule, "compliant", file_path=sf.path,
                                            description="ALLOWED_PROMPTS whitelist enforced (prompt-side)")
            break
        return self._create_finding(rule, "non_compliant", description="ALLOWED_PROMPTS whitelist not found",
                                    remediation="Implement ALLOWED_PROMPTS whitelist in prompt_loader.py")

    def _check_strict_parsing(self, context: AuditContext) -> AuditFinding:
        rule = self._rule("SEC-INJECTION-003")
        for sf in context.source_files:
            if "llm.py" not in sf.path:
                continue
            has_json_loads = "json.loads" in sf.content
            has_reject = "reject_constant" in sf.content or "object_pairs_hook" in sf.content or "parse_constant" in sf.content
            if has_json_loads and has_reject:
                return self._create_finding(rule, "compliant", file_path=sf.path,
                                            description="Strict JSON parsing with rejection of non-standard values (prompt-side)")
            break
        return self._create_finding(rule, "non_compliant", description="Strict JSON parsing not confirmed from prompt side",
                                    remediation="Use json.loads with object_pairs_hook/reject_constant in _parse()")