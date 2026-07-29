# Amazon 广告智能优化系统 V1

本仓库是可继续开发的 V1 Framework Baseline。稳定演示检查点为
`demo-milestone`；真实 Amazon Ads、第三方报表与真实 LLM 均未接入。
唯一主规格是 `codex_master_goal_amazon_ads_v1.md`。

## 前置条件

- Docker Desktop + Compose v2（全容器方式）
- 或 Python 3.13、uv、Node.js 24、pnpm 11、MySQL 8.4、Redis 7（混合开发）
- Windows 使用 PowerShell；Linux/macOS 将 `$env:NAME='value'` 改为
  `export NAME=value`，将 `Remove-Item Env:NAME` 改为 `unset NAME`

复制 `.env.example` 为本机 `.env`，只在本机设置秘密。不要提交 `.env`。

## 从零全容器启动

```powershell
docker compose -f compose.local.yml config --quiet
docker compose -f compose.local.yml up -d mysql redis
docker compose -f compose.local.yml --profile tools run --rm migrate

$env:DEMO_USER_PASSWORD = Read-Host "输入本机演示密码"
docker compose -f compose.local.yml run --rm -e DEMO_USER_PASSWORD backend python manage.py seed_demo_user --email demo@example.invalid --username demo
docker compose -f compose.local.yml run --rm backend python manage.py seed_demo_context --email demo@example.invalid
Remove-Item Env:DEMO_USER_PASSWORD

docker compose -f compose.local.yml up -d backend celery-worker celery-beat frontend nginx
docker compose -f compose.local.yml ps
curl.exe http://localhost:8080/health/live
curl.exe http://localhost:8080/health/ready
docker compose -f compose.local.yml exec backend python manage.py celery_smoke --timeout 30
```

浏览器入口为 `http://localhost:8080/`，OpenAPI UI 为
`http://localhost:8080/api/docs/`。停止但保留数据：

```powershell
docker compose -f compose.local.yml down
```

除非确认数据可丢弃，不要添加 `--volumes`。

## 前后端混合开发

先用 Compose 启动 MySQL/Redis，再在两个终端运行应用：

```powershell
docker compose -f compose.local.yml up -d mysql redis
$env:DJANGO_SETTINGS_MODULE='config.settings.local'
$env:DB_HOST='127.0.0.1'
$env:REDIS_URL='redis://127.0.0.1:6379/0'
$env:CELERY_BROKER_URL='redis://127.0.0.1:6379/0'
$env:CELERY_RESULT_BACKEND='redis://127.0.0.1:6379/1'
uv sync --project backend --frozen
uv run --project backend python backend/manage.py migrate
uv run --project backend python backend/manage.py runserver 127.0.0.1:8000
```

```powershell
pnpm --dir frontend install --frozen-lockfile
$env:VITE_DEV_PROXY_TARGET='http://127.0.0.1:8000'
pnpm --dir frontend dev
```

Worker 与 Beat 使用相同后端环境：

```powershell
uv run --project backend celery --workdir backend -A config worker --loglevel=INFO --queues=default,imports,analysis,maintenance
uv run --project backend celery --workdir backend -A config beat --loglevel=INFO
```

## 数据、fixture 与演示

`seed_demo_user` 和 `seed_demo_context` 均可重复执行；只有前者接收密码，
密码必须从环境变量传入。脱敏/虚构报表在
`tests/fixtures/reports/`，核心演示上传
`tests/fixtures/reports/campaign-anomalous.csv`。完整页面顺序和预期结果见
`docs/presentation/demo-script.md`。

迁移规则：

```powershell
uv run --project backend python backend/manage.py makemigrations --check --dry-run
uv run --project backend python backend/manage.py migrate
```

已共享迁移只能新增，不能改写。

## 检查、测试和契约

```powershell
uv run --project backend python backend/manage.py check
uv run --project backend pytest backend -q

docker compose -f compose.test.yml up -d mysql redis
docker compose -f compose.test.yml run --build --rm backend pytest -q

pnpm --dir frontend lint
pnpm --dir frontend typecheck
pnpm --dir frontend test
pnpm --dir frontend build
pnpm --dir frontend test:e2e

uv run --project backend python backend/manage.py spectacular --file openapi/schema.yaml --validate
pnpm --dir frontend generate:api
git diff --exit-code -- openapi/schema.yaml frontend/src/shared/api/generated/schema.d.ts

docker compose -f compose.local.yml config --quiet
docker compose -f compose.test.yml config --quiet
docker compose --env-file .env.example -f compose.prod.yml config --quiet
```

Playwright 使用隔离的 Django `18000` 与 Vite `15173`，优先使用本机 Chrome，
不会占用未知的 `8000` 进程。当前 2026-07-28 验收中两次运行均在浏览器启动前
因旧固定 SQLite 迁移历史失败，已改为每次运行唯一 SQLite 文件，但修复后未按
“同一问题最多两次”规则继续重跑，因此自动 E2E 状态是 `NOT VERIFIED`。

## 目录和开发入口

- `backend/apps/`：领域模块；写入走 Service，复杂读取走 Selector
- `backend/integrations/`：报表、存储、LLM、执行与监控 Adapter
- `frontend/src/features/`：业务页面和 API 模块
- `openapi/schema.yaml`：前后端契约快照
- `tests/fixtures/reports/`：虚构报表
- `docs/development/getting-started.md`：开发者入口
- `docs/acceptance/framework-release-checklist.md`：发布检查结果
- `docs/requirements/requirement-coverage-matrix.md`：逐项覆盖证据

根目录 `amazon-ads-operations-0.1.1` 是隔离目录，禁止读取、修改、扫描或复用。

## 常见问题

- Python 版本错误：必须通过 `uv run --project backend` 使用锁定的 3.13。
- 端口占用：混合开发可更换应用端口；不要终止来源不明的进程。
- Redis/MySQL readiness 失败：先检查 `docker compose ... ps` 和 `.env` 中主机名；
  容器内使用 `mysql`/`redis`，宿主进程使用 `127.0.0.1`。
- E2E 找不到浏览器：安装 Chrome Stable；`playwright.config.ts` 使用
  `channel: 'chrome'`，不需要下载整套 Playwright 浏览器。
- OpenAPI 类型有差异：先生成 schema，再运行 `pnpm --dir frontend generate:api`，
  两个文件应同时提交。

更多故障处理见 `docs/deployment/troubleshooting.md`。生产 TLS、真实备份恢复、
300 用户/200 RPS/10 分钟以及 5×100,000 行并发导入尚未在生产等价环境验证。

`compose.test.yml` 的 MySQL 使用 `tmpfs`，适合从零迁移和测试；重启 MySQL
容器会清空测试库，不应用它验证持久化。持久化恢复应使用 local/prod 卷并遵循
`docs/deployment/backup-and-restore.md`。
