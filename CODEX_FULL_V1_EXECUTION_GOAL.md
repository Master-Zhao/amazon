# Codex Full V1 Execution Goal
## Amazon 广告智能优化系统：一次性连续实现目标

> 本文件用于 Codex 的长期 Goal。  
> 目标：在现有仓库基础上连续完成 Amazon 广告智能优化系统 V1 的全部已确认框架与核心业务闭环，同时产出可直接讲解、演示和交接的完整文档。  
> 重要：本文件控制“如何执行”；`codex_master_goal_amazon_ads_v1.md` 控制“必须实现什么”。

---

## 1. 权威文件与优先级

开始前必须完整读取：

1. `CODEX_FULL_V1_EXECUTION_GOAL.md`
2. `codex_master_goal_amazon_ads_v1.md`
3. `AGENTS.md`
4. `PLANS.md`
5. `docs/requirements/confirmed-scope.md`
6. `docs/requirements/out-of-scope.md`
7. `docs/15-decision-log.md`
8. `docs/phase-1-report.md`
9. 当前 Git 状态、迁移、测试、OpenAPI、Compose 和前端工程

发生冲突时优先级为：

```text
本文件的执行规则
> codex_master_goal_amazon_ads_v1.md 的已确认需求
> 最新决策日志
> confirmed-scope
> AGENTS.md
> PLANS.md
> 旧历史文档
```

旧文档与主规格冲突时，不得采用旧方案。应在旧文档内标注“历史方案，已被当前主规格取代”，并同步当前有效结论。

---

## 2. 当前已知基线

已知 Phase 1 已完成并提交：

```text
a170273 feat: complete phase 1 foundation
tag: phase-1-complete
```

Phase 1 已验证：

- Python 3.13 / Django 5.2 / DRF
- Vue 3 / TypeScript / Vite
- MySQL 8.4
- Redis 7
- Celery Worker 与 Beat
- Nginx 与 Gunicorn
- local / test / prod Compose
- OpenAPI
- requestId
- `/health/live`
- `/health/ready`
- 前后端测试与生产构建
- 生产容器链路
- 浏览器基础验收

Phase 2A 认证模块可能存在未提交或部分完成改动。必须先检查并保留现有正确实现，不得回滚、覆盖或重新从零生成。

以下内容不得读取、扫描、复用、修改或提交：

- `amazon-ads-operations-0.1.1`
- `.arts/`
- 来源不明的 DOCX
- 真实 `.env`
- 任何密码、Token、Cookie、API 密钥或真实卖家数据

---

## 3. 本次总目标

在一个连续 Codex 任务中，按内部里程碑完成全部 V1 已确认内容。

不得在每个普通里程碑后等待用户确认。只有以下真正硬阻塞才允许暂停并询问：

- 必须使用但尚未提供的真实外部密钥
- 必须确认且无法用保守默认值代替的业务规则
- 数据会被不可逆删除
- Git 历史会被重写
- 真实 Amazon 报表格式无法通过脱敏 fixture 合理模拟
- 环境本身不可用且 Codex 无法修复

普通测试失败、浏览器工具失败、Docker 需重启、依赖冲突、迁移冲突、前后端接口不一致，均应自行诊断、修复、记录并继续。

不得因浏览器控制工具连接失败无限重试。最多尝试两次；之后使用：

- HTTP 烟雾测试
- 自动化 E2E 脚本
- API 集成测试
- 明确的人工浏览器验收步骤

并如实标记验证方式。

最终交付必须是：

1. 可运行工程
2. 可迁移数据库
3. 可测试前后端
4. 可通过 Docker Compose 启动
5. 可真实演示核心业务闭环
6. 所有已确认模块都有可用实现
7. 所有明确“只预留”的能力有稳定 Adapter 边界
8. 技术文档与代码一致
9. 演示文档可直接照着讲
10. 六人可按模块继续并行开发

---

## 4. “不得遗漏”强制机制

必须创建并持续更新：

```text
docs/requirements/requirement-coverage-matrix.md
```

