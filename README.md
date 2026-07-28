# Amazon 广告智能优化系统 V1

当前仓库已完成 Phase 1：基础工程与运行框架。它现在是一个可安装、可迁移、可测试、可构建并可通过 Docker Compose 启动的前后端工程；尚未实现登录、Tenant、广告、报表、AI、Recommendation、审批或执行业务。

唯一主规格是 [codex_master_goal_amazon_ads_v1.md](codex_master_goal_amazon_ads_v1.md)。长期规则见 [AGENTS.md](AGENTS.md)，阶段计划见 [PLANS.md](PLANS.md)。

## 技术栈

- 后端：Python 3.13、Django 5.2 LTS、DRF 3.16、Celery 5.6、Gunicorn。
- 前端：Node.js 24、Vue 3、TypeScript、Vite 8、Pinia、Axios、pnpm。
- 数据与部署：MySQL 8.4、Redis 7、Nginx、Docker Compose。
- 契约：OpenAPI 3 + 自动生成 TypeScript 类型。

本机默认 `python` 可能是 3.12；不要降低项目版本。使用 uv 管理的 Python 3.13 或容器。

## 快速启动

以下命令已在 Phase 1 实际验证：

```powershell
# 1. 校验 Compose
docker compose -f compose.local.yml config --quiet

# 2. 启动依赖
docker compose -f compose.local.yml up -d mysql redis

# 3. 独立执行迁移
docker compose -f compose.local.yml --profile tools run --rm migrate

# 4. 启动应用
docker compose -f compose.local.yml up -d backend celery-worker celery-beat frontend nginx

# 5. 检查
docker compose -f compose.local.yml ps
curl.exe http://localhost:8080/health/live
curl.exe http://localhost:8080/health/ready

# 6. 验证真实 Celery 往返
docker compose -f compose.local.yml exec backend python manage.py celery_smoke --timeout 30
```

访问：

- 首页：`http://localhost:8080/`
- 运行诊断：`http://localhost:8080/diagnostics/health`
- OpenAPI：`http://localhost:8080/api/docs/`
- Schema：`http://localhost:8080/api/schema/`

停止但保留数据：

```powershell
docker compose -f compose.local.yml down
```

不要在没有确认数据可丢弃时添加 `--volumes`。

## 测试与构建

后端：

```powershell
uv sync --project backend --frozen
uv run --project backend python backend/manage.py check
uv run --project backend python backend/manage.py makemigrations --check --dry-run
uv run --project backend pytest backend -q
```

MySQL 8.4 集成测试：

```powershell
docker compose -f compose.test.yml up -d mysql redis
docker compose -f compose.test.yml run --build --rm backend pytest -q
```

前端：

```powershell
pnpm --dir frontend install --frozen-lockfile
pnpm --dir frontend lint
pnpm --dir frontend typecheck
pnpm --dir frontend test
pnpm --dir frontend build
```

契约：

```powershell
uv run --project backend python backend/manage.py spectacular --file openapi/schema.yaml --validate
pnpm --dir frontend generate:api
```

Phase 1 最终结果：后端 SQLite 25 tests passed；MySQL 8.4 25 tests passed；前端 5 files / 15 tests passed；lint、typecheck、production build、OpenAPI/生成类型差异和三个 Compose 静态校验通过。local 7 服务均 healthy（包含 Worker/Beat）；独立 prod Compose 已实测 Gunicorn、生产静态前端、Nginx 与 requestId，并在验收后停止。

## API 基础

统一响应：

```json
{
  "code": "SUCCESS",
  "message": "操作成功",
  "data": {},
  "requestId": "req_xxx"
}
```

公共层统一处理 requestId、异常、递归 snake_case/camelCase 转换和 Decimal/日期/UUID 序列化。`/health/live` 只证明进程存活；`/health/ready` 检查 MySQL、Redis 和必需配置。

`/api/v1/` 当前只公开平台元数据，并明确返回 `businessCapabilities: "not_implemented"`。没有假登录、假 Tenant、假 Dashboard 或硬编码广告结果。

## 目录

```text
backend/                 Django、DRF、Celery、测试与首次 User 迁移
frontend/                Vue 基础应用、诊断页、Axios/Pinia/Router
infra/nginx/             local/prod 反向代理配置
openapi/                 Schema 快照
docs/architecture/       当前技术设计
docs/api/                API 与错误码
docs/deployment/         local/test/prod 运行手册
docs/testing/            测试策略与验收清单
```

根目录 `amazon-ads-operations-0.1.1` 是隔离目录，不属于本项目代码基础，禁止读取、修改、扫描或复用。

## 文档入口

- [Phase 1 报告](docs/phase-1-report.md)
- [技术方案](docs/architecture/technical-solution.md)
- [模块设计](docs/architecture/module-design.md)
- [异步任务](docs/architecture/async-task-design.md)
- [API 约定](docs/api/api-conventions.md)
- [本地开发](docs/deployment/local-development.md)
- [生产部署](docs/deployment/production-deployment.md)
- [环境变量矩阵](docs/deployment/environment-variables.md)
- [测试策略](docs/testing/test-strategy.md)
- [验收清单](docs/testing/acceptance-checklist.md)
- [决策日志](docs/15-decision-log.md)

## 当前边界

Phase 2 必须等待明确授权。真实 Amazon Ads API、第三方数据服务和真实 LLM 密钥均未接入；未执行性能测试，不声明任何并发量、QPS、延迟或广告收益。

Phase 1 只预留并校验 JWT TTL、Refresh Cookie、轮换和吊销配置，不包含登录、Token 签发或授权业务。ECharts 与自动化浏览器 E2E 依赖均未在 Phase 1 引入。
