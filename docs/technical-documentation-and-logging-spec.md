# 亚马逊广告智能体技术文档与日志记录规范

> 版本：1.0  
> 日期：2026-07-22  
> 适用范围：amazon-ads-agent-poc v0.1.0 离线 PoC 里程碑

---

## 第一部分：技术文档

### 1 背景介绍

#### 1.1 问题域

亚马逊广告投手在关键词竞价管理中面临以下核心痛点：

- **分析成本高**：每个关键词的 ACoS、ROAS 等指标需要人工计算与判断，单次分析耗时 15~30 分钟。
- **决策不一致**：不同投手对相同数据可能给出截然不同的竞价调整建议，缺乏统一决策基线。
- **风险不可控**：人工操作可能产生越权执行、候选越界或对象幻觉等安全事件，且事后难以追溯。
- **反馈缺失**：调整后的效果缺乏结构化记录，无法形成可复用的决策知识。

#### 1.2 项目定位

本系统是面向亚马逊广告关键词竞价优化的**可审计、可校验、Human-in-the-loop** 智能体工程 PoC。核心设计目标：

1. 通过确定性模块约束大模型的自由生成行为，消除候选越界、对象幻觉、证据虚构和越权执行风险。
2. 在降低人工分析成本的同时，保持人工审批作为最终安全边界。
3. 所有决策路径可追溯、可验证、可重复。

#### 1.3 当前里程碑

v0.1.0 离线 PoC 里程碑已完成：

- 单 Keyword 高 ACoS 竞价优化离线闭环
- 565 项自动化测试全部通过
- 12 个固定评估案例全部通过
- 真实模型请求数为 0，生产写入违规数为 0

---

### 2 系统架构与算法原理

#### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Workflow Orchestrator                         │
│  ┌──────────────┐  ┌──────────────┐                                │
│  │ workflow.py   │  │ langgraph_   │  两种编排实现，共享同一组确定性模块 │
│  │ (命令式)      │  │ workflow.py  │                                │
│  │              │  │ (声明式)      │                                │
│  └──────┬───────┘  └──────┬───────┘                                │
│         │                 │                                         │
│  ┌──────▼─────────────────▼───────┐                                │
│  │        确定性模块层             │                                │
│  │  ┌──────────┐ ┌──────────────┐ │                                │
│  │  │ Metrics  │ │ Evidence     │ │  确定性计算与判断               │
│  │  │ Engine   │ │ Engine       │ │  零模型参与                    │
│  │  └──────────┘ └──────────────┘ │                                │
│  │  ┌──────────┐ ┌──────────────┐ │                                │
│  │  │Candidate │ │ Runtime      │ │  确定性约束与校验               │
│  │  │ Engine   │ │ Validator    │ │  模型不可绕过                  │
│  │  └──────────┘ └──────────────┘ │                                │
│  │  ┌──────────┐ ┌──────────────┐ │                                │
│  │  │ Failure  │ │ Post         │ │  失败处理与计划冻结             │
│  │  │ Analyzer │ │ Processor    │ │                                │
│  │  └──────────┘ └──────────────┘ │                                │
│  └────────────────────────────────┘                                │
│         │                                                           │
│  ┌──────▼──────────────────────────┐                               │
│  │        Reasoner 子系统           │                               │
│  │  ┌──────┐ ┌──────┐ ┌──────────┐ │                               │
│  │  │ Stub │ │ LLM  │ │ Fake     │ │  模型选择与解释               │
│  │  │      │ │      │ │ Transport│ │  只能在候选集合内操作          │
│  │  └──────┘ └──────┘ └──────────┘ │                               │
│  │  ┌──────────────┐ ┌───────────┐ │                               │
│  │  │ HTTP         │ │ MaaS      │ │  真实模型 Transport            │
│  │  │ Transport    │ │ Transport │ │  默认关闭，双重 opt-in         │
│  │  └──────────────┘ └───────────┘ │                               │
│  └─────────────────────────────────┘                               │
│         │                                                           │
│  ┌──────▼──────────────────────────┐                               │
│  │        安全与审计层              │                               │
│  │  ┌──────────┐ ┌──────────────┐ │                               │
│  │  │ Audit    │ │ Security     │ │  追加式审计 + 安全扫描         │
│  │  │ Collector│ │ Audit        │ │  凭据脱敏 + 边界检查           │
│  │  └──────────┘ └──────────────┘ │                               │
│  │  ┌──────────┐ ┌──────────────┐ │                               │
│  │  │ Preflight│ │ Manual       │ │  dry-run 预检 + 人工介入       │
│  │  │          │ │ Intervention │ │  零生产写入                    │
│  │  └──────────┘ └──────────────┘ │                               │
│  └─────────────────────────────────┘                               │
└─────────────────────────────────────────────────────────────────────┘
```

#### 2.2 智能体闭环算法

```
输入: TaskInput (合成关键词广告数据)
输出: WorkflowResult (AgentOutput + AuditEvents + FailureAnalyses + ManualInterventionPackage?)

算法 run_workflow(task):
  1. 加载版本化规则配置 (poc-rules-v0.1.yaml)
  2. Schema 校验 TaskInput
  3. 使用 Decimal 确定性计算 CTR/CPC/CVR/ACoS/ROAS
  4. 证据充分性判断:
     - 证据不足 → completed(insufficient_evidence)
     - 无需调整 → completed(no_change_required)
     - 需要变更 → 继续
  5. Candidate Engine 从规则生成合法候选集合
     候选 = current_bid × (1 + ratio) 对每个 candidate_change_ratios
  6. Reasoner 从候选集合中选择并解释 (最多 3 次修订循环):
     a. 构建正式 Prompt (System + Scenario + 可选 Revision Feedback)
     b. Transport 调用 (Stub/Fake/HTTP/MaaS)
     c. 严格 JSON 解析 (拒绝 Markdown/容错/重复 Key/未知字段)
     d. Reasoner Output Schema 校验
     e. Runtime Validator 五重校验:
        - Schema 合法性
        - 候选归属 (suggested_value ∈ candidate_values)
        - 对象引用一致性
        - 证据路径有效性
        - 状态转换合法性
     f. 校验通过 → dry-run Preflight → waiting_for_approval
     g. 校验失败 → Failure Analyzer:
        - 可修正 → 新 attempt_id + plan_version → 回到 6a
        - 同错 2 次或达到 3 次上限 → manual_intervention_required
  7. 返回 WorkflowResult
