# Codex Master Goal：Amazon 广告智能优化系统 V1

> 用途：将本文件作为 Codex 的长期项目目标与主规格。  
> 执行方式：先让 Codex 阅读本文件并创建/更新仓库根目录 `AGENTS.md` 与 `PLANS.md`，再严格按阶段实施。  
> 原则：已确认需求必须实现；未在本文件中出现的业务能力不得擅自扩展。不得用静态页面或伪造结果冒充已经打通的后端能力。

---

## 1. 最终交付目标

建设一个面向 Amazon 个人卖家、团队卖家和公司卖家的广告智能优化系统。最终交付必须同时具备：

1. 可运行的 Django 后端。
2. 可运行的 Vue 3 前端。
3. 可执行的 MySQL 数据库迁移与初始化数据。
4. 可运行的 Redis、Celery Worker 和 Celery Beat。
5. 可上传并异步导入 Campaign、Targeting、Search Term 三类报表。
6. 可展示标准化广告数据、确定性指标与异常结果。
7. 可通过 MockLLMProvider 稳定运行四类智能体。
8. 可生成 Recommendation、Action Preview，并完成单级审批、人工执行回填和效果评估基础闭环。
9. 可验证 User、Tenant、Store、Marketplace、AdvertisingProfile、RBAC 与数据权限隔离。
10. 可查询只追加的业务审计日志。
11. 可通过 Docker Compose 启动。
12. 可执行后端、前端、集成和端到端测试。
13. 具备可横向扩展、异步削峰、并发安全和可压测的高并发框架。
14. 完整 README、架构文档、接口文档、部署文档、测试文档、团队分工文档、演示讲稿和逐步演示脚本。
15. 文档内容必须与实际代码状态一致，必须明确区分“已实现、已测试、仅预留、尚未验证”。

最终结果不能只是目录、设计文档、静态页面或不能运行的占位代码。

---

## 2. 执行规则

Codex 在任何修改前必须：

1. 检查仓库目录、Git 状态、已有代码、依赖、迁移、测试、文档和 Docker 配置。
2. 实际运行现有启动、测试、类型检查或构建命令，记录真实结果；无法运行时说明原因。
3. 创建或更新：
   - `AGENTS.md`：永久工程规则、目录约束、测试命令和禁止事项。
   - `PLANS.md`：分阶段实施计划、依赖关系、验收条件和当前进度。
   - `docs/requirements/confirmed-scope.md`：本文件中的已确认需求。
   - `docs/requirements/out-of-scope.md`：明确不做内容。
4. 先输出仓库现状与差距，再开始实现。
5. 按阶段实施；每个阶段结束时必须保持系统可启动、可迁移、可测试。
6. 优先完成真实纵向链路，不得先生成大量空模块、空类和占位文件。
7. 不得覆盖未知用途的现有代码；需要重构时先说明影响。
8. 不得擅自改变已确认技术栈、权限模型、接口契约、数据粒度和审批规则。
9. 不得声称运行了未运行的命令，不得声称通过了未执行的测试，不得虚构性能结果。
10. 缺少真实 Amazon 报表样例时，使用虚构、脱敏测试模板和可配置字段映射完成框架，但必须在文档中注明“尚未使用真实导出文件验证”。

---

## 3. 明确不属于 V1 的内容

以下内容不得实现为当前真实能力：

1. 不真实调用 Amazon Ads API。
2. 不真实接入第三方广告数据服务商。
3. 不直接修改 Amazon 后台广告。
4. 不做跨 Tenant 数据汇总。
5. 不把模块化单体擅自拆成微服务。
6. 不实现多级复杂审批流。
7. 不完整实现 Sponsored Brands 和 Sponsored Display。
8. 不实现完整库存、采购、物流、订单或财务系统。
9. 不实现未经确认的知识图谱、复杂 RAG、自动网络采集或向量平台。
10. 不引入没有实际必要的 Kubernetes、Kafka、Elasticsearch、分布式事务框架或复杂事件总线。
11. 不虚构模型效果、广告优化收益、QPS、在线用户数或延迟指标。

---

## 4. 技术栈与工程基线

### 4.1 后端

- Python 3.13
- Django 5.2 LTS
- Django REST Framework 3.16.x
- Celery 5.6.x
- Redis 7.x
- MySQL 8.4 LTS
- Gunicorn
- `pyproject.toml + uv.lock`

### 4.2 前端

- Node.js 24 LTS
- Vue 3
- TypeScript
- Vite 8.x
- Pinia
- Axios
- ECharts
- pnpm
- `package.json + pnpm-lock.yaml`