将 `codex_master_goal_amazon_ads_v1.md` 中每一条已确认要求拆成独立行，至少包含：

- Requirement ID
- 需求描述
- 来源章节
- 负责模块
- 实现文件
- 数据库迁移
- API
- 前端页面
- 测试
- 文档
- 状态
- 验证证据
- 遗留风险

状态只允许：

- `IMPLEMENTED_AND_TESTED`
- `IMPLEMENTED_NOT_FULLY_VERIFIED`
- `RESERVED_BY_CONFIRMED_SCOPE`
- `BLOCKED_BY_REAL_SAMPLE`
- `NOT_IMPLEMENTED`

最终不得存在任何未解释的 `NOT_IMPLEMENTED`。

只有下列明确边界允许 `RESERVED_BY_CONFIRMED_SCOPE`：

- `ThirdPartyProviderReportSource`：只预留，不真实接入
- `AmazonAdsApiReportSource`：只预留，不真实调用
- Sponsored Brands / Sponsored Display：只保留扩展边界
- CRITICAL 风险等级：只保留枚举
- 跨 Marketplace / 跨币种汇总：V1 不实现
- 真实 LLM Provider：只预留接口，演示使用 MockLLMProvider
- 完整库存、采购、物流、财务：不属于 V1

缺少真实 Amazon 文件时可标记 `BLOCKED_BY_REAL_SAMPLE`，但必须同时实现：

- 脱敏 fixture
- 可配置字段映射
- 解析器接口
- 文件级与行级错误
- 可重复测试
- 后续真实样例校准说明

不得用 `FRAMEWORK_READY`、空类、`pass`、`NotImplementedError`、硬编码成功响应或纯静态页面冒充实现。

---

## 5. 必须完整实现的业务闭环

必须真实打通以下流程：

```text
用户登录
→ 刷新页面恢复登录
→ 选择 Tenant
→ 选择 AmazonStore
→ 选择 Marketplace
→ 选择 AdvertisingProfile
→ 上传 Campaign / Targeting / Search Term 报表
→ 创建异步 ImportTask
→ Celery 解析
→ 文件级与行级校验
→ 部分成功与错误明细
→ 标准化入库
→ Dashboard / Campaign / Targeting / Search Term 展示
→ 指标计算
→ 异常规则
→ 四类智能体
→ Recommendation
→ Action Preview
→ 提交审批
→ 审批通过 / 驳回 / 退回
→ 人工执行清单
→ 执行结果回填
→ 效果评估基础
→ 审计日志查询
```

演示可以使用：

- 虚构或脱敏报表
- seed 演示用户和组织数据
- MockLLMProvider
- 人工执行结果

但必须真实经过：

- Vue 页面
- Django API
- MySQL
- Redis
- Celery
- Service
- 权限检查
- 审计记录

不得用纯前端硬编码代替。

---

## 6. 认证模块

必须完成：

- 自定义 User
- 邮箱登录
- JWT Access Token
- HttpOnly Refresh Cookie
- Refresh 轮换
- Refresh 吊销
- 登录
- 刷新
- 退出
- `/auth/me`
- 用户禁用
- 演示账号 seed
- 登录与失败审计基础
- Vue 登录页
- 内存 Access Token
- 页面刷新后通过 Cookie 恢复
- 并发 401 合并为一次 refresh
- refresh 失败后退出
- Token、密码、Cookie 不进入日志

认证只证明身份；Tenant、Store、Profile、功能权限必须由数据库再次校验。

---

## 7. Tenant、团队、店铺和 Profile

必须实现：

### User / Tenant / Team

- User 为全局账号
- 一个 User 可加入多个 Tenant
- Tenant 类型：
  - PERSONAL
  - TEAM
  - COMPANY
- 前端显示“卖家空间”
- Team 为 Tenant 内可选组织
- PERSONAL 可不创建 Team
- TenantMembership
- TeamMember
- Owner / Admin 基础关系

### Store / Marketplace / Profile

