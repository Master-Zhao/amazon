from dataclasses import dataclass
from typing import Protocol


class LLMProvider(Protocol):
    def generate(self, *, agent_code: str, payload: dict) -> dict: ...


@dataclass(slots=True)
class MockLLMProvider:
    def generate(self, *, agent_code: str, payload: dict) -> dict:
        run_id = payload["runId"]
        recommendation = []
        campaigns = payload.get("campaigns", [])
        if campaigns:
            campaign = campaigns[0]
            budget = campaign.get("budgetSnapshot")
            next_budget = (
                str(round(float(budget) * 1.1, 2)) if budget is not None else None
            )
            recommendation = [
                {
                    "actionType": "UPDATE_CAMPAIGN_BUDGET",
                    "objectType": "CAMPAIGN",
                    "objectId": campaign["campaignId"],
                    "beforeValue": {"budget": campaign.get("budgetSnapshot")},
                    "afterValue": {"budget": next_budget},
                    "reason": "Mock 仅基于确定性指标生成可重复解释",
                    "evidence": [{"metric": "acos", "value": campaign.get("acos")}],
                    "riskLevel": "LOW",
                }
            ]
        return {
            "schemaVersion": "1.0",
            "agentCode": agent_code,
            "runId": run_id,
            "status": "SUCCEEDED",
            "summary": f"{agent_code} 已完成",
            "evidence": payload.get("evidence", []),
            "recommendations": recommendation if agent_code == "STRATEGY" else [],
            "warnings": [],
            "errors": [],
        }


class ExternalLLMProviderBoundary:
    capability = {"available": False, "mode": "reserved", "code": "EXTERNAL_LLM"}
