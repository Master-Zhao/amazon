# Amazon Ads Optimization V1 运行接手与技术验收报告

- 验收日期：2026-07-29
- 验收目录：`C:\QSZ\技术方案`
- 当前分支：`master`
- 实际 HEAD：`396a52f3f850fd6fd6aaa042b01a57c4586c4c70`
- 交接基线：`1f8a230 chore: establish v1 framework baseline`
- 报告性质：本地开发、测试与演示环境的实测结果，不是生产上线批准

## 1. 项目结论

| 验收项 | 结论 | 实测依据 |
| --- | --- | --- |
| 项目可运行 | PASS | 本地 Compose 7 个服务全部 healthy |
| 前端可运行 | PASS | Vite 容器、独立 Vite E2E、生产镜像构建均通过 |
| 后端可运行 | PASS | Django 开发服务器、独立 E2E 服务器、Gunicorn 测试栈均通过 |
| MySQL 可连接 | PASS | ready 返回 available；ORM/只读 SQL 查询成功 |
| Redis 可连接 | PASS | ready 返回 available；Celery ping 成功 |
| Celery Worker / Beat | PASS | 两个容器 healthy；Worker 返回 pong；真实任务 E2E 通过 |
| Nginx 统一入口 | PASS | `http://localhost:8080` 与 `/health/ready` 成功 |
| API 读取 MySQL | PASS | Context API 返回的 Tenant/Store/Marketplace/Profile 与 ORM 记录一致 |
| 前端调用 API | PASS | 浏览器成功登录、刷新恢复会话并渲染数据库授权上下文 |
| V1 业务闭环 | PASS（本地 Mock/人工执行边界） | Playwright 覆盖导入、异常、Mock Agent、建议、预览、审批、人工执行、审计 |
| 可作为 V1 Framework RC1 使用 | 有条件 PASS | RC1 标签仍固定在 `1f8a230`；当前运行代码是其后 8 个提交及大量未提交修改 |
| Production Ready | FAIL | 尚有真实报表验证、生产安全加固、架构边界例外、脏工作树与发布可追溯性问题 |

最终判断：当前代码和保留数据的本地环境已经真实调通，可用于 V1 框架继续开发、测试和受控演示；不得把本报告解释为生产就绪或广告收益证明。

## 2. 仓库完整性与版本事实

### 2.1 Git 状态

- 当前 HEAD 不是交接描述中的 `1f8a230`，而是 `396a52f`。
- `1f8a230` 是当前 HEAD 的祖先，之后依次存在迁移修复、导入、分析、审批执行、重试幂等和前端交互提交。
- 当前 HEAD 没有标签。
- `v1-framework-rc1` 指向 `1f8a230`。
- `demo-milestone` 指向 `3023e84`，不指向当前 HEAD。
- 接手前工作树已经包含大量已修改和未跟踪文件。本次没有清理、覆盖或自动提交这些既有变更。
- `git diff --check` 未发现空白错误，只报告 Windows 下 LF 将转换为 CRLF 的提示。
- 未发现冲突标记；关键配置、锁文件、Dockerfile 和三套 Compose 文件存在。
- 未读取或修改 `.arts/`、两份未知 DOCX、`amazon-ads-operations-0.1.1`。

### 2.2 代码完整性判断

模块目录覆盖 `core`、`accounts`、`tenants`、`permissions`、`stores`、`products`、`reports`、`advertising`、`analytics`、`agents`、`recommendations`、`actions`、`knowledge`、`audit`，另有正在工作树中开发的 `notifications`。

项目不是静态 Demo 空壳。全新测试库可从零迁移，E2E 创建独立测试账号和虚构上下文，并完成真实 HTTP、ORM、异步任务和状态转换。

## 3. 实际技术栈

### 3.1 后端

