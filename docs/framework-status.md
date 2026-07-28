# V1 框架与能力状态

| 领域 | 状态 | 证据/说明 |
|---|---|---|
| Django/DRF/Celery 基础 | IMPLEMENTED_AND_TESTED | check、迁移、pytest、E2E |
| Vue/Router/Pinia/Axios | IMPLEMENTED_AND_TESTED | lint、typecheck、unit、build、E2E |
| MySQL/Redis/Nginx/Compose | IMPLEMENTED_NOT_FULLY_VERIFIED | Phase 1 有运行证据；M6 复验当前环境 |
| JWT 双 Token | IMPLEMENTED_AND_TESTED | 后端并发/重放测试与浏览器恢复 |
| Tenant/Store/Profile/RBAC | IMPLEMENTED_AND_TESTED | 隔离测试与浏览器四级选择 |
| 三报表导入 | BLOCKED_BY_REAL_SAMPLE | fixtures 通过；真实 Amazon 导出未验证 |
| 三事实/指标/异常 | IMPLEMENTED_AND_TESTED | Decimal/粒度/继承/规则测试 |
| Mock Agent/Recommendation | IMPLEMENTED_AND_TESTED | Schema、API 与 E2E |
| Preview/审批/执行/审计 | IMPLEMENTED_AND_TESTED | 不可变/职责分离/幂等/只追加测试 |
| 真实 LLM/Amazon API Source | RESERVED_BY_CONFIRMED_SCOPE | 只有 Adapter 边界 |
| 性能目标 | IMPLEMENTED_NOT_FULLY_VERIFIED | M6 提供计划/脚本；无能力声明 |

