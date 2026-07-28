# Phase 1 定向补缺与最终收口报告

报告日期：2026-07-28。范围：Phase 1 基础工程定向补缺与最终验收。未进入 Phase 2。

## 1. 本阶段目标

在不重做主体工程、不增加业务模型和接口的前提下，修复审查确认的文档、readiness 日志、Celery 健康检查、JWT 配置预留、API ID 序列化、环境配置、Axios 测试和 settings 测试缺口，并完成 local/prod 真实运行验收与 Git 收口。

## 2. 检查的现有文件

- 唯一主规格、`AGENTS.md`、`PLANS.md`、决策日志、Phase 1 报告、20 项验收清单和 README。
- 四份历史技术文档、环境/部署/API/测试文档。
- readiness、requestId、JSON 日志、settings、序列化、Axios、三套 Compose 与相关测试。
- Git 状态中的 `.arts/settings.json` 仅确认未跟踪状态，未读取、修改或暂存。
- `amazon-ads-operations-0.1.1` 持续隔离，未读取、扫描、修改、移动或复用。

## 3. 修复的缺口与技术决策

1. D-138 已关闭：Django 内置 `auth_*`、`django_*` 表豁免项目业务表前缀；自定义表仍必须使用批准的模块前缀。
2. ECharts 不在 Phase 1 安装；首次实现真实 Dashboard/趋势图时再引入。
3. 可重复自动化浏览器 E2E 不作为 Phase 1 的 20 项阻塞条件；此前真实浏览器验收仍有效，但未描述为自动化 E2E。
4. readiness 的 MySQL/Redis/config 失败写 JSON warning，记录依赖名、非敏感状态和同一 requestId，不记录异常正文、密码或连接串。
5. 中间件在结构化 Django 请求完成日志读取 requestId 后才重置 ContextVar；测试确认请求之间不串值。
6. Worker healthcheck 验证 PID1、Broker 连通和定向 `celery inspect ping`；Beat healthcheck 验证 PID1 与真实 beat 命令行，不使用静态文件。
7. JWT 仅建立 TTL、Refresh Cookie、轮换和吊销配置位置；未实现登录、Token 签发或硬编码 JWT 密钥。
8. API ID 使用显式 `ObjectIdentifierField`/`ObjectIdentifierListField`；不全局改写普通整数。
9. local 显式解析 `DJANGO_DEBUG`，test/prod 强制关闭；prod Compose 传入实际 Cookie/JWT 配置。
10. Axios 对 401、403、无响应网络错误、超时、标准/非标准错误和 requestId 做安全归一化。

## 4. 修改文件

- 根治理与配置：`.gitignore`、`.env.example`、`AGENTS.md`、`PLANS.md`、`README.md`、三套 Compose。
- 后端：`apps/core/health.py`、`logging.py`、`middleware.py`、`fields.py`，settings 的 `environment.py`、`base.py`、`local.py`、`prod.py`，`pyproject.toml`。
- 后端测试：health、requestId、settings、ID 字段测试。
- 前端：`shared/api/httpClient.ts` 与 `httpClient.spec.ts`。
- 文档：四份历史技术文档、决策日志、API/异步任务/部署/环境变量/测试文档、本报告与验收清单。

Phase 1 主体工程的其余新增文件随本次提交一并纳入；来源不明的 `.arts/` 和两个根目录 `.docx` 不纳入。

## 5. 新增文件

- `backend/apps/core/fields.py`
- `backend/tests/test_identifier_fields.py`
- `docs/deployment/environment-variables.md`

没有新增业务模块、业务 Model、业务 API、登录页面或 ECharts/E2E 依赖。

## 6. 依赖变化

- Python、Node 和镜像版本未变化；`uv.lock`、`pnpm-lock.yaml` 的依赖集合未因本次补缺改变。
- `uv sync --project backend --frozen` 成功。
- 前端未重复执行宿主依赖安装；local/prod Docker 构建使用冻结锁文件并成功，依赖层命中缓存。