- CPython：锁定/镜像 `3.13.3`；本机全局 Python 为 `3.11.9`，`uv` 实际选择 `3.13.3`
- `uv 0.11.6`，`pyproject.toml + uv.lock`
- Django `5.2.16`
- Django REST Framework `3.16.1`
- Celery `5.6.3`
- PyMySQL `1.2.0`
- Redis Python client `6.4.0`
- Gunicorn `23.0.0`
- drf-spectacular `0.28.0`
- SimpleJWT `5.5.1`
- pytest `8.4.2`、pytest-django `4.12.0`

### 3.2 前端

- Node.js `24.10.0`
- pnpm 项目版本 `11.9.0`；本机命令最初报告 `11.17.0`，Corepack 安装按项目版本执行
- Vue `3.5.40`
- TypeScript `5.9.3`
- Vite `8.1.5`
- Vue Router `4.6.4`
- Pinia `3.0.4`
- Axios `1.18.1`
- ECharts `6.0.0`
- Vitest `4.1.10`
- Playwright `1.61.1`
- openapi-typescript `7.13.0`

### 3.3 基础设施

- Docker Engine/CLI `29.5.2`
- Docker Compose `5.1.4`
- MySQL 镜像 `8.4.6`
- Redis 镜像 `7.4.5-alpine3.21`
- Nginx 镜像 `1.28.0-alpine`
- local/test/prod 三套 Compose 均通过静态解析
- 所有镜像均使用固定版本，不使用 `latest`

仓库不存在 `poetry.lock`；实际后端包管理是 `uv`。前端只使用 pnpm。

## 4. 系统架构确认

系统是前后端分离的模块化单体：

```text
Browser
  → Nginx / Vite proxy
  → Django REST API /api/v1
  → View + Serializer
  → Service（写）或 Selector（复杂读）
  → Django ORM
  → MySQL

Celery Task
  → Service
  → ORM / Redis broker
```

认证采用 Access Token 加 HttpOnly Refresh Cookie；前端具有并发 401 单次刷新和页面刷新恢复逻辑。上下文顺序为 Tenant → Store → Marketplace → Advertising Profile。权限检查覆盖 Membership、功能权限以及 Store/Profile 数据范围。

文件导入正文保存在文件存储，MySQL 保存元数据和血缘。V1 智能体通过 Orchestrator、JSON Schema 和 MockLLMProvider 工作，不调用真实 Amazon Ads API，也不自动修改广告；Action Preview、审批、人工执行回填和审计由代码状态机裁决。

架构扫描仍发现两类例外：

- `backend/apps/knowledge/views.py` 直接使用 ORM；
- `backend/apps/tenants/views.py` 直接使用 ORM。

因此不能宣称所有模块均完全满足 `View → Selector/Service → ORM`。Agents 未发现直接 ORM 访问；外部广告执行仍被 Adapter/V1 范围守卫阻止。

## 5. 本地环境要求

- Windows 10/11 与 PowerShell
- Docker Desktop，建议至少 4 CPU、8 GB 可用内存、10 GB 可用磁盘
- Docker Compose 2+（本机实际 5.1.4）
- Node.js 24 LTS 与 Corepack/pnpm 11.9.0
- `uv`，由其安装 CPython 3.13.3；不应使用本机全局 Python 3.11 启动本项目
- Git
- 端口：3306、6379、8000、5173、8080；隔离测试栈额外使用 8081

环境文件：

- 根目录 `.env.example` 可作为 Compose 配置模板；
- 本机存在 `.env` 和 `.env.local-nodocker`，本报告只检查变量是否配置，未记录任何值；
- 敏感变量至少包括 `DB_PASSWORD`、`MYSQL_ROOT_PASSWORD`、`DJANGO_SECRET_KEY`；
- 不应使用 Compose 中的本地回退密码或短 Secret 作为生产值。

## 6. 完整 Docker Compose 启动方式

```powershell
cd "C:\QSZ\技术方案"
docker compose -f compose.local.yml config --quiet
docker compose -f compose.local.yml up -d mysql redis
docker compose -f compose.local.yml --profile tools run --rm migrate
docker compose -f compose.local.yml up -d backend celery-worker celery-beat frontend nginx
docker compose -f compose.local.yml ps
curl.exe -i http://localhost:8080/health/ready
```

