# Amazon 广告智能优化系统 V1：长期工程规则

本文件适用于仓库根目录及全部子目录。任何自动化工具、开发者或审阅者在读取、修改、测试或交付前都必须遵守。

## 1. 规格优先级与阶段边界

1. 根目录 `codex_master_goal_amazon_ads_v1.md` 是当前唯一主需求、技术架构、实施边界、团队分工和验收规格。文件名虽不是全大写，但不得复制出第二份主规格。
2. `docs/15-decision-log.md` 记录主规格未完全确定的实施细节。主规格已明确的事项不得被旧文档中的“待确认”描述降级。
3. 发生冲突时按以下顺序处理：主规格中的明确要求 → 已确认决策 → 本文件 → 其他设计文档。必须记录冲突并同步文档，不能静默采用实现假设。
4. 严格按 `PLANS.md` 的 Phase 1—7 顺序实施。未明确授权进入下一阶段时立即停止。
5. 每阶段优先完成一条真实、可测试的纵向链路，不先生成大量空目录、空类、空接口、静态假页面或硬编码成功结果。
6. 当前根目录中的 `amazon-ads-operations-0.1.1` 是隔离目录：不得读取其业务内容，不得修改、移动、删除、扫描测试、复用依赖或复制代码。

## 2. 固定技术栈

### 后端

- Python 3.13
- Django 5.2 LTS
- Django REST Framework 3.16.x
- Celery 5.6.x
- MySQL 8.4 LTS
- Redis 7.x
- Gunicorn
- `pyproject.toml` + `uv.lock`

### 前端

- Node.js 24 LTS
- Vue 3、TypeScript、Vite 8.x
- Vue Router、Pinia、Axios、ECharts
- pnpm
- `package.json` + `pnpm-lock.yaml`

### 部署与契约

- Nginx、Docker Compose、OpenAPI
- `local / test / prod` 三套配置
- 全容器启动和 MySQL/Redis 容器加本地应用的混合开发
- 禁止 `latest` 依赖或镜像标签；禁止混用 npm、yarn、pnpm
- 核心版本升级必须先通过兼容验证并记录 ADR

## 3. 目标目录与所有权

目录在对应阶段按需创建，不得提前生成空壳：

```text
backend/
  config/
  api/v1/
  apps/
    core/
    accounts/
    tenants/
    permissions/
    stores/
    products/
    reports/
    advertising/
    analytics/
    agents/
    recommendations/
    actions/
    knowledge/
    audit/
  integrations/
    storage/
    llm/
    advertising_data/
  tests/
frontend/
  src/
    app/
    shared/
    features/
infra/
  nginx/
docs/
tests/fixtures/reports/
```

- 每个业务模块拥有其 Model、迁移、Service、Selector（需要时）、API、权限、测试和模块文档。
- `core` 只放真正通用的响应、异常、requestId、时间、审计与基础类型，不得成为业务杂物箱。
- 跨模块写操作只能调用模块公开 Service；复杂只读查询使用 Selector。
- OpenAPI 是前后端契约来源，TypeScript 类型必须由契约生成或受控同步。

## 4. 实施门槛

在依赖事项没有在 `docs/15-decision-log.md` 标为“已确认”或由主规格明确覆盖前，不得实现相关 Model、迁移、接口或页面。特别检查：

- Store、Marketplace、StoreMarketplace、AdvertisingProfile 基数和归属。
- Sponsored Products 与 Campaign/Targeting/Search Term 三类报表的字段、粒度和真实样例验证状态。
- 三类 Daily Metric 事实模型、自然键、迟到与重述细节。
- SKU 唯一范围以及 ASIN、Product、Listing 关系。
- Action Preview 动作 Schema、执行证据、漂移和部分成功细节。
- 认证安全细节、运行时兼容矩阵和锁文件。
- 文件大小、编码、Excel 工作表、保留与清理细节。

“需要真实样例最终验证”不是降低主规格范围；可先使用虚构/脱敏 fixtures 和可配置映射，但必须持续标记未通过真实导出验证。

## 5. 后端规则

- Django 首次初始化即使用自定义 User；User 是全局账号且不含 `tenant_id`。
- User 与 Tenant 通过 TenantMembership 关联；Team 可选，不为个人卖家创建虚拟 Team。
- 写调用链：`DRF View → Serializer → Service → Django ORM → MySQL`。
- 复杂读取：`DRF View → Selector → Django ORM → MySQL`。
- 异步入口：`Celery Task → Service`。
- View、Task、Agent 不得直接修改核心状态；所有状态转换由 Service/状态机服务执行。
- 所有受保护操作必须同时校验认证、有效 TenantMembership、功能权限、Store 权限、Profile 权限、对象 Tenant/Store/Profile 归属和状态守卫。
- 跨 Tenant 或完全越出数据范围返回 404；当前范围内缺动作权限返回 403。
- 数据库表名只允许 `sys_`、`ads_`、`report_`、`analytics_`、`ai_`、`action_`、`knowledge_`、`audit_`、`file_` 前缀。
- Amazon 外部 ID 使用字符串；金额使用 Decimal；时间以 UTC 存储；业务日期保留 Marketplace 语义。
- 已在共享环境执行的迁移不得修改，只能新增迁移。
- 状态写入、不可变版本、审批/执行记录和 AuditLog 应处于同一事务边界；任务在事务提交后派发。

