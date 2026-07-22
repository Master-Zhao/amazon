"""Unit tests for the rule registry."""

from __future__ import annotations

import pytest

from amazon_ads_agent.security_audit.models import AuditContext, AuditFinding, AuditRule
from amazon_ads_agent.security_audit.registry import RuleRegistry
from amazon_ads_agent.security_audit.rules import ALL_DEFAULT_RULES, DEFAULT_BOUNDARY_RULES, DEFAULT_COMPLIANCE_RULES, DEFAULT_SECURITY_RULES


class TestRuleRegistry:
    def test_register_single(self):
        registry = RuleRegistry()
        rule = AuditRule(rule_id="TEST-001", category="security", severity="high", description="test", check_function="check_test")
        registry.register(rule)
        assert registry.rule_count == 1

    def test_register_duplicate_raises(self):
        registry = RuleRegistry()
        rule = AuditRule(rule_id="TEST-001", category="security", severity="high", description="test", check_function="check_test")
        registry.register(rule)
        with pytest.raises(ValueError, match="Duplicate"):
            registry.register(rule)

    def test_register_all(self):
        registry = RuleRegistry()
        registry.register_all(DEFAULT_SECURITY_RULES)
        assert registry.rule_count == len(DEFAULT_SECURITY_RULES)

    def test_get_rules_all(self):
        registry = RuleRegistry()
        registry.register_all(ALL_DEFAULT_RULES)
        all_rules = registry.get_rules()
        assert len(all_rules) == 44

    def test_get_rules_by_category(self):
        registry = RuleRegistry()
        registry.register_all(ALL_DEFAULT_RULES)
        security_rules = registry.get_rules(category="security")
        assert len(security_rules) == len(DEFAULT_SECURITY_RULES)
        assert all(r.category == "security" for r in security_rules)

    def test_get_rules_compliance(self):
        registry = RuleRegistry()
        registry.register_all(ALL_DEFAULT_RULES)
        compliance_rules = registry.get_rules(category="compliance")
        assert len(compliance_rules) == len(DEFAULT_COMPLIANCE_RULES)

    def test_get_rules_boundary(self):
        registry = RuleRegistry()
        registry.register_all(ALL_DEFAULT_RULES)
        boundary_rules = registry.get_rules(category="boundary")
        assert len(boundary_rules) == len(DEFAULT_BOUNDARY_RULES)

    def test_get_rule_by_id(self):
        registry = RuleRegistry()
        registry.register_all(ALL_DEFAULT_RULES)
        rule = registry.get_rule("SEC-SENSITIVE-001")
        assert rule is not None
        assert rule.rule_id == "SEC-SENSITIVE-001"

    def test_get_rule_not_found(self):
        registry = RuleRegistry()
        assert registry.get_rule("NONEXISTENT") is None

    def test_execute(self):
        registry = RuleRegistry()
        rule = AuditRule(rule_id="TEST-001", category="security", severity="high", description="test", check_function="check_test")
        registry.register(rule)
        from pathlib import Path
        context = AuditContext(project_path=Path("/test"))
        finding = registry.execute(rule, context, lambda ctx: AuditFinding(
            rule_id="TEST-001", category="security", severity="high", status="compliant"
        ))
        assert finding is not None
        assert finding.status == "compliant"

    def test_all_rules_count(self):
        assert len(ALL_DEFAULT_RULES) == 44
        assert len(DEFAULT_SECURITY_RULES) == 18
        assert len(DEFAULT_COMPLIANCE_RULES) == 12
        assert len(DEFAULT_BOUNDARY_RULES) == 14