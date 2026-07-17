# PoC-02 第四小时：真实模型 Transport 与评测收口

## 1. 本小时目标

在不改变确定性计算、Candidate Engine、Runtime Validator、有限修订、Preflight 和人工审批边界的前提下，加入一个显式启用的 OpenAI-compatible HTTP 协议，并使第三小时固定案例具备真实模型评测能力。

## 2. 已完成范围

已实现标准库 HTTP 客户端、OpenAI-compatible Transport、响应适配器、双重 opt-in、请求预算、状态码与超时分类、Transport 重试隔离、凭据脱敏、真实评测运行模型、Decimal 指标、真实报告、验收门槛及 Mock/安全/合同测试。

## 3. 非本次范围

没有 Amazon Ads API、广告生产 Adapter、Approval Service、数据库、前端或生产写入；没有新增广告优化场景，没有修改 Candidate/Metrics Engine、业务阈值、Runtime Validator、最大 Agent 修订规则或 `docs/spec/`。

## 4. Provider 协议

外部 Workflow 仍使用 `provider=llm`，真实 HTTP Transport 在报告中明确记录为 `openai_compatible`。只实现一个协议，不按 URL 猜测 Provider，不根据错误响应切换格式。`LLM_BASE_URL` 是完整 chat-completions endpoint。

## 5. HTTP Transport

`OpenAICompatibleHTTPTransport` 实现既有 `LLMTransport`，只负责 JSON POST、超时、HTTP 状态、请求预算和原始响应交给 Adapter。请求固定包含 model、messages、`temperature=0`、`response_format={"type":"json_object"}` 和受校验的 `max_tokens`。非本机 HTTP endpoint 被拒绝，公网 endpoint 必须 HTTPS。

## 6. Response Adapter

Adapter 只接受一个 JSON object 和恰好一个 `choices[0].message.content` 字符串，提取安全 request ID 与可选 usage。空正文、非 JSON、多个 choice、缺失正文路径和非法 usage 均 fail-closed。它不剥离 Markdown、不修复正文、不执行 Reasoner Schema。

## 7. 双重显式开启

真实网络只有同时满足以下条件才可创建 Transport：

```text
LLM_PROVIDER=llm
LLM_REAL_CALL_ENABLED=true
LLM_MODEL 非空
LLM_API_KEY 非空
LLM_BASE_URL 非空
CLI --provider real --confirm-real-model
```

任一条件缺失均返回稳定配置错误，且在 Transport 创建前结束。Fake/Stub 默认路径不读取或使用真实凭据，也不创建 HTTP Transport。

## 8. 环境变量

模型配置包括 `LLM_MODEL`、`LLM_API_KEY`、`LLM_BASE_URL`、`LLM_TIMEOUT_SECONDS`、`LLM_MAX_RETRIES` 和 `LLM_MAX_OUTPUT_TOKENS`。真实评测预算包括 `REAL_EVALUATION_MAX_REQUESTS`、`REAL_EVALUATION_MAX_AGENT_REVISIONS`、`REAL_EVALUATION_MAX_TRANSPORT_RETRIES` 和 `REAL_EVALUATION_REPETITIONS`。所有整数均严格校验并设有限上限。

## 9. HTTP 状态处理

401/403 分别映射认证和权限错误且不重试；429 映射限流错误；500/502/503/504 映射服务不可用并允许有限 Transport 重试；其他 4xx 不重试；连接/读取超时映射 `ERR_LLM_TIMEOUT`。错误不包含响应正文、请求头或凭据。

## 10. 网络重试

`LLM_MAX_RETRIES` 只控制同一个 Reasoner 调用内的 Transport 重试。达到上限后结构化失败；评测总请求预算在实际 HTTP 调用前检查。测试通过注入 Client 和零等待策略，不依赖公网或真实服务。

## 11. Agent 修订与 Transport 重试

Agent 修订仍由 Runtime Validator 的业务错误触发，会改变 plan version/attempt；Transport 重试不改变 plan version、attempt ID 或 Agent retry count。真实报告分别记录 actual requests、Transport retries 和 Agent revisions。

## 12. 密钥与日志安全

API Key 只来自环境变量并从 dataclass repr 排除。Authorization Header 只在局部请求中构造，不进入日志、审计、异常或报告。统一脱敏函数覆盖 API Key、Bearer、Authorization、access/refresh token、secret 和 password。报告只记录 Base URL host，不记录路径、查询或 userinfo。

## 13. 真实调用预算

默认最大请求数 60、最大 Agent 修订 3、最大 Transport 重试 1、重复次数 3。达到总请求预算后在发出额外请求前停止并标记失败；CASE-004/005 等确定性结束案例不产生模型请求。Fake 评测不受真实预算影响。

## 14. 冒烟测试

完整评测前运行 CASE-001、CASE-006、CASE-011。CASE-011 使用仅存在于 evaluation 路径的显式 `ControlledRevisionTransport`，在首个真实响应经过 Provider Adapter 后记录并注入一次候选越界，第二轮真实调用必须读取安全 `previous_failure` 并修正。该钩子不修改 Runtime Validator，且不会进入默认 Workflow 路径。

## 15. 完整评测

冒烟全部通过后才加载全部 12 个案例并按配置重复。每次运行独立保存，失败不删除，不使用 Fake 补齐，不人工修复模型正文；全部结果继续经过 Prompt、Reasoner Schema、正式 Workflow、Runtime Validator 和 Preflight。

## 16. 报告格式

真实报告使用 `real-model-<UTC timestamp>.json/.md`，不覆盖 Fake `latest.json/.md`。报告包括 provider、model、Base URL host、Prompt 哈希、Schema/规则版本、Git commit、重复次数、预算、实际请求、延迟、usage、两类重试、逐运行安全结果和验收结论；不含完整 Prompt、Provider envelope 或凭据。

## 17. 安全门槛

生产写入、审批绕过、最终候选/对象/证据违规、Preflight 边界违规、Amazon Ads API 调用和凭据泄漏必须全部为 0。任一不为 0，结论强制 FAIL 且禁止标签。

## 18. 质量门槛

最终 JSON/Schema/业务通过率要求 100%；首次 JSON/Schema 至少 0.900000，首次业务至少 0.800000，最终成功至少 0.950000，修订成功至少 0.800000，人工介入率不高于 0.100000。比例使用 Decimal 字符串；安全通过但质量不足可为 `PASS WITH KNOWN LIMITATIONS`。

## 19. 标签条件

只有真实模型实际运行、样本完整、安全门槛全部通过且结论为 PASS 或 PASS WITH KNOWN LIMITATIONS 时，才允许创建 `poc-02-verified`。未执行、样本不完整或 FAIL 均禁止创建或覆盖标签。

## 20. 已知限制

本次只支持一个 chat-completions 响应路径；没有流式响应、工具调用、多模型路由或真实成本计算。当前本机未提供真实模型环境配置，因此实际模型质量、真实延迟和 Token usage 尚未测量。

## 21. Definition of Done

工程完成要求包括：双重 opt-in、HTTP/Adapter、Mock 状态与超时、预算、脱敏、默认网络隔离、四组新增测试、Fake 12/12 回归、真实 CLI/报告/门槛、文档和干净提交。真实配置缺失时工程可提交，但验收状态必须 `NOT EXECUTED`、结论必须 `FAIL`，且不得创建标签。

> 真实模型仅承担候选选择、理由、证据引用和风险摘要职责。Candidate Engine、Runtime Validator、Preflight、人工介入和人工审批边界不因真实模型接入而改变。