```

#### 2.3 确定性优先原则

| 原则 | 实现 |
|---|---|
| Decimal 优先 | 所有金额、竞价、比例使用 `decimal.Decimal`，序列化为 Decimal 字符串，零浮点 |
| 候选先于模型 | Candidate Engine 根据版本化规则确定性生成候选，Reasoner 只能选择 |
| Schema ≠ 业务合法 | Schema 校验通过后仍须经过 Runtime Validator 五重校验 |
| 有限自动修订 | 最多 3 次修订，同错连续 2 次立即停止 |
| Human-in-the-loop | 合法变更停在 `waiting_for_approval`，不自动进入生产写入 |
| 零生产写入 | `production_write_called` 始终为 `false` |

#### 2.4 LangGraph 声明式编排

项目同时维护两种编排实现：

| 维度 | `workflow.py` (命令式) | `langgraph_workflow.py` (声明式) |
|---|---|---|
| 编排方式 | `while True` 循环 + `continue` | `StateGraph` 节点 + 条件边 |
| 状态管理 | 局部变量 + 参数传递 | `AgentState(TypedDict)` |
| 路由逻辑 | `if/elif/else` | `route_after_*` 函数 |
| 终态判断 | `return` | `END` 节点 |
| 可视化 | 无 | 支持 `graph.compile().get_graph()` |

LangGraph StateGraph 节点拓扑：

```
load_config → validate_input → calculate_metrics → evaluate_evidence
                                                        │
                                    ┌───────────────────┼───────────────────┐
                                    │                                       │
                            complete_no_change → END              generate_candidates
                                                                        │
                                                              select_reasoner
                                                                        │
                                                              reasoner_call ←─────┐
                                                                    │               │
                                              ┌─────────────────────┼─────────┐     │
                                              │                     │         │     │
                                             END              validate_runtime   │
                                                                  │               │
                                              ┌─────────────────┼─────────┐     │
                                              │                 │         │     │
                                          preflight      reasoner_call     │
                                              │             (修订)          │
                                          waiting_for_approval              │
                                              │                               │
                                             END ◄───────────────────────────┘
                                          (人工介入终态)
```

#### 2.5 Reasoner 子系统架构

```
┌──────────────────────────────────────────────────┐
│                Reasoner.reason()                  │
│              (统一调用合同)                        │
├──────────────────────────────────────────────────┤
│  PromptBuilder ──→ LLMTransportRequest           │
│                         │                         │
│              ┌──────────▼──────────┐              │
│              │  Transport Router   │              │
│              ├─────┬──────┬────────┤              │
│              │Stub │ Fake │ HTTP/  │              │
│              │     │      │ MaaS   │              │
│              └─────┴──────┴────────┘              │
│                         │                         │
│              ┌──────────▼──────────┐              │
│              │  严格 JSON 解析      │              │
│              │  + Schema 校验      │              │
│              └──────────┬──────────┘              │
│                         │                         │
│              ┌──────────▼──────────┐              │
│              │  ReasonerResult     │              │
│              │  (不可信输出)        │              │
│              └─────────────────────┘              │
└──────────────────────────────────────────────────┘
```

Transport 重试与 Agent 修订的隔离：

- Transport 重试：网络层 429/5xx 的有限重试，不改变 `retry_count`、`plan_version` 或 `attempt_id`
- Agent 修订：业务层校验失败后的计划修订，更新 `plan_version` 和 `attempt_id`
- 两者独立计数，互不影响

---

### 3 详细操作步骤

#### 3.1 环境准备

```bash
# 进入 PoC 目录
cd amazon-ads-agent-poc

# 创建虚拟环境
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

# 安装依赖
pip install -e ".[test]"
```

#### 3.2 离线运行（默认 Stub Reasoner）

```bash
# 运行高 ACoS 关键词示例
python -m amazon_ads_agent examples/high-acos-keyword.json

# 运行证据不足示例
python -m amazon_ads_agent examples/insufficient-evidence.json

# 运行无需调整示例
python -m amazon_ads_agent examples/no-change-required.json

# 运行首次非法后修订示例
python -m amazon_ads_agent examples/invalid-reasoner-output.json --reasoner-mode invalid_once

# 运行连续相同错误示例
python -m amazon_ads_agent examples/repeated-invalid-output.json --reasoner-mode always_invalid
```

#### 3.3 测试执行

```bash
# 全量测试
pytest tests/ -v

# 仅 Fake LLM 集成测试
pytest tests/ -v -k "fake"

# 仅 HTTP Transport Mock 测试
pytest tests/ -v -k "http_transport"

# 仅安全审计测试
pytest tests/ -v -k "security_audit"
```

#### 3.4 评估框架运行

```bash
# 离线评估（Fake Transport，12 个固定案例）
python -m evaluation.run_evaluation

# 查看评估报告
cat evaluation/results/latest.md
```

#### 3.5 安全审计运行

```bash
# 完整安全审计
python -m amazon_ads_agent.security_audit .

# 仅安全扫描
python -m amazon_ads_agent.security_audit . --check security

