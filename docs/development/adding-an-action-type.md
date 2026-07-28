# 添加 Action 类型

在 `apps.recommendations.services.ALLOWED_ACTIONS` 登记类型，并在
`validate_recommendation` 增加对象归属、状态、before/proposed 值、Decimal 和
动作专属校验。同步 Action Preview 序列化、人工执行清单和前端展示。

状态变更必须经过 `create_preview`、`submit_preview`、`decide_preview` 和
`record_execution`；提交冻结 `ActionPreviewVersion`，RETURNED 创建新版本，
批准创建 `ExecutionTask`，执行完成触发 `evaluate_execution`。不得提供普通更新/
删除 Approval、Execution、Audit 记录的 API。

每种动作至少做 Service 参数化测试；影响审批的类型还需 PERSONAL 自确认、
TEAM/COMPANY 职责分离、重复审批/执行和 beforeValue 漂移测试。最终同步 OpenAPI
与 TypeScript 类型。