禁止混用 npm、yarn 和 pnpm。禁止使用 `latest` 依赖或镜像标签。核心版本升级必须先测试，并记录 ADR。

### 4.3 部署

- Nginx
- Docker Compose
- `local / test / prod` 三套环境
- 支持全容器启动
- 支持 MySQL、Redis 在容器内，Django、Celery、Vue 在本机运行的混合开发方式

---

## 5. 总体架构

采用前后端分离的模块化单体：

```text
Browser
  -> Nginx
     -> Vue static assets
     -> /api/v1 -> Django/Gunicorn
                      -> MySQL
                      -> Redis
                      -> FileStorage
                      -> Celery queues
                      -> LLMProvider

Celery Worker
  -> report import
  -> metric calculation
  -> agent analysis
  -> effect evaluation

Celery Beat
  -> scheduled evaluation
  -> retention cleanup
  -> maintenance checks
```

后端建议模块：

```text
backend/
├── config/
├── api/v1/
├── apps/
│   ├── core/
│   ├── accounts/
│   ├── tenants/
│   ├── permissions/
│   ├── stores/
│   ├── products/
│   ├── reports/
│   ├── advertising/
│   ├── analytics/
│   ├── agents/
│   ├── recommendations/
│   ├── actions/
│   ├── knowledge/
│   └── audit/
├── integrations/
│   ├── storage/
│   ├── llm/
│   └── advertising_data/
└── tests/
```

规则：

- 写操作：`View -> Serializer -> Service -> Django ORM`
- 复杂只读查询：`View -> Selector -> Django ORM`
- 异步入口：`Celery Task -> Service`
- Celery Task 不得复制业务逻辑或绕过 Service 随意改状态。
- Agent 不得直接访问 ORM，只能通过 Orchestrator、Selector 和 Service。
- 文件、LLM、广告数据来源必须通过 Adapter。
- V1 不强制 Repository 层。
- `core` 只放真正通用的基类、响应、异常、requestId、时间和审计基础能力，不得成为业务杂物箱。
- 每个业务模块拥有模型、迁移、API、Service、Selector（需要时）、权限和测试；小模块无需提前拆出大量空目录。

---

## 6. 用户、租户、团队、店铺与广告 Profile

### 6.1 核心关系

- User 是全局账号。
- 一个 User 可加入多个 Tenant。
- Tenant 前端显示为“卖家空间”，类型：
  - `PERSONAL`
  - `TEAM`
  - `COMPANY`
- Tenant 可选创建 Team；个人卖家不要求 Team。
- 一个 Tenant 可拥有多个 AmazonStore。
- 一个 AmazonStore 只属于一个 Tenant。
- 一个 AmazonStore 可关联多个 Marketplace。
- Marketplace 是全局基础数据。
- Store 与 Marketplace 通过 StoreMarketplace 关联。
- 一个 StoreMarketplace 可拥有多个 AdvertisingProfile。
- AdvertisingProfile 只属于一个 StoreMarketplace。
- Campaign、AdGroup、Ad、Keyword、Product Target、Search Term 与指标必须可追溯到 AdvertisingProfile。

前端上下文顺序：

```text
Tenant -> AmazonStore -> Marketplace -> AdvertisingProfile
```

只有一个选项自动选择；多个选项允许切换。V1 禁止跨 Tenant 汇总。

### 6.2 权限

功能权限：`User -> Role -> Permission`

- User 可拥有多个 Role。
- 支持系统内置角色和 Tenant 自定义角色。
- 内置角色不可删除，可复制。
- Tenant 自定义角色只能组合现有 permission code，不得创建任意权限码。

数据权限：

- Store 权限：允许进入 Store。
- Profile 权限：广告数据访问与操作必须拥有。
- Profile 等级：
  - `VIEW`
  - `OPERATE`
  - `APPROVE`
  - `EXECUTE`
  - `MANAGE`
- Profile 可直接授权给 User，也可授权给 Team。
- 直接授权与团队授权取并集；同一 Profile 取最高等级。
- Tenant Owner/Admin 默认拥有当前 Tenant 所有 Profile 权限。
- V1 使用白名单授权，不实现显式 DENY。

每个业务请求必须同时校验：

1. 已认证用户。
2. 有效 TenantMembership。
3. 功能权限。
4. Store 数据范围。
5. AdvertisingProfile 数据范围。

跨 Tenant 或完全不在数据范围中的对象返回 404；当前 Tenant 内对象存在但缺少操作权限时返回 403。前端隐藏菜单或按钮不能替代后端校验。

---

## 7. 认证与 API 契约

认证采用 JWT 双 Token：

- Access Token 短期有效，前端优先保存在内存。
- Refresh Token 放在 HttpOnly Cookie。
- Token 只证明身份；Tenant、Store、Profile、功能权限在后端数据库校验。