# 仅边界检查
python -m amazon_ads_agent.security_audit . --check boundary
```

#### 3.6 真实模型运行（需显式启用）

```bash
# 设置环境变量
set LLM_PROVIDER=llm
set LLM_MODEL=glm-4-flash
set LLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4/chat/completions
set LLM_API_KEY=<your-key>
set LLM_REAL_CALL_ENABLED=true

# 运行（需 CLI 确认）
python -m amazon_ads_agent examples/high-acos-keyword.json --reasoner-provider llm
```

> **安全约束**：真实调用必须同时满足 `LLM_REAL_CALL_ENABLED=true` 环境变量和 CLI 显式确认。API Key 仅允许来自环境变量，不进入源码、配置、日志、审计、错误或报告。

---

### 4 适用场景分析

#### 4.1 核心适用场景

| 场景 | 描述 | 当前支持 |
|---|---|---|
| 单关键词高 ACoS 降价 | ACoS 超过目标阈值，建议降低竞价 | 完整支持 |
| 证据不足安全退出 | 点击/订单数据不足，无法做出可靠判断 | 完整支持 |
| 无需调整安全退出 | 数据充分但 ACoS 未触发调整规则 | 完整支持 |
| 首次非法后自动修订 | Reasoner 返回非法输出，系统自动修正 | 完整支持 |
| 连续错误人工介入 | 同一错误连续出现，停止自动修订 | 完整支持 |

#### 4.2 扩展场景（尚未实现）

| 场景 | 描述 | 状态 |
|---|---|---|
| Campaign 预算优化 | 广告活动级别的预算调整 | 未实现 |
| Ad Group 级别优化 | 广告组级别的竞价策略 | 未实现 |
| 多关键词批量处理 | 同时处理多个关键词 | 未实现 |
| 正式 Approval Service | 人工审批的持久化与 RBAC | 未实现 |
| Amazon Ads API 写入 | 真实广告平台写入 | 未实现 |

#### 4.3 不适用场景

- 生产环境广告投放（当前为合成数据 PoC）
- 实时竞价决策（当前为离线分析）
- 多市场/多币种场景（当前仅单一市场假设）

---

### 5 优缺点评估

#### 5.1 优势

| 优势 | 说明 |
|---|---|
| **确定性优先** | 关键数值、对象、版本、证据、规则和状态由确定性模块控制，模型无法绕过 |
| **安全边界严格** | 零生产写入、零真实模型请求（默认）、凭据脱敏、双重 opt-in |
| **可审计可追溯** | 每一步状态转换都有 Schema-valid 审计事件，含 trace_id 和 step_id |
| **可验证可重复** | 565 项测试 + 12 个固定评估案例，任何修改可立即检测回归 |
| **模型可替换** | 统一 Reasoner.reason() 合同，Stub/Fake/HTTP/MaaS 可互换 |
| **失败安全** | fail-closed 设计：校验失败→人工介入，而非静默通过 |
| **有限修订** | 最多 3 次自动修订，同错 2 次立即停止，避免无限循环 |

#### 5.2 局限

| 局限 | 说明 |
|---|---|
| **仅单关键词** | 当前只支持单个 Keyword 的竞价优化，不支持批量或层级结构 |
| **合成数据** | 所有验证基于合成数据，真实模型质量未经验证 |
| **无持久化** | 审计事件存储在内存中，进程结束即丢失 |
| **无前端** | 缺少审批页面和可视化界面 |
| **LangGraph 未接入运行时** | 声明式编排代码已实现但未作为默认运行时 |
| **无 Approval Service** | 人工审批缺乏持久化、RBAC 和通知机制 |
| **日志系统不完善** | 当前仅有内存审计事件，缺少结构化应用日志和分级日志 |

---

## 第二部分：日志记录规范与实施方案

### 6 现有审计系统分析

#### 6.1 当前实现

项目当前通过 `AuditCollector`（`src/amazon_ads_agent/audit.py`）实现了追加式内存审计事件收集：

- **格式**：Schema-valid JSON 事件（`audit-event.schema.json`，Draft 2020-12）
- **存储**：进程内 `list[dict]`，进程结束即丢失
- **输出**：CLI 通过 `stderr` 输出事件摘要行
- **安全**：自动过滤 `access_token`、`refresh_token`、`authorization_header`、`secret`、`password` 等敏感键

#### 6.2 当前审计事件字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `schema_version` | const "2.0" | Schema 版本 |
| `event_id` | string | 全局唯一事件 ID |
| `task_id` | string | 任务 ID |
| `run_id` | string | 运行 ID |
| `attempt_id` | string\|null | 尝试 ID |
| `step_id` | string | 步骤序号 |
| `trace_id` | string | 追踪 ID（task_id + run_id 的 SHA-256 前 16 位） |
| `event_type` | string | 事件类型（如 `task_loaded`、`runtime_validation_failed`） |
| `occurred_at` | RFC 3339 | 发生时间 |
| `plan_version` | integer | 计划版本 |
| `data_snapshot_id` | string | 数据快照 ID |
| `status_before` | string\|null | 状态转换前 |
| `status_after` | string | 状态转换后 |
| `summary` | string | 事件摘要 |
| `error_code` | string\|null | 错误码（`ERR_*` 格式） |
| `metadata` | object | 附加元数据（禁止敏感键） |

#### 6.3 当前不足

1. **无日志级别**：所有事件以同一优先级记录，无法区分 DEBUG/INFO/WARN/ERROR
2. **无持久化**：内存存储，进程退出后丢失
3. **无结构化应用日志**：缺少 Python `logging` 模块集成，无法输出到文件/外部系统
4. **无采样与聚合**：高频事件无采样机制，长时间运行可能产生大量事件
5. **无关联 ID 传播**：跨服务调用时无法传播 trace_id

---

### 7 日志级别划分标准

#### 7.1 四级日志体系

| 级别 | 数值 | 用途 | 产出环境 | 示例 |
|---|---|---|---|---|
| **DEBUG** | 10 | 开发调试信息，仅开发环境启用 | 开发 | 候选值列表、Prompt 模板版本、JSON 解析细节 |
| **INFO** | 20 | 正常业务流程关键节点 | 全部 | 任务加载、指标计算完成、证据判断结果、等待人工审批 |
| **WARN** | 30 | 可恢复异常或接近边界条件 | 全部 | Transport 重试、修订次数接近上限、证据天数不足但未触发终止 |
| **ERROR** | 40 | 不可恢复错误或安全违规 | 全部 | Schema 校验失败、候选越界、生产写入违规、Reasoner 服务不可用 |

#### 7.2 级别判定决策树

```
是否涉及安全违规（生产写入/凭据泄露/越权执行）？
  └─ 是 → ERROR
  └─ 否 → 是否导致流程终止且无法自动恢复？
        └─ 是 → ERROR
        └─ 否 → 是否触发自动修订或 Transport 重试？
              └─ 是 → WARN
              └─ 否 → 是否为业务流程关键节点？
                    └─ 是 → INFO
                    └─ 否 → DEBUG
