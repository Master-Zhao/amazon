# 已确认范围

## 1. 依据与状态

- 唯一主规格：`codex_master_goal_amazon_ads_v1.md`。
- 本文是主规格的范围索引，不替代主规格。
- 当前只完成 Phase 0 文档与审计，没有任何业务能力实现。
- 主规格已明确的要求视为已确认；仍依赖真实 Amazon 报表样例或实施细节的事项在本文单独标记。

## 2. 最终交付

V1 必须交付：

1. 可运行的 Django 后端和 Vue 3 前端。
2. MySQL 迁移/初始化数据、Redis、Celery Worker/Beat、Nginx、Docker Compose。
3. Campaign、Targeting、Search Term 三类报表的 CSV/Excel 手工上传、异步导入、错误、重处理和血缘。
4. Sponsored Products 基础广告结构和产品/ASIN/SKU/Listing 能力。
5. 三类独立每日事实、确定性指标、历史快照、目标 ACOS 和异常规则。
6. 四类 Agent、AnalysisOrchestrator、统一版本化 JSON Schema 和 MockLLMProvider。
7. Recommendation、Action Preview、单级审批、人工执行回填、基础效果评估。
8. User/Tenant/Team/RBAC、Store/Marketplace/Profile 与功能/数据权限隔离。
9. 只追加业务审计、轻量知识中心。
10. 后端、前端、集成、E2E、Compose 与并发测试，以及完整文档和演示脚本。

## 3. 固定技术与架构

- 后端：Python 3.13、Django 5.2 LTS、DRF 3.16.x、Celery 5.6.x、MySQL 8.4 LTS、Redis 7.x、Gunicorn、uv。
- 前端：Node.js 24 LTS、Vue 3、TypeScript、Vite 8.x、Vue Router、Pinia、Axios、ECharts、pnpm。
- 部署：Nginx、Docker Compose、`local/test/prod`。
- 架构：前后端分离的模块化单体，不拆微服务。
- 写路径：View → Serializer → Service → ORM。
- 读路径：View → Selector → ORM。
- 异步路径：Celery Task → Service。
- 文件、LLM、广告数据来源经 Adapter。

## 4. 身份、组织与数据范围

- User 是全局账号，不含 `tenant_id`；可通过 TenantMembership 加入多个 Tenant。
- Tenant 类型为 PERSONAL、TEAM、COMPANY。
- Team 可选；个人卖家无需虚拟 Team。
- Tenant 拥有多个 AmazonStore；Store 只属于一个 Tenant。
- Store 与全局 Marketplace 通过 StoreMarketplace 关联。
- StoreMarketplace 拥有多个 AdvertisingProfile；Profile 只属于一个 StoreMarketplace。
- 前端上下文固定为 `Tenant → AmazonStore → Marketplace → AdvertisingProfile`。
- V1 禁止跨 Tenant 汇总。

## 5. 权限

- 功能权限采用 User/Role/Permission；Role 绑定 Tenant 上下文。
- 支持系统内置角色和 Tenant 自定义角色；自定义角色只能组合既有 permission code。
- Store 与 Profile 均有数据授权。
- Profile 等级为 VIEW、OPERATE、APPROVE、EXECUTE、MANAGE。
- Profile 可直接授权 User，也可授权 Team；取并集且同 Profile 取最高等级。
- Tenant Owner/Admin 默认拥有当前 Tenant 所有 Profile 权限。
- V1 使用白名单，不实现显式 DENY。
- 每个请求同时校验认证、Membership、功能权限、Store、Profile、对象归属和状态守卫。
- 跨 Tenant 或完全越出范围返回 404；当前范围内缺动作权限返回 403。

## 6. 认证与 API

- JWT 双 Token：短期 Access Token，前端优先保存在内存；Refresh Token 放 HttpOnly Cookie。
- REST/JSON，前缀 `/api/v1`，统一 `code/message/data/requestId`。
- Python/数据库 snake_case；API/TypeScript camelCase。
- API ID 使用字符串；金额为 Decimal 字符串并带 currency。
- 时间点以 UTC 存储并用 ISO 8601；业务日期保留 Marketplace 本地语义。
- 异步创建返回 HTTP 202 和字符串 taskId。
- OpenAPI 是前后端契约；列表分页且限制最大页大小。

## 7. 广告与产品

- V1 完整实现 Sponsored Products。
- 层级至少为 Profile → Campaign → AdGroup → Ad/Keyword/ProductTarget。
- Search Term 是实际搜索/匹配词，不等同 Keyword。
- Product 为 Tenant 内部产品。
- MarketplaceCatalogItem 在 `(marketplace_id, asin)` 唯一。
- ProductListing 在 `(store_marketplace_id, seller_sku)` 唯一。
- 一个 Product 可有多个 Listing；一个 ASIN 可映射多个 SKU/Listing；Ad 主要关联 Listing。

## 8. 报表、文件和导入

