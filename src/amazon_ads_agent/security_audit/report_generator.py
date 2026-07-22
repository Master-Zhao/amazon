"""Audit report generator with JSON and Markdown output."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import (
    AuditFinding,
    AuditReport,
    AuditSummary,
    PotentialImprovement,
    create_report_id,
    create_timestamp,
    redact_evidence,
)


class AuditReportGenerator:
    """Generates audit reports in JSON and Markdown formats."""

    def generate_report(
        self,
        security_findings: tuple[AuditFinding, ...],
        compliance_findings: tuple[AuditFinding, ...],
        boundary_findings: tuple[AuditFinding, ...],
        project_path: str,
    ) -> AuditReport:
        all_findings = security_findings + compliance_findings + boundary_findings
        summary = self._build_summary(all_findings)
        improvements = self._identify_improvements(all_findings)
        return AuditReport(
            report_id=create_report_id(),
            generated_at=create_timestamp(),
            project_path=project_path,
            security_findings=security_findings,
            compliance_findings=compliance_findings,
            boundary_findings=boundary_findings,
            summary=summary,
            potential_improvements=improvements,
        )

    def _build_summary(self, all_findings: tuple[AuditFinding, ...]) -> AuditSummary:
        total = len(all_findings)
        compliant = sum(1 for f in all_findings if f.status == "compliant")
        non_compliant = sum(1 for f in all_findings if f.status == "non_compliant")
        critical = sum(1 for f in all_findings if f.severity == "critical" and f.status == "non_compliant")
        high = sum(1 for f in all_findings if f.severity == "high" and f.status == "non_compliant")
        medium = sum(1 for f in all_findings if f.severity == "medium" and f.status == "non_compliant")
        low = sum(1 for f in all_findings if f.severity == "low" and f.status == "non_compliant")
        return AuditSummary(
            total_rules=total,
            compliant_count=compliant,
            non_compliant_count=non_compliant,
            critical_count=critical,
            high_count=high,
            medium_count=medium,
            low_count=low,
        )

    def _identify_improvements(self, all_findings: tuple[AuditFinding, ...]) -> tuple[PotentialImprovement, ...]:
        improvements: list[PotentialImprovement] = []
        for f in all_findings:
            if f.status == "non_compliant":
                improvements.append(PotentialImprovement(
                    improvement_id=f"IMP-{f.rule_id}",
                    severity=f.severity,
                    description=f.description,
                    affected_files=(f.file_path,) if f.file_path else (),
                    remediation=f.remediation,
                ))
        return tuple(improvements)

    def to_json(self, report: AuditReport) -> dict[str, Any]:
        def _finding_to_dict(f: AuditFinding) -> dict[str, Any]:
            return {
                "rule_id": f.rule_id,
                "category": f.category,
                "severity": f.severity,
                "status": f.status,
                "file_path": f.file_path,
                "line_number": f.line_number,
                "description": f.description,
                "evidence": redact_evidence(f.evidence),
                "remediation": f.remediation,
            }

        def _improvement_to_dict(imp: PotentialImprovement) -> dict[str, Any]:
            return {
                "improvement_id": imp.improvement_id,
                "severity": imp.severity,
                "description": imp.description,
                "affected_files": list(imp.affected_files),
                "remediation": imp.remediation,
            }

        return {
            "report_id": report.report_id,
            "generated_at": report.generated_at,
            "project_path": report.project_path,
            "summary": {
                "total_rules": report.summary.total_rules,
                "compliant_count": report.summary.compliant_count,
                "non_compliant_count": report.summary.non_compliant_count,
                "critical_count": report.summary.critical_count,
                "high_count": report.summary.high_count,
                "medium_count": report.summary.medium_count,
                "low_count": report.summary.low_count,
            },
            "security_findings": [_finding_to_dict(f) for f in report.security_findings],
            "compliance_findings": [_finding_to_dict(f) for f in report.compliance_findings],
            "boundary_findings": [_finding_to_dict(f) for f in report.boundary_findings],
            "potential_improvements": [_improvement_to_dict(imp) for imp in report.potential_improvements],
        }

    def to_markdown(self, report: AuditReport) -> str:
        lines: list[str] = []
        lines.append(f"# Security Audit Report")
        lines.append("")
        lines.append(f"- **Report ID**: {report.report_id}")
        lines.append(f"- **Generated At**: {report.generated_at}")
        lines.append(f"- **Project Path**: {report.project_path}")
        lines.append("")

        lines.append("## Summary")
        lines.append("")
        s = report.summary
        lines.append(f"| Metric | Count |")
        lines.append(f"|--------|-------|")
        lines.append(f"| Total Rules | {s.total_rules} |")
        lines.append(f"| Compliant | {s.compliant_count} |")
        lines.append(f"| Non-Compliant | {s.non_compliant_count} |")
        lines.append(f"| Critical | {s.critical_count} |")
        lines.append(f"| High | {s.high_count} |")
        lines.append(f"| Medium | {s.medium_count} |")
        lines.append(f"| Low | {s.low_count} |")
        lines.append("")

        for category_name, findings in [
            ("Security Findings", report.security_findings),
            ("Compliance Findings", report.compliance_findings),
            ("Boundary Findings", report.boundary_findings),
        ]:
            lines.append(f"## {category_name}")
            lines.append("")
            if not findings:
                lines.append("_No findings._")
                lines.append("")
                continue
            sorted_findings = sorted(findings, key=lambda f: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(f.severity, 4))
            for f in sorted_findings:
                status_icon = "✅" if f.status == "compliant" else "❌" if f.status == "non_compliant" else "➖"
                lines.append(f"### {status_icon} {f.rule_id} ({f.severity})")
                lines.append(f"- **Status**: {f.status}")
                if f.file_path:
                    lines.append(f"- **File**: {f.file_path}")
                if f.line_number:
                    lines.append(f"- **Line**: {f.line_number}")
                lines.append(f"- **Description**: {f.description}")
                if f.evidence:
                    lines.append(f"- **Evidence**: {redact_evidence(f.evidence)}")
                if f.remediation:
                    lines.append(f"- **Remediation**: {f.remediation}")
                lines.append("")

        if report.potential_improvements:
            lines.append("## Potential Improvements")
            lines.append("")
            for imp in report.potential_improvements:
                lines.append(f"- **{imp.improvement_id}** ({imp.severity}): {imp.description}")
                if imp.affected_files:
                    lines.append(f"  - Affected: {', '.join(imp.affected_files)}")
                if imp.remediation:
                    lines.append(f"  - Remediation: {imp.remediation}")
            lines.append("")

        return "\n".join(lines)

    def write_reports(
        self,
        report: AuditReport,
        json_path: Path | None = None,
        markdown_path: Path | None = None,
    ) -> None:
        if json_path is not None:
            json_path.parent.mkdir(parents=True, exist_ok=True)
            json_path.write_text(json.dumps(self.to_json(report), indent=2, ensure_ascii=False), encoding="utf-8")
        if markdown_path is not None:
            markdown_path.parent.mkdir(parents=True, exist_ok=True)
            markdown_path.write_text(self.to_markdown(report), encoding="utf-8")