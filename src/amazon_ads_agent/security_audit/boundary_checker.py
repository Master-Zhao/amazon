"""Architecture boundary checker for audit rules."""

from __future__ import annotations

import ast
from typing import Any, Sequence

from .checkers import BaseChecker
from .models import AuditContext, AuditFinding
from .rules import DEFAULT_BOUNDARY_RULES


def _extract_imports(source_file: Any) -> dict[str, list[str]]:
    tree = source_file.ast_tree
    if tree is None:
        return {}
    imports: dict[str, list[str]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            names = [alias.name for alias in node.names]
            imports.setdefault(module, []).extend(names)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imports.setdefault(alias.name, [])
    return imports


def _extract_class_definitions(source_file: Any) -> list[str]:
    tree = source_file.ast_tree
    if tree is None:
        return []
    classes: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            classes.append(node.name)
    return classes


def _extract_method_signatures(source_file: Any, class_name: str) -> list[str]:
    tree = source_file.ast_tree
    if tree is None:
        return []
    methods: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    args = [a.arg for a in item.args.args]
                    methods.append(f"{item.name}({', '.join(args)})")
    return methods


class BoundaryChecker(BaseChecker):
    """Checks architecture boundaries for 14 boundary rules."""

    @property
    def category(self) -> str:
        return "boundary_check"

    def check(self, context: AuditContext) -> Sequence[AuditFinding]:
        findings: list[AuditFinding] = []
        findings.append(self._check_workflow_reasoner_boundary(context))
        findings.append(self._check_reasoner_transport_boundary(context))
        findings.append(self._check_transport_adapter_boundary(context))
        findings.append(self._check_candidate_reasoner_boundary(context))
        findings.append(self._check_validator_workflow_boundary(context))
        findings.append(self._check_reasoner_immutability_resp(context))
        findings.append(self._check_audit_append_resp(context))
        findings.append(self._check_config_no_fallback(context))
        findings.append(self._check_evaluator_reuse(context))
        findings.append(self._check_reasoner_protocol_signature(context))
        findings.append(self._check_transport_protocol_signature(context))
        findings.append(self._check_schema_validation_independence(context))
        findings.append(self._check_langgraph_routing(context))
        findings.append(self._check_candidate_validation(context))
        return findings

    def _rule(self, rule_id: str):
        for r in DEFAULT_BOUNDARY_RULES:
            if r.rule_id == rule_id:
                return r
        raise ValueError(f"Unknown rule: {rule_id}")

    def _check_workflow_reasoner_boundary(self, context: AuditContext) -> AuditFinding:
        rule = self._rule("BOUNDARY-MODULE-001")
        for sf in context.source_files:
            if "workflow.py" not in sf.path and "langgraph_workflow.py" not in sf.path:
                continue
            has_reason_call = "reason(" in sf.content or ".reason(" in sf.content
            no_credential_pass = "api_key" not in sf.content or "api_key" not in sf.content.split("reason(")[0] if "reason(" in sf.content else True
            if has_reason_call:
                return self._create_finding(rule, "compliant", file_path=sf.path,
                                            description="Workflow calls reasoner via reason(); ReasonerInput carries no credentials")
            break
        return self._create_finding(rule, "non_compliant", description="Workflow-Reasoner boundary not confirmed",
                                    remediation="Ensure workflow calls reasoner.reason(reasoner_input) without passing credentials")

    def _check_reasoner_transport_boundary(self, context: AuditContext) -> AuditFinding:
        rule = self._rule("BOUNDARY-MODULE-002")
        for sf in context.source_files:
            if "llm.py" not in sf.path:
                continue
            has_transport_call = "transport.complete" in sf.content or "self.transport" in sf.content
            has_transport_request = "LLMTransportRequest" in sf.content
            if has_transport_call and has_transport_request:
                return self._create_finding(rule, "compliant", file_path=sf.path,
                                            description="Reasoner calls transport.complete(request); LLMTransportRequest carries no credentials")
            break
        return self._create_finding(rule, "non_compliant", description="Reasoner-Transport boundary not confirmed",
                                    remediation="Use LLMTransportRequest without credentials in transport.complete()")

    def _check_transport_adapter_boundary(self, context: AuditContext) -> AuditFinding:
        rule = self._rule("BOUNDARY-MODULE-003")
        has_transport_response = False
        has_adapter = False
        for sf in context.source_files:
            if "http_transport.py" in sf.path or "maas_transport.py" in sf.path:
                if "LLMTransportResponse" in sf.content:
                    has_transport_response = True
            if "response_adapter.py" in sf.path or "maas_response_adapter.py" in sf.path:
                has_adapter = True
        if has_transport_response and has_adapter:
            return self._create_finding(rule, "compliant",
                                        description="Transport returns LLMTransportResponse; response adapter in independent module")
        return self._create_finding(rule, "non_compliant", description="Transport-Adapter boundary not confirmed",
                                    remediation="Return LLMTransportResponse from transport; parse in independent adapter module")

    def _check_candidate_reasoner_boundary(self, context: AuditContext) -> AuditFinding:
        rule = self._rule("BOUNDARY-MODULE-004")
        has_candidate_values = False
        has_runtime_check = False
        for sf in context.source_files:
            if "base.py" in sf.path and "candidate_values" in sf.content:
                has_candidate_values = True
            if "runtime_validator.py" in sf.path and "CANDIDATE_OUT_OF_RANGE" in sf.content:
                has_runtime_check = True
        if has_candidate_values and has_runtime_check:
            return self._create_finding(rule, "compliant",
                                        description="candidate_values immutable; runtime_validator enforces suggested_value in candidate set")
        return self._create_finding(rule, "non_compliant", description="Candidate-Reasoner boundary not confirmed",
                                    remediation="Ensure candidate_values is immutable and runtime_validator checks membership")

    def _check_validator_workflow_boundary(self, context: AuditContext) -> AuditFinding:
        rule = self._rule("BOUNDARY-MODULE-005")
        for sf in context.source_files:
            if "runtime_validator.py" not in sf.path:
                continue
            has_validate = "validate_runtime" in sf.content
            has_error_codes = "ERR_" in sf.content
            if has_validate and has_error_codes:
                return self._create_finding(rule, "compliant", file_path=sf.path,
                                            description="runtime_validator independently validates schema, references, rules, state")
            break
        return self._create_finding(rule, "non_compliant", description="Validator-Workflow boundary not confirmed",
                                    remediation="Implement independent validate_runtime() with distinct error codes")

    def _check_reasoner_immutability_resp(self, context: AuditContext) -> AuditFinding:
        rule = self._rule("BOUNDARY-RESP-001")
        for sf in context.source_files:
            if "base.py" not in sf.path:
                continue
            has_frozen = "frozen=True" in sf.content
            has_readonly = "Read-only" in sf.content or "never carries credentials" in sf.content
            if has_frozen:
                return self._create_finding(rule, "compliant", file_path=sf.path,
                                            description="ReasonerInput is frozen; immutable responsibility enforced")
            break
        return self._create_finding(rule, "non_compliant", description="Reasoner immutability responsibility not confirmed",
                                    remediation="Make ReasonerInput frozen=True with clear responsibility documentation")

    def _check_audit_append_resp(self, context: AuditContext) -> AuditFinding:
        rule = self._rule("BOUNDARY-RESP-002")
        for sf in context.source_files:
            if "audit.py" not in sf.path:
                continue
            has_record = "def record" in sf.content
            has_set_attempt = "set_attempt_id" in sf.content
            if has_record and has_set_attempt:
                return self._create_finding(rule, "compliant", file_path=sf.path,
                                            description="record() only appends; set_attempt_id() only updates context")
            break
        return self._create_finding(rule, "non_compliant", description="Audit append-only responsibility not confirmed",
                                    remediation="Ensure record() only appends and set_attempt_id() only updates context")

    def _check_config_no_fallback(self, context: AuditContext) -> AuditFinding:
        rule = self._rule("BOUNDARY-RESP-003")
        for sf in context.source_files:
            if "config_loader.py" not in sf.path:
                continue
            has_require = "require_config" in sf.content
            has_error = "RuleConfigError" in sf.content
            if has_require and has_error:
                return self._create_finding(rule, "compliant", file_path=sf.path,
                                            description="require_config() throws RuleConfigError; no fallback inference")
            break
        return self._create_finding(rule, "non_compliant", description="Config no-fallback responsibility not confirmed",
                                    remediation="Implement require_config() that raises RuleConfigError without fallback")

    def _check_evaluator_reuse(self, context: AuditContext) -> AuditFinding:
        rule = self._rule("BOUNDARY-RESP-004")
        eval_dir = context.project_path / "evaluation"
        if not eval_dir.is_dir():
            return self._create_finding(rule, "not_applicable", description="No evaluation directory found")
        py_files = list(eval_dir.rglob("*.py"))
        for pf in py_files:
            try:
                content = pf.read_text(encoding="utf-8")
                if "run_workflow" in content or "validate_runtime" in content or "validate_task_input" in content:
                    return self._create_finding(rule, "compliant", file_path=str(pf),
                                                description="Evaluator reuses formal Workflow/Schema/Runtime Validator")
            except (OSError, UnicodeDecodeError):
                continue
        return self._create_finding(rule, "non_compliant", description="Evaluator does not reuse formal components",
                                    remediation="Ensure evaluator reuses run_workflow, validate_runtime, validate_task_input")

    def _check_reasoner_protocol_signature(self, context: AuditContext) -> AuditFinding:
        rule = self._rule("BOUNDARY-IFACE-001")
        for sf in context.source_files:
            if "base.py" not in sf.path:
                continue
            if sf.ast_tree is None:
                continue
            methods = _extract_method_signatures(sf, "Reasoner")
            if any("reason" in m for m in methods):
                return self._create_finding(rule, "compliant", file_path=sf.path,
                                            description="Reasoner Protocol defines reason(self, reasoner_input) -> ReasonerResult")
            break
        return self._create_finding(rule, "non_compliant", description="Reasoner Protocol signature not confirmed",
                                    remediation="Define Reasoner Protocol with reason(self, reasoner_input) -> ReasonerResult")

    def _check_transport_protocol_signature(self, context: AuditContext) -> AuditFinding:
        rule = self._rule("BOUNDARY-IFACE-002")
        for sf in context.source_files:
            if "transport.py" not in sf.path:
                continue
            if sf.ast_tree is None:
                continue
            methods = _extract_method_signatures(sf, "LLMTransport")
            if any("complete" in m for m in methods):
                return self._create_finding(rule, "compliant", file_path=sf.path,
                                            description="LLMTransport Protocol defines complete(self, request) -> LLMTransportResponse")
            break
        return self._create_finding(rule, "non_compliant", description="LLMTransport Protocol signature not confirmed",
                                    remediation="Define LLMTransport Protocol with complete(self, request) -> LLMTransportResponse")

    def _check_schema_validation_independence(self, context: AuditContext) -> AuditFinding:
        rule = self._rule("BOUNDARY-IFACE-003")
        for sf in context.source_files:
            if "schema_loader.py" not in sf.path:
                continue
            has_task = "validate_task_input" in sf.content
            has_output = "validate_agent_output" in sf.content
            has_failure = "validate_failure_analysis" in sf.content
            has_manual = "validate_manual_intervention_package" in sf.content
            has_audit = "validate_audit_event" in sf.content
            if has_task and has_output and has_failure and has_manual and has_audit:
                return self._create_finding(rule, "compliant", file_path=sf.path,
                                            description="5 independent schema validation functions present")
            break
        return self._create_finding(rule, "non_compliant", description="Schema validation independence not confirmed",
                                    remediation="Implement 5 independent validate_* functions in schema_loader.py")

    def _check_langgraph_routing(self, context: AuditContext) -> AuditFinding:
        rule = self._rule("BOUNDARY-IFACE-004")
        for sf in context.source_files:
            if "langgraph_workflow.py" not in sf.path:
                continue
            has_evidence_route = "route_after_evidence" in sf.content
            has_validation_route = "route_after_validation" in sf.content
            has_reasoner_route = "route_after_reasoner" in sf.content
            if has_evidence_route and has_validation_route and has_reasoner_route:
                return self._create_finding(rule, "compliant", file_path=sf.path,
                                            description="3 explicit routing functions: route_after_evidence, route_after_validation, route_after_reasoner")
            break
        return self._create_finding(rule, "non_compliant", description="LangGraph routing functions not confirmed",
                                    remediation="Implement route_after_evidence, route_after_validation, route_after_reasoner")

    def _check_candidate_validation(self, context: AuditContext) -> AuditFinding:
        rule = self._rule("BOUNDARY-IFACE-005")
        for sf in context.source_files:
            if "runtime_validator.py" not in sf.path:
                continue
            has_candidate_check = "CANDIDATE_OUT_OF_RANGE" in sf.content or "candidate_values" in sf.content
            if has_candidate_check:
                return self._create_finding(rule, "compliant", file_path=sf.path,
                                            description="Runtime Validator checks suggested_value in candidate_values; ERR_CANDIDATE_OUT_OF_RANGE")
            break
        return self._create_finding(rule, "non_compliant", description="Candidate validation not confirmed",
                                    remediation="Validate suggested_value belongs to candidate_values; return ERR_CANDIDATE_OUT_OF_RANGE")