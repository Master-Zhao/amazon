# Amazon 广告智能优化系统 V1：Phase 1—7 实施计划

## 1. 计划状态

- 当前阶段：Phase 0 已执行文档落库，等待验收。
- 当前应用状态：没有后端、前端、依赖清单、迁移、测试、Compose 或环境示例，系统不可启动。
- 下一阶段：仅在用户明确授权后进入 Phase 1。
- 依赖顺序：`Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6 → Phase 7`。
- 纵向原则：每个阶段交付真实可运行切片，不以空模块或静态页面代替。

## 2. 全阶段公共门禁

每阶段开始前：

1. 对照 `codex_master_goal_amazon_ads_v1.md`、`AGENTS.md` 和 `docs/15-decision-log.md`。
2. 检查 Git、工作区、依赖、迁移和上阶段测试证据。
3. 不读取或复用 `amazon-ads-operations-0.1.1`。
4. 对未确认实施细节先记录决策，不将主规格降级。

每阶段结束前：

1. 运行该阶段相关测试、类型检查、构建、OpenAPI 和 Compose 检查。
2. 从干净数据库验证迁移；共享环境已有迁移只新增不修改。
3. 更新 README、决策、风险、接口、测试和当前状态文档。
4. 报告真实通过、失败、跳过及原因。

---

## Phase 1：基础工程与可启动环境

### 实现目标

建立最小但完整的 Django/Vue 模块化单体基础工程，实现本地与容器可启动、MySQL/Redis/Celery/Nginx 连通、统一 API 基础能力和健康检查。不得创建业务 Model。

### 涉及模块

- 后端：`config`、`api/v1`、`apps/core`、Celery 配置。
- 前端：`src/app`、`src/shared`，最小应用壳与健康状态页。
- 基础设施：MySQL、Redis、API、Worker、Beat、Nginx、前端构建。
- 契约：统一响应、统一异常、requestId、camelCase、OpenAPI。

### 预计修改文件

- 根目录：`.gitignore`、`.env.example`、`compose.yaml`、`README.md`。
- 后端：`backend/pyproject.toml` 或根 `pyproject.toml`、`uv.lock`、`backend/manage.py`、`backend/config/**`、`backend/api/v1/**`、`backend/apps/core/**`、`backend/tests/**`。
- 前端：`frontend/package.json`、`frontend/pnpm-lock.yaml`、`frontend/vite.config.ts`、`frontend/tsconfig*.json`、`frontend/src/app/**`、`frontend/src/shared/**`。
- 部署：`backend/Dockerfile`、`frontend/Dockerfile`、`infra/nginx/**`。
- CI 文件只在执行环境明确后创建。

### 数据库迁移

- 只产生 Django 基础迁移能力；不得创建业务域 Model。
- 自定义 User 必须在首次业务迁移前设计并于 Phase 2 首次迁移中落地，不能先迁移默认 `auth.User`。
- 验证空数据库 `migrate` 可运行；记录 Django 内置表。

### 接口交付

- `GET /health/live`
- `GET /health/ready`
- `/api/v1` 统一响应与错误示例。
- OpenAPI Schema 端点及校验命令。

### 前后端依赖

- 先冻结 Python 3.13、Node 24、Django/DRF/Celery/Vite 兼容矩阵，再生成锁文件。
- 前端只依赖健康检查和 OpenAPI 基线；不依赖业务 API。
- Celery 只交付可验证的基础任务，不伪造业务任务。

### 测试要求

- Django `check`、基础 pytest、OpenAPI 校验。
- Celery 与 Redis 最小任务往返。
- 前端 typecheck、组件/单元测试、生产构建。
- `docker compose config --quiet`、全容器启动、live/ready 探测。
- 混合开发方式启动验证。
- 检查仓库无秘密、无 `latest`、无 npm/yarn 锁文件。

### 文档要求

- 更新 README 启动、停止、测试、故障排查。
- 新增部署、本地开发、API 错误码和环境变量文档。
- 在决策日志记录兼容矩阵验证与锁定结果。

### 验收条件

- 干净环境可按 README 安装、迁移、启动并访问前后端与健康端点。
- Worker/Beat 可运行，Redis/MySQL ready 失败时 `/health/ready` 正确失败。
- 无业务 Model、空业务 API 或伪业务页面。

### 风险和回滚方式

