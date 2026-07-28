from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol


class LLMProviderError(RuntimeError):
    retryable = False


class LLMProviderUnavailable(LLMProviderError):
    pass


class LLMProviderTimeout(LLMProviderError):
    retryable = True


class LLMProvider(Protocol):
    timeout_seconds: int
    max_retries: int

    def generate(self, *, agent_code: str, payload: dict) -> dict: ...


@dataclass(slots=True)
class MockLLMProvider:
    timeout_seconds = 1
    max_retries = 0

    def generate(self, *, agent_code: str, payload: dict) -> dict:
        run_id = payload["runId"]
        recommendation = []
        campaigns = payload.get("campaigns", [])
        if campaigns:
            campaign = campaigns[0]
            budget = campaign.get("budgetSnapshot")
            next_budget = (
                str((Decimal(str(budget)) * Decimal("1.10")).quantize(Decimal("0.01")))
                if budget is not None
                else None
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


class ExternalLLMProvider:
    capability = {"available": False, "mode": "reserved", "code": "EXTERNAL_LLM"}
    timeout_seconds = 30
    max_retries = 2

    def generate(self, *, agent_code: str, payload: dict) -> dict:
        raise LLMProviderUnavailable(
            "Real LLM provider is reserved and cannot be configured in V1"
        )


# Backward-compatible capability name used by existing tests and documentation.
ExternalLLMProviderBoundary = ExternalLLMProvider
RealLLMProvider = ExternalLLMProvider
