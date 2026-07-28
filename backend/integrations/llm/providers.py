from decimal import Decimal
from typing import Protocol

from django.conf import settings


class LLMProvider(Protocol):
    provider_code: str

    def generate(
        self,
        *,
        agent_code: str,
        run_id: str,
        context: dict[str, object],
    ) -> dict[str, object]: ...


class MockLLMProvider:
    provider_code = "mock-v1"

    def generate(
        self,
        *,
        agent_code: str,
        run_id: str,
        context: dict[str, object],
    ) -> dict[str, object]:
        recommendations: list[dict[str, object]] = []
        evidence: list[dict[str, object]] = []
        campaigns = context.get("campaigns", [])
        if agent_code in {"BUDGET_ANALYSIS", "COMPOSITE_STRATEGY"}:
            for campaign in campaigns if isinstance(campaigns, list) else []:
                if not isinstance(campaign, dict):
                    continue
                anomalies = campaign.get("anomalies", [])
                high_acos = next(
                    (
                        item
                        for item in anomalies
                        if isinstance(item, dict)
                        and item.get("ruleCode") == "HIGH_ACOS"
                        and item.get("status") == "ANOMALY"
                    ),
                    None,
                )
                budget = campaign.get("dailyBudget")
                if high_acos is None or budget is None:
                    continue
                before = Decimal(str(budget))
                after = max(Decimal("1.00"), (before * Decimal("0.90")).quantize(Decimal("0.01")))
                item_evidence = {
                    "metricId": campaign["metricId"],
                    "ruleCode": "HIGH_ACOS",
                    "ruleVersion": high_acos["ruleVersion"],
                    "observedAcos": high_acos["observedValue"],
                    "targetAcos": high_acos["thresholdValue"],
                    "sourceBatchId": campaign["sourceBatchId"],
                }
                evidence.append(item_evidence)
                recommendations.append(
                    {
                        "actionType": "UPDATE_CAMPAIGN_BUDGET",
                        "objectType": "Campaign",
                        "objectId": str(campaign["campaignId"]),
                        "beforeValue": {
                            "dailyBudget": format(before, "f"),
                            "currency": campaign["currency"],
                        },
                        "afterValue": {
                            "dailyBudget": format(after, "f"),
                            "currency": campaign["currency"],
                        },
                        "reason": (
                            "ACOS is above the inherited target. The deterministic "
                            "demo strategy proposes a 10% budget reduction for "
                            "human review."
                        ),
                        "evidence": [item_evidence],
                        "riskLevel": high_acos.get("riskLevel") or "MEDIUM",
                    }
                )
        summary_by_agent = {
            "DATA_ANALYSIS": "Deterministic Campaign metrics were summarized.",
            "ANOMALY_DIAGNOSIS": "Versioned anomaly results were interpreted.",
            "BUDGET_ANALYSIS": "Budget adjustment candidates were generated.",
            "COMPOSITE_STRATEGY": (
                f"Generated {len(recommendations)} structured recommendation(s)."
            ),
        }
        return {
            "schemaVersion": "agent-result-v1",
            "agentCode": agent_code,
            "runId": run_id,
            "status": "SUCCEEDED",
            "summary": summary_by_agent.get(agent_code, "Analysis completed."),
            "evidence": evidence,
            "recommendations": recommendations,
            "warnings": [],
            "errors": [],
        }


def get_llm_provider() -> LLMProvider:
    provider = settings.LLM_PROVIDER
    if provider == "mock":
        return MockLLMProvider()
    raise NotImplementedError(
        "Only MockLLMProvider is enabled in V1; no real model key is required."
    )