API 统一规则：

- REST API + JSON
- 前缀 `/api/v1`
- 统一响应：

```json
{
  "code": "SUCCESS",
  "message": "操作成功",
  "data": {},
  "requestId": "req_xxx"
}
```

- 使用语义化 HTTP 状态码。
- 文件上传使用 `multipart/form-data`。
- 异步任务创建返回 HTTP 202 和字符串 `taskId`。
- Python 与数据库使用 `snake_case`。
- API 与 TypeScript 使用 `camelCase`，由统一序列化/渲染层转换。
- API 中 ID 使用字符串。
- 金额使用 Decimal，并以字符串和币种传输：

```json
{
  "amount": "100.00",
  "currency": "USD"
}
```

- 操作时间数据库保存 UTC，API 使用 ISO 8601。
- 广告指标日期保留 Profile 所在 Marketplace 的本地业务日期，不因 UTC 转换而改变。
- OpenAPI 是前后端契约；生成或同步 TypeScript 类型。
- 所有列表分页并设置最大页大小。

---

## 8. 广告类型、广告模型和产品模型

### 8.1 广告类型

- V1 完整实现 Sponsored Products。
- Sponsored Brands、Sponsored Display 只保留 `ad_type` 等扩展边界。

广告层级至少包括：

```text
AdvertisingProfile
  -> Campaign
     -> AdGroup
        -> Ad
        -> Keyword
        -> ProductTarget
```

Search Term 是买家实际搜索或匹配到的词，不等于卖家投放的 Keyword。

### 8.2 产品

- Product：卖家内部产品。
- MarketplaceCatalogItem：Marketplace 下的 ASIN，唯一 `(marketplace_id, asin)`；ASIN 不是全球唯一。
- ProductListing：StoreMarketplace 下的 seller SKU，唯一 `(store_marketplace_id, seller_sku)`。
- 一个 Product 可有多个 Listing。
- 一个 ASIN 可映射多个 SKU/Listing。
- Ad 主要关联 ProductListing。
- V1 只做 Product、ASIN、SKU、Listing 基础能力，不扩展完整库存和利润系统。

---

## 9. 报表数据来源与导入

### 9.1 三类 V1 报表

V1 必须完整支持：

1. Campaign Report
2. Targeting Report
3. Search Term Report

Advertised Product Report 仅作为未来扩展方向记录，不属于 V1 必须实现范围。

V1 真实数据入口是用户手动上传 CSV/Excel。

定义统一 ReportSource：

- `FileUploadReportSource`：V1 完整实现。
- `ThirdPartyProviderReportSource`：只预留接口。
- `AmazonAdsApiReportSource`：只预留接口。

未来所有来源统一进入：

```text
source
 -> raw file/data
 -> ReportUpload
 -> ImportTask
 -> ImportBatch
 -> field mapping
 -> validation
 -> normalization
 -> deduplication
 -> batch persistence
 -> authoritative fact update
 -> audit and source trace
```

业务模块不得依赖具体第三方字段名。

### 9.2 存储与追溯

文件本体通过 FileStorage 保存到本地持久卷或对象存储。MySQL 保存：

- 文件元数据、地址、哈希
- ReportUpload
- ImportTask
- ImportBatch
- 行级错误
- 正式任务状态
- 标准化对象与事实数据
- 来源批次关系

Redis 只用于队列、缓存、临时进度和短期协调，不能作为正式事实来源。

历史规则：

- ReportUpload、ImportTask、ImportBatch 只追加，不覆盖。
- 重处理必须创建新的 Task 与 Batch。
- 新 Batch 可修正当前权威事实。
- 当前权威记录必须可追溯到来源 ImportBatch。
- 需要完整追溯的原始解析行，可压缩为 JSONL 放入 FileStorage；不得无条件把全部原始行重复写入 MySQL。

### 9.3 导入行为

必须支持：

- 文件级校验：无法读取、格式不支持、缺少关键表头、Profile 不匹配等；整份失败。
- 行级校验：合法行入库，错误行记录。
- 部分成功：如 100 行成功 95、失败 5，状态 `PARTIAL_SUCCEEDED`。
- 重复文件提示，但允许重新处理。
- Celery 异步解析。
- 大文件流式保存、分块读取、批量查询、批量写入。
- 禁止逐行重复查询与逐行事务提交。
- 导入状态机至少：`QUEUED/RUNNING/SUCCEEDED/PARTIAL_SUCCEEDED/FAILED`。
- 同一 ImportBatch 必须防止并发重复执行。

---

## 10. 指标事实表、权威粒度和跨币种规则