## 7. 数据库迁移

- 未新增或修改迁移。
- `makemigrations --check --dry-run`：`No changes detected`。
- local MySQL `migrate --check`：exit 0。
- 独立 prod MySQL 从零执行 Django 内置迁移与 `accounts.0001_initial` 成功。
- Django 内置 `auth_*`、`django_*` 表按 D-138 豁免；自定义 User 表保持 `sys_user`。

## 8. 新增接口与页面

- 新增接口：无。
- 新增页面：无。
- OpenAPI Schema SHA-256 生成前后均为 `E8B603A792283D69D0B9EDB221BD346674B51B029CA63123EC93C6CFE7A45B64`。
- TypeScript 生成类型 SHA-256 生成前后均为 `5724EF6DD0E4D42D0C1F9CCA07C9916310AD30D7F1A984BDECF9E72D204D46B8`。

## 9. 更新文档

- 四份旧技术文档已明确标记为历史方案、指出由主规格取代并列出当前有效结论。
- 新增完整 local/test/prod 环境变量矩阵，包含必需性、默认值、各环境取值、敏感性与使用位置。
- README、部署、API、异步任务、测试策略、决策日志、计划与验收状态已同步最终真实结果。

## 10. 实际执行的主要命令

```powershell
uv sync --project backend --frozen
uv run --project backend python backend/manage.py check
uv run --project backend python backend/manage.py makemigrations --check --dry-run
uv run --project backend python backend/manage.py migrate --check
uv run --project backend pytest backend
uv run --project backend python backend/manage.py spectacular --file openapi/schema.yaml --validate

pnpm --dir frontend generate:api
pnpm --dir frontend lint
pnpm --dir frontend typecheck
docker run --rm amazon-ads-frontend:0.1.0-local pnpm test
docker run --rm amazon-ads-frontend:0.1.0-local pnpm build

docker compose -f compose.local.yml config --quiet
docker compose -f compose.test.yml config --quiet
docker compose --env-file .env.example -f compose.prod.yml config --quiet
docker compose -f compose.local.yml build backend frontend
docker compose -f compose.local.yml up -d --wait --wait-timeout 240 ...
docker compose -f compose.local.yml --profile tools run --rm migrate
docker compose -f compose.local.yml exec -T backend python manage.py celery_smoke --timeout 30
docker compose -f compose.local.yml stop redis
docker compose -f compose.local.yml start redis
docker compose -f compose.test.yml run --build --rm backend pytest -q
docker compose --env-file .env.example -f compose.prod.yml build backend frontend
docker compose --env-file .env.example -f compose.prod.yml up -d --wait ...
docker compose --env-file .env.example -f compose.prod.yml down
```

受限宿主 Vitest 首次因 esbuild `spawn EPERM` 失败，随后在 Node 24 local 镜像中完整通过。一次把 `DJANGO_SETTINGS_MODULE=config.settings.local` 继续带入 pytest，导致测试错误连接 local MySQL；切回明确的 `config.settings.test` 后完整通过。最初 Docker daemon 未启动/沙箱无权访问，用户启动并授权后全部 Docker 验证完成。上述失败均未被计为通过结果。

## 11. 测试与运行结果

### 后端

- 宿主 Python 3.13.3 / SQLite：25 passed，0 failed，0 skipped。
- MySQL 8.4.6 隔离 Compose：25 passed，0 failed，0 skipped。
- Django check：0 issues。
- 迁移差异：0；local migrate check：exit 0；prod 从零迁移成功。
- OpenAPI 生成/验证成功且无哈希差异。

### 前端

- lint：0 warning/error。
- typecheck：通过。
- Vitest：5 files、15 tests 全部通过。
- production build：96 modules；`index.html` 0.52 kB，CSS 2.85 kB，JS 144.72 kB（gzip 55.77 kB）。
- OpenAPI 类型生成成功且无哈希差异。

