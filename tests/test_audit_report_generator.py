"""Unit tests for the report generator and audit runner."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from amazon_ads_agent.security_audit.models import AuditFinding, AuditReport, AuditSummary
from amazon_ads_agent.security_audit.report_generator import AuditReportGenerator
from amazon_ads_agent.security_audit.runner import AuditRunner, create_default_registry


def _compliant_finding(rule_id="SEC-001", category="security", severity="high"):
    return AuditFinding(rule_id=rule_id, category=category, severity=severity, status="compliant")


def _non_compliant_finding(rule_id="SEC-002", category="security", severity="critical"):
    return AuditFinding(rule_id=rule_id, category=category, severity=severity, status="non_compliant",
                        description="test issue", remediation="fix it")


class TestAuditReportGenerator:
    def test_generate_report(self):
        gen = AuditReportGenerator()
        report = gen.generate_report(
            security_findings=(_compliant_finding(),),
            compliance_findings=(_compliant_finding(rule_id="COMP-001", category="compliance"),),
            boundary_findings=(_compliant_finding(rule_id="BOUND-001", category="boundary"),),
            project_path="/test",
        )
        assert report.report_id.startswith("audit-")
        assert "T" in report.generated_at
        assert report.project_path == "/test"

    def test_build_summary(self):
        gen = AuditReportGenerator()
        findings = (
            _compliant_finding(),
            _non_compliant_finding(),
            AuditFinding(rule_id="COMP-001", category="compliance", severity="medium", status="compliant"),
        )
        report = gen.generate_report(security_findings=findings[:2], compliance_findings=findings[2:],
                                     boundary_findings=(), project_path="/test")
        assert report.summary.total_rules == 3
        assert report.summary.compliant_count == 2
        assert report.summary.non_compliant_count == 1
        assert report.summary.critical_count == 1

    def test_identify_improvements(self):
        gen = AuditReportGenerator()
        findings = (_non_compliant_finding(), _compliant_finding())
        report = gen.generate_report(security_findings=findings, compliance_findings=(), boundary_findings=(), project_path="/test")
        assert len(report.potential_improvements) == 1
        assert report.potential_improvements[0].improvement_id == "IMP-SEC-002"

    def test_to_json_no_credentials(self):
        gen = AuditReportGenerator()
        findings = (AuditFinding(rule_id="SEC-001", category="security", severity="high", status="non_compliant",
                                 evidence="api_key=sk-secret123"),)
        report = gen.generate_report(security_findings=findings, compliance_findings=(), boundary_findings=(), project_path="/test")
        result = gen.to_json(report)
        assert isinstance(result, dict)
        evidence_str = str(result["security_findings"][0]["evidence"])
        assert "sk-secret123" not in evidence_str
        assert "[REDACTED]" in evidence_str

    def test_to_markdown(self):
        gen = AuditReportGenerator()
        findings = (_compliant_finding(), _non_compliant_finding())
        report = gen.generate_report(security_findings=findings, compliance_findings=(), boundary_findings=(), project_path="/test")
        md = gen.to_markdown(report)
        assert "# Security Audit Report" in md
        assert "## Summary" in md
        assert "## Security Findings" in md

    def test_to_markdown_severity_sort(self):
        gen = AuditReportGenerator()
        findings = (
            AuditFinding(rule_id="SEC-LOW", category="security", severity="low", status="non_compliant"),
            AuditFinding(rule_id="SEC-CRIT", category="security", severity="critical", status="non_compliant"),
            AuditFinding(rule_id="SEC-HIGH", category="security", severity="high", status="non_compliant"),
        )
        report = gen.generate_report(security_findings=findings, compliance_findings=(), boundary_findings=(), project_path="/test")
        md = gen.to_markdown(report)
        crit_pos = md.find("SEC-CRIT")
        high_pos = md.find("SEC-HIGH")
        low_pos = md.find("SEC-LOW")
        assert crit_pos < high_pos < low_pos

    def test_write_reports(self, tmp_path):
        gen = AuditReportGenerator()
        report = gen.generate_report(security_findings=(_compliant_finding(),), compliance_findings=(), boundary_findings=(), project_path="/test")
        json_path = tmp_path / "report.json"
        md_path = tmp_path / "report.md"
        gen.write_reports(report, json_path=json_path, markdown_path=md_path)
        assert json_path.exists()
        assert md_path.exists()
        data = json.loads(json_path.read_text(encoding="utf-8"))
        assert data["report_id"] == report.report_id


class TestAuditRunner:
    def test_init_default_registry(self):
        from pathlib import Path
        runner = AuditRunner(Path("/nonexistent"))
        assert runner.registry.rule_count == 44

    def test_context_caching(self, tmp_path):
        src_dir = tmp_path / "src" / "pkg"
        src_dir.mkdir(parents=True)
        (src_dir / "__init__.py").write_text("", encoding="utf-8")
        runner = AuditRunner(tmp_path)
        ctx1 = runner._get_context()
        ctx2 = runner._get_context()
        assert ctx1 is ctx2

    def test_run_full_audit(self, tmp_path):
        src_dir = tmp_path / "src" / "amazon_ads_agent"
        src_dir.mkdir(parents=True)
        (src_dir / "__init__.py").write_text("", encoding="utf-8")
        runner = AuditRunner(tmp_path)
        report = runner.run_full_audit()
        assert isinstance(report, AuditReport)
        assert report.summary.total_rules > 0