- 风险：Python 3.13 与 Celery/驱动兼容、Windows 与 Linux 差异、镜像不稳定。
- 回滚：锁定最后通过 smoke 的依赖与镜像摘要；基础设施配置按单文件回退，不修改已发布迁移。

---

## Phase 2：认证、多租户、Store/Profile 与权限

### 实现目标

实现全局 User、Tenant/Team/RBAC、StoreMarketplace/Profile 层级、JWT 双 Token、Store/Profile 授权与前端上下文切换，形成真实隔离链路。

### 涉及模块

- `accounts`、`tenants`、`permissions`、`stores`、`audit` 最小能力。
- 前端 `auth`、`tenant-context`、`system`。
- 统一 RequestContext、权限 Service、数据范围 Selector。

### 预计修改文件

- `backend/apps/accounts/**`
- `backend/apps/tenants/**`
- `backend/apps/permissions/**`
- `backend/apps/stores/**`
- `backend/apps/audit/**` 的基础审计。
- `backend/api/v1/**`、OpenAPI Schema、seed 命令。
- `frontend/src/features/auth/**`
- `frontend/src/features/tenant-context/**`
- `frontend/src/features/system/**`
- `frontend/src/shared/http/**`、Pinia、路由守卫。

### 数据库迁移

- 首次迁移即自定义 `sys_user`。
- `sys_tenant`、Membership、Team/Member、Role/Permission/关系。
- `ads_store`、`ads_marketplace`、`ads_store_marketplace`、`ads_advertising_profile`。
- Store 与 Profile 的 User/Team 白名单授权及等级约束。
- `audit_log` 基础只追加表。
- 所有表名和唯一约束通过前缀/同 Tenant 测试。

### 接口交付

- 登录、刷新、退出、当前用户。
- Tenant 列表/切换、上下文恢复。
- Store、Marketplace、Profile 可访问列表与切换。
- 成员、Team、Role、Permission、Store/Profile 授权管理。
- 后端生成菜单/权限结果。

### 前后端依赖

- 前端所有业务路由依赖 Tenant 上下文；Store/Profile 只展示后端授权集合。
- JWT Access 内存优先，Refresh 为 HttpOnly Cookie；需完成 CSRF/CORS/SameSite/轮换/吊销细节。
- Phase 3 的所有对象必须依赖此阶段授权 Service。

### 测试要求

- 登录、刷新、退出和 Refresh 重放/吊销。
- User 多 Tenant、无 Team 个人卖家、系统角色/自定义角色。
- 直接与团队授权并集、Profile 最高等级。
- 跨 Tenant/Store/Profile 列表与详情隔离，403/404 规则。
- 并发刷新、重复授权、失效 Membership。
- 前端上下文、菜单、路由和错误状态。

### 文档要求

- 数据模型、权限模型、认证、安全、OpenAPI、错误码。
- 更新决策日志中认证细节、Profile 授权模型和权限编码。

### 验收条件

- 两个 Tenant、多个 Store/Profile 的 seed 场景可重复验证隔离。
- API 绕过前端仍不能越权；跨 Tenant 对象 ID 返回 404。
- 自定义 User 首迁移、权限审计和前端切换链路真实可用。

### 风险和回滚方式

- 风险：授权基数误建、JWT Cookie 跨域配置、权限缓存串租户。
- 回滚：权限缓存可禁用并回退到 MySQL；Model 变更只通过新迁移修正；认证变更保留兼容窗口。

---

## Phase 3：广告、产品、上传与三类报表

### 实现目标

实现 Sponsored Products 基础主数据、产品关系、FileStorage/ReportSource、Campaign/Targeting/Search Term 三类 CSV/Excel 异步导入、错误明细、重处理和血缘。

### 涉及模块

- `products`、`advertising`、`reports`
- `integrations/storage`、`integrations/advertising_data`
- Celery `imports` 队列
- 前端 `reports` 与基础广告对象浏览

### 预计修改文件

- 上述模块的 Model、migration、Service、Selector、API、Task 和 tests。
- `tests/fixtures/reports/` 中六类虚构/脱敏 fixture。
- FileStorage 本地适配器和 ReportSource 端口。
- 前端上传、任务、错误、重处理、原始文件授权下载页面。
- 三类 ReportSchema/FieldMapping 配置与 OpenAPI。

### 数据库迁移