```text
Tenant
→ AmazonStore
→ StoreMarketplace
→ Marketplace
→ AdvertisingProfile
```

规则：

- 一个 Tenant 可有多个 Store
- 一个 Store 只属于一个 Tenant
- 一个 Store 可关联多个 Marketplace
- Marketplace 为全局参考数据
- 一个 StoreMarketplace 可有多个 AdvertisingProfile
- Campaign、AdGroup、Ad、Keyword、ProductTarget、SearchTerm 必须追溯到 Profile

前端选择顺序：

```text
Tenant → Store → Marketplace → AdvertisingProfile
```

只有一个选项自动选择，多个允许切换。

---

## 8. RBAC 和数据权限

必须实现：

- User
- Role
- Permission
- UserRole
- 系统内置角色
- Tenant 自定义角色
- 自定义角色只能组合已有 permission code
- 系统角色不可删除，可复制

数据权限：

- Store 权限
- AdvertisingProfile 权限
- 用户直接授权
- Team 授权
- 二者取并集
- 同一 Profile 取最高等级
- Tenant Owner / Admin 拥有当前 Tenant 全 Profile 权限
- V1 无显式 DENY

Profile 等级：

- VIEW
- OPERATE
- APPROVE
- EXECUTE
- MANAGE

每个业务接口必须检查：

```text
登录身份
∩ TenantMembership
∩ 功能权限
∩ Store 范围
∩ Profile 范围
```

响应规则：

- 跨 Tenant 或无数据范围：404
- 当前 Tenant 内缺少功能权限：403
- 前端隐藏按钮不代替后端校验

必须覆盖越权测试。

---

## 9. 广告与产品模型

V1 主广告类型：

- Sponsored Products

扩展枚举：

- Sponsored Brands
- Sponsored Display

广告层级：

```text
AdvertisingProfile
→ Campaign
→ AdGroup
→ Ad
→ Keyword / ProductTarget
```

必须支持：

- Campaign
- AdGroup
- Ad
- Keyword
- ProductTarget
- SearchTerm
- 普通关键词匹配：
  - BROAD
  - PHRASE
  - EXACT
- Negative Keyword：
  - Campaign 级
  - AdGroup 级

产品：

- Product：卖家内部产品
- MarketplaceCatalogItem：
  - `(marketplace_id, asin)` 唯一
- ProductListing：
  - `(store_marketplace_id, seller_sku)` 唯一
- 一个 Product 可有多个 Listing
- 一个 ASIN 可映射多个 SKU
- Ad 主要关联 ProductListing

不实现完整库存、采购、物流和财务。

---

## 10. 报表导入

V1 完整支持：

- Campaign Report
- Targeting Report
- Search Term Report

数据来源：

```text
ReportSource
├── FileUploadReportSource：完整实现
├── ThirdPartyProviderReportSource：预留
└── AmazonAdsApiReportSource：预留
```

无论来源，统一进入：

```text
ReportUpload
→ ImportTask
→ ImportBatch
→ 字段映射
→ 校验
→ 标准化
→ 去重
→ 批量写入
→ 更新权威事实
→ 审计和血缘
```

必须实现：

- CSV / Excel
- `multipart/form-data`
- HTTP 202 + taskId
- FileStorage 抽象
- 本地持久化实现
- 文件哈希
- 文件级错误
- 行级错误
- `PARTIAL_SUCCEEDED`
- 重复提示
- 允许重处理
- 重处理创建新 Task / Batch
- 历史 Upload / Task / Batch 只追加
- 当前权威数据可由新 Batch 修正
- 权威记录可追溯来源 Batch
- 原始解析结果可压缩 JSONL 存储
- 大文件流式保存、分块读取
- 批量查询与批量写入
- 同一 ImportBatch 幂等与并发保护

缺少真实 Amazon 样例时，必须提供脱敏 fixtures：

- campaign-valid
- campaign-partial-errors
- targeting-valid
- search-term-valid
- duplicate-report
- unauthorized-profile-report

---

## 11. 每日事实、指标与异常

必须分别建立：

