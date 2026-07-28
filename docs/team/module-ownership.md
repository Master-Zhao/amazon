# 六人团队模块所有权

## 1. 原则

- 所有权表示交付和评审责任，不表示可以绕过契约或单独改变主规格。
- 模块所有者同时负责迁移、OpenAPI、测试、文档和跨 Tenant/Store/Profile 安全。
- 共享文件由总体架构负责人维护；业务模块通过公开 Service/Selector 交接。
- 所有人不得读取或复用隔离目录 `amazon-ads-operations-0.1.1`。

## 2. RACI

| 成员 | 主责 | 关键交付 | 必须协作 |
|---|---|---|---|
| 成员 1：产品、需求与演示 | 业务范围、角色、流程、字段、验收、演示故事 | PRD、流程图、原型、字段/规则、产品讲稿、验收清单 | 与成员 2 冻结契约；向 4/5/6 提供业务口径和演示数据 |
| 成员 2：架构、集成、DevOps、技术文档 | 总体架构、`config/core/api/v1`、Compose/Nginx/Gunicorn、OpenAPI、日志、性能、集成 | 可启动工程、架构/部署/API/性能文档、契约、集成检查表 | 评审成员 3/4/5 后端边界和成员 6 契约消费 |
| 成员 3：身份、租户、店铺、权限后端 | `accounts`、`tenants`、`permissions`、`stores` | JWT、User/Tenant/Team/RBAC、StoreMarketplace/Profile、授权、401/403/404、迁移/API/测试/审计 | 向 4/5 提供 RequestContext/授权 Service，向 6 提供上下文 API |
| 成员 4：报表、广告、产品、指标后端 | `reports`、`advertising`、`products`、`analytics`、storage/advertising_data | 三报表、FileStorage/ReportSource、广告/产品、三事实表、异常、Dashboard Selector | 使用成员 3 权限；向成员 5 提供冻结指标/异常；向 6 提供数据 API |
| 成员 5：Agent、建议、审批、执行、知识、审计后端 | `agents`、`recommendations`、`actions`、`knowledge`、`audit`、llm | MockLLMProvider、四 Agent、Schema、Recommendation、Preview、审批、回填、评估、知识、审计 | 消费成员 3 权限和成员 4 数据；向 6 提供工作流 API |
| 成员 6：Vue、联调、E2E、演示环境 | `frontend/src/app/shared/features`、E2E | 登录/上下文/菜单、全部业务页面、Axios/Pinia/OpenAPI 类型、前端测试/构建、演示验证 | 与 2 管契约，与 3/4/5 联调，不用静态假数据代替后端 |

## 3. 目录所有权

| 路径 | 主责 | 必审 |
|---|---|---|
| `codex_master_goal_amazon_ads_v1.md`、`AGENTS.md`、`PLANS.md` | 成员 2 | 成员 1 |
| `backend/config`、`backend/api/v1`、`backend/apps/core` | 成员 2 | 受影响模块所有者 |
| `backend/apps/accounts/tenants/permissions/stores` | 成员 3 | 成员 2 |
| `backend/apps/products/reports/advertising/analytics` | 成员 4 | 成员 2、3 |
| `backend/integrations/storage/advertising_data` | 成员 4 | 成员 2 |
| `backend/apps/agents/recommendations/actions/knowledge/audit` | 成员 5 | 成员 2、3 |
| `backend/integrations/llm` | 成员 5 | 成员 2 |
| `frontend` | 成员 6 | 成员 2 和对应 API 所有者 |
| `compose.yaml`、Dockerfile、`infra/nginx`、环境模板 | 成员 2 | 成员 6、相关后端所有者 |
| `tests/fixtures/reports` | 成员 4 | 成员 1、6 |
| `docs/requirements`、`docs/presentation` | 成员 1 | 成员 2、6 |
| `docs/architecture/api/deployment/testing` | 成员 2 | 对应模块所有者 |

## 4. 共享文件变更规则

- OpenAPI、公共错误码、权限编码、状态名称、表名前缀、上下文头/Cookie 发生变化时，模块所有者先提交契约变更说明。
- 迁移文件由对应 Model 所有者创建；发布后只新增，不改旧迁移。
- 前端不得自行猜测枚举或字段；后端不得在未通知成员 6 时破坏契约。
- 冲突由成员 2 组织，成员 1 对业务范围作最终确认；结果写入决策日志。
