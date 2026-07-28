REQUIRED_OUTPUT_KEYS = {
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


class StructuredAgent:
    code = ""

    def __init__(self, provider):
        self.provider = provider

    def run(self, payload):
        output = self.provider.generate(agent_code=self.code, payload=payload)
        missing = REQUIRED_OUTPUT_KEYS.difference(output)
        if missing or output.get("schemaVersion") != "1.0":
            raise ValueError(f"Invalid agent output schema: {sorted(missing)}")
        if output["agentCode"] != self.code or output["runId"] != payload["runId"]:
            raise ValueError("Agent output scope identity mismatch")
        return output


class DataAnalysisAgent(StructuredAgent):
    code = "DATA_ANALYSIS"


class AnomalyDiagnosisAgent(StructuredAgent):
    code = "ANOMALY_DIAGNOSIS"


class BudgetAnalysisAgent(StructuredAgent):
    code = "BUDGET_ANALYSIS"


class StrategyAgent(StructuredAgent):
    code = "STRATEGY"

