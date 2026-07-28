# 06 状态机

## 1. 通用规则

- 状态只能由Service/状态机服务转换。
- 每次转换校验当前状态、权限、Tenant/Store范围、版本号和业务守卫。
- 转换与业务写入、AuditLog、待派发任务记录处于同一事务边界。
- 终态历史不回滚；重试创建新attempt、Run、Version或EvaluationSnapshot。
- 默认非法转换错误码：`INVALID_STATE_TRANSITION`。
- 并发版本不一致：`STATE_VERSION_CONFLICT`。
- 守卫失败：`STATE_GUARD_FAILED`。
- 权限失败：`PERMISSION_DENIED`；跨隔离边界对外可返回`RESOURCE_NOT_FOUND`。

表中“权限”均附带有效Membership、Store授权和对象归属校验。

## 2. 报表导入

| 状态 | 含义 | 合法前置 | 允许动作/权限 | 守卫 | 转换后动作 | 终态/重试 |
|---|---|---|---|---|---|---|
| `UPLOADED` | 文件已持久化、未校验 | 创建 | 开始校验：系统；取消：`reports.cancel` | 文件元数据和Store上下文存在 | 排队校验或记录取消 | 否；失败重试创建新ImportTask |
| `VALIDATING` | 校验文件、字段和范围 | UPLOADED | 校验：系统；取消：`reports.cancel` | Schema版本可用、文件可读 | 成功转PARSING，失败转FAILED | 否；新attempt |
| `PARSING` | 解析和标准化行 | VALIDATING | 解析：系统；取消：`reports.cancel` | 编码/工作表规则满足 | 创建原始行清单和错误，转IMPORTING或FAILED | 否；新attempt |
| `IMPORTING` | 去重并写权威事实 | PARSING | 导入：系统 | 粒度键、事务和重述规则可用 | 计算计数、指标和异常 | 否；新attempt |
| `SUCCEEDED` | 全部有效数据成功 | IMPORTING | 查看：`reports.view` | 成功数>0且错误数=0 | 审计、更新查询可见性 | 是；重导创建新Task/Batch |
| `PARTIAL_SUCCEEDED` | 部分有效、部分拒绝 | IMPORTING | 查看/下载错误：`reports.view` | 成功数>0且错误数>0；阈值待确认 | 审计并暴露错误 | 是；重导创建新Task/Batch |
| `FAILED` | 本次尝试失败 | VALIDATING/PARSING/IMPORTING | 查看：`reports.view`；重试：`reports.upload`或专用权限待定 | 保存稳定错误码 | 关闭attempt、审计 | 是；创建新attempt |
| `CANCELLED` | 在允许阶段取消 | UPLOADED/VALIDATING/PARSING；IMPORTING是否允许待确认 | 取消：`reports.cancel` | 未进入不可安全中断的事务 | 停止后续任务、审计 | 是；重新创建Task |

建议和待确认：是否增加队列态、PARTIAL阈值、IMPORTING取消策略。不得在确认前改名或删除现有状态。

## 3. 分析任务

| 状态 | 含义 | 合法前置 | 允许动作/权限 | 守卫 | 转换后动作 | 终态/重试 |
|---|---|---|---|---|---|---|
| `DRAFT` | 分析范围尚可编辑 | 创建 | 编辑/提交：`analysis.create`；取消：`analysis.cancel` | 单Store、范围授权、日期有效 | 提交时冻结ScopeSnapshot | 否；不适用 |
| `QUEUED` | 已冻结并等待编排 | DRAFT | 启动：系统；取消：`analysis.cancel` | Snapshot/hash完整 | 创建本轮AgentRun | 否；取消后新建任务 |
| `RUNNING` | Orchestrator执行中 | QUEUED | 推进：系统；取消：`analysis.cancel` | AgentVersion和Mock/Provider可用 | 保存步骤、证据和错误 | 否；失败重试创建新Run attempt |
| `SUCCEEDED` | 已产生有效结构化结果 | RUNNING | 查看：`analysis.view` | 必需Agent结果Schema全部通过 | 允许创建Recommendation | 是；重新分析创建新Task |
| `FAILED` | 本轮无法完成 | QUEUED/RUNNING | 查看：`analysis.view`；重试：`analysis.create` | 错误已落库 | 审计并关闭本轮Run | 是；新Run或新Task，策略待确认 |
| `CANCELLED` | 用户/系统取消 | DRAFT/QUEUED/RUNNING | `analysis.cancel` | 不存在已提交Recommendation | 停止未开始步骤、保留历史 | 是；新Task |

## 4. Agent运行

Agent运行采用建议状态集；此前没有给定AgentRun状态名，因此实现前仍需状态评审。

