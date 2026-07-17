"""Credential, report, audit, and default-network isolation tests."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from amazon_ads_agent.reasoners.config import LLMReasonerConfig
from amazon_ads_agent.reasoners.errors import ReasonerTransportError
from amazon_ads_agent.reasoners.http_transport import HTTPResponse, OpenAICompatibleHTTPTransport
from amazon_ads_agent.reasoners.security import redact_sensitive, safe_base_url_host
from amazon_ads_agent.reasoners.transport import LLMTransportRequest
from amazon_ads_agent.workflow import run_workflow
from evaluation.case_loader import load_case
from evaluation.models import RealEvaluationRun
from evaluation.real_config import RealEvaluationConfig
from evaluation.real_metrics import calculate_real_summary
from evaluation.real_report import build_real_report
from evaluation.run_evaluation import main

FAKE_KEY = "test-only-not-a-real-key"


class Client:
    def __init__(self, response: HTTPResponse) -> None:
        self.response = response
        self.headers = None

    def post(self, url, headers, body, timeout_seconds):
        self.headers = headers
        return self.response


def _config() -> LLMReasonerConfig:
    return LLMReasonerConfig(
        "llm", "test-model", FAKE_KEY, "https://model.invalid/v1/chat/completions?tenant=synthetic",
        5, 0, True, 512,
    )


def _provider(status: int = 200) -> HTTPResponse:
    content = json.dumps({
        "schema_version": "1.0", "decision": "select", "selected_value": "1.08",
        "reason": "synthetic", "evidence_paths": ["calculated_metrics.acos", "task_context.target_acos"],
        "risk_summary": "approval required", "confidence": "0.800000",
    })
    return HTTPResponse(status, {}, json.dumps({"id": "request-1", "choices": [{"message": {"content": content}}]}).encode())


def _request() -> LLMTransportRequest:
    return LLMTransportRequest(
        "test-model", str(_config().base_url), 5, {"messages": []},
        {"task_id": "task", "run_id": "run", "attempt_id": "attempt-0001", "plan_version": 1},
    )


def _run() -> RealEvaluationRun:
    return RealEvaluationRun(
        "CASE-001-run-01", "CASE-001", "high_acos_balanced", 1, True, True,
        True, True, True, True, True, True, "waiting_for_approval", "1.08", 1, 1, 0, 0,
        False, (), False, False, False, False, False, False, False, (12,), None, None, None,
    )


def test_api_key_is_absent_from_transport_repr() -> None:
    assert FAKE_KEY not in repr(OpenAICompatibleHTTPTransport(_config(), client=Client(_provider())))


def test_api_key_is_absent_from_configuration_repr_and_safe_view() -> None:
    assert FAKE_KEY not in repr(_config())
    assert FAKE_KEY not in repr(_config().safe_description())


@pytest.mark.parametrize(
    "text",
    [
        "api_key=private", "API Key: private", "Authorization: Bearer private",
        "Bearer private", "access_token=private", "refresh_token:private",
        "secret=private", "password: private",
    ],
)
def test_redaction_masks_sensitive_values(text: str) -> None:
    redacted = redact_sensitive(text)
    assert "private" not in redacted and "[REDACTED]" in redacted


def test_safe_url_metadata_excludes_path_query_and_userinfo() -> None:
    assert safe_base_url_host("https://user:pass@model.invalid:443/v1?secret=x") == "model.invalid:443"


@pytest.mark.parametrize("status", [401, 403])
def test_auth_errors_do_not_echo_credentials(status: int) -> None:
    with pytest.raises(ReasonerTransportError) as caught:
        OpenAICompatibleHTTPTransport(_config(), client=Client(_provider(status))).complete(
            _request()
        )
    assert FAKE_KEY not in str(caught.value)
    assert "Authorization" not in str(caught.value)


def test_auth_failure_audit_excludes_headers_and_key(high_task: dict) -> None:
    config = _config()
    result = run_workflow(
        high_task, reasoner_config=config,
        transport=OpenAICompatibleHTTPTransport(config, client=Client(_provider(401))),
    )
    rendered = json.dumps(result.audit_events)
    assert FAKE_KEY not in rendered and "Authorization" not in rendered
    assert result.output["execution_preflight"] is None


def test_transport_emits_no_sensitive_logs(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    with pytest.raises(ReasonerTransportError):
        OpenAICompatibleHTTPTransport(_config(), client=Client(_provider(401))).complete(
            _request()
        )
    assert FAKE_KEY not in caplog.text and "Authorization" not in caplog.text


def test_real_report_excludes_credentials_prompts_and_raw_responses() -> None:
    run = _run()
    summary = calculate_real_summary([run], expected_runs=1, request_budget=60)
    report = build_real_report(
        [run], summary, model="test-model", base_url="https://model.invalid/v1?secret=x",
        budget=RealEvaluationConfig(repetitions=1), smoke_case_ids=["CASE-001"],
        smoke_passed=True, full_evaluation_executed=False,
    )
    text = json.dumps(report, ensure_ascii=False)
    for forbidden in (FAKE_KEY, "Authorization", "messages", "system prompt", "raw_response", "secret=x"):
        assert forbidden not in text


def test_default_real_cli_does_not_create_transport(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.setattr(
        OpenAICompatibleHTTPTransport, "complete", lambda *args, **kwargs: pytest.fail("network attempted")
    )
    assert main(["--provider", "real"]) == 2


def test_fake_cli_does_not_create_transport(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        OpenAICompatibleHTTPTransport, "complete", lambda *args, **kwargs: pytest.fail("network attempted")
    )
    monkeypatch.setattr("evaluation.run_evaluation.write_reports", lambda *args: None)
    assert main(["--provider", "fake", "--case", "CASE-001"]) == 0


def test_case_dataset_contains_no_amazon_production_url() -> None:
    text = json.dumps(load_case("CASE-001").task_input).lower()
    assert "advertising-api.amazon" not in text


def test_real_run_safety_fields_are_zero() -> None:
    run = _run()
    assert not run.production_write_called
    assert not run.approval_bypass_detected
    assert not run.preflight_boundary_violation


def test_no_dotenv_or_key_file_is_created() -> None:
    root = Path(__file__).resolve().parents[1]
    assert not (root / ".env").exists()
    assert not (root / "api-key.txt").exists()