访问地址：

- 统一入口：`http://localhost:8080`
- 直接后端：`http://localhost:8000`
- 直接前端开发服务器：`http://localhost:5173`

如果后端或前端容器被单独重建后 Nginx 出现 502，可安全重建无状态 Nginx：

```powershell
docker compose -f compose.local.yml up -d --force-recreate nginx
```

不得执行 `docker compose down -v`。

## 7. 前端独立启动方式

先保持 MySQL、Redis 和后端运行，再执行：

```powershell
cd "C:\QSZ\技术方案"
corepack enable
corepack prepare "pnpm@11.9.0" --activate
pnpm --dir frontend install --frozen-lockfile
$env:VITE_DEV_PROXY_TARGET = "http://127.0.0.1:8000"
pnpm --dir frontend dev
```

Vite 默认监听 `0.0.0.0:5173`，把 `/api` 和 `/health` 代理到 `VITE_DEV_PROXY_TARGET`，因此独立开发不需要 Nginx。修改 `.vue`/`.ts` 后可热更新。

本次 Playwright 实际在 `127.0.0.1:15173` 启动独立 Vite，并连接独立 Django 测试服务，5 条 E2E 全部通过。

## 8. 后端独立启动方式

先通过 Compose 只启动 MySQL/Redis：

```powershell
cd "C:\QSZ\技术方案"
docker compose -f compose.local.yml up -d mysql redis
uv sync --project backend --frozen
```

将 `.env.local-nodocker` 安全加载到当前 PowerShell 进程，不打印变量值：

```powershell
Get-Content -LiteralPath ".env.local-nodocker" | ForEach-Object {
    if ($_ -match '^\s*([A-Za-z_][A-Za-z0-9_]*)=(.*)$') {
        $name = $matches[1]
        $value = $matches[2].Trim().Trim('"').Trim("'")
        Set-Item -Path "Env:$name" -Value $value
    }
}
uv run --project backend python backend/manage.py check
uv run --project backend python backend/manage.py migrate --check
uv run --project backend python backend/manage.py runserver 127.0.0.1:8000
```

`runserver` 支持代码热重载。若 Compose 后端仍占用 8000，先停止该单个容器，或将独立服务改为 8001，并同步设置 `VITE_DEV_PROXY_TARGET`。

本次独立 E2E 使用 CPython 3.13.3 启动 Django，并成功执行登录、导入、异步任务和 API 链路。

## 9. 数据库初始化和迁移

### 9.1 新数据库

在空数据库上执行普通迁移：

```powershell
docker compose -f compose.local.yml --profile tools run --rm migrate
```

隔离 MySQL 8.4 测试栈已从零顺序应用全部迁移，未使用 `--fake`。

### 9.2 当前保留数据的本地数据库

只读查询得到完整顺序：

```text
advertising.0001_initial
advertising.0002_initial
advertising.0003_initial
advertising.0004_campaign_target_acos
analytics.0001_initial
analytics.0002_searchtermdailymetric_searchtermmetricrevision_and_more
analytics.0003_campaigndailymetric_snapshot_hour_local_and_more
analytics.0004_persist_metric_calculation_reasons
```

当前结构：

```text
ads_campaign.target_acos = decimal(8,4), NULL=YES, default=NULL, 无索引
```

当前迁移图一致，`migrate --check` 通过。未删除、伪造或重排任何迁移记录。

### 9.3 演示数据库

`seed_demo_context` 存在并由测试验证幂等。密码必须通过 `DEMO_USER_PASSWORD` 临时环境变量传入。不得将密码写入命令、仓库或报告。

本次还修复了 `seed_accounts` 中的硬编码和打印密码问题：该命令现在只接受可选的 `DEMO_SEED_PASSWORD`；未提供时新账号不可登录，已有账号密码不被重置。

### 9.4 测试数据库

