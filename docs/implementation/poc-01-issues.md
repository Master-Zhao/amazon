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
