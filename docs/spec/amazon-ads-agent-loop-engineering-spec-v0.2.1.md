# 亚马逊广告智能体闭环功能设计与 Loop Engineering 工程规范 V0.2.1 补丁

## 1. 文档基本信息

| 项目 | 内容 |
|---|---|
| 补丁版本 | V0.2.1 |
| 基线版本 | `amazon-ads-agent-loop-engineering-spec-v0.2.md` |
| 修订日期 | 2026-07-17 |
| 修订性质 | PoC-01 兼容性澄清与协议修复 |
| 适用范围 | PoC-01 人工介入终态、人工介入材料和计划摘要校验 |
| 生产能力影响 | 无；不增加 API、审批、执行或生产写入能力 |

V0.2.1 是对 V0.2 的小版本补丁，不重写 V0.2。除本文明确替代的人工介入输出表达和 PoC 计划摘要校验外，V0.2 的业务范围、安全边界、状态机、人工审批和生产 fail-closed 要求继续有效。

## 2. 版本变更

| 编号 | 变更 | 兼容性影响 |
|---|---|---|
| PATCH-001 | 明确 `manual_intervention_required` 是失败运行的人工处理终态，不是待审批状态 | 替代 V0.2 第 18.1、23.4 节中无法表达空变更人工介入的部分 |
| PATCH-002 | AgentOutput 增加 `manual_intervention_package_id` | 人工介入时必填；其他状态为空或不存在 |
| PATCH-003 | 增加独立 ManualInterventionPackage 协议 | 人工材料不再伪装成执行预检或合法广告变更 |
| PATCH-004 | PoC-01 运行期必须重算冻结计划摘要 | 任何冻结计划业务字段变化且复用旧摘要时 fail-closed |

## 3. AgentOutput 人工介入语义

AgentOutput 表达工作流当前最终状态。当自动修订达到停止条件时：

```text
current_status = manual_intervention_required
human_approval_required = false
execution_preflight = null
changes = []
completion_reason = null
manual_intervention_package_id = 非空引用
```

该结果不是待审批的合法广告修改方案。人工介入不等于人工审批；失败方案不得进入审批，不得执行预检，不得调用正式执行。原 `run_id` 在此状态下成为不可变终态。

当 `current_status=waiting_for_approval` 时，`manual_intervention_package_id` 必须为空，`human_approval_required=true`，且 dry-run 预检必须通过并保持 `production_write_called=false`。

当状态为 `completed` 或中间态 `validating_plan` 时，`manual_intervention_package_id` 必须为空。

## 4. ManualInterventionPackage

ManualInterventionPackage 是独立、Schema 可校验的人工处理材料，至少记录：停止原因、最后错误及指纹、全部失败尝试、计划版本、重试次数、数据快照、关联审计事件、恢复限制和禁止复用内容。

包必须保证：

```text
original_run_terminal = true
production_write_called = false
```

恢复限制必须明确：未来恢复需要授权人员显式创建新 `run_id`；不得复用失败方案或旧审批；不得自动重放；必须重新校验输入和配置。PoC-01 不实现恢复、审批或执行服务。

## 5. 停止原因

`stop_reason` 至少允许：

- `same_error_repeated`
- `maximum_revisions_reached`
- `uncorrectable_validation_failure`
- `rule_config_missing`
- `invalid_state_transition`
- `internal_safety_guard`

同一错误指纹连续出现两次时使用 `same_error_repeated`；达到配置的最大自动修订次数时使用 `maximum_revisions_reached`。两者都不得再调用 Reasoner 或 preflight。

## 6. PoC-01 计划摘要守卫

PoC-01 的冻结摘要覆盖对象、动作、候选集合、建议值、期望当前值、期望对象版本、变化比例、理由、证据、置信度和风险等级。运行期 Validator 必须独立重算摘要。

计划字段变化但仍提交旧 `plan_digest` 时返回：

```text
ERR_PLAN_DIGEST_MISMATCH
```

摘要不一致不得进入 preflight 或 `waiting_for_approval`。该 PoC 澄清不改变 V0.2 对审批后计划不可原地修改的要求。

## 7. 安全边界不变

本补丁不增加真实大模型、提示词、Amazon Ads API、Approval Service、RBAC、数据库、前端、Campaign 预算场景、production Adapter、生产写入、回滚或自动重放。所有业务 Decimal 继续使用字符串和 `decimal.Decimal`；所有正常路径的 `production_write_called` 继续为 `false`。
