# V1 最终验收报告

> 历史验收记录：当前 2026-07-28 重新验收已由根目录
> `V1_VERIFIED_DELIVERY_REPORT.md` 取代。旧 E2E PASS 和旧测试数量不得
> 作为当前 HEAD 证据；当前为后端 112、前端 46、Playwright NOT VERIFIED。

验收日期：2026-07-28。稳定演示基线为 `3023e84` / `demo-milestone`，M6 只在其后增加兼容性、幂等、索引和交付收口。

| 范围 | 实际命令/方式 | 结果 |
|---|---|---|
| Django check | `manage.py check`（test settings） | PASS，0 issues |
| 迁移差异 | `makemigrations --check --dry-run` | PASS，No changes detected |
| SQLite 从零迁移 | 隔离 `m6-clean.sqlite3` 后 `migrate --noinput` | PASS，随后删除临时数据库 |
| SQLite 全量测试 | `pytest backend -q` | PASS，82 passed / 25 warnings |
| MySQL 8.4 从零测试 | `compose.test.yml run --rm backend pytest --create-db -q` | PASS，82 passed / 25 warnings |
| 前端 lint | `pnpm --dir frontend lint` | PASS |
| 前端 typecheck | `pnpm --dir frontend typecheck` | PASS |
| 前端 unit | `pnpm --dir frontend test` | PASS，9 files / 31 tests |
| 前端 production build | `pnpm --dir frontend build` | PASS；Dashboard lazy chunk 508.92 kB 警告 |
| OpenAPI | `spectacular --validate` + `generate:api` | PASS，Schema 与类型已同步 |
| Chrome E2E | `pnpm --dir frontend test:e2e` | PASS，1 条完整闭环；18000/15173 |
| Compose 静态 | local/test/prod `config --quiet` | PASS，3/3 |
| Docker 运行 | test Compose 从零构建、迁移、启动 | PASS，7 服务 healthy |
| HTTP 健康 | 8081 live/ready/前端 | PASS，均成功 |
| 只读负载烟雾 | `load_smoke.py`，10 RPS × 5 秒 | PASS，50/50 HTTP 200 |
| 正式容量压测 | 300 用户、200 RPS、10 分钟 | NOT VERIFIED，未执行 |
| 备份恢复演练 | 隔离恢复与数据抽样 | NOT VERIFIED，仅交付手册 |
| 真实 Amazon 报表 | 三类真实脱敏导出 | BLOCKED_BY_REAL_SAMPLE |

MySQL 首次从零测试暴露旧 `SearchTerm` 复合自然键超过 InnoDB 键长度。修复保留原迁移不变：新增 `0001_squashed_0002_initial` 供新安装使用，并用 `0004` 将既有库字段前向调整为 255；修复后 MySQL 82 项全量通过。

测试过程中首次 Docker build 因 Docker Hub 匿名令牌请求 EOF 失败，单次重试成功。首次 MySQL 测试在迁移阶段失败；修复索引长度后又发现容器未挂载根目录 fixtures，增加 test Compose 只读 fixture 挂载后最终通过。以上失败均未隐去。

验收结束后已执行 `docker compose -f compose.test.yml down`；未启动 local Compose，未占用或终止宿主 8000 的未知进程。

## Framework Baseline 增量验收

本次代码变更后的实际结果：Django check 0 issues；无迁移差异；受影响测试
41 passed；后端全量 103 passed / 25 warnings；前端 lint/typecheck PASS，
10 files / 33 tests PASS，production build PASS（保留 508.92 kB chunk 警告）；
OpenAPI validate 与 TypeScript 生成 PASS；隔离 18000/15173 的 Chrome 核心 E2E
1 passed；local/test/prod Compose 静态检查 3/3 PASS；`git diff --check` PASS。

本次未改 Compose，故未重复完整镜像拉取和 7 服务运行验证；继续引用上表 M6
真实 Docker/MySQL 证据。生产 TLS、监控 exporter、备份恢复、300 用户/
200 RPS/10 分钟、5×100,000 行并发导入仍为 NOT VERIFIED。
