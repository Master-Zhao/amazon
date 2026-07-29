# Framework Release Checklist

> 当前复核说明：历史 E2E PASS 不适用于当前 HEAD。当前 Playwright 为
> NOT VERIFIED，且批量执行部分成功未实现，因此不创建 `v1-framework-rc2`。

| 检查项 | 结果 | 证据 |
|---|---|---|
| README 从零/全容器/混合启动 | PASS | README 与 Compose 配置 |
| Python/pnpm 锁文件有效 | PASS | `uv.lock`, `pnpm-lock.yaml` frozen 安装基线 |
| 数据库从零迁移 | PASS | M6 MySQL 8.4；本次无新迁移 |
| seed 可重复 | PASS | `test_seed_demo_user_requires_password_and_is_idempotent` |
| API、前端、Worker、Beat 可启动 | PASS | M6 test Compose 7 服务 healthy |
| OpenAPI/TypeScript 可再生成 | PASS | 本次生成、验证和差异检查 |
| fixtures 有说明 | PASS | README、报表开发指南 |
| 后端/前端测试可运行 | PASS | 本次全量测试报告 |
| 核心 E2E 可运行 | NOT VERIFIED | 两次在浏览器启动前的旧固定 SQLite 迁移历史处失败 |
| Adapter 有接口、错误和示例 | PASS | `integrations/` 与 adapter 指南 |
| 权限统一入口 | PASS | `apps.permissions.services.authorize` |
| 未知文件持续排除 | PASS | 未跟踪且未暂存；隔离目录由 `.gitignore` 排除 |
| 仓库无秘密 | PASS | tracked 文件扫描与 `.gitignore` |
| Coverage Matrix 无遗漏 | PASS | 60 项、无 `NOT_IMPLEMENTED` |
| 未验证项有方案 | PASS | backlog、性能计划、矩阵验证命令 |
| 真实样例兼容 | BLOCKED | 三类真实 Amazon 导出尚未提供 |
| 生产 TLS/监控/备份恢复/容量 | NOT VERIFIED | 需生产等价环境执行 |

结论：Framework RC 可发布；它不是生产容量、真实数据兼容或真实外部集成认证。