## 6. 前端规则

- 调用链：`Vue 页面 → 业务 API 模块 → Axios 统一客户端 → Django REST API`。
- 当前上下文顺序固定为 `Tenant → AmazonStore → Marketplace → AdvertisingProfile`。
- 菜单、路由守卫和按钮隐藏只改善体验，不能替代后端授权。
- Pinia 不保存可由服务器权威恢复的长期业务事实。
- 所有数据页处理加载、刷新、空数据、部分失败、完全失败、无权限和版本冲突。
- 所有金额展示 currency；不同 Marketplace 或 currency 不直接相加。
- 不使用前端静态数据冒充未实现后端；固定 AI 演示结果只能来自 MockLLMProvider，业务演示数据只能来自 seed/fixtures。

## 7. AI、数据、审计与安全边界

- 指标、金额、权限、状态转换、异常和确定性规则由代码裁决，不由 LLM 裁决。
- 所有模型调用经过 LLMProvider；测试和稳定演示使用 MockLLMProvider，不配置真实模型密钥。
- Agent 只读取 Orchestrator 授予的最小数据范围，通过统一版本化 JSON Schema 通信；不得直接访问 ORM、相互自由调用或写正式业务数据。
- 不保存或展示模型隐藏思维过程。
- V1 不调用真实 Amazon Ads API、第三方广告数据商或自动修改广告。
- CSV、Excel、截图和附件正文不进入 MySQL；MySQL 只保存元数据、哈希、位置和血缘。
- ReportUpload、ImportTask、ImportBatch 以及 RecommendationRevision、ActionPreviewVersion、ApprovalRecord、ExecutionRecord、AuditLog 按主规格保持只追加语义。
- Redis 仅用于 Celery、短期缓存、短锁和可恢复进度，不得成为审批、执行或审计唯一存储。
- 密码、JWT、Refresh Token、Cookie、密钥、真实账号和未脱敏报表不得进入仓库或日志。

## 8. 明确禁止事项

- 不引入微服务、Kafka、Kubernetes、Elasticsearch、复杂 RAG、知识图谱、向量平台、自动网络采集、复杂事件总线或分布式事务框架。
- 不完整实现 Sponsored Brands、Sponsored Display、库存、采购、物流、订单或财务系统。
- 不实现跨 Tenant 汇总、多级审批或跨币种直接汇总。
- 不物理删除 Campaign、Keyword、Target 以替代暂停。
- 不修改未知用途文件，不覆盖用户变更，不进入隔离目录。
- 不虚构测试、性能、QPS、模型效果、广告收益、在线用户数或启动状态。
- 不用 TODO、空接口、静态页面、假数据响应或占位代码宣称链路已完成。

## 9. 标准检查命令

以下是工程创建后的标准命令；仅当对应文件存在时执行。每次交付必须记录实际命令和真实结果：

```powershell
uv sync --frozen
uv run python backend/manage.py check
uv run python backend/manage.py makemigrations --check --dry-run
uv run python backend/manage.py migrate --check
uv run pytest backend

pnpm --dir frontend install --frozen-lockfile
pnpm --dir frontend typecheck
pnpm --dir frontend test
pnpm --dir frontend build

docker compose config --quiet
docker compose up -d --build
docker compose ps
```

还必须按阶段运行 OpenAPI 校验、生成类型差异检查、浏览器 E2E、迁移从零执行、健康检查和相关安全/并发测试。当前 Phase 0 没有工程清单，上述项目级检查不可执行；不得把“计划命令”报告为“已执行”。

## 10. 完成标准

一次变更只有同时满足以下条件才可报告完成：

1. 范围属于当前获授权阶段。
2. 代码、迁移、API、页面、测试和文档状态一致。
3. 相关测试、类型检查、构建、OpenAPI 和 Compose 检查已执行；未执行项写明原因。
4. Tenant/Store/Profile 隔离、权限、状态、幂等、并发和只追加不变量有相应测试。
5. 没有秘密、真实账号、未脱敏报表或真实外部调用。
6. 当前阶段结束时系统可启动、可迁移、可测试；如尚未建立工程，必须明确报告不可启动。

## 11. 每阶段报告格式

每阶段至少报告：

1. 本阶段目标
2. 检查的现有文件
3. 修改文件
4. 新增文件
5. 依赖变化
6. 数据库迁移
7. 新增接口
8. 新增页面
9. 更新文档
10. 实际执行的命令
11. 测试通过/失败/跳过数量
12. 未执行或无法验证内容
13. 对既有契约的影响
14. 遗留风险
15. 当前启动方法
16. 当前演示链路可走到哪一步
17. 下一阶段计划

不得只写“完成”，也不得提前开始下一阶段。
