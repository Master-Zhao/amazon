# 项目结构与依赖方向

`accounts` 负责身份；`tenants/stores/permissions` 负责组织和数据范围；
`products/advertising` 负责主数据；`reports` 负责上传与导入；
`analytics` 负责三类事实和异常；`agents/recommendations/actions` 负责优化闭环；
`knowledge/audit` 负责只读知识与只追加审计。

允许的调用方向是 API View → Serializer → Service → ORM；复杂只读为
View → Selector → ORM；Celery Task → Service。跨 App 写入必须调用对方
Service。`apps.permissions.services.authorize` 是统一授权入口。

禁止 View、Task、Agent 直接改变核心状态；禁止 Agent 访问 ORM；禁止
analytics 把 `CampaignDailyMetric`、`TargetingDailyMetric` 与
`SearchTermDailyMetric` 相加；禁止跨 Marketplace/currency 汇总金额。
外部能力只能从 `backend/integrations/` 的 Protocol 进入。
