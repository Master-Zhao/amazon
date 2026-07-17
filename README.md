# Amazon Ads Agent PoC

## PoC-02 第四小时：显式真实模型模式

真实模型 HTTP 模式默认关闭，只支持一个 `openai_compatible` chat-completions 协议。真实评测必须同时设置：

```text
LLM_PROVIDER=llm
LLM_REAL_CALL_ENABLED=true
LLM_MODEL=<set-in-local-environment>
LLM_API_KEY=<set-in-local-environment>
LLM_BASE_URL=<set-in-local-environment>
```

并显式运行：

```powershell
python evaluation/run_evaluation.py --provider real --confirm-real-model --case CASE-001
python evaluation/run_evaluation.py --provider real --confirm-real-model
```

真实调用可能产生费用，并受 `REAL_EVALUATION_MAX_REQUESTS` 等预算限制。真实报告使用 `evaluation/results/real-model-<UTC timestamp>.*`，不会覆盖 Fake `latest.*`。默认 pytest、Fake 评测和 Stub CLI 不访问真实网络；当前仍无 Amazon Ads API、Approval Service 或生产写入，所有合法建议仍停在人工审批前。没有真实运行时不得声称模型质量通过或创建验证标签。

## PoC-02 第三小时：确定性离线评测

离线评测框架位于 `evaluation/`，当前包含 12 个固定案例及一一对应的机器可判定 Expected。运行：

```powershell
python evaluation/run_evaluation.py
python evaluation/run_evaluation.py --case CASE-006
```

所有结果均使用 Fake Provider、ReasonerStub、Fake Transport 或预定义模拟响应，`real_model_used=false`，不需要 `LLM_API_KEY`，不访问真实模型网络或 Amazon Ads API，也没有生产写入能力。这些结果验证离线框架和固定合同，不代表真实模型回答质量。详细说明见 `evaluation/README.md` 与 `docs/implementation/poc-02-hour-03-evaluation-framework.md`。

本项目使用合成亚马逊关键词广告数据，验证一个可运行、可测试、可审计的竞价优化闭环。

> 本项目是 PoC。
> 不连接真实 Amazon Ads API。
> 不具备生产写入能力。
> 所有正式广告参数修改都必须在未来实现的审批服务中由授权人员确认。

## PoC 目标

跑通“确定性分析—候选生成—Reasoner 选择—运行期校验反馈—有限自动修订—dry-run 预检—等待人工确认”。最终合法变更必须停在 `waiting_for_approval`，`human_approval_required=true`，且 `production_write_called=false`。

## 当前支持场景

- 单个合成 Keyword。
- 高 ACoS 触发竞价降低候选。
- 数据不足直接完成。
- ACoS 未超目标时无变更完成。
- Reasoner 首次非法后修订成功。
- Reasoner 连续相同非法输出后转人工介入。

## 架构简图

```text
Synthetic JSON
  -> Draft 2020-12 Schema + cross-field validation
  -> Decimal Metrics
  -> Evidence Gate
  -> Deterministic Candidate Engine
  -> Reasoner Stub (selection/explanation only)
  -> Deterministic Post-processor
  -> Runtime Validator
      -> FailureAnalysis -> bounded revision (if correctable)
  -> local dry-run Preflight
  -> waiting_for_approval (automatic changes stop)
```

AuditCollector 在每个关键步骤追加 Schema 校验过的内存审计事件。运行期 Validator/Preflight 与开发期 pytest 完全分离。

PoC 当前规范基线由不可变的 V0.2 原文和 [V0.2.1 补丁](docs/spec/amazon-ads-agent-loop-engineering-spec-v0.2.1.md)共同组成。V0.2.1 只澄清人工介入输出和计划摘要守卫，不增加任何生产能力。

## 目录结构

