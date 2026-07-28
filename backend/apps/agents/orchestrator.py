from apps.agents.models import AgentCode


REQUIRED_RESULT_KEYS = {
    "schemaVersion",
    "agentCode",
    "runId",
    "status",
    "summary",
    "evidence",
    "recommendations",
    "warnings",
    "errors",
}

REQUIRED_RECOMMENDATION_KEYS = {
    "actionType",
    "objectType",
    "objectId",
    "beforeValue",
    "afterValue",
    "reason",
    "evidence",
    "riskLevel",
}


class AgentResultValidationError(ValueError):
    pass


def validate_agent_result(result: dict[str, object]) -> None:
    missing = REQUIRED_RESULT_KEYS - result.keys()
    if missing:
        raise AgentResultValidationError(
            f"Agent result missing keys: {', '.join(sorted(missing))}"
        )
    if result["schemaVersion"] != "agent-result-v1":
        raise AgentResultValidationError("Unsupported agent result schemaVersion")
    if result["status"] != "SUCCEEDED":
        raise AgentResultValidationError("Agent result status must be SUCCEEDED")
    recommendations = result["recommendations"]
    if not isinstance(recommendations, list):
        raise AgentResultValidationError("recommendations must be a list")
    for recommendation in recommendations:
        if not isinstance(recommendation, dict):
            raise AgentResultValidationError("recommendation must be an object")
        recommendation_missing = REQUIRED_RECOMMENDATION_KEYS - recommendation.keys()
        if recommendation_missing:
            raise AgentResultValidationError(
                "Recommendation missing keys: "
                + ", ".join(sorted(recommendation_missing))
            )


class AnalysisOrchestrator:
    def __init__(self, provider):
        self.provider = provider

    def run(
        self,
        *,
        run_id: str,
        authorized_context: dict[str, object],
    ) -> list[dict[str, object]]:
        results: list[dict[str, object]] = []
        accumulated_context = dict(authorized_context)
        for agent_code in (
            AgentCode.DATA_ANALYSIS,
            AgentCode.ANOMALY_DIAGNOSIS,
            AgentCode.BUDGET_ANALYSIS,
            AgentCode.COMPOSITE_STRATEGY,
        ):
            result = self.provider.generate(
                agent_code=agent_code,
                run_id=run_id,
                context=accumulated_context,
            )
            validate_agent_result(result)
            results.append(result)
            accumulated_context["priorAgentSummaries"] = [
                item["summary"] for item in results
            ]
        return results