```

#### 7.3 审计事件与日志级别的映射

| 审计 event_type | 建议日志级别 | 依据 |
|---|---|---|
| `task_loaded` | INFO | 正常流程起点 |
| `schema_validated` | INFO | 正常校验通过 |
| `metrics_calculated` | DEBUG | 确定性计算细节 |
| `evidence_evaluated` | INFO | 关键决策节点 |
| `candidates_generated` | DEBUG | 候选生成细节 |
| `reasoner_provider_selected` | INFO | Provider 确认 |
| `llm_request_started` | INFO | 外部调用起点 |
| `reasoner_prompt_built` | DEBUG | Prompt 构建细节 |
| `reasoner_response_received` | INFO | 外部响应到达 |
| `reasoner_response_parsed` | DEBUG | 解析细节 |
| `reasoner_schema_validation_passed` | DEBUG | Schema 通过 |
| `reasoner_schema_validation_failed` | ERROR | Schema 失败 |
| `reasoner_revision_feedback_added` | INFO | 修订反馈注入 |
| `llm_transport_retry` | WARN | Transport 重试 |
| `llm_request_succeeded` | INFO | 外部调用成功 |
| `llm_request_failed` | ERROR | 外部调用失败 |
| `reasoner_completed` | INFO | Reasoner 完成 |
| `runtime_validation_failed` | ERROR | 业务校验失败 |
| `runtime_validation_passed` | INFO | 业务校验通过 |
| `failure_analyzed` | WARN | 失败分析（可恢复）或 ERROR（不可恢复） |
| `plan_revised` | WARN | 触发自动修订 |
| `preflight_passed` | INFO | 预检通过 |
| `waiting_for_approval` | INFO | 等待人工审批 |
| `completed_without_change` | INFO | 安全退出 |
| `manual_intervention_required` | ERROR | 需要人工介入 |

---

### 8 关键业务链路日志埋点策略

#### 8.1 埋点原则

1. **入口必埋**：每个工作流入口和外部调用入口必须记录 INFO 日志
2. **出口必埋**：每个终态（completed/waiting_for_approval/manual_intervention_required）必须记录 INFO/ERROR 日志
3. **异常必埋**：所有 `except` 块必须记录 ERROR 日志
4. **重试必埋**：所有 Transport 重试和 Agent 修订必须记录 WARN 日志
5. **安全必埋**：所有安全相关事件（凭据、越权、生产写入）必须记录 ERROR 日志
6. **禁止敏感**：日志中不得出现 API Key、Authorization Header、access_token 等敏感值

#### 8.2 各模块埋点清单

##### 8.2.1 Workflow 编排层

| 埋点位置 | 级别 | 消息模板 | 关键上下文 |
|---|---|---|---|
| `run_workflow` 入口 | INFO | `workflow.started` | `task_id`, `run_id`, `rule_set_version` |
| `validate_task_input` 通过 | INFO | `workflow.input_validated` | `task_id` |
| `validate_task_input` 失败 | ERROR | `workflow.input_validation_failed` | `task_id`, `error_code` |
| `evaluate_evidence` 判断 | INFO | `workflow.evidence_decided` | `task_id`, `outcome`, `reason_codes` |
| 安全退出（insufficient/no_change） | INFO | `workflow.completed_safely` | `task_id`, `completion_reason` |
| 进入修订循环 | WARN | `workflow.revision_started` | `task_id`, `plan_version`, `retry_count` |
| 达到人工介入 | ERROR | `workflow.manual_intervention` | `task_id`, `error_code`, `retry_count` |
| 等待人工审批 | INFO | `workflow.awaiting_approval` | `task_id`, `plan_version`, `plan_digest` |
| `run_workflow` 出口 | INFO | `workflow.finished` | `task_id`, `current_status`, `duration_ms` |

##### 8.2.2 Metrics Engine

| 埋点位置 | 级别 | 消息模板 | 关键上下文 |
|---|---|---|---|
| 指标计算完成 | DEBUG | `metrics.calculated` | `task_id`, `acos`, `roas`, `ctr`, `cpc`, `cvr` |
| 指标计算异常 | ERROR | `metrics.calculation_failed` | `task_id`, `error_code` |

##### 8.2.3 Evidence Engine

| 埋点位置 | 级别 | 消息模板 | 关键上下文 |
|---|---|---|---|
| 证据判断完成 | INFO | `evidence.evaluated` | `task_id`, `outcome`, `analysis_days`, `reason_count` |
| 证据天数接近阈值 | WARN | `evidence.days_near_minimum` | `task_id`, `analysis_days`, `minimum` |

##### 8.2.4 Candidate Engine

| 埋点位置 | 级别 | 消息模板 | 关键上下文 |
|---|---|---|---|
| 候选生成完成 | DEBUG | `candidates.generated` | `task_id`, `candidate_count`, `candidate_values` |
| 当前竞价超出范围 | WARN | `candidates.bid_out_of_range` | `task_id`, `current_bid`, `min_bid`, `max_bid` |

##### 8.2.5 Reasoner 子系统

| 埋点位置 | 级别 | 消息模板 | 关键上下文 |
|---|---|---|---|
| Provider 选择 | INFO | `reasoner.provider_selected` | `task_id`, `provider`, `model` |
| Prompt 构建完成 | DEBUG | `reasoner.prompt_built` | `task_id`, `template_version`, `revision_added` |
| Transport 请求开始 | INFO | `reasoner.transport_request_started` | `task_id`, `provider`, `model`, `attempt_id` |
| Transport 重试 | WARN | `reasoner.transport_retrying` | `task_id`, `retry_count`, `max_retries`, `status_code` |
| Transport 重试耗尽 | ERROR | `reasoner.transport_retries_exhausted` | `task_id`, `total_retries` |
| 响应接收 | INFO | `reasoner.response_received` | `task_id`, `request_id`, `latency_ms` |
| JSON 解析失败 | ERROR | `reasoner.json_parse_failed` | `task_id`, `error_code` |
| Schema 校验失败 | ERROR | `reasoner.schema_validation_failed` | `task_id`, `field_path`, `error_code` |
| Reasoner 调用成功 | INFO | `reasoner.call_succeeded` | `task_id`, `provider`, `model`, `request_id` |
| Reasoner 调用失败 | ERROR | `reasoner.call_failed` | `task_id`, `error_code`, `provider` |

##### 8.2.6 Runtime Validator

| 埋点位置 | 级别 | 消息模板 | 关键上下文 |
|---|---|---|---|
| 校验通过 | INFO | `validation.runtime_passed` | `task_id`, `plan_version` |
| 校验失败 | ERROR | `validation.runtime_failed` | `task_id`, `plan_version`, `error_code`, `failed_rule_ids` |
| 候选越界检测 | ERROR | `validation.candidate_out_of_range` | `task_id`, `suggested_value`, `candidate_values` |
| 对象引用不一致 | ERROR | `validation.object_reference_invalid` | `task_id`, `expected`, `actual` |

##### 8.2.7 Failure Analyzer

| 埋点位置 | 级别 | 消息模板 | 关键上下文 |
|---|---|---|---|
| 失败分析完成 | WARN | `failure.analyzed` | `task_id`, `error_code`, `fingerprint`, `next_action` |
| 同错连续计数 | WARN | `failure.consecutive_same_error` | `task_id`, `consecutive_count`, `limit` |
| 修订次数接近上限 | WARN | `failure.revisions_near_limit` | `task_id`, `retry_count`, `max_revisions` |

##### 8.2.8 Preflight

| 埋点位置 | 级别 | 消息模板 | 关键上下文 |
|---|---|---|---|
| Preflight 通过 | INFO | `preflight.passed` | `task_id`, `production_write_called=false` |
| 生产写入违规 | ERROR | `preflight.production_write_violation` | `task_id` |

##### 8.2.9 安全审计

| 埋点位置 | 级别 | 消息模板 | 关键上下文 |
|---|---|---|---|
| 安全扫描发现 | ERROR | `security.finding` | `rule_id`, `severity`, `description` |
| 边界违规 | ERROR | `security.boundary_violation` | `rule_id`, `boundary_type` |
| 凭据检测 | ERROR | `security.credential_detected` | `location`, `key_type` |

---

### 9 日志输出格式规范

#### 9.1 结构化日志格式

所有日志输出采用 JSON Lines 格式（每行一个 JSON 对象），便于机器解析和日志平台采集：

```json
{
  "timestamp": "2026-07-22T10:30:45.123456+00:00",
  "level": "INFO",
  "logger": "amazon_ads_agent.workflow",
  "message": "workflow.awaiting_approval",
  "trace_id": "trace-a1b2c3d4e5f67890",
  "span_id": "step-0012",
  "task_id": "task-001",
  "run_id": "run-001",
  "attempt_id": "attempt-0001",
  "plan_version": 1,
  "context": {
    "plan_digest": "sha256:abc123...",
    "production_write_called": false
  },
  "error_code": null,
  "duration_ms": null
}
```

#### 9.2 字段规范

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `timestamp` | RFC 3339 with μs | 是 | 事件发生时间，UTC，含微秒和时区 |
| `level` | enum | 是 | DEBUG/INFO/WARN/ERROR |
| `logger` | string | 是 | 模块路径，如 `amazon_ads_agent.workflow` |
| `message` | string | 是 | 点分消息模板，如 `workflow.awaiting_approval` |
| `trace_id` | string | 是 | 全链路追踪 ID |
| `span_id` | string | 否 | 当前步骤 ID |
| `task_id` | string | 条件 | 业务任务 ID（工作流内必填） |
| `run_id` | string | 条件 | 运行 ID（工作流内必填） |
| `attempt_id` | string | 否 | 当前尝试 ID |
| `plan_version` | integer | 否 | 当前计划版本 |
| `context` | object | 否 | 业务上下文键值对 |
| `error_code` | string | 否 | 错误码（`ERR_*` 格式） |
| `duration_ms` | integer | 否 | 操作耗时（毫秒） |

#### 9.3 敏感字段过滤规则

以下字段**禁止**出现在任何日志输出中：

```
access_token, refresh_token, authorization_header, secret, password,
api_key, api_secret, credential, token, bearer, private_key
```

过滤实现应在日志 Formatter 层统一处理，而非依赖各调用点手动过滤：

```python
FORBIDDEN_LOG_KEYS = frozenset({
    "access_token", "refresh_token", "authorization_header",
    "secret", "password", "api_key", "api_secret",
    "credential", "token", "bearer", "private_key",
})