```text
amazon-ads-agent-poc/
├── AGENTS.md
├── README.md
├── pyproject.toml
├── config/                # 显式版本化、不可生产使用的规则
├── docs/spec/             # 原样复制的 V0.2 主规范
├── docs/implementation/   # 本 PoC 任务与问题记录
├── schemas/               # 四个 Draft 2020-12 Schema
├── examples/              # 五个合成输入
├── src/amazon_ads_agent/  # 业务包与 CLI
└── tests/                 # 单元、闭环和安全测试
```

## 环境要求

- Python 3.11 或更高版本
- `jsonschema`
- `PyYAML`
- 测试额外使用 `pytest`

不需要数据库、浏览器、真实凭据或网络服务。

## 安装方式

建议在虚拟环境中安装：

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[test]"
```

如果当前 Python 已安装三项依赖，也可直接执行：

```bash
python -m pip install -e .
```

## 运行命令

```bash
python -m amazon_ads_agent examples/high-acos-keyword.json
python -m amazon_ads_agent examples/insufficient-evidence.json
python -m amazon_ads_agent examples/no-change-required.json
python -m amazon_ads_agent examples/invalid-reasoner-output.json --reasoner-mode invalid_once
python -m amazon_ads_agent examples/repeated-invalid-output.json --reasoner-mode always_invalid
```

安装后也可使用：

```bash
amazon-ads-agent examples/high-acos-keyword.json
```

CLI 将步骤日志写到 stderr，将包含 `agent_output` 与 `manual_intervention_package` 的结构化协议信封写到 stdout。正常路径中人工介入包为 `null`；人工介入路径中该包为独立对象。正常完成或等待审批返回 0；输入错误返回 2；人工介入返回 3；不可恢复内部错误返回 4。

## 测试命令

```bash
pytest -q
```

测试覆盖 Schema 正反例、Decimal 与指标、证据、候选、Reasoner、运行期校验、五条工作流、审计、无网络和无生产能力检查。

## 示例输出

高 ACoS 正常路径的关键字段：

```json
{
  "agent_output": {
    "current_status": "waiting_for_approval",
    "plan_version": 1,
    "changes": [
      {
        "candidate_values": ["1.02", "1.08", "1.14"],
        "suggested_value": "1.08"
      }
    ],
    "human_approval_required": true,
    "execution_preflight": {
      "mode": "dry_run",
      "production_write_called": false
    },
    "manual_intervention_package_id": null
  },
  "manual_intervention_package": null
}
```

## 自动修订

初始方案是 `attempt-0001/plan_version=1`。Runtime Validator 会把候选外值等错误交给 Failure Analyzer。可修正时创建新 `attempt_id`、递增 `plan_version` 并把结构化失败反馈给 Reasoner Stub。最多自动修订 3 次、最多 4 个方案版本；同一错误指纹连续出现 2 次立即停止。校验和预检通过后自动修改永久停止。

## 人工确认

本仓库不实现 Approval Service。`waiting_for_approval` 只表示计划已冻结并等待未来的授权审批系统处理；它不代表已批准或已执行。`manual_intervention_required` 同样不代表批准。

always-invalid 场景在同一错误连续出现两次后返回退出码 3。其 AgentOutput 为 `manual_intervention_required`、`human_approval_required=false`、`execution_preflight=null`，并通过 `manual_intervention_package_id` 引用独立的 ManualInterventionPackage。包中记录错误指纹、尝试历史、审计事件和恢复限制，且固定 `original_run_terminal=true`、`production_write_called=false`。人工介入不等于人工审批；失败方案不会进入审批或 preflight。

## 安全边界

- 只有本地 `dry_run` 预检，没有生产 Adapter。
- 不访问网络，不包含 Amazon Ads API URL。
- 不读取或记录真实令牌、认证头、密钥或密码。
- 不支持暂停、删除、归档、回滚或自动重放。
- Reasoner Stub 不能创建候选、对象、规则或执行动作。
- 金额、竞价和比例使用 `decimal.Decimal`，JSON 使用字符串。
- 配置缺失或出现生产开关时 fail-closed。
- `production_write_called` 的正常路径永远是 `false`。

## 当前限制

仅支持单 Keyword、高 ACoS 降价和合成数据；置信度是版本化 PoC 配置，不是生产评分；审计只保存在内存；没有数据库、真实模型、真实 API、正式审批、RBAC 或前端。跨字段计数关系由 Schema 加载器的确定性语义校验补齐，因为标准 JSON Schema 不支持同级数值比较。

连续非法输出的人工介入表达问题已由 V0.2.1 补丁和独立 ManualInterventionPackage 解决，记录见 `docs/implementation/poc-01-issues.md`；V0.2 原文件未被修改。

## 与主工程规范的关系

`docs/spec/amazon-ads-agent-loop-engineering-spec-v0.2.md` 是不可变主工程规范，`docs/spec/amazon-ads-agent-loop-engineering-spec-v0.2.1.md` 是当前 PoC 补丁基线。本 PoC 只落地计划生成前半闭环，重点追踪 FR-003～FR-013、NFR-003、NFR-004、NFR-007～NFR-010 和 NFR-013。实现任务只能缩小范围，不能把 PoC 简化升级为生产默认行为。

## 后续建议

未来版本应先由规范明确人工介入结果协议，再补齐持久化审计、正式 Approval Service、RBAC、平台规则与币种精度配置、只读数据适配器及沙箱 Adapter Contract。生产 Adapter 必须在审批、并发锁、幂等和审计守卫全部落地后单独评审，不应直接加入本 PoC。

## PoC-02 第一小时：Reasoner Provider 配置

默认 Provider 仍为离线 `stub`。可使用 `--reasoner-provider stub|llm` 或环境变量 `LLM_PROVIDER` 显式选择；`--reasoner-mode` 仅适用于 Stub。LLM 工程骨架读取下列环境变量，仓库和示例不保存变量值：

```text
LLM_PROVIDER
LLM_MODEL
LLM_API_KEY
LLM_BASE_URL
LLM_TIMEOUT_SECONDS
LLM_MAX_RETRIES
```

当前仓库只提供注入式 Fake Transport 与 fail-closed 的未配置 Transport，不包含真实 HTTP 客户端，也不会访问模型网络。选择 `llm` 时，模型名、API Key 和 Base URL 缺失都会明确失败，不会静默回退到 Stub。

模型服务重试由 LLMReasoner 内部计数，不增加 Agent 的 `retry_count`、`plan_version` 或 `attempt_id`。合法 Provider 结果仍必须经过 Runtime Validator 和本地 dry-run preflight，并停在 `waiting_for_approval`；`production_write_called` 保持为 `false`。

详细设计与离线测试边界见 `docs/implementation/poc-02-hour-01-reasoner-provider.md`。

本阶段只完成真实模型 Provider 的工程接入能力，不代表正式提示词完成，也不代表真实模型回答质量已经通过。

## PoC-02 第二小时：正式 Prompt 与输出合同

正式 Reasoner 模板位于 `prompts/reasoner-system.md`、`prompts/keyword-bid-optimization.md` 和 `prompts/revision-feedback.md`；独立输出合同位于 `schemas/reasoner-output.schema.json`。

LLM 输出必须是符合 Schema 1.0 的单个纯 JSON object。Markdown 代码块、JSON 前后附加文字、多个 JSON、数组根、未知字段和自动类型转换都会被拒绝。模型只能选择 `candidate_values` 中已有的 Decimal 字符串，不能创建竞价、修改对象、规则、快照、版本、审批或执行状态。

Schema 通过不代表业务合法。输出仍必须经过 Runtime Validator 和本地 dry-run preflight，并在真实修改前等待人工审批。当前没有真实模型网络、Amazon Ads API 或生产写入，也尚未进行真实模型回答质量评估。

详细说明见 `docs/implementation/poc-02-hour-02-prompt-and-output-contract.md`。