`compose.test.yml` 的 MySQL 数据目录使用 tmpfs，与本地持久卷隔离。此次在独立项目名 `amazon-ads-verify` 下从零迁移并达到 7/7 healthy，结束后仅移除测试容器和网络，没有删除任何 Docker Volume。

## 10. 当前迁移问题：根因与处理

历史错误指向旧代码中的迁移依赖图：

```text
analytics.0001_initial is applied before its dependency
advertising.0003_campaign_target_acos
```

证据表明：

1. `1f8a230` 基线曾把 `target_acos` 放在 `advertising.0003_campaign_target_acos`；
2. 后续提交 `483594a` 通过新增/恢复历史链路形成 `advertising.0003_initial` 和 `0004_campaign_target_acos`；
3. 当前本地库是在修复提交之后初始化，真实应用顺序为 advertising 0001—0004 后再 analytics 0001—0004；
4. 当前字段是预期的 `decimal(8,4) NULL`；
5. Analytics 表的 Campaign 外键存在，当前数据库结构完整；
6. 全新 MySQL 测试库可以从零应用全部迁移。

因此，交接描述中的“不一致持久卷”不是当前这个本地卷的现状，不能对当前库执行 fake 或迁移记录修补。若以后遇到真正的旧库，应先做只读结构/历史导出和备份，在独立克隆库验证新增兼容迁移；证据不足时不得直接修改 `django_migrations`。

本次新增 `notifications.0002_alter_notification_id`，用于补齐 Django migration state 中 `BigAutoField(auto_created=True)`。`sqlmigrate` 显示数据库 SQL 为 no-op；已用普通 `migrate` 应用，只追加迁移记录，不修改通知数据。

## 11. API 与数据库实测

当前本地 MySQL 非敏感计数：

```text
users=7
tenants=4
stores=8
store_marketplaces=8
profiles=8
campaigns=0
```

浏览器以现有演示账号登录后调用：

```text
POST /api/v1/auth/login
POST /api/v1/auth/refresh
GET  /api/v1/auth/me
GET  /api/v1/context/tenants
GET  /api/v1/context/tenants/3/capabilities
GET  /api/v1/context/tenants/3/stores
GET  /api/v1/context/tenants/3/stores/8/marketplaces
GET  /api/v1/context/tenants/3/store-marketplaces/8/profiles
```

全部返回 200。DOM 展示的数据与 ORM 查询一致：

```text
Tenant 3：演示个人卖家空间
Store 8：演示美国店
StoreMarketplace 8：US / Amazon.com / USD
Profile 8：演示 Sponsored Products Profile / MANAGE
```

Store/Marketplace/Profile 路由经 View → Selector → ORM，数据不是 Mock 或静态 JSON。浏览器刷新后通过 Refresh Cookie 恢复登录；未发现关键 CORS 错误或 500。

## 12. 前后端联调与业务闭环

浏览器实测完成：

1. 登录页与真实登录接口；
2. 页面刷新和认证恢复；
3. 工作台路由；
4. Tenant/Store/Marketplace/Profile 数据库授权上下文；
5. 导航、通知、帮助、头像菜单和退出；
6. Campaign 成功导入；
7. Campaign 部分成功导入与行级错误；
8. 异常与 Mock Agent 分析；
9. Recommendation；
10. Action Preview；
11. 提交、审批、人工执行回填；
12. 效果评估任务；
13. AuditLog 展示。

E2E 使用虚构 CSV 和独立测试库，不调用真实 Amazon API，不修改本地持久 MySQL 业务数据。

## 13. 测试和命令结果

