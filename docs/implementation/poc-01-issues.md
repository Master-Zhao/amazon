# PoC 规范问题记录

## ISSUE-001：人工介入终态与空变更约束的表达冲突

- 问题编号：ISSUE-001
- 发现时间：2026-07-17T11:27:17+08:00
- 关联规范章节或编号：V0.2 第 18.1、23.4 节；本次任务第 11.5、12.11 节
- 问题描述：V0.2 规定 `changes=[]` 时 AgentOutput 必须为 `completed`，而本次 PoC 明确要求 Reasoner 连续返回相同非法值后输出 `manual_intervention_required`，且非法值不能作为合法 change 保留。
- 对实现的影响：单一 AgentOutput Schema 无法同时把“空变更只允许 completed”和“连续非法输出的人工介入结果”都表达为合法终态。
- 临时处理：按当前实现任务优先级，为 PoC Schema 增加仅用于失败闭环的 `manual_intervention_required + changes=[] + completion_reason=null` 分支；该分支不进入预检或审批，生产写入保持为 false。
- 是否阻断 PoC：否。
- 建议修订版本：后续规范明确区分 AgentOutput 与 WorkflowFailureResult，或为 DATA-003 增加人工介入失败变体。
- 当前状态：已记录，采用隔离的 PoC 处理。

### V0.2.1 修复记录

- 原始问题：AgentOutput 的空变更分支无法清楚区分业务完成与自动修订失败后的人工介入，并曾用一个 `passed=false` 的 preflight 占位对象表达“未执行预检”。
- 修复方案：新增 V0.2.1 补丁规范和独立 ManualInterventionPackage。AgentOutput 只表达 `manual_intervention_required` 终态并引用包；人工介入时 `execution_preflight=null`、`human_approval_required=false`、`changes=[]`。
- 修改文件：`docs/spec/amazon-ads-agent-loop-engineering-spec-v0.2.1.md`、`schemas/agent-output.schema.json`、`schemas/manual-intervention-package.schema.json`、`src/amazon_ads_agent/manual_intervention.py`、`workflow.py`、`models.py`、`schema_loader.py`、`cli.py` 及相关测试。
- Schema 变化：AgentOutput 新增 `manual_intervention_package_id` 条件约束；新增 Draft 2020-12 ManualInterventionPackage Schema；人工介入路径禁止 execution_preflight 对象。
- 兼容性影响：CLI 结构化输出升级为 `agent_output` 与 `manual_intervention_package` 两部分的协议信封。正常业务数值、候选、状态和退出码不变；always-invalid 仍返回退出码 3。
- 测试证据：新增 33 项独立反向与协议测试；完整套件 103 项通过。覆盖同错两次、最大修订、包正反例、旧摘要复用和人工介入不进入 preflight。
- 对应版本：V0.2.1。
- 当前状态：resolved。

## 记录规则

每个问题必须包含：

- 问题编号；
- 发现时间；
- 关联规范章节或编号；
- 问题描述；
- 对实现的影响；
- 临时处理；
- 是否阻断 PoC；
- 建议修订版本；
- 当前状态。