每日事实表分开：

- Campaign Daily Metric
- Targeting Daily Metric
- Search Term Daily Metric

原始指标：

- impressions
- clicks
- spend
- orders
- sales

公式由 Python 确定性计算：

- `CTR = clicks / impressions`
- `CPC = spend / clicks`
- `CVR = orders / clicks`
- `ACOS = spend / sales`
- `ROAS = sales / spend`

无有效分母时：

- 返回 `null`
- 保存原因，如 `NO_SALES`、`NO_SPEND`、`NO_CLICKS`
- 不返回 0 或无穷大冒充有效值

权威页面来源：

- Dashboard、Campaign 列表和 Campaign 详情以 Campaign Daily Metric 为主要权威粒度。
- Keyword、Product Target 分析以 Targeting Daily Metric 为权威粒度。
- Search Term 分析以 Search Term Daily Metric 为权威粒度。
- 不得将不同粒度事实表相加造成重复统计。

快照：

- Campaign Daily Metric 保留当天预算与状态快照。
- Targeting Daily Metric 保留必要的竞价与状态快照。
- 历史展示不得用对象当前值覆盖过去日期的业务状态。

币种与站点：

- V1 不直接合计不同 Marketplace 或不同 currency 的金额指标。
- 多 Marketplace 数据分别展示。
- 未来同 Tenant 内多店铺/多 Marketplace 汇总必须先明确汇率来源、汇率日期、原币金额、目标币种、Marketplace 时区和业务日期边界。

---

## 11. 目标 ACOS、异常和风险

目标 ACOS 继承：

```text
Campaign > AdvertisingProfile > Tenant
```

更具体配置优先。

异常规则由确定性规则引擎判断，AI 只解释。阈值层级：

```text
system default -> Tenant -> AdvertisingProfile -> Campaign
```

风险等级：

- LOW
- MEDIUM
- HIGH
- CRITICAL 仅预留

需要最小数据门槛。数据不足返回 `INSUFFICIENT_DATA`，不得判断为正常或异常。

至少覆盖：

- 高 ACOS
- 高花费无订单
- 点击多但转化低
- 预算过早耗尽
- 低曝光/低点击等基础可配置规则

规则必须可测试、可解释、可追溯到配置版本。

---

## 12. 多智能体、LLM 与统一 JSON Schema

V1 四类智能体：

1. 数据分析智能体
2. 异常诊断智能体
3. 预算分析智能体
4. 综合策略智能体

职责：

- Python：指标计算与数据汇总。
- 规则引擎：异常、风险与数据充分性。
- AI：解释原因、生成结构化建议。
- Service：权限、对象、状态、金额和风险校验，以及正式保存。

统一流程：

```text
authorized Selector/Service data
 -> deterministic metrics/rules
 -> AnalysisOrchestrator
 -> agent
 -> LLMProvider
 -> unified versioned JSON Schema
 -> backend validation
 -> Recommendation
```

要求：

- Agent 不自由聊天，只通过 Orchestrator 和结构化结果通信。
- 所有 Agent 共用统一、版本化 JSON Schema；可扩展专用字段，但统一外层至少包含：
  - schemaVersion
  - agentCode
  - runId
  - status
  - summary
  - evidence
  - recommendations
  - warnings
  - errors
- 统一 LLMProvider，预留真实 Provider，完整实现 MockLLMProvider。
- 测试和稳定演示默认使用 MockLLMProvider。
- 只发送当前 Tenant、已授权 Profile、本次分析所需的最少数据。
- 禁止发送密码、JWT、Refresh Token、Cookie、密钥、其他 Tenant 数据或无关完整数据库。
- AI 不得直接操作 ORM、审批状态或真实 Amazon 广告。

AgentRun 状态至少：`QUEUED/RUNNING/SUCCEEDED/FAILED`。

---

## 13. Recommendation、动作、审批和人工执行

V1 支持：

- 更新 Campaign 预算
- 暂停/启用 Campaign
- 更新 Keyword 竞价
- 暂停/启用 Keyword
- 更新 Product Target 竞价
- 暂停/启用 Product Target
- 新增普通 Keyword
- 新增 Negative Keyword

普通 Keyword 匹配：

- BROAD
- PHRASE
- EXACT

Negative Keyword 支持：

- Campaign 级
- AdGroup 级

不物理删除 Campaign、Keyword、Target，用暂停替代。

每条建议至少包含：

- actionType
- objectType
- objectId
- beforeValue
- afterValue
- reason
- evidence
- riskLevel

后端必须校验：

- JSON Schema
- Tenant/Profile 归属
- 当前对象状态
- 修改前值是否仍有效
- 金额、币种
- 预算/竞价上下限
- 用户功能与 Profile 权限
- 风险规则

