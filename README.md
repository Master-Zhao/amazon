# Amazon 广告智能优化系统 V1

本项目目标是建设一套面向 Amazon 个人、团队和公司卖家的、可审计且由人工控制的广告智能优化系统。系统通过三类报表导入、确定性指标与异常、受控 Agent、Recommendation、Action Preview、单级审批、人工执行回填和基础效果评估形成闭环。

V1 不连接真实 Amazon Advertising API，不允许 AI 自动修改广告。经过批准的动作只生成待人工执行清单。

## 当前唯一主规格

根目录 [codex_master_goal_amazon_ads_v1.md](codex_master_goal_amazon_ads_v1.md) 是当前唯一主需求、架构、边界、分工和验收规格。长期工程规则见根目录 `AGENTS.md`，实施计划见 `PLANS.md`。

## 已确认核心范围

- 技术栈：Python 3.13、Django 5.2 LTS、DRF 3.16.x、Celery 5.6.x、MySQL 8.4 LTS、Redis 7.x；Node 24 LTS、Vue 3、TypeScript、Vite 8.x、pnpm。
- 架构：前后端分离的模块化单体，OpenAPI 契约，Docker Compose + Nginx。
- 上下文：Tenant → AmazonStore → Marketplace → AdvertisingProfile。
- 权限：RBAC + Store/Profile 白名单授权，Profile 等级为 VIEW/OPERATE/APPROVE/EXECUTE/MANAGE。
- 报表：Campaign、Targeting、Search Term 三类 CSV/Excel 手工上传与异步导入。
- 广告：V1 完整支持 Sponsored Products。
- AI：四类 Agent 仅通过 Orchestrator 和 LLMProvider；测试/演示使用 MockLLMProvider。
- 正式动作：Recommendation → Action Preview → 单级 Approval → 人工 Execution。

详细范围见 [confirmed-scope.md](docs/requirements/confirmed-scope.md)，明确排除见 [out-of-scope.md](docs/requirements/out-of-scope.md)。

## 当前状态

Phase 0 已完成仓库审计和治理文档落库。

当前仓库没有 Django 工程、Vue 工程、依赖清单、数据库迁移、测试、Dockerfile、Compose 或环境示例，因此：

- 系统当前不能启动。
- 后端测试、前端类型检查/构建和 E2E 当前不可执行。
- 当前演示只能展示需求、架构、差距和实施计划，不能执行登录或任何业务链路。
- 尚未使用真实 Amazon 导出报表验证任何 Schema、粒度或解析行为。
- 尚未执行性能测试，不能声明达到并发、QPS 或延迟目标。

完整差距见 [gap-analysis.md](docs/requirements/gap-analysis.md)，实际命令与结果见 [phase-0-audit.md](docs/phase-0-audit.md)。

## 文档导航

| 文档 | 内容 |
|---|---|
| [项目总览](docs/00-project-overview.md) | 旧架构设计总览，部分内容待按主规格同步 |
| [项目范围](docs/01-project-scope.md) | 旧 V1a—V1d 范围，和三报表主规格存在差异 |
| [业务流程](docs/02-business-workflow.md) | 端到端业务闭环 |
| [领域模型](docs/03-domain-model.md) | 候选领域边界与关系 |
| [数据库设计](docs/04-database-design.md) | 候选逻辑表，部分事实/权限关系待同步 |
| [权限模型](docs/05-permission-model.md) | RBAC 与隔离设计，Profile 等级授权待同步 |
| [状态机](docs/06-state-machines.md) | 导入、分析、建议、审批、执行和评估状态 |
| [API 规范](docs/07-api-conventions.md) | REST、错误、异步、幂等、OpenAPI |
| [后端架构](docs/08-backend-architecture.md) | Django 模块与职责 |
| [前端架构](docs/09-frontend-architecture.md) | Vue 模块、路由与页面状态 |
| [运行基线](docs/10-runtime-baseline.md) | 旧待确认记录；版本已由主规格明确，仍需兼容实测 |
| [AI 架构](docs/11-ai-agent-architecture.md) | Agent、Orchestrator、LLM 边界 |
| [测试策略](docs/12-testing-strategy.md) | 测试分层和关键场景 |
| [验收标准](docs/13-v1-acceptance-criteria.md) | 旧验收清单，后续需按三报表同步 |
| [风险登记](docs/14-risk-register.md) | 业务与技术风险 |
| [决策日志](docs/15-decision-log.md) | 主规格同步确认和剩余实施细节 |
| [团队所有权](docs/team/module-ownership.md) | 六人职责与目录所有权 |
| [接口交接](docs/team/interface-handoffs.md) | 跨模块/前后端契约 |
| [开发顺序](docs/team/development-sequence.md) | Phase 1—7 团队协作顺序 |

## 目录隔离

根目录 `amazon-ads-operations-0.1.1` 不属于当前项目代码基础。未经另行明确授权，不得读取其业务内容，不得修改、移动、删除、测试扫描或复用。
