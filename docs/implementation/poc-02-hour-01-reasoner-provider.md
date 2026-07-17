# PoC-02 第一小时：Reasoner Provider 抽象与安全配置

## 1. 本小时目标

本小时在不改变 PoC-01 安全边界的前提下，为现有 Reasoner Stub 增加统一 Provider 抽象。系统可显式选择离线 Stub 或 LLM 工程骨架，并能区分配置错误、传输错误、超时、响应错误和重试耗尽。默认路径仍为 Stub，所有验收测试均离线执行。

## 2. 当前范围

实现范围包括不可变 `ReasonerInput`、只表达选择与解释的 `ReasonerResult`、统一 `Reasoner.reason()` 接口、Stub 兼容迁移、Provider Factory、Transport 协议、可编程 Fake Transport、环境变量配置和结构化错误。Workflow 继续独占状态迁移、方案版本、运行时校验、preflight 与人工介入协议。

## 3. 非本次范围

本次不编写正式提示词，不创建回答质量评估数据集，不运行真实模型质量评估，不接入真实 HTTP 模型客户端、Amazon Ads API、数据库、前端、Approval Service 或生产写入能力。Candidate Engine、规则计算和 V0.2/V0.2.1 协议边界保持不变。

## 4. Reasoner Provider 架构

`reasoners/base.py` 定义统一输入、输出和协议。Workflow 将快照、确定性指标、只读候选集、约束及上一轮 FailureAnalysis 组装为不可变输入，只调用 `reason()`。Provider 返回的结果始终是不可信建议；Post Processor 形成候选计划，Runtime Validator 再验证候选归属、对象引用、快照、版本、证据和状态。

旧的 `amazon_ads_agent.reasoner` 现在是兼容导出层。原有 `ReasonerStub.select()` 保留，旧测试注入的 `select()` 实现通过适配器进入统一接口，新 Workflow 本身不再调用旧方法。

## 5. Stub 与 LLM 职责

Stub 保留 `valid`、`invalid_once`、`always_invalid` 三种模式及原选择语义，不初始化 Transport，也不访问网络。LLMReasoner 只负责把不可变输入转换为最小 Transport 请求、调用注入的 Transport、解析测试 JSON，并返回 ReasonerResult。它不生成候选集、对象、`change_id`、`plan_digest`、审批状态或方案版本。

当前消息内容仅用于验证 Provider 和 Transport 工程接入，不代表正式模型提示词。正式提示词属于后续独立任务。

## 6. Transport 职责

Transport 只理解模型服务请求和原始响应，不理解广告业务，也不生成 ReasonerResult。请求包含模型名、服务地址、超时、占位消息和非敏感追踪元数据；响应包含请求 ID、状态码、原始 body 和 usage。Fake Transport 可编程返回响应或异常，并记录调用次数与最后请求。NotConfiguredTransport 始终 fail-closed，不进行网络操作。

## 7. 配置环境变量

配置仅从集中定义的环境变量读取：

- `LLM_PROVIDER`：`stub` 或 `llm`，默认 `stub`；
- `LLM_MODEL`：选择 LLM 时必填；
- `LLM_API_KEY`：选择 LLM 时必填，只能来自环境变量；
- `LLM_BASE_URL`：选择 LLM 时必填；
- `LLM_TIMEOUT_SECONDS`：正整数，默认 30；
- `LLM_MAX_RETRIES`：非负整数，默认 1。

LLM 配置不完整或非法时明确失败，不回退 Stub。API Key 被排除在 `repr()`、安全描述、Transport 请求、异常、日志和审计之外。版本化业务规则 YAML 继续固定为离线 Stub，不承载任何模型凭据。

## 8. 网络重试与方案修订

网络或临时服务重试在 LLMReasoner 内部完成，以 `transport_retry_count` 记录。它们属于同一次 Agent 调用，不改变 `attempt_id`、`plan_version` 或 Agent `retry_count`。只有 Provider 成功返回业务选择、Runtime Validator 判定为可修正错误时，Workflow 才执行方案修订，并增加 `agent_revision_count`、`retry_count` 与方案版本。两类计数分别进入审计，不混用。

## 9. 密钥安全

仓库、YAML、JSON、文档示例和正常测试不保存真实密钥。测试唯一允许的占位文本是明确标识的 `test-only-not-a-real-key`。审计只记录 Provider、模型、请求 ID、安全错误码和两个非敏感计数，不记录完整敏感请求头、凭据环境变量值或服务原始错误内容。

## 10. 测试方法

四个新增测试模块分别覆盖 Provider 工厂、环境配置和脱敏、Transport/LLMReasoner、PoC-01 兼容性。Fake Transport 模拟合法响应、空响应、非 JSON、字段错误、超时、临时服务错误、重试成功和重试耗尽。Workflow 集成测试验证候选外值被 Runtime Validator 拒绝、服务失败不进入 preflight、合法结果停在 `waiting_for_approval`、网络重试不改变 Agent 版本，以及五个原示例状态不变。默认和测试路径不访问真实网络。

## 11. 已知限制

当前没有真实 HTTP Transport，没有正式提示词，没有独立 Reasoner 输出 Schema，也没有真实模型回答质量结论。严格响应字段检查仅用于本小时的工程契约；候选外数值仍交给现有 Runtime Validator 和自动修订闭环。Provider 接入不会扩大业务场景或执行权限。

## 12. Definition of Done

完成标准为：统一接口和不可变输入输出可用；旧导入与 Stub 三模式兼容；Provider Factory 不静默回退；LLM 配置和服务错误结构化；Fake Transport 可完全离线测试；密钥不进入仓库或可观察输出；网络重试与 Agent 修订严格隔离；五个原示例、ManualInterventionPackage 和 PoC-01 全量测试保持通过；`production_write_called=false`；不存在 Amazon Ads API 或真实模型网络调用。

本阶段只完成真实模型 Provider 的工程接入能力，不代表正式提示词完成，也不代表真实模型回答质量已经通过。
