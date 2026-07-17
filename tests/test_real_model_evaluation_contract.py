"""Real evaluation, reporting, budget, and acceptance contract tests."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from amazon_ads_agent.reasoners.config import LLMReasonerConfig
from amazon_ads_agent.reasoners.http_transport import HTTPResponse, OpenAICompatibleHTTPTransport
from evaluation.case_loader import load_case
from evaluation.models import EvaluationError, RealEvaluationRun
from evaluation.real_config import RealEvaluationConfig
from evaluation.real_evaluator import evaluate_real_case
from evaluation.real_metrics import calculate_real_summary, evaluate_acceptance
from evaluation.real_report import build_real_markdown, build_real_report, write_real_reports
from evaluation.run_evaluation import RESULTS_ROOT, _real_output_paths, build_parser, main

FAKE_KEY = "test-only-not-a-real-key"


class Client:
    def __init__(self, responses: list[HTTPResponse]) -> None:
        self.responses = list(responses)
        self.call_count = 0

    def post(self, url, headers, body, timeout_seconds):
        self.call_count += 1
        return self.responses.pop(0)


def _config() -> LLMReasonerConfig:
    return LLMReasonerConfig(
        "llm", "test-model", FAKE_KEY, "https://model.invalid/v1/chat/completions", 5, 0, True, 512
    )


def _provider(value: str = "1.08", *, usage: bool = True) -> HTTPResponse:
    content = json.dumps({
        "schema_version": "1.0", "decision": "select", "selected_value": value,
        "reason": "structured synthetic response",
        "evidence_paths": ["calculated_metrics.acos", "task_context.target_acos"],
        "risk_summary": "human approval is required", "confidence": "0.800000",
    })
    document = {"id": "request-test", "choices": [{"message": {"content": content}}]}
    if usage:
        document["usage"] = {"prompt_tokens": 12, "completion_tokens": 8, "total_tokens": 20}
    return HTTPResponse(200, {}, json.dumps(document).encode())


def _run(**overrides) -> RealEvaluationRun:
    values = dict(
        run_id="CASE-001-run-01", case_id="CASE-001", name="high_acos_balanced", repetition=1,
        passed=True, reasoner_required=True, first_json_passed=True, first_schema_passed=True,
        first_business_passed=True, final_json_passed=True, final_schema_passed=True,
        final_business_passed=True, terminal_status="waiting_for_approval", selected_value="1.08",
        reasoner_call_count=1, actual_request_count=1, agent_revision_count=0, transport_retry_count=0,
        manual_intervention_generated=False, error_codes=(), production_write_called=False,
        approval_bypass_detected=False, final_candidate_violation_detected=False,
        final_hallucinated_object_detected=False, final_invalid_evidence_detected=False,
        preflight_boundary_violation=False, controlled_failure_injection=False, latencies_ms=(10,),
        input_token_count=12, output_token_count=8, total_token_count=20,
    )
    values.update(overrides)
    return RealEvaluationRun(**values)


def test_parser_defaults_to_fake_and_supports_real() -> None:
    assert build_parser().parse_args([]).provider == "fake"
    assert build_parser().parse_args(["--provider", "real", "--confirm-real-model"]).confirm_real_model


def test_real_provider_requires_cli_confirmation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "llm")
    assert main(["--provider", "real"]) == 2


def test_confirmation_is_rejected_for_fake() -> None:
    assert main(["--provider", "fake", "--confirm-real-model"]) == 2


def test_real_default_paths_are_timestamped_and_separate() -> None:
    json_path, md_path = _real_output_paths(None, None)
    assert json_path.parent == RESULTS_ROOT and md_path.parent == RESULTS_ROOT
    assert json_path.name.startswith("real-model-") and md_path.name.startswith("real-model-")
    assert json_path.name not in {"latest.json", "latest.md"}


@pytest.mark.parametrize(
    ("json_path", "md_path"),
    [(Path("../real-model-x.json"), Path("evaluation/results/real-model-x.md")),
     (Path("evaluation/results/custom.json"), Path("evaluation/results/real-model-x.md"))],
)
def test_real_output_path_traversal_or_wrong_prefix_is_rejected(json_path: Path, md_path: Path) -> None:
    with pytest.raises(EvaluationError, match="ERR_EVALUATION_PATH_INVALID"):
        _real_output_paths(json_path, md_path)


def test_case_004_real_mode_makes_zero_requests() -> None:
    client = Client([])
    transport = OpenAICompatibleHTTPTransport(_config(), client=client)
    run = evaluate_real_case(
        load_case("CASE-004"), repetition=1, reasoner_config=_config(), transport=transport,
        budget=RealEvaluationConfig(repetitions=1),
    )
    assert run.passed and run.reasoner_call_count == 0 and run.actual_request_count == 0
    assert client.call_count == 0


def test_controlled_case_011_revision_is_explicit_and_separated() -> None:
    client = Client([_provider(), _provider()])
    transport = OpenAICompatibleHTTPTransport(_config(), client=client)
    run = evaluate_real_case(
        load_case("CASE-011"), repetition=1, reasoner_config=_config(), transport=transport,
        budget=RealEvaluationConfig(repetitions=1), controlled_revision=True,
    )
    assert run.passed and run.controlled_failure_injection
    assert run.agent_revision_count == 1 and run.actual_request_count == 2
    assert run.transport_retry_count == 0
    assert "ERR_CANDIDATE_OUT_OF_RANGE" in run.error_codes


def test_controlled_revision_does_not_repair_non_json_model_content() -> None:
    bad = HTTPResponse(200, {}, json.dumps({
        "id": "request-test", "choices": [{"message": {"content": "not-json"}}]
    }).encode())
    run = evaluate_real_case(
        load_case("CASE-011"), repetition=1, reasoner_config=_config(),
        transport=OpenAICompatibleHTTPTransport(_config(), client=Client([bad])),
        budget=RealEvaluationConfig(repetitions=1), controlled_revision=True,
    )
    assert not run.passed and not run.controlled_failure_injection
    assert run.terminal_status == "manual_intervention_required"


def test_real_run_records_usage_and_latency_without_raw_response() -> None:
    ticks = iter([0, 9_000_000])
    transport = OpenAICompatibleHTTPTransport(_config(), client=Client([_provider()]), clock=lambda: next(ticks))
    run = evaluate_real_case(
        load_case("CASE-001"), repetition=1, reasoner_config=_config(), transport=transport,
        budget=RealEvaluationConfig(repetitions=1),
    )
    assert run.latencies_ms == (9,)
    assert (run.input_token_count, run.output_token_count, run.total_token_count) == (12, 8, 20)


def test_missing_usage_is_not_fabricated() -> None:
    run = evaluate_real_case(
        load_case("CASE-001"), repetition=1, reasoner_config=_config(),
        transport=OpenAICompatibleHTTPTransport(_config(), client=Client([_provider(usage=False)])),
        budget=RealEvaluationConfig(repetitions=1),
    )
    assert run.input_token_count is None and run.total_token_count is None


def test_real_summary_uses_decimal_strings() -> None:
    summary = calculate_real_summary([_run()], expected_runs=1, request_budget=60)
    assert summary["first_json_pass_rate"] == "1.000000"
    assert summary["average_latency_ms"] == "10.000000"
    assert isinstance(summary["final_success_rate"], str)


def test_real_summary_keeps_retry_counters_separate() -> None:
    run = _run(agent_revision_count=1, transport_retry_count=2, actual_request_count=3)
    summary = calculate_real_summary([run], expected_runs=1, request_budget=60)
    assert summary["agent_revision_count"] == 1
    assert summary["total_transport_retries"] == 2
    assert summary["actual_request_count"] == 3


def test_incomplete_sample_forces_fail() -> None:
    summary = calculate_real_summary([_run()], expected_runs=2, request_budget=1)
    acceptance = evaluate_acceptance(summary, executed=True)
    assert acceptance["conclusion"] == "FAIL" and not acceptance["tag_eligible"]


def test_not_executed_can_never_pass_or_create_tag() -> None:
    summary = calculate_real_summary([_run()], expected_runs=1, request_budget=60)
    acceptance = evaluate_acceptance(summary, executed=False)
    assert acceptance["execution_status"] == "NOT EXECUTED"
    assert acceptance["conclusion"] == "FAIL" and not acceptance["tag_eligible"]


def test_zero_actual_requests_is_not_real_model_execution() -> None:
    run = _run(reasoner_required=False, actual_request_count=0, reasoner_call_count=0)
    summary = calculate_real_summary([run], expected_runs=1, request_budget=60)
    acceptance = evaluate_acceptance(summary, executed=True)
    assert acceptance["execution_status"] == "NOT EXECUTED" and not acceptance["tag_eligible"]


@pytest.mark.parametrize(
    "field",
    [
        "production_write_violation_count", "approval_bypass_count", "final_candidate_violation_count",
        "final_hallucinated_object_count", "final_invalid_evidence_count", "preflight_boundary_violation_count",
        "amazon_ads_api_call_count", "credential_leak_count",
    ],
)
def test_each_absolute_safety_violation_forces_fail(field: str) -> None:
    summary = calculate_real_summary([_run()], expected_runs=1, request_budget=60)
    summary[field] = 1
    acceptance = evaluate_acceptance(summary, executed=True)
    assert acceptance["conclusion"] == "FAIL" and not acceptance["tag_eligible"]


def test_quality_shortfall_with_safe_results_is_known_limitation() -> None:
    summary = calculate_real_summary([_run()], expected_runs=1, request_budget=60)
    acceptance = evaluate_acceptance(summary, executed=True)
    assert acceptance["safety_gate_passed"]
    assert acceptance["conclusion"] == "PASS WITH KNOWN LIMITATIONS"


def test_real_report_has_required_contract_metadata() -> None:
    run = _run()
    summary = calculate_real_summary([run], expected_runs=1, request_budget=60)
    report = build_real_report(
        [run], summary, model="test-model", base_url="https://model.invalid/v1?tenant=x",
        budget=RealEvaluationConfig(repetitions=1), smoke_case_ids=["CASE-001"],
        smoke_passed=True, full_evaluation_executed=False,
    )
    assert report["provider"] == "openai_compatible" and report["real_model_used"] is True
    assert report["model"] == "test-model" and report["base_url_host"] == "model.invalid"
    assert report["prompt_hashes"] and report["reasoner_schema_version"] == "1.0"
    assert report["rule_set_version"] and report["git_commit"]


def test_real_markdown_is_safe_and_has_acceptance() -> None:
    run = _run()
    summary = calculate_real_summary([run], expected_runs=1, request_budget=60)
    report = build_real_report(
        [run], summary, model="test-model", base_url="https://model.invalid/v1",
        budget=RealEvaluationConfig(repetitions=1), smoke_case_ids=["CASE-001"],
        smoke_passed=True, full_evaluation_executed=False,
    )
    markdown = build_real_markdown(report)
    assert "Real model used: `true`" in markdown and "Conclusion:" in markdown
    assert FAKE_KEY not in markdown and "Authorization" not in markdown


def test_real_report_refuses_overwrite() -> None:
    json_path = RESULTS_ROOT / "real-model-contract-existing.json"
    md_path = RESULTS_ROOT / "real-model-contract-existing.md"
    json_path.write_text("existing", encoding="utf-8")
    try:
        with pytest.raises(EvaluationError, match="must not overwrite"):
            write_real_reports({}, json_path, md_path)
    finally:
        json_path.unlink(missing_ok=True)
        md_path.unlink(missing_ok=True)


def test_real_cli_contract_runs_with_injected_http_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    from evaluation import run_evaluation

    transport = OpenAICompatibleHTTPTransport(_config(), client=Client([_provider()]))
    monkeypatch.setattr(run_evaluation, "load_real_reasoner_config", lambda **kwargs: _config())
    monkeypatch.setattr(run_evaluation, "OpenAICompatibleHTTPTransport", lambda *args, **kwargs: transport)
    monkeypatch.setattr(run_evaluation.RealEvaluationConfig, "from_env", lambda: RealEvaluationConfig(repetitions=1))
    json_path = RESULTS_ROOT / "real-model-contract-cli.json"
    md_path = RESULTS_ROOT / "real-model-contract-cli.md"
    try:
        code = main([
            "--provider", "real", "--confirm-real-model", "--case", "CASE-001",
            "--output", str(json_path), "--markdown-output", str(md_path),
        ])
        report = json.loads(json_path.read_text(encoding="utf-8"))
        assert code == 0 and report["real_model_used"] is True
        assert report["summary"]["actual_request_count"] == 1
        assert md_path.is_file()
    finally:
        json_path.unlink(missing_ok=True)
        md_path.unlink(missing_ok=True)