失败结果不能进入正式 Action Preview。

### 13.1 单级审批

- 个人卖家 Tenant Owner 可自我确认。
- TEAM/COMPANY 中提交人不能审批自己的方案。
- 结果：`APPROVED/REJECTED/RETURNED`
- 提交人可在审批完成前撤回。
- 提交后的 ActionPreviewVersion 不可修改。
- RETURNED 后创建新版本，不覆盖旧版本。
- ApprovalRecord 只追加。

ActionPreview 状态至少：

- DRAFT
- PENDING_APPROVAL
- APPROVED
- REJECTED
- RETURNED
- WITHDRAWN

### 13.2 人工执行

审批通过后生成手工执行清单。用户在 Amazon 后台操作并逐项回填：

- SUCCESS
- FAILED
- SKIPPED
- 实际执行值
- 执行时间
- 备注
- 证据文件

批量执行允许部分成功。必须通过幂等键、唯一约束和状态检查防止重复审批与重复回填。

---

## 14. 知识中心

保留“知识中心”一级菜单并真实可用，但 V1 只实现轻量基础知识：

- 广告指标说明
- 三类报表说明
- 异常规则说明
- 优化动作说明
- 操作指南
- 常见问题

实现只读的分类、文章列表与详情，可用 seed 数据初始化。不得扩展复杂 RAG、知识图谱、自动采集或向量检索。

---

## 15. 前端架构和页面

目录：

```text
src/
├── app/
├── shared/
└── features/
    ├── auth/
    ├── tenant-context/
    ├── dashboard/
    ├── reports/
    ├── campaigns/
    ├── targeting/
    ├── search-terms/
    ├── analysis/
    ├── recommendations/
    ├── actions/
    ├── knowledge/
    └── system/
```

每个 feature 拥有自己的 pages、components、api、types、routes。

一级菜单：

1. 工作台
2. 数据中心
3. 广告分析
4. 智能优化
5. 审批执行
6. 知识中心
7. 系统管理

规则：

- Vue 路由组件前端固定注册。
- 后端返回权限/菜单结果控制显示。
- Pinia 只保存用户、Access Token、Tenant/Store/Marketplace/Profile 上下文、权限编码、菜单和必要偏好。
- 所有 HTTP 通过统一 Axios 客户端。
- Axios 处理 Access Token、`X-Tenant-ID`、刷新、requestId、401、403、超时和统一错误。
- 页面统一支持加载、正常、空数据、部分失败、完全失败、无权限。
- OpenAPI 生成或同步 TypeScript 类型。
- 不得用前端静态数据冒充未实现后端；演示固定 AI 结果只能来自 MockLLMProvider，固定业务数据只能来自 seed/fixtures。

核心页面：

- 登录
- 工作台
- 报表上传、任务、错误明细、原始文件
- Campaign 列表/详情
- Keyword/Product Target 分析
- Search Term 分析
- AI 分析任务与结果
- Recommendation
- Action Preview
- 待审批/审批记录
- 人工执行清单与回填
- 知识中心
- 用户、团队、角色、权限、Store、Profile 授权、规则配置
- 审计日志

---

## 16. 高并发、横向扩展与性能验收基线

继续使用模块化单体，不因高并发擅自拆微服务。

必须实现：

1. Django API 无状态，支持多个 Gunicorn/Django 实例。
2. 文件导入、指标计算、AI 分析、效果评估进入 Celery，不阻塞 HTTP。
3. Celery 至少拆分 `imports`、`analysis`、`maintenance` 队列，配置独立并发、超时和有限重试。
4. Redis 只做队列、缓存、进度和短期协调。
5. 分页、最大页大小、筛选、排序和必要字段投影。
6. 大文件流式/分块处理与批量入库。
7. 为 Tenant、Profile、业务日期、外部对象 ID、任务状态建立合理单列/联合索引。
8. `select_related/prefetch_related` 或等效方法消除 N+1；关键 Selector 有查询数量测试。
9. MySQL、Redis、HTTP、LLM 设置连接池、超时和有限重试。
10. 上传、任务创建、导入、审批和执行回填具备幂等性。
11. 状态转换通过 Service，使用事务、唯一约束、版本号、乐观锁或必要行锁防并发覆盖。
12. 接口限流、背压和明确过载错误；不得无限堆积。
13. 缓存键必须包含 Tenant/Profile 范围，定义 TTL 与失效策略，禁止串租户。
14. 健康检查、requestId/taskId、慢查询、接口延迟、错误率、Celery 积压和 Worker 吞吐可观察。
15. 提供 Locust 或等效压力测试脚本和可重复报告。

