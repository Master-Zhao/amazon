# PoC-02 第二小时：正式提示词与结构化输出合同

## 1. 本小时目标

本小时把第一小时的 Provider 工程骨架推进到可严格验证的提示词合同：建立正式 System Prompt、单 Keyword 竞价场景 Prompt、修订反馈 Prompt、独立 Reasoner Output Schema、受限 Prompt Loader、稳定 Prompt Builder 和严格纯 JSON 解析。所有模型输出仍是不可信建议，不能绕过现有确定性安全边界。

## 2. 已完成范围

实现覆盖三个仓库内提示词、Draft 2020-12 输出 Schema、Prompt 文件白名单加载、稳定 JSON 数据封装、模型响应严格解析、Schema 自校验与输出校验、ReasonerResult 转换、模型置信度隔离、previous_failure 安全投影，以及相应审计和离线测试。Stub、Provider Factory、Transport、Workflow、Runtime Validator 和 ManualInterventionPackage 保持原有职责。

## 3. 非本次范围

本次没有真实 HTTP Transport、真实模型调用、模型评估数据集、回答质量统计、Amazon Ads API、Approval Service、数据库、前端或生产写入。没有新增广告优化场景，也没有修改 Candidate Engine 或 `docs/spec/`。第三小时和第四小时内容尚未开始。

## 4. Prompt 文件结构

正式模板固定在 `prompts/`：`reasoner-system.md` 定义全局角色和安全边界；`keyword-bid-optimization.md` 定义单 Keyword 场景和输入结构；`revision-feedback.md` 定义确定性校验失败后的修订规则。调用方只能通过文件名白名单加载这三个模板，不能传入绝对路径或执行目录穿越。

## 5. System Prompt 职责

System Prompt 将模型限定为候选选择器和解释器。它可阅读结构化任务、指标、确定性计算、候选与约束，只能选择一个候选字符串，生成理由、证据路径、风险摘要和模型置信度。它明确禁止创建竞价、修改规则、对象、快照或版本，禁止 API、审批和执行行为，并要求只输出一个纯 JSON object。

## 6. 场景 Prompt 职责

场景 Prompt 描述任务上下文、对象引用、原始指标、派生指标、合法候选和只读约束。Prompt Builder 不把 keyword 等自然语言直接拼接为指令，而是把完整输入稳定序列化到标记清晰的 JSON 数据块中。`selected_value` 必须与 `candidate_values` 的某个字符串完全一致，不允许重新计算、取整、改变精度或增加单位。

## 7. Revision Prompt 职责

只有 `previous_failure` 非空时才增加第三条 user message。反馈被投影为 `error_code`、`error_fingerprint`、`safe_message` 和 `failed_rule_ids`，不会携带堆栈、请求头、密钥、内部路径或原始响应。修订 Prompt 只允许修正失败字段，不允许降低 Validator 标准、改变候选、对象、目标、快照、版本、规则或任务范围。

## 8. Reasoner Output Schema

`schemas/reasoner-output.schema.json` 使用 JSON Schema Draft 2020-12，版本为 1.0，根节点必须是 object，且 `additionalProperties=false`。必填字段为 `schema_version`、`decision`、`selected_value`、`reason`、`evidence_paths`、`risk_summary` 和 `confidence`。Decimal 字段必须是字符串；confidence 仅允许 0 到 1。审批、执行、对象、规则、候选、快照和计划字段都会作为未知字段被拒绝。

## 9. JSON 严格解析规则

LLMReasoner 只接受一个纯 JSON object，允许正文首尾 JSON 空白，但不做任何宽容提取或修复。Markdown fence、解释性前缀或后缀、多个 JSON、重复键、非标准 NaN/Infinity、数组根、缺失字段、额外字段和 JSON number 形式的 Decimal 都会失败。解析器不会从代码块提取 JSON，不会删除未知字段，也不会把 number 转为字符串。

## 10. Schema 与 Runtime Validator 的职责边界

Schema 负责结构、类型、必填字段、长度、格式和未知字段；Schema 通过只证明输出符合 Reasoner 合同。Runtime Validator 继续校验 selected_value 是否属于确定性候选集、证据路径和值是否来自任务或确定性指标、对象引用和快照是否一致、规则是否满足、状态是否合法。业务失败仍进入原 Failure Analyzer 闭环。

## 11. previous_failure 流程

首次 ReasonerInput 的 previous_failure 为空，因此只有 system 和场景 user message。若 Runtime Validator 返回可修正错误，Workflow 增加 Agent 方案版本和 attempt_id，并把 FailureAnalysis 作为下一轮 ReasonerInput 的 previous_failure。Prompt Builder 仅提取安全字段，增加 revision message；它本身不改变版本、候选或对象。修订成功后仍停在 `waiting_for_approval`，同错连续两次仍进入人工介入。

## 12. Prompt Injection 防护

System Prompt 明确自然语言数据字段不具有系统权限。Prompt Builder 使用 `json.dumps(..., ensure_ascii=False, sort_keys=True, separators=(",", ":"))` 序列化数据，不使用 eval、代码模板或未转义字符串拼接。恶意 keyword 只存在于 user message 的 JSON 字符串字段，不会进入 system message、增加 message、改变 role 或创建新指令层级。

## 13. 人工审批边界

ReasonerResult 不是可执行计划；Schema 通过也不是批准。结果必须继续经过 Runtime Validator 和本地 dry-run preflight。合法变更固定要求人工审批，当前 PoC 没有 Approval Service、Amazon Ads API 或生产 Adapter，`production_write_called` 始终为 false。模型不得生成审批 ID、执行状态或已执行声明。

## 14. 测试方法

第二小时新增四个测试模块，覆盖 Schema 正反例、Prompt Loader/Builder、静态 Prompt 安全规则、恶意 keyword 隔离、纯 JSON 严格解析、模型置信度隔离、候选越界、证据路径错误、previous_failure 修订、同错停止、审计脱敏和 Fake Transport 网络隔离。第一小时与 PoC-01 测试继续全量运行，五个 Stub 示例单独复验。

## 15. 已知限制

Schema 1.0 只支持当前 `decision=select` 的单 Keyword 场景。模型 confidence 只保留为 ReasonerResult 解释元数据，不能覆盖系统确定性 confidence。当前没有真实模型兼容性或回答质量证据；Fake Transport 仅验证工程合同。Prompt 内容和 Schema 后续变更必须独立评审并配套测试。

## 16. Definition of Done

完成条件包括：三个 Prompt 和独立 Schema 存在并可安全加载；占位消息被移除；LLMReasoner 只接受严格纯 JSON；Schema 在 Runtime Validator 前执行；模型不能扩大候选或权限；previous_failure 安全进入第二轮；合法修订可通过，同错仍按原规则停止；ManualInterventionPackage 不变；全部测试、五个 Stub 示例、Fake LLM 场景和安全扫描通过；无真实网络、Amazon Ads API 或生产写入；未开始评估数据集。

本阶段完成的是正式提示词和结构化输出合同，不代表真实模型回答质量已经通过。所有测试仍使用 Fake Transport，不访问真实模型服务。
