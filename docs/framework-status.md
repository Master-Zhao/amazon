# V1 Framework 当前复核状态

复核日期：2026-07-28。历史 `demo-milestone` 与 `v1-framework-rc1` 标签保持不动。

| 领域 | 状态 | 当前证据/限制 |
|---|---|---|
| Django/DRF/Celery | IMPLEMENTED_AND_TESTED | check；无迁移差异；112/112 tests；Task → Service |
| Vue/Router/Pinia/Axios | IMPLEMENTED_AND_TESTED | lint/typecheck/build；17 files / 46 tests；路由懒加载 |
| MySQL/Redis/Nginx/Compose | IMPLEMENTED_AND_TESTED | 三套静态检查；当前源码 test 栈 7 服务 healthy；HTTP/Celery/MySQL smoke |
| JWT 与 Tenant/Store/Profile/RBAC | IMPLEMENTED_AND_TESTED | API/组件/隔离测试及 Docker HTTP 四级上下文 |
| 三报表导入 | BLOCKED_BY_REAL_SAMPLE | 虚构 CSV/XLSX 通过；真实 Amazon 导出未验证 |
| 三事实/指标/异常 | IMPLEMENTED_AND_TESTED | Decimal、null reason、粒度、币种、规则 |
| Mock Agent/Recommendation | IMPLEMENTED_AND_TESTED | 四 Invocation、统一 Schema、重试幂等、11 类校验 |
| Preview/审批/执行/效果/审计 | IMPLEMENTED_AND_TESTED | 只追加、漂移、职责分离、证据、基础评估 |
| 真实浏览器全路径 | IMPLEMENTED_NOT_FULLY_VERIFIED | 两次 Playwright 在浏览器启动前被旧固定 SQLite 阻断；修复后未第三次运行 |
| 完整业务对话框 | IMPLEMENTED_NOT_FULLY_VERIFIED | 可操作内联页面存在；要求的全部上下文字段未集中展示 |
| 批量执行部分成功 | NOT_IMPLEMENTED | 仅支持单 Preview 的执行结果回填 |
| 真实 LLM/Amazon/第三方 | RESERVED_BY_CONFIRMED_SCOPE | Adapter 边界存在；不联网、不自动执行 |
| 正式容量/TLS/备份恢复 | IMPLEMENTED_NOT_FULLY_VERIFIED | 文档/脚本存在；生产等价验证未执行 |

50 项矩阵当前主分类为 44 `IMPLEMENTED_AND_TESTED`、5
`IMPLEMENTED_NOT_FULLY_VERIFIED`、1 `NOT_IMPLEMENTED`；多项已测试能力另附
浏览器 `NOT VERIFIED` 注记。详见根目录 `V1_ACCEPTANCE_MATRIX.md`。

由于两条 Playwright 未通过且批量执行部分成功未实现，不创建
`v1-framework-rc2`。