### 16.1 我们确定的 V1 参考验收目标

以下是“目标”，不是未测试前的能力声明：

参考环境：

- 8 vCPU
- 16 GB RAM
- SSD
- Docker Compose
- MySQL、Redis、API、Worker 可独立限制资源

API 基线：

- 300 个并发虚拟用户
- 持续 200 RPS，运行 10 分钟
- 常用读接口 p95 不高于 1 秒
- 创建异步任务类写接口 p95 不高于 1.5 秒
- 非预期错误率低于 1%
- 401、403、404、429 等预期业务响应不计入系统错误

异步并发安全：

- 同时提交 5 个、每个 100,000 行的虚构 CSV 导入任务，必须无重复批次执行、无数据串租户、无状态覆盖；记录完成时间和 Worker 吞吐，不强制虚构完成时间。
- 同时创建 20 个 Mock AI 分析任务，必须无重复 Recommendation、无状态越级、无越权对象落库。
- 对单实例与双 API 实例进行对比测试并记录吞吐变化；不能达到目标时报告瓶颈和优化方案，不得篡改结果。

---

## 17. 安全、日志、审计和保留

- 技术日志与业务审计日志分开。
- 技术日志输出 stdout/stderr，由部署平台收集。
- 审计日志写 MySQL，只追加，普通用户不能改删。
- 登录、权限、Profile 授权、上传/重处理、规则、AI、建议修改、Action Preview、审批、执行和重要配置必须审计。
- 修改类操作记录脱敏 before/after。
- 密码、JWT、Refresh Token、Cookie、LLM/第三方密钥不得进入日志、审计、仓库或前端。
- 真实密钥只通过环境变量或密钥管理；仓库只提交 `.env.example`。
- 原始报表和证据文件保留期限可配置，默认 365 天；到期可归档或删除文件，但保留元数据、ImportBatch 和审计记录。
- 审计日志长期保留并支持归档。
- 提供 `/health/live` 与 `/health/ready`。
- 记录应用版本、Git commit 和构建时间。
- 提供 MySQL 与文件备份/恢复文档。

---

## 18. 六人团队最终分工

该分工由技术方案负责人确定，作为本项目默认模块所有权。

### 成员 1：产品、需求与演示业务负责人

负责：

- 用户需求、角色、业务场景、功能边界
- 产品流程、页面原型、字段说明
- 演示故事线、演示数据语义
- 产品验收清单
- 与技术负责人确认需求变更

交付：

- PRD
- 用户流程图
- 页面原型
- 字段与业务规则清单
- 产品演示讲稿
- 产品验收清单

### 成员 2：总体架构、集成、DevOps 与技术文档负责人

负责：

- 总体架构、模块边界、数据模型和接口规范
- `config`、`core` 公共规范、`api/v1` 总路由
- Docker Compose、Nginx、Gunicorn、环境配置、健康检查
- OpenAPI、错误码、requestId、日志规范
- 性能测试方案、集成审查和最终联调
- 技术方案文档与明天的技术讲解

交付：

- 可启动基础工程
- 架构/部署/API/性能文档
- 模块接口清单
- 集成与演示检查表

### 成员 3：身份、租户、店铺与权限后端负责人

模块：

- accounts
- tenants
- permissions
- stores

交付：

- JWT 双 Token
- User/Tenant/Team/Role/Permission
- Store/Marketplace/StoreMarketplace/Profile
- Store/Profile 授权与权限合并
- 401/403/404 规则
- 相关 API、迁移、测试、审计

### 成员 4：报表、广告、产品与指标后端负责人

模块：

- reports
- advertising
- products
- analytics
- integrations/storage
- integrations/advertising_data

交付：

- 三类报表上传、异步导入、错误明细、重处理
- ReportSource/FileStorage
- 广告与产品基础模型
- 三类每日事实表、指标、异常与 Dashboard Selector
- 相关 API、迁移、fixtures、测试

### 成员 5：智能体、建议、审批、执行与审计后端负责人

模块：

- agents
- recommendations
- actions
- knowledge
- audit
- integrations/llm

交付：

- LLMProvider/MockLLMProvider
- 四类 Agent 与 AnalysisOrchestrator
- 统一 JSON Schema
- Recommendation、Action Preview、审批、执行回填、效果评估基础
- 轻量知识中心
- 审计查询
- 相关 API、迁移、测试

### 成员 6：Vue 前端、接口联调、E2E 与演示环境负责人

模块：

- frontend/src/app
- frontend/src/shared
- frontend/src/features

交付：