- CampaignDailyMetric
- TargetingDailyMetric
- SearchTermDailyMetric

不得互相相加。

权威页面：

- Dashboard / Campaign：CampaignDailyMetric
- Keyword / ProductTarget：TargetingDailyMetric
- SearchTerm：SearchTermDailyMetric

原始指标：

- impressions
- clicks
- spend
- orders
- sales

确定性公式：

- CTR = clicks / impressions
- CPC = spend / clicks
- CVR = orders / clicks
- ACOS = spend / sales
- ROAS = sales / spend

分母无效：

- 返回 null
- 保存原因
- 不返回 0 或 Infinity

快照：

- Campaign 日指标保存预算和状态快照
- Targeting 日指标保存竞价和状态快照
- 历史展示不得使用当前值覆盖历史值

目标 ACOS：

```text
Campaign > AdvertisingProfile > Tenant
```

异常阈值：

```text
system default > Tenant > Profile > Campaign
```

风险：

- LOW
- MEDIUM
- HIGH
- CRITICAL 预留

数据不足：

- `INSUFFICIENT_DATA`

不同 Marketplace 或不同 currency 不得直接汇总金额。

---

## 12. 多智能体

必须实现：

- AnalysisOrchestrator
- Data Analysis Agent
- Anomaly Diagnosis Agent
- Budget Analysis Agent
- Strategy Agent
- LLMProvider
- MockLLMProvider
- 真实 Provider 接口边界

职责：

- Python：计算指标
- 规则引擎：判定异常
- AI：解释和建议
- Service：校验并保存正式业务结果

Agent 不得直接操作 ORM。

所有 Agent 使用统一、版本化 JSON Schema，至少包含：

- schemaVersion
- agentCode
- runId
- status
- summary
- evidence
- recommendations
- warnings
- errors

后端必须校验：

- Schema
- Tenant 归属
- Profile 归属
- 当前值
- 状态
- 金额
- 币种
- 预算 / 竞价限制
- 风险
- 权限

AI 只能接收当前任务最少授权数据，不能接收密码、Token、Cookie、密钥、其他 Tenant 数据。

---

## 13. Recommendation、Action Preview、审批和执行

必须支持动作：

- UPDATE_CAMPAIGN_BUDGET
- ENABLE_CAMPAIGN
- PAUSE_CAMPAIGN
- UPDATE_KEYWORD_BID
- ENABLE_KEYWORD
- PAUSE_KEYWORD
- UPDATE_TARGET_BID
- ENABLE_TARGET
- PAUSE_TARGET
- ADD_KEYWORD
- ADD_NEGATIVE_KEYWORD

不物理删除 Campaign、Keyword、Target。

每条建议包含：

- actionType
- objectType
- objectId
- beforeValue
- afterValue
- reason
- evidence
- riskLevel

单级审批：

- PERSONAL Tenant Owner 可自我确认
- TEAM / COMPANY 提交人不能审批自己
- APPROVED
- REJECTED
- RETURNED
- 提交完成前可撤回
- 提交后的 ActionPreviewVersion 不可修改
- 退回创建新版本
- ApprovalRecord 只追加

审批通过后生成手工执行清单。

执行回填：

- SUCCEEDED
- FAILED
- SKIPPED
- 实际执行值
- 执行时间
- 备注
- 证据文件
- 批量允许部分成功

必须实现效果评估基础任务和结果模型。

---

## 14. 知识中心

V1 保留“知识中心”一级菜单并实现基础内容：

- 指标说明
- 异常规则说明
- 操作指南
- 常见问题
- 优化动作说明

不实现：

- 复杂 RAG
- 知识图谱
- 自动网络采集
- 向量平台

---

## 15. 前端

目录：

```text
src/
├── app/
├── shared/
└── features/
```

features：

- auth
- tenant-context
- dashboard
- reports
- campaigns
- targeting
- search-terms
- analysis
- recommendations
- actions
- knowledge
- system

一级菜单：

- 工作台
- 数据中心
- 广告分析
- 智能优化
- 审批执行
- 知识中心
- 系统管理

