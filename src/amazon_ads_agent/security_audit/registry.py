"""Rule registry for registering and executing audit checks."""

from __future__ import annotations

from typing import Callable, Sequence

from .models import AuditContext, AuditFinding, AuditRule


class RuleRegistry:
    """Central registry for audit rules with execution support."""

    def __init__(self) -> None:
        self._rules: dict[str, AuditRule] = {}

    def register(self, rule: AuditRule) -> None:
        if rule.rule_id in self._rules:
            raise ValueError(f"Duplicate rule_id: {rule.rule_id}")
        self._rules[rule.rule_id] = rule

    def register_all(self, rules: Sequence[AuditRule]) -> None:
        for rule in rules:
            self.register(rule)

    def get_rules(self, category: str | None = None) -> tuple[AuditRule, ...]:
        if category is None:
            return tuple(self._rules.values())
        return tuple(r for r in self._rules.values() if r.category == category)

    def get_rule(self, rule_id: str) -> AuditRule | None:
        return self._rules.get(rule_id)

    def execute(
        self,
        rule: AuditRule,
        context: AuditContext,
        check_fn: Callable[[AuditContext], AuditFinding | None],
    ) -> AuditFinding | None:
        return check_fn(context)

    @property
    def rule_count(self) -> int:
        return len(self._rules)