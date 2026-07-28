from decimal import Decimal

import pytest

from apps.agents.models import AgentCode
from apps.agents.orchestrator import (
    AgentResultValidationError,
    AnalysisOrchestrator,
    validate_agent_result,
)
from apps.analytics.calculations import calculate_metrics
from apps.analytics.services import metric_formulas
from integrations.llm.providers import MockLLMProvider


def test_deterministic_formulas_and_zero_denominator_reasons():
    calculated = calculate_metrics(
        impressions=100,
        clicks=10,
        spend="20.00",
        orders=2,
        sales="80.00",
    )
    empty = calculate_metrics(
        impressions=0,
        clicks=0,
        spend="0",
        orders=0,
        sales="0",
    )

    assert calculated["ctr"] == Decimal("0.1")
    assert calculated["cpc"] == Decimal("2")
    assert calculated["cvr"] == Decimal("0.2")
    assert calculated["acos"] == Decimal("0.25")
    assert calculated["roas"] == Decimal("4")
    assert empty["ctr"] is None
    assert empty["acos"] is None
    assert empty["roas"] is None
    assert empty["invalid_reasons"] == {
        "ctr": "NO_IMPRESSIONS",
        "cpc": "NO_CLICKS",
        "cvr": "NO_CLICKS",
        "acos": "NO_SALES",
        "roas": "NO_SPEND",
    }


def test_selector_formula_contract_returns_value_or_explicit_reason():
    formulas = metric_formulas(
        impressions=0,
        clicks=0,
        spend="0",
        orders=0,
        sales="0",
    )

    assert formulas["ctr"] == {"value": None, "reason": "NO_IMPRESSIONS"}
    assert formulas["cpc"] == {"value": None, "reason": "NO_CLICKS"}
    assert formulas["acos"] == {"value": None, "reason": "NO_SALES"}
    assert formulas["roas"] == {"value": None, "reason": "NO_SPEND"}


def test_mock_orchestrator_runs_all_four_agents_with_one_versioned_schema():
    context = {
        "campaigns": [
            {
                "campaignId": "1",
                "metricId": "11",
                "sourceBatchId": "21",
                "dailyBudget": "50.00",
                "currency": "USD",
                "anomalies": [
                    {
                        "ruleCode": "HIGH_ACOS",
                        "ruleVersion": 1,
                        "status": "ANOMALY",
                        "observedValue": "0.40",
                        "thresholdValue": "0.25",
                        "riskLevel": "MEDIUM",
                    }
                ],
            }
        ]
    }

    results = AnalysisOrchestrator(MockLLMProvider()).run(
        run_id="run-1",
        authorized_context=context,
    )

    assert [item["agentCode"] for item in results] == list(AgentCode.values)
    assert all(item["schemaVersion"] == "agent-result-v1" for item in results)
    assert all(item["runId"] == "run-1" for item in results)
    assert results[-1]["recommendations"][0]["actionType"] == (
        "UPDATE_CAMPAIGN_BUDGET"
    )
    assert results[-1]["recommendations"][0]["afterValue"] == {
        "dailyBudget": "45.00",
        "currency": "USD",
    }


def test_agent_schema_validation_rejects_missing_or_wrong_version():
    with pytest.raises(AgentResultValidationError, match="missing keys"):
        validate_agent_result({"schemaVersion": "agent-result-v1"})

    invalid = MockLLMProvider().generate(
        agent_code=AgentCode.DATA_ANALYSIS,
        run_id="run-invalid",
        context={},
    )
    invalid["schemaVersion"] = "unexpected"
    with pytest.raises(AgentResultValidationError, match="schemaVersion"):
        validate_agent_result(invalid)