必须实现真实页面：

- 登录
- Tenant / Store / Marketplace / Profile 选择
- Dashboard
- 报表上传
- 导入任务
- 错误明细
- Campaign 列表与详情
- Targeting
- Search Term
- 分析任务
- Recommendation
- Action Preview
- 待审批与审批记录
- 人工执行清单
- 执行回填
- 审计日志
- 角色与授权基础管理
- 知识中心基础页面

每个页面包含：

- loading
- normal
- empty
- partial failure
- failure
- forbidden

所有请求经过统一 Axios 客户端。

OpenAPI 作为契约，生成 TypeScript 类型。

不得用静态假业务结果冒充后端。

---

## 16. API 约定

- REST
- `/api/v1`
- JSON
- 统一：
  - code
  - message
  - data
  - requestId
- 文件：multipart/form-data
- 异步：HTTP 202 + taskId
- HTTP 语义状态码
- Python / DB：snake_case
- API / TypeScript：camelCase
- ID：字符串
- 金额：Decimal 字符串 + currency
- 操作时间：UTC
- API 时间：ISO 8601
- 广告指标日期：Profile 所在站点本地业务日期

调用链：

```text
View → Serializer → Service → ORM
View → Selector → ORM
Celery Task → Service
```

V1 不强制 Repository。

外部能力必须使用 Adapter。

---

## 17. 安全、日志和审计

必须实现：

- 技术日志与业务审计分离
- requestId / taskId
- 审计只追加
- 关键权限、导入、规则、AI、建议、审批、执行、配置操作审计
- 修改操作保存脱敏 before / after
- 密码、Token、Cookie、密钥不得写日志
- 跨 Tenant 缓存隔离
- 密钥通过环境变量或密钥管理
- 仓库只提交 `.env.example`
- 原始文件与执行证据保留期限可配置
- 到期可归档或删除文件
- 元数据和审计长期保留

---

## 18. 高并发与可扩展

必须实现架构和验证能力：

- 无状态 Django API
- 多 Gunicorn 实例可扩容
- Celery 队列：
  - default
  - imports
  - analysis
  - maintenance
- 重任务异步
- 列表分页
- 流式文件
- 分块解析
- 批量写入
- 联合索引
- 避免 N+1
- Selector
- 数据库 / Redis / HTTP / LLM 连接超时
- 有限重试
- 幂等键
- 唯一约束
- 乐观锁或必要行锁
- 防重复审批
- 防重复执行
- 限流
- 背压
- 缓存 TTL 和失效
- Tenant / Profile 缓存键隔离
- 健康检查
- 慢查询
- API 延迟
- 错误率
- Celery 积压
- Worker 吞吐监控基础
- 压测脚本

性能目标基线：

- 参考环境：8 核、16GB、SSD
- 300 并发虚拟用户
- 持续 200 RPS，10 分钟
- 常用读接口 p95 ≤ 1 秒
- 异步任务创建接口 p95 ≤ 1.5 秒
- 非预期错误率 < 1%
- 同时 5 个、每个 10 万行导入任务
- 同时 20 个 Mock AI 任务

不得虚构达到目标。必须保存真实测试环境、结果和瓶颈；未达到时如实报告。

---

## 19. 部署

必须保留并持续验证：

- local / test / prod
- MySQL 8.4
- Redis 7
- Django / Gunicorn
- Celery Worker
- Celery Beat
- Vue production build
- Nginx
- 持久卷
- 独立迁移步骤
- `/health/live`
- `/health/ready`
- 版本号
- Git SHA
- 构建时间
- 备份恢复说明
- 常见故障排查

---

## 20. 测试

必须包含：

- 后端单元测试
- 后端集成测试
- MySQL 集成测试
- 前端单元测试
- lint
- typecheck
- production build
- API 集成测试
- Celery 测试
- 权限隔离测试
- 状态机合法 / 非法转换
- Mock AI Schema 测试
- 非法 JSON
- 越权对象
- 超限建议
- 导入正常 / 部分错误 / 重复 / 越权
- 至少一条自动化浏览器 E2E
- Docker Compose 启动验证
- README 从零启动验证
- 压测脚本与报告