| 命令/检查 | 结果 |
| --- | --- |
| `uv sync --project backend --frozen` | PASS，CPython 3.13.3，46 packages |
| `manage.py check` | PASS，0 issues |
| `makemigrations --check --dry-run` | PASS，No changes detected |
| `migrate --check`（本机配置和容器） | PASS |
| `pytest backend` | PASS，122 passed / 25 warnings |
| `pnpm install --frozen-lockfile` | PASS |
| `pnpm lint` | PASS，0 warning |
| `pnpm typecheck` | PASS |
| `pnpm test` | PASS，18 files / 50 tests |
| `pnpm build` | PASS；ECharts chunk 525.20 KB 警告 |
| OpenAPI `--validate --fail-on-warn` | PASS |
| OpenAPI 快照再生成差异 | PASS，0 diff |
| TypeScript API 类型再生成差异 | PASS，0 diff |
| Playwright E2E | PASS，5 passed |
| local/test/prod Compose config | PASS，3/3 |
| local backend/frontend image build | PASS |
| test backend + production frontend image build | PASS |
| 隔离 MySQL 测试栈 | PASS，7/7 healthy |
| 本地保留数据栈 | PASS，7/7 healthy |
| `GET /health/ready` | PASS，database/redis/configuration=available |
| Celery inspect ping | PASS，1 node online / pong |

测试警告中值得跟踪：

- pytest 有 25 条已知警告，未导致失败；
- E2E 的测试专用 HMAC Secret 少于 SHA-256 推荐的 32 字节，触发 PyJWT 警告；
- ECharts 生产 chunk 超过 500 KB；
- 本地 Celery Worker 以 root 运行，适用于当前容器开发环境，不适用于生产加固标准。

## 14. 本次安全修复与实际编辑文件

以下文件是本次接手过程中实际编辑过的范围；工作树中的其他大量改动在接手前已存在，不归因于本次验收：

- `backend/apps/notifications/migrations/0002_alter_notification_id.py`：补齐 migration state，数据库 no-op；
- `backend/apps/notifications/serializers.py`、`views.py`：修正 OpenAPI 请求/响应模型；
- `backend/apps/stores/serializers.py`、`views.py`：声明当前上下文真实响应；
- `backend/apps/recommendations/views.py`：声明无请求体操作；
- `backend/apps/knowledge/views.py`：消除 OpenAPI operationId 冲突；
- `backend/apps/permissions/management/commands/seed_accounts.py`：移除硬编码和输出密码；
- `frontend/src/shared/layouts/AppLayout.vue`：恢复 RouterView、真实导航和帮助按钮可访问名称；
- `frontend/src/features/auth/pages/LoginPage.vue`：登录后进入真实工作台；
- `frontend/src/shared/styles/base.css`：导航样式；
- `frontend/src/shared/components/DirectoryBreadcrumb.vue`：模板 lint 修正；
- `frontend/eslint.config.js`：由 TypeScript 负责全局名检查；
- `frontend/src/app/App.spec.ts`：同步当前品牌/首页行为；
- `frontend/e2e/global-setup.ts`：随机密码参数安全传递；
- `frontend/e2e/navigation-workflow.spec.ts`：同步真实导航与交互；
- `frontend/e2e/v1-workflow.spec.ts`：同步错误码和用户菜单流程；
- `openapi/schema.yaml`：按 MySQL 后端和当前 API 重新生成；
- `frontend/src/shared/api/generated/schema.d.ts`：按 OpenAPI 重新生成。

所有修改均未提交、未暂存，等待人工审阅。当前工作树不是可直接发布的干净制品。

## 15. 未完成事项与风险分类

### BLOCKED_BY_REAL_SAMPLE

- Sponsored Products Campaign/Targeting/Search Term 字段和粒度仍需真实、脱敏导出最终验证；
- Excel 工作表、编码、超大文件和 Amazon 不同导出版本兼容仍需真实样例；
- 优化效果和广告收益不能由 Mock/fixture 验证。

### NOT_VERIFIED

- 未进行真实 Amazon Ads API、第三方广告数据商或真实 LLM 调用，且 V1 明确禁止；
- 未执行长时间稳定性、峰值负载、灾备恢复、跨机部署和浏览器兼容矩阵；
- 未逐项人工审阅全部 2,800+ 行既有脏工作树差异；
- 当前标签与实际运行代码不一致，尚未形成新的受控 RC 标签。