- Product、MarketplaceCatalogItem、ProductListing。
- Campaign、AdGroup、Ad、Keyword、ProductTarget、SearchTerm。
- ReportDefinition/SchemaVersion、Upload/File、ImportTask/Batch/Error、FieldMappingVersion、RawRowManifest。
- 外部 ID 使用字符串；自然键、幂等、批次锁和同 Profile 约束。
- 不在本阶段创建指标事实表，除非作为 Phase 4 的同阶段首迁移并明确授权。

### 接口交付

- 三类报表上传，返回 202、字符串 taskId、taskUrl。
- 任务列表/详情/轮询、错误明细、重处理、授权下载。
- Campaign/Targeting/Search Term 标准化对象的基础只读 API。

### 前后端依赖

- 依赖 Phase 2 的 Tenant/StoreMarketplace/Profile 上下文和权限。
- 三种解析器共享 ReportSource、SchemaVersion、FieldMapping、批次状态机。
- 缺真实样例时使用 fixtures，页面和文档持续显示未通过真实导出验证。

### 测试要求

- 文件级失败、行级错误、完全成功、部分成功、重复和重处理。
- Profile 不匹配、越权上传、恶意文件名、MIME/魔数/大小、编码。
- 流式保存、分块读取、批量查询/写入，无逐行查询和事务。
- Celery 重试、同批次并发防重、提交后派发。
- 三类 fixture 各自的 Schema、自然键、血缘和授权测试。

### 文档要求

- 报表导入设计、字段映射、样例状态、存储与保留、异步任务设计。
- 明确“已用 fixture 验证”和“未用真实 Amazon 导出验证”。

### 验收条件

- 三类 fixture 均可真实上传、异步处理、查询结果和错误。
- 原始正文不进入 MySQL；每条标准化记录可追溯 ImportBatch。
- 重处理创建新 Task/Batch，不覆盖历史批次。

### 风险和回滚方式

- 风险：真实列名/编码/工作表/自然键不符，批次重述语义错误，大文件资源耗尽。
- 回滚：解析器和映射版本只追加；失败批次不发布权威数据；可切回上一 SchemaVersion；数据库修正用新迁移。

---

## Phase 4：指标、异常和分析页面

### 实现目标

实现三类独立每日事实表、快照、确定性指标、目标 ACOS 继承、版本化异常规则及 Dashboard/Campaign/Targeting/Search Term 页面。

### 涉及模块

- `analytics`、`advertising`、`reports`
- Celery 指标计算任务
- 前端 `dashboard`、`campaigns`、`targeting`、`search-terms`

### 预计修改文件

- 三类 DailyMetric Model/migration。
- 指标计算、异常规则、目标 ACOS Service。
- 权威粒度 Selector、查询数量测试、OpenAPI。
- 四类前端页面与 ECharts 组件。

### 数据库迁移

- CampaignDailyMetric、TargetingDailyMetric、SearchTermDailyMetric 分表。
- Campaign 预算/状态快照、Targeting 竞价/状态快照。
- AnomalyRule/Record、目标 ACOS 配置版本。
- Tenant/Profile/业务日期/外部对象 ID 索引。

### 接口交付

- Dashboard 指标与异常。
- Campaign 列表/详情/趋势。
- Keyword/Product Target 分析。
- Search Term 分析。
- 目标 ACOS 和异常规则配置。

### 前后端依赖

- 依赖 Phase 3 三类权威导入批次。
- Dashboard 只用 Campaign 粒度；Targeting/Search Term 不与 Campaign 事实相加。
- 前端金额与币种强绑定，多 Marketplace 分开展示。

### 测试要求

- CTR/CPC/CVR/ACOS/ROAS 正常、零分母、Decimal、null 原因。
- 三粒度隔离、币种隔离、历史快照不被当前值覆盖。
- 迟到/重述后权威事实与来源批次。
- ACOS 继承、异常阈值边界、INSUFFICIENT_DATA、规则版本追溯。
- Selector 查询数量和 N+1 防护。

### 文档要求

- 数据模型、粒度矩阵、公式/单位、异常规则、权威页面来源。
- 更新真实样例验证状态。

### 验收条件

- 三类指标与页面从真实后端返回，不使用静态假数据。
- 不同粒度和币种不会重复汇总。
- 所有异常由可复现规则产生，AI 未参与裁决。

### 风险和回滚方式