测试数据只能虚构或脱敏。

---

## 21. 文档

代码与文档同步完成。至少包括：

```text
README.md
docs/requirements/confirmed-scope.md
docs/requirements/out-of-scope.md
docs/requirements/requirement-coverage-matrix.md
docs/architecture/technical-solution.md
docs/architecture/system-context.md
docs/architecture/module-design.md
docs/architecture/data-model.md
docs/architecture/permission-model.md
docs/architecture/async-task-design.md
docs/architecture/ai-agent-design.md
docs/architecture/concurrency-design.md
docs/api/api-conventions.md
docs/api/error-codes.md
docs/deployment/local-development.md
docs/deployment/docker-deployment.md
docs/deployment/production-deployment.md
docs/deployment/backup-and-restore.md
docs/deployment/troubleshooting.md
docs/testing/test-strategy.md
docs/testing/acceptance-checklist.md
docs/testing/performance-test-plan.md
docs/team/module-ownership.md
docs/team/interface-handoffs.md
docs/team/development-sequence.md
docs/presentation/technical-presentation.md
docs/presentation/demo-script.md
docs/presentation/likely-questions.md
docs/presentation/one-page-summary.md
docs/framework-status.md
docs/final-v1-report.md
docs/ai-development-records/
```

必须提供 Mermaid：

- 总体架构图
- 业务闭环
- 核心 ER
- 权限流程
- 报表导入时序
- Agent 流程
- 审批状态机
- 部署图
- 团队依赖图

`technical-presentation.md` 必须能直接用于讲解。

`demo-script.md` 必须逐步写：

- 点击哪里
- 输入什么
- 页面显示什么
- 后端发生什么
- 演示时说什么
- 异常处理
- 演示账号
- fixture 路径
- 演示前检查命令

---

## 22. 六人分工文档

必须按照以下默认归属更新团队文档：

1. 产品需求、原型、产品讲解和演示故事
2. 总体架构、集成、DevOps、技术文档和技术讲解
3. 认证、Tenant、Team、Store、Profile、RBAC 和数据权限
4. 报表、广告模型、产品模型、指标、异常和数据中心
5. Agent、Recommendation、Action Preview、审批、执行、知识中心和审计
6. Vue 前端、OpenAPI 联调、E2E 和演示

必须写清：

- 模块所有权
- API 交接
- 数据契约
- 开发顺序
- 冲突文件
- 验收责任

---

## 23. 内部连续执行里程碑

Codex 必须在一次任务内按顺序执行，但不需要等待用户确认：

### M0：状态保护与认证收口

- 检查 Git
- 保留 Phase 2A 已有改动
- 完成认证
- 测试
- 提交

提交：

```text
feat: complete authentication
```

### M1：Tenant、Store、Profile、RBAC

- 模型
- 迁移
- Service
- API
- 权限
- 前端选择
- 测试
- 文档

提交：

```text
feat: implement tenant store profile permissions
```

### M2：报表与广告数据

- 三类报表
- FileStorage
- ReportSource
- 导入任务
- 批次
- 错误
- 广告与产品模型
- fixtures
- 测试

提交：

```text
feat: implement advertising report imports
```

### M3：指标、异常和分析页面

- 三事实表
- 指标
- 快照
- ACOS 继承
- 异常规则
- Dashboard
- Campaign / Targeting / Search Term
- 测试

提交：

```text
feat: implement advertising analytics
```

### M4：Agent 与优化闭环

- 四 Agent
- Orchestrator
- MockLLM
- JSON Schema
- Recommendation
- Action Preview
- 审批
- 执行
- 效果评估
- 审计
- 测试

提交：

```text
feat: implement optimization workflow
```

### M5：完整前端和 E2E

- 所有页面
- 权限菜单
- 页面状态
- OpenAPI 类型
- 自动化 E2E
- 演示链路

提交：

