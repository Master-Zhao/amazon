# V1 实现与运行状态审计

审计日期：2026-07-28

审计基线：`1f8a230 chore: establish v1 framework baseline`

审计阶段：Stage 1（只读审计，未修改数据库）

## 结论

当前仓库不能据现有 `localhost:8080` 的运行结果判定为可交付 V1。

原因是运行中的 Docker 后端绑定目录为：

```text
C:\QSZ\技术方案 - 副本\backend -> /app
```

而本次交付仓库为：

```text
C:\QSZ\技术方案
```

两者是不同 Git 谱系。运行日志证明“副本”能够完成部分真实 API/Celery
链路，但不能作为当前 `1f8a230` 仓库的验收证据。

## 保护状态

- `phase-1-complete`、`demo-milestone`、`v1-framework-rc1` 均存在且未移动。
- 当前 HEAD 为 `1f8a230`，未 reset、revert 或 checkout 覆盖。
- 当前工作区仅发现未知未跟踪目录 `backups/`；未读取、未修改、未删除、未暂存。
- 未读取或修改 `.arts/`、两份未知 DOCX、`amazon-ads-operations-0.1.1`。
- 未重启、重建或停止任何现有 Docker 容器。
- 未执行任何数据库写操作。

## 已执行的只读检查

```powershell
git status --short
git diff --stat
git diff --check
git log --oneline --decorate -20
git tag --list
docker compose -f compose.local.yml ps -a
docker inspect amazon-ads-local-backend-1 --format '{{json .Mounts}}'
docker compose -f compose.local.yml logs --tail 200 backend celery-worker celery-beat
python backend/manage.py showmigrations --plan
python backend/manage.py migrate --plan
```

还通过 MySQL `information_schema` 和只读 `SELECT` 核对了实际迁移记录、
表字段、索引、约束与关键表行数。

## Git 与运行环境

| 项目 | 实际结果 |
| --- | --- |
| 当前 HEAD | `1f8a230` |
| 已有标签 | `phase-1-complete`、`demo-milestone`、`v1-framework-rc1` |
| 未跟踪内容 | `backups/`，未知且保持排除 |
| 本仓库已跟踪改动 | 无 |
| Docker 服务 | backend、frontend、nginx、mysql、redis、celery-worker、celery-beat 全部 healthy |
| 对外端口 | Nginx 8080、backend 8000、frontend 5173、MySQL 3306、Redis 6379 |
| Docker 后端源码 | `C:\QSZ\技术方案 - 副本\backend` |
| MySQL 数据卷 | `amazon-ads-local_mysql_local_data` |

## 真实运行证据的适用范围

运行日志包含以下真实请求及成功状态：

- 登录、Tenant/Store/Marketplace/Profile 上下文查询；
- Campaign、Targeting、Search Term 三类报表上传；
- ImportTask 查询及 Celery `process_import_task`；
- Campaign、Targeting、Search Term 分析查询；
- 分析任务创建及 Celery `process_agent_run_task`；
- Recommendation 查询；
- Action Preview 创建和提交审批；
- 健康检查。

这些证据仅证明“技术方案 - 副本”与当前 MySQL 数据卷之间曾运行上述链路。
它们不证明当前 `1f8a230` 工作树可以迁移、启动或复现链路。

## 迁移图审计

### 数据库实际记录

数据库已记录的关键历史包含：

```text
advertising.0001_initial
advertising.0002_initial
advertising.0003_initial
advertising.0004_campaign_target_acos
analytics.0001_initial
analytics.0002_searchtermdailymetric_searchtermmetricrevision_and_more
analytics.0003_campaigndailymetric_snapshot_hour_local_and_more
permissions.0001_initial
actions.0001_initial
actions.0002_initial
```

### 当前仓库关键文件

当前仓库对应内容为：

```text
advertising.0001_initial
advertising.0002_initial
advertising.0001_squashed_0002_initial
advertising.0003_campaign_target_acos
advertising.0004_alter_searchterm_query_text_and_more
analytics.0001_initial
permissions.0001_initial
permissions.0002_seed_permissions
actions.0001_initial
actions.0002_actionpreview_idempotency_key_and_more
```

`python backend/manage.py migrate --plan` 的真实结果：

```text
InconsistentMigrationHistory:
Migration analytics.0001_initial is applied before its dependency
advertising.0003_campaign_target_acos
```

### 漂移范围