def sanitize_log_record(record: dict) -> dict:
    def _sanitize(obj):
        if isinstance(obj, dict):
            return {k: "[REDACTED]" if k.lower() in FORBIDDEN_LOG_KEYS else _sanitize(v)
                    for k, v in obj.items()}
        if isinstance(obj, list):
            return [_sanitize(item) for item in obj]
        return obj
    return _sanitize(record)
```

#### 9.4 CLI 输出格式

CLI 保持双通道输出：

- **stdout**：JSON 协议信封（agent_output + manual_intervention_package）
- **stderr**：人类可读的审计摘要行

```
step-0001 task_loaded -> validating_data
step-0002 schema_validated -> analyzing
step-0003 evidence_evaluated -> generating_plan [outcome=generate_candidates]
step-0004 candidates_generated -> generating_plan [candidate_count=3]
step-0005 reasoner_completed -> validating_plan [provider=stub]
step-0006 runtime_validation_passed -> preflighting
step-0007 preflight_passed -> waiting_for_approval [production_write_called=False]
step-0008 waiting_for_approval -> waiting_for_approval
```

---

### 10 日志采集与存储方案

#### 10.1 架构总览

```
┌─────────────────────────────────────────────────────────┐
│                    应用进程                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ AuditCollector│  │ Structured   │  │ CLI stderr   │  │
│  │ (业务审计)    │  │ Logger       │  │ (人类可读)   │  │
│  │              │  │ (应用日志)    │  │              │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────────┘  │
│         │                 │                              │
│  ┌──────▼─────────────────▼───────┐                     │
│  │        Log Handler Router      │                     │
│  │  ┌──────────┐ ┌──────────────┐ │                     │
│  │  │ Console  │ │ File         │ │                     │
│  │  │ Handler  │ │ Handler      │ │                     │
│  │  │ (JSON)   │ │ (JSON Lines) │ │                     │
│  │  └──────────┘ └──────────────┘ │                     │
│  └────────────────────────────────┘                     │
└─────────────────────────────────────────────────────────┘
                          │
                   文件系统日志文件
                          │
              ┌───────────▼───────────┐
              │    日志采集 Agent      │
              │  (Filebeat/Fluentd)   │
              └───────────┬───────────┘
                          │
              ┌───────────▼───────────┐
              │   日志存储与检索       │
              │  (Elasticsearch/      │
              │   Loki/ClickHouse)    │
              └───────────┬───────────┘
                          │
              ┌───────────▼───────────┐
              │   日志可视化与告警     │
              │  (Kibana/Grafana)     │
              └───────────────────────┘