- 登录、上下文切换、菜单权限
- 工作台、数据中心、广告分析、智能优化、审批执行、知识中心、系统管理页面
- Axios、Pinia、OpenAPI 类型
- 页面状态、前端测试、生产构建
- 端到端联调、演示账号与演示脚本验证

协作原则：

- 成员 2 维护契约与总集成，不包揽所有业务代码。
- 成员 3/4/5 先以 OpenAPI/接口草案与成员 6 对齐，前后端并行。
- 模块所有者维护自己的迁移、测试和文档。
- 共享核心文件由成员 2 评审，避免多人无序修改。
- Codex 必须生成 `docs/team/module-ownership.md`、`interface-handoffs.md`、`development-sequence.md`。

---

## 19. 实施阶段

### Phase 0：仓库审计和主规格落库

- 检查现状
- 创建 AGENTS.md、PLANS.md
- 创建 confirmed-scope/out-of-scope
- 输出差距、风险、实施顺序
- 不进行大规模业务实现

### Phase 1：基础工程与可启动环境

- Django/Vue 工程
- MySQL/Redis/Celery/Nginx/Compose
- 统一响应、异常、requestId、OpenAPI
- health live/ready
- local/test/prod 配置
- README 启动
- smoke test

### Phase 2：认证、多租户、Store/Profile 与权限

- User/Tenant/Team/RBAC
- Store/Marketplace/Profile
- JWT 双 Token
- 权限和上下文 API
- 前端登录、选择器与菜单
- 跨 Tenant 测试

### Phase 3：广告、产品、上传与三类报表

- 模型、迁移、fixtures
- FileStorage/ReportSource
- Campaign/Targeting/Search Term 导入
- ImportTask/Batch、部分成功、重处理和追溯
- 前端数据中心与任务状态

### Phase 4：指标、异常和分析页面

- 三类事实表
- 快照、公式、目标 ACOS、异常规则
- Dashboard/Campaign/Targeting/Search Term API 与页面
- 不同粒度与币种隔离测试

### Phase 5：Agent、建议、审批、执行与审计

- MockLLMProvider、统一 Schema、四 Agent、Orchestrator
- Recommendation、Action Preview、单级审批
- 人工执行回填、基础效果评估
- 审计和知识中心
- 对应前端页面

### Phase 6：高并发与稳定性

- 幂等、并发锁、索引、查询优化、队列隔离
- 限流、超时、重试、缓存隔离
- Locust 压测和报告
- 安全审查

### Phase 7：完整验收、文档与明天演示

- 后端/前端/E2E 测试
- Docker 从零启动
- seed 演示数据
- Campaign 主演示链路
- Targeting/Search Term 验证
- 演示讲稿、逐步脚本、常见问题、完成状态
- 文档与代码一致性检查

不得因为演示优先而删除 Targeting 或 Search Term；三类报表都属于 V1，Campaign 只是主演示链路。

---

## 20. 测试与验收

必须包含：

- 后端单元测试
- 后端集成测试
- 前端组件测试
- TypeScript 类型检查
- 前端生产构建
- 至少一条浏览器端到端链路
- Docker Compose 启动测试
- README 从零运行验证
- 并发和压力测试脚本

fixtures：

```text
tests/fixtures/reports/
├── campaign-valid.csv
├── campaign-partial-errors.csv
├── targeting-valid.csv
├── search-term-valid.csv
├── duplicate-report.csv
└── unauthorized-profile-report.csv
```

必须验证：

1. 登录、刷新、退出。
2. Tenant/Store/Marketplace/Profile 切换。
3. RBAC、Profile 权限和跨 Tenant 隔离。
4. 三类报表导入。
5. 文件级失败、行级错误、部分成功、重复和重处理。
6. 指标公式、零分母、快照、不同事实粒度和币种隔离。
7. Celery 异步任务。
8. Mock Agent 合法 JSON。
9. 非法 JSON、越权对象、币种不一致、超限建议被拦截。
10. Action Preview 合法/非法状态转换。
11. 提交人不能自审、个人 Owner 自确认。
12. 版本冻结、退回新版本、重复审批和重复回填。
13. 审计只追加。
14. 页面加载、空、部分失败、失败和无权限状态。
15. Docker 与 README 可复现。

---

## 21. 文档交付

至少生成并填充真实内容：

