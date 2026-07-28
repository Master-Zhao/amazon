# AI Agent 设计

V1 的 AI 链路固定为 `AnalysisTask → Orchestrator → 四个结构化 Agent → Recommendation Service`。四个 Agent 分别承担数据分析、异常诊断、预算分析和策略生成；它们只能读取 Orchestrator 传入的 Tenant/Profile 冻结范围、确定性指标和证据，不访问 ORM，也不相互自由调用。

所有调用都经过 `LLMProvider`。当前唯一启用实现是无密钥、可重复的 `MockLLMProvider`；真实 Provider 只有不可用的边界声明。统一输出 Schema 版本为 `1.0`，包含运行身份、Agent 身份、状态、摘要、证据、建议、警告和错误。缺字段、版本不符或运行身份不符时立即拒绝。

LLM 不裁决权限、金额、状态、指标或动作合法性。策略输出落库前由 Recommendation Service 重新核对允许动作、对象所属 Profile、beforeValue 漂移及金额边界。模型隐藏思维过程不保存；仅保存结构化结果、证据和必要摘要。