```

#### 10.2 本地文件存储

##### 10.2.1 文件命名与轮转

```
logs/
├── agent.log              # 当前日志（JSON Lines）
├── agent.log.1            # 第 1 个轮转文件
├── agent.log.2            # 第 2 个轮转文件
├── audit/
│   ├── audit-2026-07-22.jsonl   # 当日审计事件归档
│   └── audit-2026-07-21.jsonl   # 前一日审计事件归档
└── evaluation/
    └── eval-2026-07-22.jsonl    # 当日评估日志
```

##### 10.2.2 轮转策略

| 参数 | 值 | 说明 |
|---|---|---|
| 单文件最大大小 | 50 MB | 超过自动轮转 |
| 保留文件数 | 10 | 最多保留 10 个轮转文件 |
| 审计归档保留 | 90 天 | 审计事件按日归档，保留 90 天 |
| 压缩 | gzip | 轮转文件自动压缩 |

#### 10.3 Python logging 配置方案

```python
import logging
import logging.config
from pathlib import Path

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

LOGGING_CONFIG: dict = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "amazon_ads_agent.logging_utils.StructuredJsonFormatter",
            "format": "%(timestamp)s %(level)s %(logger)s %(message)s",
        },
        "human": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "filters": {
        "sensitive": {
            "()": "amazon_ads_agent.logging_utils.SensitiveDataFilter",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
            "formatter": "human",
            "filters": ["sensitive"],
            "level": "INFO",
        },
        "file_json": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOG_DIR / "agent.log"),
            "maxBytes": 50 * 1024 * 1024,
            "backupCount": 10,
            "formatter": "json",
            "filters": ["sensitive"],
            "level": "DEBUG",
            "encoding": "utf-8",
        },
    },
    "loggers": {
        "amazon_ads_agent": {
            "level": "DEBUG",
            "handlers": ["console", "file_json"],
            "propagate": False,
        },
        "amazon_ads_agent.reasoners": {
            "level": "DEBUG",
            "handlers": ["console", "file_json"],
            "propagate": False,
        },
        "amazon_ads_agent.security_audit": {
            "level": "INFO",
            "handlers": ["console", "file_json"],
            "propagate": False,
        },
    },
    "root": {
        "level": "WARNING",
        "handlers": ["console"],
    },
}
```

#### 10.4 审计事件与日志的统一

审计事件（AuditCollector）和应用日志（Python logging）应保持双向一致：

1. **审计事件同步写入日志**：每次 `audit.record()` 调用时，同时通过 `logging` 输出对应级别的日志记录
2. **日志包含审计关键字段**：日志记录的 `context` 中包含 `trace_id`、`step_id`、`event_type` 等审计字段
3. **审计归档独立持久化**：审计事件在内存收集完成后，额外写入按日归档的 JSONL 文件

```python
import logging

logger = logging.getLogger(__name__)