文件哈希对比确认，除 `accounts` 外，下列应用的已执行初始迁移在两条谱系中
均不相同：

- tenants
- stores
- permissions
- products
- reports
- advertising
- analytics
- agents
- recommendations
- actions
- audit

这不是单一字段缺失，而是历史迁移名称冲突、依赖图冲突和数据库状态冲突。

## 真实数据库结构差异

现有数据不可丢失。只读检查确认：

- `sys_permission` 只有 `id`、`code`、`name`，没有 `description`；
- `ads_campaign.id` 为 `bigint`，当前 RC1 模型使用 UUID；
- `ads_campaign` 使用 `currency_code`、`ad_product_type` 等字段，当前模型字段不同；
- actions、reports、analytics、agents、recommendations、tenants、stores、products、
  permissions、audit 的主键和字段亦存在同类差异；
- 数据库现有 3 个用户、15 条权限、2 个 Campaign、2 条 Campaign 指标和
  37 条迁移记录；
- `ads_campaign.target_acos` 已存在，且数据库已有对应索引和约束。

因此，直接运行当前迁移、用 `--fake`、修改 `django_migrations` 或重建数据库
都不安全，也不符合任务约束。

## 当前代码能力审计

### 已存在但尚未在本仓库真实运行验证

- JWT 登录、refresh Cookie、logout 和会话恢复代码；
- Tenant → Store → Marketplace → Profile 级联上下文；
- 三类报表上传、ImportTask 与解析服务；
- 三类独立事实表、指标计算和异常；
- 四 Agent、MockLLMProvider、Recommendation；
- Action Preview、审批、人工执行、审计；
- Vue 路由、API 模块、Pinia、Axios、ECharts；
- 后端测试 16 个模块、前端单元/交互测试、一个 Playwright 工作流文件；
- local/test/prod Compose 和 OpenAPI。

这些项目当前分类为 `IMPLEMENTED_NOT_FULLY_VERIFIED`，不能写成
`IMPLEMENTED_AND_TESTED`。

### 已确认缺陷

1. 当前仓库无法针对现有数据库加载完整迁移计划。
2. Docker 运行源码并非当前仓库，验收对象错位。
3. 迁移漂移覆盖 11 个业务应用，不能仅修补两个字段。
4. `sys_permission.description` 模型字段没有对应的安全后续迁移。
5. 当前前端多个页面只在首次 mount 加载，不响应 Profile/Tenant 切换。
6. Targeting 与 Search Term 页面以原始 JSON `<pre>` 展示，缺少筛选、分页、
   指标语义、loading、retry 和详情。
7. Report 页面创建任务后只查询一次，没有可靠轮询、进度、超时和完整错误摘要。
8. Action 回填将备注硬编码，缺少实际执行值、执行时间和备注输入。
9. Optimization 页面把创建 Preview 和提交审批合并，无法审阅完整版本内容；
   审批弹窗及所需上下文字段缺失。
10. Role 创建失败未捕获，成功/错误反馈和权限编辑能力不完整。
11. Audit 页面不响应 Tenant 切换，字段仅覆盖事件、对象和 requestId。
12. 现有 Playwright 证据不足以覆盖用户要求的两条完整路径和 50 项验收。

## 状态分类

| 分类 | 当前内容 |
| --- | --- |
| `IMPLEMENTED_AND_TESTED` | 仅限已直接读取验证的 Git/Docker/DB 审计事实 |
| `IMPLEMENTED_NOT_FULLY_VERIFIED` | 当前仓库中的业务代码、测试、Compose、OpenAPI |
| `RESERVED_BY_CONFIRMED_SCOPE` | Amazon Ads API、第三方报表源、真实 LLM、自动执行、Sponsored Brands、Sponsored Display |
| `BLOCKED_BY_REAL_SAMPLE` | 三类 Amazon 真实脱敏导出兼容认证 |
| `NOT_IMPLEMENTED` | 当前审计列出的完整交互、两条 E2E、50 项验收及安全迁移协调 |

## Stage 2 进入门槛

数据库写入前必须先：

1. 将现有数据卷生成可恢复备份，备份文件保持在 Git 外；
2. 固化所有已执行历史迁移的真实快照；
3. 为冲突应用设计只向前的兼容迁移，不使用 `--fake`；
4. 同时准备空数据库从零迁移和旧数据库升级测试；
5. 在复制出的测试数据库验证数据行、索引和约束不丢失后，才允许升级现有库。
