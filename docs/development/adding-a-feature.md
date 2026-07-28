# 添加业务功能

1. 在所属 App 定义 Model/迁移；不要把业务对象放进 `core`。
2. Serializer 负责输入；Service 负责事务、授权和状态；Selector 负责复杂读取。
3. View 只编排 Serializer 与 Service/Selector，并使用统一响应。
4. 异步入口只调用 Service，例如 `apps.reports.tasks.process_import_task` →
   `apps.reports.services.process_task`。
5. 增加 Tenant/Profile 跨界 404、范围内缺权限 403、幂等和并发测试。
6. 生成并验证 `openapi/schema.yaml`，再运行 `pnpm --dir frontend generate:api`。
7. 前端在 `frontend/src/features/<feature>/api` 和 `pages` 中实现真实 API 状态。

指标通过 `apps.analytics.calculations.calculate_metrics` 与
`upsert_daily_metric` 增加；异常规则以 `AnomalyRuleVersion` 和
`evaluate_campaign_metric` 扩展，并保留版本。