AUDIT_LEVEL_MAP: dict[str, int] = {
    "task_loaded": logging.INFO,
    "schema_validated": logging.INFO,
    "metrics_calculated": logging.DEBUG,
    "evidence_evaluated": logging.INFO,
    "candidates_generated": logging.DEBUG,
    "reasoner_provider_selected": logging.INFO,
    "llm_request_started": logging.INFO,
    "reasoner_prompt_built": logging.DEBUG,
    "reasoner_response_received": logging.INFO,
    "reasoner_response_parsed": logging.DEBUG,
    "reasoner_schema_validation_passed": logging.DEBUG,
    "reasoner_schema_validation_failed": logging.ERROR,
    "reasoner_revision_feedback_added": logging.INFO,
    "llm_transport_retry": logging.WARNING,
    "llm_request_succeeded": logging.INFO,
    "llm_request_failed": logging.ERROR,
    "reasoner_completed": logging.INFO,
    "runtime_validation_failed": logging.ERROR,
    "runtime_validation_passed": logging.INFO,
    "failure_analyzed": logging.WARNING,
    "plan_revised": logging.WARNING,
    "preflight_passed": logging.INFO,
    "waiting_for_approval": logging.INFO,
    "completed_without_change": logging.INFO,
    "manual_intervention_required": logging.ERROR,
}


class AuditCollector:
    # ... 现有实现 ...

    def record(self, event_type: str, status_before, status_after, summary, **kwargs) -> dict:
        # ... 现有审计事件构建逻辑 ...
        event = self._build_event(event_type, status_before, status_after, summary, **kwargs)
        validate_audit_event(event)
        self._events.append(event)

        log_level = AUDIT_LEVEL_MAP.get(event_type, logging.INFO)
        logger.log(
            log_level,
            event_type,
            extra={
                "trace_id": self._trace_id,
                "step_id": event["step_id"],
                "task_id": self._task["task_id"],
                "run_id": self._task["run_id"],
                "attempt_id": self._task.get("attempt_id"),
                "plan_version": kwargs.get("plan_version", 0),
                "error_code": kwargs.get("error_code"),
                "audit_context": kwargs.get("metadata"),
            },
        )
        return dict(event)
```

#### 10.5 外部日志采集

##### 10.5.1 Filebeat 配置示例

```yaml
filebeat.inputs:
  - type: log
    enabled: true
    paths:
      - logs/agent.log*
      - logs/audit/*.jsonl
      - logs/evaluation/*.jsonl
    json.keys_under_root: true
    json.add_error_key: true
    fields:
      app: amazon-ads-agent
      env: poc
      version: "0.1.0"
    fields_under_root: true

output.elasticsearch:
  hosts: ["localhost:9200"]
  index: "amazon-ads-agent-%{+yyyy.MM.dd}"
```

##### 10.5.2 Loki 配置示例（Promtail）

```yaml
scrape_configs:
  - job_name: amazon_ads_agent
    static_configs:
      - targets:
          - localhost
        labels:
          job: amazon-ads-agent
          __path__: /var/log/amazon-ads-agent/**/*.log
    pipeline_stages:
      - json:
          expressions:
            level: level
            logger: logger
            message: message
            trace_id: trace_id
            task_id: task_id
      - labels:
          level:
          logger:
          trace_id:
      - timestamp:
          source: timestamp
          format: RFC3339Nano
```

#### 10.6 日志查询与告警

##### 10.6.1 关键查询

```elasticsearch
# 查询所有人工介入事件
{"query": {"term": {"message": "workflow.manual_intervention"}}}

# 查询特定 trace_id 的全链路
{"query": {"term": {"trace_id": "trace-a1b2c3d4e5f67890"}}}

# 查询所有 ERROR 级别日志
{"query": {"term": {"level": "ERROR"}}}

