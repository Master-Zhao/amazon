# Phase 1 验收清单

最终更新：2026-07-28。状态只使用 `PASS`、`FAIL`、`NOT VERIFIED`。

| # | 验收标准 | 状态 | 最终真实命令或证据 |
|---:|---|---|---|
| 1 | 当前目录已经初始化为 Git 仓库 | PASS | Phase 0 基线提交 `748ef13`；本次最终 Git 检查通过 |
| 2 | 后端依赖可以从锁文件安装 | PASS | `uv sync --project backend --frozen` 成功；local/prod 镜像冻结安装成功 |
| 3 | 前端依赖可以从锁文件安装 | PASS | local/prod Docker 构建执行冻结依赖层；`pnpm-lock.yaml` 未漂移 |
| 4 | 自定义 User 在第一次迁移中正确建立 | PASS | 独立 prod MySQL 从零执行 `accounts.0001_initial`；`sys_user` 保持首次自定义 User |
| 5 | Django check 通过 | PASS | 宿主及 local backend `manage.py check`：0 issues |
| 6 | 后端测试通过 | PASS | 宿主 SQLite 25 passed；MySQL 8.4.6 隔离 Compose 25 passed |
| 7 | OpenAPI Schema 能够生成 | PASS | `spectacular --validate` exit 0；生成前后 SHA-256 相同 |
| 8 | `/health/live` 能够访问 | PASS | local 与 prod 均经 Nginx 返回 HTTP 200；requestId 头/体一致 |
| 9 | `/health/ready` 正确反映 MySQL、Redis和配置状态 | PASS | 正常 200；Redis 停止时 503；JSON warning 与响应同 requestId；恢复后 200 |
| 10 | Celery Worker 可以执行 smoke task并可健康探测 | PASS | smoke task 成功，taskId `6dd14fe1-8108-4383-b141-ee1817a68d21`；Worker inspect ping healthcheck 为 healthy |
| 11 | 前端 lint 通过 | PASS | `pnpm --dir frontend lint`，0 warning/error |
| 12 | 前端 typecheck 通过 | PASS | `pnpm --dir frontend typecheck`，exit 0 |
| 13 | 前端单元测试通过 | PASS | Node 24 local 镜像：5 files / 15 tests passed |
| 14 | 前端 production build 通过 | PASS | Vite 8.1.5，96 modules，exit 0 |
| 15 | Compose 配置检查通过 | PASS | local/test/prod 三个 `config --quiet` 均 exit 0 |
| 16 | 全容器或最小 Compose 环境能够启动 | PASS | local 7 服务均 healthy；Worker/Beat 不再只是 Up |
| 17 | Nginx 能够提供前端并代理 Gunicorn 后端 | PASS | 独立 prod Compose：生产静态首页、`/health/live`、`/health/ready` 实测 200；后端确认为 Gunicorn |
| 18 | README 中的命令经过实际验证 | PASS | config → build → dependencies → migrate → services → health/smoke 顺序实际执行成功 |
| 19 | 文档已经与代码同步 | PASS | 历史文档、README、环境矩阵、部署/API/测试、PLANS、决策日志和阶段报告已更新 |
| 20 | 没有进入 Phase 2 业务实现 | PASS | 无登录、Token 签发、Tenant/Store/Profile/RBAC、报表、AI 或审批业务实现 |

汇总：`PASS 20 / FAIL 0 / NOT VERIFIED 0`。

自动化浏览器 E2E 不属于本清单的 Phase 1 阻塞项。本次没有新增 E2E 依赖或脚本；此前真实浏览器验收有效，但不能解释为可重复自动化 E2E 已完成。后续业务前端联调和 Phase 7 必须补充。

Phase 1 之外仍未验证：性能与并发目标、正式 TLS、备份恢复、生产监控/高可用、真实 Amazon 三类脱敏报表，以及任何 Phase 2—7 业务链路。