- 三类必做报表：Campaign、Targeting、Search Term。
- V1 真实入口是用户手工上传 CSV/Excel。
- FileUploadReportSource 完整实现；第三方和 Amazon API Source 仅保留接口。
- 流程包含上传、Task/Batch、映射、校验、标准化、去重、批量持久化、权威事实、审计和血缘。
- 文件正文在 FileStorage；MySQL 保存元数据、哈希、地址和血缘。
- 文件级致命错误整份失败；合法行入库、错误行记录；合法与错误并存为 PARTIAL_SUCCEEDED。
- 状态至少为 QUEUED、RUNNING、SUCCEEDED、PARTIAL_SUCCEEDED、FAILED。
- ReportUpload、ImportTask、ImportBatch 只追加；重处理创建新 Task/Batch。
- 新 Batch 可修正当前权威事实；权威记录可追溯来源 Batch。
- 原始解析行可压缩为 JSONL 存储，不无条件重复写 MySQL。
- 大文件流式保存、分块读取、批量查询和批量写入；禁止逐行查询和逐行事务。

## 9. 指标、粒度、币种和异常

- 独立事实：Campaign Daily Metric、Targeting Daily Metric、Search Term Daily Metric。
- 原始指标：impressions、clicks、spend、orders、sales。
- 确定性公式：CTR、CPC、CVR、ACOS、ROAS。
- 无有效分母返回 null 并保存原因，不以 0/Infinity 伪装。
- Dashboard/Campaign 以 Campaign 粒度为权威；Keyword/ProductTarget 以 Targeting 粒度；Search Term 以 Search Term 粒度。
- Campaign 保存预算/状态日快照；Targeting 保存竞价/状态日快照。
- 不同 Marketplace/currency 不直接合计。
- 目标 ACOS 继承优先级：Campaign > Profile > Tenant。
- 异常阈值：system default → Tenant → Profile → Campaign。
- 风险 LOW/MEDIUM/HIGH，CRITICAL 仅预留。
- 数据不足为 INSUFFICIENT_DATA；规则可测试、解释并追溯版本。

## 10. AI 和建议

- 四类 Agent：数据分析、异常诊断、预算分析、综合策略。
- Orchestrator 固定编排、冻结范围、裁剪输入、验证 Schema。
- 外层 Schema 至少包含 schemaVersion、agentCode、runId、status、summary、evidence、recommendations、warnings、errors。
- 所有调用经过 LLMProvider；测试和稳定演示完整使用 MockLLMProvider。
- Agent 不直接访问 ORM、扩大范围、审批或执行。
- 正式 Recommendation 只能由 Service 从通过校验的结果创建。
- 保存 AgentVersion、输入摘要、结构化结果、证据和错误；不保存隐藏思维过程。

## 11. 动作、审批和执行

V1 动作：

- 更新 Campaign 预算。
- 暂停/启用 Campaign。
- 更新 Keyword 竞价。
- 暂停/启用 Keyword。
- 更新 Product Target 竞价。
- 暂停/启用 Product Target。
- 新增 BROAD/PHRASE/EXACT 普通 Keyword。
- 新增 Campaign/AdGroup 级 Negative Keyword。

规则：

- 不物理删除 Campaign、Keyword、Target，以暂停替代。
- 每项包含 actionType、objectType/id、before/after、reason、evidence、riskLevel。
- 后端校验 Schema、归属、状态、before 漂移、金额/币种、上下限、权限和风险。
- Action Preview 状态至少 DRAFT、PENDING_APPROVAL、APPROVED、REJECTED、RETURNED、WITHDRAWN。
- PERSONAL Tenant Owner 可自我确认；TEAM/COMPANY 提交人不能审批自己的方案。
- 提交版本不可变；退回创建新版本；ApprovalRecord 只追加。
- 批准后生成手工清单，回填 SUCCESS/FAILED/SKIPPED、实际值、时间、备注和证据。
- 批量执行允许部分成功；用幂等键、唯一约束和状态检查防重复。

## 12. 知识、审计与保留

- 知识中心一级菜单真实可用，V1 只做指标、报表、异常、动作、指南、FAQ 的只读分类/文章。
- 技术日志与 AuditLog 分开；AuditLog 在 MySQL 只追加。
- 登录、授权、上传、规则、AI、建议、Preview、审批、执行和配置必须审计。
- 修改类操作记录脱敏 before/after。
- 原始报表和证据文件默认保留 365 天，到期可归档/删除正文；元数据、ImportBatch 和审计保留。
- 提供 live/ready、应用版本/Git commit/构建时间、备份恢复文档。

## 13. 性能与可扩展目标

- 保持无状态 API、异步削峰、队列隔离、分页、批处理、索引、N+1 防护、连接池、超时、有限重试、幂等、并发控制、限流、缓存隔离和可观测性。
- 参考目标为 300 并发虚拟用户、200 RPS 持续 10 分钟等主规格指标。
- 这些是未来验收目标，不是当前能力声明；只有 Phase 6 的真实压测结果可以证明。

## 14. 仍需真实样例或实现期确认

- 三类 Amazon 导出文件的实际列名、标题行、编码、Excel 工作表、日期/金额格式。
- 三类自然粒度键、外部 ID 稳定性、迟到/重述的边界案例。
- 上传大小 P95/P99、解析资源配置和真实性能。
- ProductTarget expression、Search Term 归因和 Marketplace/Profile 内容一致性。
- 在获得样例前可实现可配置 Schema/Mapping 和虚构 fixtures，但必须标记“尚未使用真实导出文件验证”。