# 查询生产写入违规
{"query": {"term": {"message": "preflight.production_write_violation"}}}
```

##### 10.6.2 告警规则

| 告警名称 | 条件 | 级别 | 通知方式 |
|---|---|---|---|
| 生产写入违规 | `message:preflight.production_write_violation` 出现 | P0 紧急 | 立即短信+邮件 |
| 凭据泄露 | `message:security.credential_detected` 出现 | P0 紧急 | 立即短信+邮件 |
| Reasoner 连续失败 | 5 分钟内 `message:reasoner.call_failed` ≥ 3 | P1 高 | 邮件 |
| Transport 重试频繁 | 10 分钟内 `message:reasoner.transport_retrying` ≥ 10 | P2 中 | 邮件 |
| 人工介入频率高 | 1 小时内 `message:workflow.manual_intervention` ≥ 5 | P2 中 | 邮件 |

---

### 11 实施路线

#### 11.1 Phase 1：基础日志框架（1~2 天）

- [ ] 创建 `logging_utils.py` 模块，实现 `StructuredJsonFormatter` 和 `SensitiveDataFilter`
- [ ] 在 `workflow.py` 和 `langgraph_workflow.py` 中集成 Python `logging`
- [ ] 修改 `AuditCollector.record()` 同步输出日志
- [ ] 配置文件轮转和本地文件存储
- [ ] 更新 `pyproject.toml` 添加日志目录到 `.gitignore`

#### 11.2 Phase 2：全模块埋点（2~3 天）

- [ ] 在 Metrics Engine、Evidence Engine、Candidate Engine 中添加日志埋点
- [ ] 在 Reasoner 子系统（LLMReasoner、Transport、PromptBuilder）中添加日志埋点
- [ ] 在 Runtime Validator、Failure Analyzer、Preflight 中添加日志埋点
- [ ] 在 Security Audit 子系统中添加日志埋点
- [ ] 更新现有测试验证日志输出

#### 11.3 Phase 3：持久化与采集（1~2 天）

- [ ] 实现审计事件按日 JSONL 归档
- [ ] 配置 Filebeat/Promtail 采集规则
- [ ] 搭建 Elasticsearch/Loki 存储和 Kibana/Grafana 可视化
- [ ] 配置告警规则

#### 11.4 Phase 4：验证与文档（1 天）

- [ ] 验证日志级别映射与审计事件一致
- [ ] 验证敏感字段过滤完整性
- [ ] 验证 trace_id 全链路追踪
- [ ] 更新 AGENTS.md 添加日志相关约束
- [ ] 更新测试套件

---

### 附录 A：审计事件类型完整清单

| # | event_type | 建议日志级别 | 触发条件 |
|---|---|---|---|
| 1 | `task_loaded` | INFO | 工作流启动 |
| 2 | `schema_validated` | INFO | TaskInput Schema 校验通过 |
| 3 | `metrics_calculated` | DEBUG | Decimal 指标计算完成 |
| 4 | `evidence_evaluated` | INFO | 证据充分性判断完成 |
| 5 | `completed_without_change` | INFO | 证据不足或无需调整 |
| 6 | `candidates_generated` | DEBUG | 候选集合生成完成 |
| 7 | `reasoner_provider_selected` | INFO | Reasoner Provider 确认 |
| 8 | `llm_request_started` | INFO | LLM Transport 请求开始 |
| 9 | `reasoner_prompt_built` | DEBUG | Prompt 构建完成 |
| 10 | `reasoner_response_received` | INFO | 模型响应接收 |
| 11 | `reasoner_response_parsed` | DEBUG | 响应 JSON 解析完成 |
| 12 | `reasoner_schema_validation_passed` | DEBUG | Reasoner Output Schema 通过 |
| 13 | `reasoner_schema_validation_failed` | ERROR | Reasoner Output Schema 失败 |
| 14 | `reasoner_revision_feedback_added` | INFO | 修订反馈注入 Prompt |
| 15 | `llm_transport_retry` | WARN | Transport 层重试 |
| 16 | `llm_request_succeeded` | INFO | LLM 请求成功 |
| 17 | `llm_request_failed` | ERROR | LLM 请求失败 |
| 18 | `reasoner_completed` | INFO | Reasoner 调用完成 |
| 19 | `runtime_validation_failed` | ERROR | 运行时业务校验失败 |
| 20 | `runtime_validation_passed` | INFO | 运行时业务校验通过 |
| 21 | `failure_analyzed` | WARN/ERROR | 失败分析完成 |
| 22 | `plan_revised` | WARN | 计划修订 |
| 23 | `preflight_passed` | INFO | dry-run 预检通过 |
| 24 | `waiting_for_approval` | INFO | 等待人工审批 |
| 25 | `manual_intervention_required` | ERROR | 需要人工介入 |

### 附录 B：错误码清单

| 错误码 | 类别 | 日志级别 | 说明 |
|---|---|---|---|
| `ERR_RULE_CONFIG_MISSING` | 配置 | ERROR | 规则版本不匹配 |
| `ERR_SCHEMA_VALIDATION_FAILED` | Schema | ERROR | Schema 校验失败 |
| `ERR_CANDIDATE_OUT_OF_RANGE` | 业务 | ERROR | 候选越界 |
| `ERR_CURRENT_VALUE_MISMATCH` | 数据 | ERROR | 当前值不匹配 |
| `ERR_OBJECT_VERSION_MISMATCH` | 数据 | ERROR | 对象版本不匹配 |
| `ERR_OBJECT_REFERENCE_INVALID` | 数据 | ERROR | 对象引用无效 |
| `ERR_CHANGE_RATIO_EXCEEDED` | 业务 | ERROR | 变更比例超限 |
| `ERR_EVIDENCE_REFERENCE_INVALID` | 业务 | ERROR | 证据引用无效 |
| `ERR_STATE_TRANSITION_INVALID` | 安全 | ERROR | 状态转换非法 |
| `ERR_PLAN_DIGEST_MISMATCH` | 安全 | ERROR | 计划摘要不匹配 |
| `ERR_PRODUCTION_WRITE_FORBIDDEN` | 安全 | ERROR | 生产写入被禁止 |
| `ERR_REASONER_OUTPUT_SCHEMA_FAILED` | Schema | ERROR | Reasoner 输出 Schema 失败 |
| `ERR_LLM_CONFIG_MISSING` | 配置 | ERROR | LLM 配置不完整 |
| `ERR_LLM_CONFIG_INVALID` | 配置 | ERROR | LLM 配置无效 |
| `ERR_LLM_AUTHENTICATION_FAILED` | 安全 | ERROR | 认证失败（401） |
| `ERR_LLM_PERMISSION_DENIED` | 安全 | ERROR | 权限拒绝（403） |
| `ERR_LLM_RATE_LIMITED` | 限流 | WARN | 速率限制（429） |
| `ERR_LLM_SERVICE_UNAVAILABLE` | 服务 | WARN | 服务不可用（5xx） |
| `ERR_LLM_TIMEOUT` | 服务 | WARN | 请求超时 |
| `ERR_LLM_TRANSPORT_FAILED` | 服务 | WARN | Transport 失败 |
| `ERR_LLM_RETRIES_EXHAUSTED` | 服务 | ERROR | 重试耗尽 |
| `ERR_LLM_RESPONSE_INVALID` | 响应 | ERROR | 响应格式无效 |
| `ERR_LLM_RESPONSE_EMPTY` | 响应 | ERROR | 响应为空 |
| `ERR_REAL_EVALUATION_BUDGET_EXCEEDED` | 预算 | ERROR | 请求预算耗尽 |
| `ERR_REAL_EVALUATION_CONFIG_INVALID` | 配置 | ERROR | 评估配置无效 |