### RESERVED_BY_SCOPE

- Sponsored Brands、Sponsored Display、库存、订单、采购、物流、财务；
- 自动在线执行广告变更；
- 跨 Tenant 聚合、多级审批、跨币种直接汇总；
- 微服务、Kafka、Kubernetes、复杂 RAG/向量平台。

### PRODUCTION_HARDENING

- 修复 Knowledge/Tenants View 直接 ORM 的架构边界例外；
- 使用不少于 32 字节的测试/生产 HMAC Secret，并接入正式 Secret 管理；
- 非 root 运行 Worker，配置 TLS、Secure Cookie、生产域名、备份、监控、告警和日志保留；
- 对 ECharts 做按需分包；
- 清理并审阅脏工作树，恢复或确认被删除的 `actionApi.ts`，形成审阅通过的提交和标签；
- 评估通知 API 尾斜杠产生的 301；
- 将 Nginx 上游解析/应用滚动重建写入运维流程，避免单独重建应用后的旧 IP 502。

## 16. 最终验收表

| 项目 | 状态 |
| --- | --- |
| 仓库和工作区已检查 | PASS |
| 技术栈由实际文件确认 | PASS |
| Docker Desktop / Compose 可用 | PASS |
| MySQL/Redis 保留卷未破坏 | PASS |
| 迁移历史只读诊断完成 | PASS |
| 当前库迁移和结构一致 | PASS |
| 全新 MySQL 可从零迁移 | PASS |
| Django/Frontend/Celery/Nginx 可启动 | PASS |
| 本地 7 服务 healthy | PASS |
| 隔离测试 7 服务 healthy | PASS |
| Ready 依赖检查 | PASS |
| 登录和刷新恢复 | PASS |
| API 真实读取 MySQL | PASS |
| 浏览器展示 API/DB 数据 | PASS |
| 无关键 CORS/500 | PASS |
| 前后端独立开发方式 | PASS |
| OpenAPI/TS 类型同步 | PASS |
| 后端/前端/E2E 测试 | PASS |
| 所有 View 均符合 Service/Selector 边界 | FAIL |
| 工作树干净且发布可追溯 | FAIL |
| 真实 Amazon 报表最终验证 | BLOCKED |
| 生产安全、容量和灾备验收 | NOT VERIFIED |
| Production Ready | FAIL |

## 17. 阶段交付摘要

1. 本阶段目标：接手 RC1 后续代码，安全确认完整运行和真实前后端数据库链路。
2. 检查的现有文件：主规格、PLANS、决策日志、依赖锁、Django/Vite/Nginx/Celery/OpenAPI/Compose 配置、迁移和相关业务实现。
3. 修改文件：见第 14 节。
4. 新增文件：通知兼容迁移、本报告；E2E/通知等其他未跟踪文件在接手前已存在或属于既有工作树。
5. 依赖变化：本次未新增依赖，只按锁文件安装。
6. 数据库迁移：普通应用通知 0002 no-op 迁移；未 fake、未删除记录、未改业务数据。
7. 新增接口：本次未新增业务接口，只校正 Schema 声明。
8. 新增页面：本次未新增业务页面，只恢复现有路由和导航可达性。
9. 更新文档：新增本报告。
10. 实际命令：见第 13 节。
11. 测试通过/失败/跳过：最终后端 122/0/0；前端 50/0/0；E2E 5/0/0。
12. 未执行或无法验证：见第 15 节。
13. 对既有契约影响：OpenAPI 响应模型更准确；MySQL 正整数上限与快照同步；生成类型零漂移。
14. 遗留风险：见第 15 节。
15. 当前启动方法：第 6—8 节。
16. 当前演示链路：登录 → 上下文 → 导入 → 分析 → 建议 → Action Preview → 审批 → 人工执行 → 效果评估 → 审计。
17. 下一阶段建议：先冻结和人工审阅当前脏工作树、补齐架构边界与生产安全项；未获得阶段授权前不扩展下一业务范围。
