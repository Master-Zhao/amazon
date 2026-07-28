# V1 模块设计

## 后端模块

| 模块 | 职责 |
|---|---|
| `core` | envelope、异常、requestId、case conversion、分页、限流、缓存键、健康 |
| `accounts` | 全局 User、JWT refresh 轮换和认证审计 |
| `tenants/stores/permissions` | Membership、四级上下文、RBAC 与数据授权 |
| `products/advertising` | 商品关系与 Sponsored Products 主数据 |
| `reports` | 上传、任务、解析、批次、行错误与重处理 |
| `analytics` | 三类事实、确定性指标、异常规则和 Selector |
| `agents/recommendations` | Orchestrator、结构化 Agent、修订和动作验证 |
| `actions` | Preview 版本、审批、人工执行证据和效果评估 |
| `knowledge/audit` | 只读知识与只追加审计 |

写调用固定为 View → Serializer → Service → ORM；复杂读由 Selector 承担；
Task 只调用 Service；Agent 不得访问 ORM。权限统一入口是
`apps.permissions.services.authorize`。

`backend/integrations/` 隔离报表来源、文件存储、LLM、Amazon 执行和监控外部
能力；当前启用 FileUpload、LocalFileStorage、MockLLM 与 ManualExecution，
其余仅保留稳定接口。

## 前端

`frontend/src/app` 负责启动、Router 和菜单；`shared` 负责 Axios、生成类型、
布局与上下文 Store；`features` 按认证、上下文、导入、广告、分析、优化、执行、
知识和审计组织。调用方向为页面 → feature API → 统一 Axios → Django。

## 契约

后端以 drf-spectacular 生成 `openapi/schema.yaml`，前端用 openapi-typescript
生成 `frontend/src/shared/api/generated/schema.d.ts`。schema 与生成类型必须在
同一变更中同步并通过差异检查。