```text
feat: complete v1 frontend workflow
```

### M6：并发、部署、文档与最终验收

- 幂等与锁
- 索引与查询优化
- 限流
- 缓存
- 压测
- 文档
- 演示脚本
- 从零启动
- 最终覆盖矩阵

提交：

```text
chore: finalize v1 delivery
```

每个里程碑必须：

1. 只提交自己产生的已知文件
2. 运行相关迁移
3. 运行相关测试
4. 更新 OpenAPI
5. 更新必要文档
6. 更新覆盖矩阵
7. 创建 Git 提交
8. 保持系统可启动
9. 继续下一个里程碑

---

## 24. 失败与时间控制

不得在同一失败动作上无限重试。

规则：

- 浏览器工具：最多两次
- 同一命令无新信息：最多两次
- Docker 启动失败：诊断后最多两次
- 依赖安装失败：修复锁文件或网络后最多两次
- 无法验证：记录 `IMPLEMENTED_NOT_FULLY_VERIFIED`，继续完成其他模块

不能为了赶时间：

- 跳过迁移
- 删除测试
- 降低权限
- 用前端假数据
- 硬编码成功
- 把未实现写为完成
- 修改主需求
- 引入未确认基础设施

优先级：

1. 系统可启动
2. 数据不串租户
3. 核心闭环可演示
4. 所有需求有实现位置
5. 测试
6. 文档
7. 性能优化

但最终报告必须如实披露未完成项。

---

## 25. 最终验收

最终必须实际执行并记录：

### 后端

- `uv sync --project backend --frozen`
- Django check
- makemigrations check
- migrate
- 全量 pytest
- MySQL 集成测试
- OpenAPI 生成与验证

### 前端

- pnpm frozen install
- lint
- typecheck
- unit test
- production build
- OpenAPI 类型生成
- 自动化 E2E

### 容器

- 三套 Compose 静态检查
- local 启动
- prod 启动
- MySQL / Redis 健康
- Worker / Beat 健康
- Nginx / Gunicorn
- health live / ready
- 核心业务 API
- 完整演示链路

### 数据与安全

- 跨 Tenant 404
- Tenant 内功能越权 403
- Profile 权限
- 缓存隔离
- 日志无密码 / Token / Cookie / 密钥
- 审计只追加
- 幂等
- 重复审批 / 重复执行防护

### 演示

- 登录
- 上下文选择
- Campaign 正常报表
- 部分错误报表
- Dashboard
- 异常
- Mock AI
- Recommendation
- Action Preview
- 审批
- 执行回填
- 审计

---

## 26. 最终报告格式

完成后只输出：

1. 最终 Git 提交与标签
2. 可启动命令
3. 演示账号与 fixture 使用方式
4. 已实现业务闭环
5. Requirement Coverage Matrix 汇总
6. 数据库迁移
7. API
8. 前端页面
9. 后端测试结果
10. 前端测试结果
11. E2E 结果
12. Docker 与生产验证
13. 性能测试结果
14. 安全和权限验证
15. 文档清单
16. 六人分工
17. `RESERVED_BY_CONFIRMED_SCOPE` 项
18. `BLOCKED_BY_REAL_SAMPLE` 项
19. 未完成或未验证项
20. 风险与下一步

不得只回复“已完成”。

---

## 27. 完成条件

只有同时满足以下条件，才能声称“V1 完整框架已完成”：

- 所有已确认需求已进入覆盖矩阵
- 无未解释的 `NOT_IMPLEMENTED`
- 核心业务闭环真实运行
- 三类报表框架真实可导入脱敏 fixture
- 权限与跨 Tenant 隔离真实测试
- Mock AI 到审批执行真实闭环
- 前端核心页面真实调用后端
- Docker 可启动
- 测试结果真实
- 文档与代码一致
- 演示脚本可执行

真实 Amazon 报表、真实第三方服务、真实 Amazon API、真实 LLM 和生产级性能未验证时，必须如实说明，不得阻塞已确认的 V1 框架交付，也不得伪装为已经完成。