| 状态 | 含义 | 合法前置 | 允许动作/权限 | 守卫 | 转换后动作 | 终态/重试 |
|---|---|---|---|---|---|---|
| `QUEUED` | 等待执行 | 创建 | 系统启动 | 父AnalysisTask为RUNNING | 锁定AgentVersion | 否 |
| `RUNNING` | 运行工具和LLM | QUEUED | 系统推进/取消 | Scope和工具白名单有效 | 追加AgentStep | 否 |
| `SUCCEEDED` | 输出Schema通过 | RUNNING | 系统完成 | 证据和结构化结果完整 | 通知Orchestrator | 是；新attempt |
| `FAILED` | 调用或验证失败 | QUEUED/RUNNING | 系统失败 | 保存错误码且不保存隐藏思维 | 通知Orchestrator | 是；新attempt |
| `CANCELLED` | 父任务取消 | QUEUED/RUNNING | 系统取消 | 无不可中断提交 | 停止后续步骤 | 是；新attempt |

## 5. AI建议

| 状态 | 含义 | 合法前置 | 允许动作/权限 | 守卫 | 转换后动作 | 终态/重试 |
|---|---|---|---|---|---|---|
| `GENERATED` | AI原始Revision已生成 | 创建 | 接受/修改/拒绝：`recommendations.review` | 原始Revision和证据完整 | 追加审计 | 否 |
| `ACCEPTED` | 操作员接受当前Revision | GENERATED/MODIFIED | 提交：`recommendations.submit`；修改：`recommendations.review` | 当前Revision版本匹配 | 更新容器状态，不改Revision | 否 |
| `MODIFIED` | 存在人工Revision | GENERATED/ACCEPTED/MODIFIED | 再修改/接受/提交：相应权限 | 新Revision Schema通过 | 追加RecommendationRevision | 否 |
| `REJECTED` | 建议终止 | GENERATED/MODIFIED/ACCEPTED | 查看：`recommendations.view` | 拒绝原因满足要求 | 审计 | 是；新分析生成新Recommendation |
| `SUBMITTED` | 已提交生成/关联Preview | ACCEPTED/MODIFIED | 撤回：`recommendations.withdraw`，条件受限 | 当前Revision冻结且Preview已创建 | 关联PreviewVersion | 条件终态；重提创建新Preview版本 |
| `WITHDRAWN` | 提交后在允许窗口撤回 | SUBMITTED | 查看 | Preview尚未批准或执行 | 使关联草稿/待审批流程按规则撤回 | 是；新Revision/Preview流程 |

建议和待确认：`MODIFIED`是流程态还是Revision派生态；`SUBMITTED`的精确时点；已进入审批后是否允许撤回。

## 6. Action Preview

| 状态 | 含义 | 合法前置 | 允许动作/权限 | 守卫 | 转换后动作 | 终态/重试 |
|---|---|---|---|---|---|---|
| `DRAFT` | 容器有可编辑草稿 | 创建/RETURNED后新版本 | 编辑：`actions.create`；提交：`actions.submit`；撤回：`actions.withdraw` | 动作Schema、对象状态、before值、权限有效 | 提交生成不可变Version/hash | 否 |
| `PENDING_APPROVAL` | 具体Version等待单级审批 | DRAFT | 决定：`approvals.decide`；撤回：`actions.withdraw` | Version不可变、审批人不能违反待确认职责分离规则 | 追加ApprovalRecord | 否 |
| `APPROVED` | 单级审批通过 | PENDING_APPROVAL | 发布就绪：系统 | 版本未过期、对象未漂移或漂移规则通过 | 执行前校验 | 否；失败不得改旧Version |
| `REJECTED` | 审批拒绝并终止该Version | PENDING_APPROVAL | 查看 | 审批原因完整 | 审计 | 是；新PreviewVersion |
| `RETURNED` | 退回修改 | PENDING_APPROVAL | 基于容器创建新草稿：`actions.create` | 旧Version保持不可变 | 创建新Version序列 | 该Version终态；容器可继续 |
| `WITHDRAWN` | 提交者撤回 | DRAFT/PENDING_APPROVAL；批准后是否允许待确认 | `actions.withdraw` | 无执行任务 | 审计、关闭待审批 | 是；新Version |
| `READY_TO_EXECUTE` | 已批准并通过执行前校验 | APPROVED | 生成任务：系统/`executions.execute` | 目标状态与批准快照满足漂移规则 | 创建ExecutionTask/Item | 否；生成失败重试不改Version |
| `EXPIRED` | 超过有效期 | PENDING_APPROVAL/APPROVED/READY_TO_EXECUTE | 系统标记 | 当前时间超过expiresAt且未开始执行 | 审计、禁止执行 | 是；新Version |

建议和待确认：APPROVED与READY_TO_EXECUTE之间的执行前校验、过期时点和漂移容忍；不得直接合并现有状态。

## 7. 审批

V1审批流程不维护可任意改写的独立状态行；流程状态由Action Preview和只追加ApprovalRecord派生。

