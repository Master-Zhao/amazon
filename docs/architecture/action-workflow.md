# 动作工作流

V1 不调用 Amazon Ads 写接口。系统只生成建议和人工执行清单：

`OPEN Recommendation → DRAFT Preview → PENDING_APPROVAL → APPROVED/REJECTED/RETURNED → manual ExecutionRecord → EffectEvaluation`

- Preview 每个版本有内容哈希；提交时冻结，冻结后模型层拒绝任何更新。
- Preview、审批和执行都在 Service 的事务与行锁中转换状态，并写入同事务 AuditLog。
- PERSONAL Tenant 的 Owner 可自确认；TEAM/COMPANY 的提交人不得审批自己的方案。
- 退回产生新 PreviewVersion，不修改旧版本。ApprovalRecord、ExecutionRecord 和 AuditLog 只追加。
- 批准后创建人工执行任务和逐项清单；回填支持 `SUCCEEDED`、`FAILED`、`SKIPPED`，幂等键阻止重复记录。
- EffectEvaluation 当前建立可追溯 baseline，后续观测值仍由确定性数据任务计算。

所有动作重新校验 Tenant/Profile 权限和最低操作等级。前端按钮与路由只改善体验，不能替代后端授权。

