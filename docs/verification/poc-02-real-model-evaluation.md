# PoC-02 真实模型验收报告

## 验收元数据

| 字段 | 结果 |
|---|---|
| 验收日期 | 2026-07-17 |
| 工程基线 Git commit | `eaf35c608ff9167858e64b61f276e2f8543fee9e` |
| Python | `3.12.4` |
| Provider 协议 | `openai_compatible`（工程已实现，未实际调用） |
| 模型 | N/A，环境变量未设置 |
| Base URL host | N/A，环境变量未设置 |
| Prompt 版本 | `reasoner-prompt-v1.0` |
| reasoner-system.md SHA-256 | `39D9159CD1F7195F4B0885E09A51A25C65D5FAF568137BC885559A6F69685C36` |
| keyword-bid-optimization.md SHA-256 | `6C238BBE1FA2AC3E78D9A27CF3426F3360F4F6BDC936B0663F3CD8E5E43F5AA9` |
| revision-feedback.md SHA-256 | `207B2F837C8E87E436AF7799BEABCAFCB5D3B9962A97BCCE7C01AB8BBB53E753` |
| Reasoner Schema | `1.0` |
| 规则版本 | `poc-rules-v0.1` |
| 环境变量完整 | 否 |
| API Key 脱敏 | 工程与 Mock 测试通过；未读取真实值 |

## 执行结果

| 项目 | 结果 |
|---|---|
| HTTP Mock 测试 | 通过 |
| Fake 评测 | 12/12 通过，`real_model_used=false` |
| 真实冒烟测试 | NOT EXECUTED |
| 完整真实评测案例数 | 0 |
| 重复次数 | 0（配置默认值为 3，但未执行） |
| 实际真实请求数 | 0 |
| 请求预算 | 默认 60，未消耗 |
| 首次 JSON 通过率 | N/A，不伪造 |
| 首次 Schema 通过率 | N/A，不伪造 |
| 首次业务校验通过率 | N/A，不伪造 |
| 最终成功率 | N/A，不伪造 |
| 修订成功率 | N/A，不伪造 |
| 候选违规 | N/A；Mock 安全测试通过 |
| 虚构对象 | N/A；Mock 安全测试通过 |
| 错误证据 | N/A；Mock 安全测试通过 |
| 审批绕过 | 0（工程/Mock 门槛） |
| 人工介入 | N/A |
| 平均延迟 | N/A，不伪造 |
| Token usage | N/A，不伪造 |
| Transport 重试 | 0 次真实；Mock 分类与隔离测试通过 |
| Agent 修订 | 0 次真实；受控 CASE-011 Mock 修订测试通过 |
| Production 写入违规 | 0 |
| Amazon Ads API 调用 | 0 |

## 三个冒烟案例

- CASE-001：NOT EXECUTED；没有真实模型凭据。
- CASE-006：NOT EXECUTED；没有真实模型凭据。
- CASE-011：NOT EXECUTED；受控故障注入合同仅通过 Mock 测试。

## 已知限制

当前会话没有设置 `LLM_PROVIDER`、`LLM_REAL_CALL_ENABLED`、`LLM_MODEL`、`LLM_API_KEY` 或 `LLM_BASE_URL`。因此没有创建真实 Transport，没有访问公网，没有产生费用，也没有真实模型输出、延迟或 usage 证据。

## 最终结论

- 运行状态：`NOT EXECUTED`
- 正式结论：`FAIL`
- `poc-02-verified`：未创建

真实模型质量评估未执行。

工程接入完成不代表真实模型回答质量通过。

未创建 `poc-02-verified` 标签。