- 风险：事实自然键或重述更新错误、历史快照污染、页面误汇总。
- 回滚：保留批次血缘，停用新规则版本，重新从原始批次构建权威事实；不重写历史审计。

---

## Phase 5：Agent、建议、审批、执行与审计

### 实现目标

实现 MockLLMProvider、四类 Agent、Orchestrator、Recommendation/Action Preview、单级审批、人工执行回填、基础效果评估、轻量知识中心和审计查询。

### 涉及模块

- `agents`、`recommendations`、`actions`、`knowledge`、`audit`
- `integrations/llm`
- Celery `analysis`、`maintenance` 队列
- 前端 `analysis`、`recommendations`、`actions`、`knowledge`、审计页面

### 预计修改文件

- 统一 JSON Schema、LLMProvider/Mock、Orchestrator、四 Agent。
- Recommendation Revision、Preview Version、Approval、Execution、Evaluation 的 Model/Service/状态机。
- 轻量分类/文章 seed。
- 对应 API、OpenAPI、前端页面、fixtures、测试。

### 数据库迁移

- AnalysisTask/ScopeSnapshot、Agent/Version/Run/Step。
- Recommendation/Revision。
- ActionPreview/Version/Item、ApprovalRecord、ExecutionTask/Item/Record、EffectEvaluation/Snapshot。
- Knowledge 分类/文章以及必要的偏好事件基础。
- 只追加约束、幂等键、内容哈希、版本和状态并发控制。

### 接口交付

- 分析任务创建/查询/取消与结果。
- Recommendation 查看/接受/修订/拒绝。
- Preview 创建/提交/撤回，审批批准/拒绝/退回。
- 人工执行清单、逐项回填、确认。
- 效果评估、知识中心、审计查询。

### 前后端依赖

- 依赖 Phase 4 的确定性指标与异常。
- Agent 只消费冻结授权范围；Action Service 重新验证对象、before、金额、币种、权限、状态和风险。
- TEAM/COMPANY 提交人不得自批；PERSONAL Owner 可自我确认。

### 测试要求

- Mock 合法/非法 JSON、超时、限流、Provider 失败。
- Scope 越界、非法动作、币种不一致、超限值不能落正式数据。
- Revision/Version/Record 只追加。
- 全部合法/非法状态转换、重复提交/审批/回填、并发版本冲突。
- 退回创建新版本、提交人自批规则、部分执行。
- 审计 requestId/对象链路和附件权限。
- 页面全部状态与至少一条浏览器端到端闭环。

### 文档要求

- AI 架构、Schema、动作工作流、状态机、安全审计、知识边界。
- 明确 Mock 与真实 Provider 状态；不得配置真实密钥。

### 验收条件

- Mock 从 Phase 4 数据生成结构化建议，经过真实后端校验、审批和人工回填。
- 审批与执行始终引用不可变版本。
- 可查询完整审计链；Amazon 后台仍仅人工操作。

### 风险和回滚方式

- 风险：模型输出越权、状态竞争、版本内容漂移、隐私泄露。
- 回滚：禁用 AgentVersion/规则版本、切回 Mock、使新流程只读；历史只追加记录不删除；修复用新版本和新迁移。

---

## Phase 6：高并发与稳定性

### 实现目标

在不拆微服务的前提下完成幂等、锁、索引、查询优化、队列隔离、限流、超时、重试、缓存隔离、可观测性、安全审查和可重复压测。

### 涉及模块

- 全部关键 Service/Selector/Task。
- API/Gunicorn、MySQL、Redis、Celery、Nginx。
- Locust 或等效压测工具。

### 预计修改文件

- Compose 资源与多实例配置、Celery 路由和 Worker 配置。
- Service 幂等/乐观锁/必要行锁。
- Selector 索引与查询投影。
- 限流、缓存、超时、重试、指标和结构化日志。
- `tests/performance/**` 与性能报告。

### 数据库迁移

- 只新增经查询计划证据支持的索引、唯一约束和版本字段。
- 不提前分区，不引入新数据库或分布式事务。

### 接口交付

- 不新增无业务必要的 API；完善 429/过载错误、任务积压和健康就绪语义。
- 可观测接口不得泄露敏感信息。

### 前后端依赖

- 依赖 Phase 1—5 的稳定业务契约。
- 前端遵守 429、轮询退避、超时和幂等键。

### 测试要求