| 派生状态/决定 | 含义 | 前置 | 动作/权限 | 守卫 | 后置 | 终态/重试 |
|---|---|---|---|---|---|---|
| `PENDING` | 尚无本级决定 | Preview=PENDING_APPROVAL | approve/reject/return：`approvals.decide` | 单级step=1、版本匹配、Store授权 | 追加一条决定记录 | 否 |
| `APPROVED` | 决定批准 | PENDING | approve | 待确认是否禁止自批；评论规则满足 | Preview→APPROVED | 本attempt终态；不得覆盖 |
| `REJECTED` | 决定拒绝 | PENDING | reject | 原因必填 | Preview→REJECTED | 本attempt终态 |
| `RETURNED` | 决定退回 | PENDING | return | 修改意见必填 | Preview→RETURNED | 本attempt终态 |
| `WITHDRAWN` | 提交者先于决定撤回 | PENDING | `actions.withdraw` | 无既有决定 | Preview→WITHDRAWN；无伪审批记录或记录系统事件 | 终态 |

审批非法转换使用`APPROVAL_INVALID_STATE`，重复决定使用`APPROVAL_ALREADY_DECIDED`。

## 8. 人工执行

| 状态 | 含义 | 合法前置 | 允许动作/权限 | 守卫 | 转换后动作 | 终态/重试 |
|---|---|---|---|---|---|---|
| `WAITING_MANUAL_EXECUTION` | 等待操作员开始 | 创建 | 开始：`executions.execute`；取消：`executions.cancel` | Preview Version仍可执行 | 记录执行人和开始时间 | 否 |
| `MANUAL_EXECUTING` | 人工执行并逐项回填 | WAITING_MANUAL_EXECUTION | 回填：`executions.execute` | 每项对应PreviewItem；实际值Schema有效 | 追加ExecutionRecord | 否 |
| `WAITING_CONFIRMATION` | 所有必需项已回填 | MANUAL_EXECUTING | 确认：`executions.confirm`；补充失败记录：`executions.execute` | 必需项均有最新结果；证据规则满足 | 汇总结果并审计 | 否 |
| `CONFIRMED` | 执行结果已确认 | WAITING_CONFIRMATION | 查看 | 确认人/职责分离规则满足 | 创建EffectEvaluation | 是；后续修正追加新记录并重新确认策略待确认 |
| `MANUAL_FAILED` | 无法完成本任务 | MANUAL_EXECUTING/WAITING_CONFIRMATION | 标记失败：`executions.execute` | 失败原因完整 | 审计并禁止直接进入评估或按规则评估 | 是；创建新ExecutionTask |
| `CANCELLED` | 开始前取消 | WAITING_MANUAL_EXECUTION | `executions.cancel` | 没有ExecutionRecord | 审计 | 是；重新生成任务需新记录 |

建议和待确认：部分成功的任务级表示、高风险证据、谁负责最终确认。

## 9. 效果评估

| 状态 | 含义 | 合法前置 | 允许动作/权限 | 守卫 | 转换后动作 | 终态/重试 |
|---|---|---|---|---|---|---|
| `WAITING_OBSERVATION` | 等待观察窗口结束 | 创建 | 查看：`evaluations.view`；到期触发：系统 | 执行已CONFIRMED；窗口已冻结 | 到期排队 | 否 |
| `EVALUATING` | 计算前后指标 | WAITING_OBSERVATION | 系统/`evaluations.run` | 基线、观察期和数据版本可用 | 创建不可变Snapshot | 否；失败创建新评估attempt |
| `EFFECTIVE` | 达到有效标准 | EVALUATING | 查看 | 冻结规则判定 | 审计、可生成知识候选 | 是；重评新Snapshot |
| `PARTIALLY_EFFECTIVE` | 部分指标有效 | EVALUATING | 查看 | 冻结规则判定 | 同上 | 是；新Snapshot |
| `INEFFECTIVE` | 未达到标准 | EVALUATING | 查看 | 冻结规则判定 | 同上 | 是；新Snapshot |
| `NEGATIVE_EFFECT` | 指标显著恶化 | EVALUATING | 查看 | 冻结规则判定 | 风险提示、审计 | 是；新Snapshot |
| `INCONCLUSIVE` | 数据不足或无法归因 | EVALUATING | 查看 | 最低数据量/完整性不满足 | 记录原因 | 是；数据更新后新Snapshot |

## 10. 状态一致性结论

- 所有给定状态均保留，未改名、未删除。
- REJECTED与RETURNED含义不同：前者终止版本，后者允许容器创建新版本。
- APPROVED与READY_TO_EXECUTE暂不合并，前者是审批结果，后者是执行前校验通过。
- 推荐重试均创建新尝试或不可变记录，不将历史终态改回运行态。
- 当前仍需确认取消边界、部分成功、职责分离、过期和对象漂移规则。
