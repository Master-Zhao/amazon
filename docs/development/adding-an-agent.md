# 添加 Agent

继承 `apps.agents.agent_definitions.StructuredAgent`，定义版本化输入/输出 schema，
由 `apps.agents.services.run_orchestrator` 从 `AnalysisTask.scope_snapshot`
传入最小范围快照。Agent 只能调用
`integrations.llm.providers.LLMProvider.generate`，不得 import Model 或访问 ORM。

确定性金额、权限、状态和异常规则必须在后端 Service 校验；LLM 输出进入
`apps.recommendations.services.validate_recommendation` 后才能持久化。测试使用
`MockLLMProvider`，覆盖 schema 错误、越 Profile 对象、旧 beforeValue、无效金额
和重试幂等。真实 Provider 仅实现保留接口，不在 V1 测试中发起网络调用。