- 主规格参考环境下执行 300 虚拟用户、200 RPS、10 分钟目标测试并如实报告。
- 5×100,000 行虚构 CSV 并发导入。
- 20 个 Mock AI 并发任务。
- 单/双 API 实例对比。
- 队列隔离、缓存串租户、幂等、状态覆盖、连接池和故障恢复。
- 未达到目标时记录瓶颈，不修改或美化结果。

### 文档要求

- 并发设计、性能计划、环境、脚本、原始结果、瓶颈和优化。
- 安全审查、容量边界和未验证项。

### 验收条件

- 压测可重复，结果有环境和版本证据。
- 无重复批次、串租户、状态覆盖或重复 Recommendation。
- 只能声明实际测得能力，目标与结果严格分开。

### 风险和回滚方式

- 风险：优化破坏正确性、锁竞争、缓存不一致、压测环境不等价。
- 回滚：功能开关关闭缓存/优化路径，撤销未发布索引迁移或用新迁移修正；保留基线结果对比。

---

## Phase 7：完整验收、文档与演示

### 实现目标

完成从零部署、全量自动化验收、Campaign 主演示链路、Targeting/Search Term 证据、完整文档和诚实的当前状态。

### 涉及模块

- 全系统、部署、测试、seed/fixtures、文档与演示资产。

### 预计修改文件

- README 和 `docs/architecture/**`、`docs/api/**`、`docs/deployment/**`、`docs/testing/**`、`docs/presentation/**`。
- `tests/fixtures/reports/**`、seed、E2E、验收脚本。
- AI 开发记录、变更摘要、最终决策和风险状态。

### 数据库迁移

- 不计划新增业务模型；只允许修复验收发现的问题且必须新增迁移。
- 验证全新数据库与升级数据库两条路径。

### 接口交付

- 冻结 V1 OpenAPI，生成前端类型，完成破坏性变更检查。
- 不在验收阶段临时扩展范围。

### 前后端依赖

- 所有前端演示步骤必须对应真实 API、Service、数据库、Task 和审计结果。
- MockLLMProvider 与 seed/fixtures 是唯一固定演示数据来源。

### 测试要求

- 后端单元/集成、安全、前端组件、typecheck、build、OpenAPI、E2E。
- Compose 从零启动、README 逐步复现、备份/恢复演练。
- Campaign 完整链路；Targeting/Search Term 导入和页面/测试证据。
- 跨 Tenant 404、部分导入、审批职责分离、审计只追加。

### 文档要求

- 完成主规格要求的全部架构、API、部署、测试、团队、演示和 AI 开发记录。
- `technical-presentation.md` 可直接讲解；`demo-script.md` 包含点击、输入、预期、后台行为、讲解词和故障备用步骤。
- 每项标记已实现、已测试、仅预留或尚未验证。

### 验收条件

- 干净环境按 README 可启动、迁移、构建、测试和演示。
- 17 步主演示链路可重复；未完成项不以假页面掩盖。
- 文档、OpenAPI、代码和测试证据一致。

### 风险和回滚方式

- 风险：演示数据污染、文档漂移、临时修复破坏契约、环境不可复现。
- 回滚：保留已通过版本、锁文件、镜像和 seed 快照；演示失败使用文档化恢复步骤，不用静态页面冒充。

## 3. Phase 1 准确启动清单

收到明确授权后，Phase 1 按以下顺序执行：

1. 复核并同步主规格与决策日志中运行时、JWT、StoreMarketplace/Profile、三报表等已明确事项。
2. 初始化 Git（仅在用户授权或确认仓库应受 Git 管理后）。
3. 验证 Python 3.13 与指定 Django/DRF/Celery/MySQL 驱动兼容；当前机器默认 Python 3.12.4，不能直接作为目标运行时。
4. 初始化 Django 自定义 User 友好的项目骨架，但暂不创建 User 迁移或业务 Model。
5. 初始化 Vue 3/TypeScript/Vite 8/pnpm 工程。
6. 添加 MySQL 8.4、Redis 7、API、Worker、Beat、前端、Nginx Compose 服务和固定版本。
7. 实现配置分层、环境示例、统一响应/异常/requestId/camelCase/OpenAPI。
8. 实现 live/ready、Celery smoke 和最小前端联通。
9. 执行并记录后端检查、前端 typecheck/test/build、Compose config/start、健康检查。
10. 更新 README、部署、API、测试、决策与风险文档，停止在 Phase 1。