### Worker 与 Beat

- local `docker compose ps` 显示 `celery-worker` 与 `celery-beat` 均为 `healthy`，不再只是 `Up`。
- Worker 定向 inspect ping healthcheck 通过；Celery smoke 成功，taskId `6dd14fe1-8108-4383-b141-ee1817a68d21`。
- Beat PID1/真实命令行 healthcheck 通过。

### readiness 故障与 requestId

- 正常 `/health/ready`：HTTP 200，依赖均 `available`。
- 停止 Redis 后：HTTP 503，响应头和响应体均为 `phase1-redis-down-final`。
- JSON warning 的 `requestId` 同为 `phase1-redis-down-final`，`event=readiness_check_failed`、`dependency=redis`、`dependency_status=unavailable`。
- 日志未出现密码或 Redis 完整连接串；带密码连接串的不泄漏由后端自动化测试覆盖。
- Redis 恢复后 `/health/ready` 返回 200；local 全服务恢复 healthy。

### 生产 Gunicorn 与 Nginx

- 独立 prod Compose 从零迁移并启动成功。
- backend 以 uid 10001 运行 Gunicorn master + 3 workers，不使用 `runserver`。
- frontend 容器运行 Nginx 并提供 Vite production build，不运行 Vite dev server。
- 外层 Nginx 首页 HTTP 200，HTML 引用哈希静态资源。
- `/health/live`、`/health/ready` 经 Nginx → Gunicorn 均返回 200，requestId 原样透传。
- 验收后 prod 容器和网络已 `down`；local 7 服务未受影响并保持 healthy。

## 12. 20 项验收汇总

`PASS 20 / FAIL 0 / NOT VERIFIED 0`。逐项证据见 `docs/testing/acceptance-checklist.md`。自动化浏览器 E2E 不属于这 20 项 Phase 1 阻塞条件，仍明确记录为后续待办。

## 13. 对既有契约的影响

- 现有 HTTP 路径、响应信封和 OpenAPI 无变化。
- 新增显式 ID Serializer 字段约定；普通业务整数、Decimal 与 UUID 语义不变。
- readiness 失败新增安全的结构化日志，不改变 200/503 响应契约。
- Compose 的 Worker/Beat 新增健康状态，不改变服务名或启动命令。

## 14. 当前仍未验证与遗留风险

- 可重复自动化浏览器 E2E、移动端/多浏览器矩阵仍待后续业务联调和 Phase 7。
- 性能、QPS、延迟、容量和故障注入压测属于 Phase 6，未执行且不声明结果。
- 正式 TLS、外部负载均衡、备份恢复、监控告警、高可用与 Beat 单实例治理未完成。
- 真实 Amazon 三类脱敏报表样例仍未提供，继续阻塞后续 Schema/粒度最终验证。
- Phase 1 JWT 配置只是预留；CSRF、轮换、吊销和登录链路必须在 Phase 2 明确授权后实现并测试。

## 15. 当前启动方法

```powershell
docker compose -f compose.local.yml up -d mysql redis
docker compose -f compose.local.yml --profile tools run --rm migrate
docker compose -f compose.local.yml up -d backend celery-worker celery-beat frontend nginx
docker compose -f compose.local.yml ps
```

当前 local 服务保持运行，可访问 `http://localhost:8080/`。

## 16. 当前演示链路

可真实演示基础首页、运行诊断、OpenAPI、live/ready、requestId、Redis 故障/恢复和 Celery smoke。不能演示登录、Tenant/Store/Profile、报表、广告、AI、Recommendation、审批或执行；这些能力没有静态假页面或假响应。

## 17. 下一阶段与阶段边界

Phase 1 已最终收口。只有收到新的明确授权后才能进入 Phase 2；本次没有实现登录、Tenant、Store、Profile、RBAC、报表、智能体或审批，严格停留在 Phase 1。
