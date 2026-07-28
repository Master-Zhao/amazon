# V1 Framework Baseline 状态

| 领域 | 状态 | 证据/说明 |
|---|---|---|
| Django/DRF/Celery | IMPLEMENTED_AND_TESTED | check、无迁移差异、103 tests、Task → Service |
| Vue/Router/Pinia/Axios | IMPLEMENTED_AND_TESTED | lint、typecheck、10 files/33 tests、build、E2E |
| MySQL/Redis/Nginx/Compose | IMPLEMENTED_AND_TESTED | M6 7 服务 healthy；本次 3 套静态检查 |
| JWT 与 Tenant/Store/Profile/RBAC | IMPLEMENTED_AND_TESTED | 隔离/重放测试和浏览器恢复/四级上下文 |
| 三报表导入 | BLOCKED_BY_REAL_SAMPLE | 虚构 CSV/XLSX 与流式输出通过；真实导出未验证 |
| 三事实/指标/异常 | IMPLEMENTED_AND_TESTED | Decimal、粒度、继承、规则和 Task 委托测试 |
| Mock Agent/11 类 Recommendation | IMPLEMENTED_AND_TESTED | schema + 11 类确定性 Service 测试；逐类 E2E 为 backlog |
| Preview/退回/审批/执行/审计 | IMPLEMENTED_AND_TESTED | 冻结、只追加、证据、幂等和基础效果评估 |
| 限流/缓存/监控框架 | IMPLEMENTED_NOT_FULLY_VERIFIED | Tenant 隔离自动测试；生产多实例/exporter/告警未验证 |
| 真实 LLM/Amazon/第三方 | RESERVED_BY_CONFIRMED_SCOPE | 正式 Adapter 接口存在但不联网 |
| 正式容量/TLS/备份恢复 | IMPLEMENTED_NOT_FULLY_VERIFIED | 计划与命令存在，生产等价验证未执行 |

矩阵最终统计：44 / 6 / 7 / 3 / 0（按 AND_TESTED、NOT_FULLY、RESERVED、
BLOCKED、NOT_IMPLEMENTED 顺序）。稳定演示仍为 `3023e84` /
`demo-milestone`。
