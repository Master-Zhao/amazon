"""Unit tests for security audit data models and helpers."""

from __future__ import annotations

import pytest

from amazon_ads_agent.security_audit.models import (
    AuditContext,
    AuditFinding,
    AuditReport,
    AuditRule,
    AuditSummary,
    ConfigFile,
    PotentialImprovement,
    PromptFile,
    SchemaFile,
    SourceFile,
    create_report_id,
    create_timestamp,
    redact_evidence,
)


class TestAuditRule:
    def test_create_success(self):
        rule = AuditRule(rule_id="SEC-001", category="security", severity="high", description="test", check_function="check_test")
        assert rule.rule_id == "SEC-001"
        assert rule.category == "security"
        assert rule.severity == "high"

    def test_invalid_severity_raises(self):
        with pytest.raises(ValueError, match="severity"):
            AuditRule(rule_id="SEC-001", category="security", severity="extreme", description="test", check_function="check_test")

    def test_invalid_category_raises(self):
        with pytest.raises(ValueError, match="category"):
            AuditRule(rule_id="SEC-001", category="unknown", severity="high", description="test", check_function="check_test")

    def test_frozen(self):
        rule = AuditRule(rule_id="SEC-001", category="security", severity="high", description="test", check_function="check_test")
        with pytest.raises(AttributeError):
            rule.severity = "low"


class TestAuditFinding:
    def test_create_compliant(self):
        f = AuditFinding(rule_id="SEC-001", category="security", severity="high", status="compliant")
        assert f.status == "compliant"

    def test_create_non_compliant(self):
        f = AuditFinding(rule_id="SEC-001", category="security", severity="high", status="non_compliant")
        assert f.status == "non_compliant"

    def test_create_partial(self):
        f = AuditFinding(rule_id="COMP-001", category="compliance", severity="medium", status="partial")
        assert f.status == "partial"

    def test_create_clear(self):
        f = AuditFinding(rule_id="BOUND-001", category="boundary", severity="high", status="clear")
        assert f.status == "clear"

    def test_create_unclear(self):
        f = AuditFinding(rule_id="BOUND-002", category="boundary", severity="medium", status="unclear")
        assert f.status == "unclear"

    def test_create_violated(self):
        f = AuditFinding(rule_id="BOUND-003", category="boundary", severity="critical", status="violated")
        assert f.status == "violated"

    def test_invalid_status_raises(self):
        with pytest.raises(ValueError, match="status"):
            AuditFinding(rule_id="SEC-001", category="security", severity="high", status="invalid")

    def test_evidence_akia_redacted(self):
        f = AuditFinding(rule_id="SEC-001", category="security", severity="critical", status="non_compliant",
                         evidence="Found key AKIAIOSFODNN7EXAMPLE in code")
        assert "AKIAIOSFODNN7EXAMPLE" not in f.evidence
        assert "AKIA[REDACTED]" in f.evidence

    def test_evidence_bearer_redacted(self):
        f = AuditFinding(rule_id="SEC-001", category="security", severity="critical", status="non_compliant",
                         evidence="token: Bearer abc123token")
        assert "abc123token" not in f.evidence
        assert "[REDACTED]" in f.evidence

    def test_evidence_api_key_redacted(self):
        f = AuditFinding(rule_id="SEC-001", category="security", severity="high", status="non_compliant",
                         evidence="api_key=sk-abc123secretkey")
        assert "sk-abc123secretkey" not in f.evidence
        assert "[REDACTED]" in f.evidence

    def test_evidence_password_redacted(self):
        f = AuditFinding(rule_id="SEC-001", category="security", severity="high", status="non_compliant",
                         evidence="password=mysecretpass")
        assert "mysecretpass" not in f.evidence
        assert "[REDACTED]" in f.evidence

    def test_frozen(self):
        f = AuditFinding(rule_id="SEC-001", category="security", severity="high", status="compliant")
        with pytest.raises(AttributeError):
            f.status = "non_compliant"


class TestRedactEvidence:
    def test_akia_redaction(self):
        assert "AKIA[REDACTED]" in redact_evidence("key=AKIAIOSFODNN7EXAMPLE")

    def test_bearer_redaction(self):
        assert "Bearer [REDACTED]" in redact_evidence("Bearer abc123token")

    def test_api_key_redaction(self):
        result = redact_evidence("api_key=sk-abc123")
        assert "sk-abc123" not in result
        assert "[REDACTED]" in result

    def test_no_secrets_unchanged(self):
        assert redact_evidence("normal text") == "normal text"


class TestAuditSummary:
    def test_defaults_zero(self):
        s = AuditSummary()
        assert s.total_rules == 0
        assert s.compliant_count == 0
        assert s.non_compliant_count == 0
        assert s.critical_count == 0

    def test_manual_values(self):
        s = AuditSummary(total_rules=44, compliant_count=40, non_compliant_count=4)
        assert s.total_rules == 44
        assert s.compliant_count == 40


class TestPotentialImprovement:
    def test_create(self):
        imp = PotentialImprovement(improvement_id="IMP-001", severity="medium", description="test improvement")
        assert imp.improvement_id == "IMP-001"
        assert isinstance(imp.affected_files, tuple)

    def test_with_affected_files(self):
        imp = PotentialImprovement(improvement_id="IMP-001", severity="medium", description="test",
                                   affected_files=("a.py", "b.py"))
        assert len(imp.affected_files) == 2


class TestAuditReport:
    def test_create(self):
        r = AuditReport(report_id="audit-abc", generated_at="2026-01-01T00:00:00", project_path="/test")
        assert r.report_id == "audit-abc"
        assert isinstance(r.security_findings, tuple)
        assert isinstance(r.compliance_findings, tuple)
        assert isinstance(r.boundary_findings, tuple)


class TestAuditContext:
    def test_create_defaults(self):
        from pathlib import Path
        ctx = AuditContext(project_path=Path("/test"))
        assert ctx.source_files == []
        assert ctx.config_files == []
        assert ctx.prompt_files == []
        assert ctx.schema_files == []


class TestHelpers:
    def test_create_report_id(self):
        rid = create_report_id()
        assert rid.startswith("audit-")
        assert len(rid) == 18

    def test_create_timestamp(self):
        ts = create_timestamp()
        assert "T" in ts
        assert len(ts) > 10