```text
README.md
docs/
├── requirements/
│   ├── confirmed-scope.md
│   └── out-of-scope.md
├── architecture/
│   ├── technical-solution.md
│   ├── system-context.md
│   ├── module-design.md
│   ├── data-model.md
│   ├── permission-model.md
│   ├── report-import-design.md
│   ├── async-task-design.md
│   ├── ai-agent-design.md
│   ├── action-workflow.md
│   ├── security-audit-design.md
│   └── concurrency-design.md
├── api/
│   ├── api-conventions.md
│   └── error-codes.md
├── deployment/
│   ├── local-development.md
│   ├── docker-deployment.md
│   ├── production-deployment.md
│   ├── backup-and-restore.md
│   └── troubleshooting.md
├── testing/
│   ├── test-strategy.md
│   ├── acceptance-checklist.md
│   ├── performance-test-plan.md
│   └── performance-test-results.md
├── team/
│   ├── module-ownership.md
│   ├── interface-handoffs.md
│   └── development-sequence.md
├── presentation/
│   ├── technical-presentation.md
│   ├── demo-script.md
│   ├── likely-questions.md
│   ├── current-status.md
│   └── one-page-summary.md
└── ai-development-records/
    ├── prompts/
    ├── implementation-logs/
    ├── test-results/
    ├── architecture-decisions/
    └── change-summaries/
```

文档使用清晰编号，但不强制固定章节数量。

`technical-presentation.md` 必须能直接照着讲，包含：

- 需求和边界
- 完整业务闭环
- 架构、数据流和技术选型
- 权限、多租户和安全
- 三类报表与数据粒度
- 指标、异常与 AI 分工
- 审批和人工执行
- 高并发设计与诚实的测试状态
- 六人分工
- 当前已实现/未实现
- 演示流程和后续扩展

必须提供 Mermaid：

- 总体架构图
- 核心业务流程图
- Tenant/Store/Profile 实体关系
- 权限校验流程
- 报表导入时序
- 多智能体流程
- Action Preview 状态图
- 部署图
- 团队模块依赖图

`demo-script.md` 必须写明点击、输入、预期页面、后台行为、讲解词、数据文件、账号、演示前检查和故障备用步骤。

---

## 22. 明天演示主链路

使用虚构/脱敏 seed 与 fixtures：

1. 登录。
2. 展示 Tenant 并切换 Store、Marketplace、Profile。
3. 上传 Campaign 报表。
4. 查看 202 + taskId 和处理中状态。
5. Celery 完成导入。
6. 查看成功/错误行，演示一份部分成功报表。
7. 查看 Campaign 与 Dashboard 指标、快照和异常。
8. 创建 AI 分析任务。
9. MockLLMProvider 返回统一 JSON。
10. 展示 Recommendation。
11. 创建并提交 Action Preview。
12. 使用不同审批账号批准。
13. 生成人工执行清单。
14. 回填成功或失败结果。
15. 查看审计日志。
16. 演示跨 Tenant 对象访问返回 404。
17. 说明 Targeting 和 Search Term 已属于 V1 并展示对应导入/页面或测试结果。

未完整实现的内容必须诚实标记，不得用静态假页面冒充。

---

## 23. 每阶段报告格式

Codex 每阶段必须报告：

1. 本阶段目标。
2. 检查的现有文件。
3. 修改文件。
4. 新增文件。
5. 依赖变化。
6. 数据库迁移。
7. 新增接口。
8. 新增页面。
9. 更新文档。
10. 实际执行的命令。
11. 测试通过/失败数量。
12. 未执行或无法验证内容。
13. 对既有契约的影响。
14. 遗留风险。
15. 当前启动方法。
16. 当前演示链路可走到哪一步。
17. 下一阶段计划。

不得只说“完成”。

---

# 第一个 Codex 任务：Phase 0

请先阅读本文件，并执行 Phase 0。此任务禁止直接大规模生成业务代码。

具体要求：

1. 检查仓库目录、Git 状态、已有前后端代码、依赖、迁移、测试、文档、Docker 配置和可运行命令。
2. 尝试运行当前已有的后端测试、前端类型检查/构建或最小启动检查；记录真实输出。
3. 创建或更新根目录 `AGENTS.md`，将本文件中的永久规则、目录约束、测试命令、禁止事项和报告格式整理进去。
4. 创建或更新 `PLANS.md`，按 Phase 1—7 写出可执行计划、文件范围、依赖关系、验收标准和回滚风险。
5. 创建：
   - `docs/requirements/confirmed-scope.md`
   - `docs/requirements/out-of-scope.md`
   - `docs/team/module-ownership.md`
   - `docs/team/interface-handoffs.md`
   - `docs/team/development-sequence.md`
6. 输出当前仓库与目标之间的差距清单，并标记：
   - 已存在
   - 部分存在
   - 缺失
   - 需要真实报表样例才能最终验证
7. 不得声称系统已经达到任何性能目标。
8. 完成后按“每阶段报告格式”汇报，并给出 Phase 1 的准确实施任务，但不要自行开始 Phase 1。
