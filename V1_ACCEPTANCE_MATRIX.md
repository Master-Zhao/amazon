# V1 真实用户路径验收矩阵

日期：2026-07-28
当前修复提交：`396a52f`（Stage 5）；Stage 6 文档提交见最终 Git 记录。

状态含义：

- `IMPLEMENTED_AND_TESTED`：至少有自动 API/Service/组件或 Docker 实测证据。
- `IMPLEMENTED_NOT_FULLY_VERIFIED`：代码可操作，但缺少要求的真实浏览器或完整分支证据。
- `NOT_IMPLEMENTED`：没有满足要求的真实 API/UI。

本轮 Playwright 两次均在浏览器启动前因旧固定 SQLite 迁移历史失败。已改成
每次运行唯一 SQLite 文件，但按“两次上限”未第三次执行。因此下表不能把
组件/API 通过写成浏览器 E2E PASS。

| # | 用户路径 | 存在/可操作 | 前端路由 | API | Service/Selector | 数据库表 | 测试 | 当前结果 | 修复提交 | 验收证据 |
|---:|---|---|---|---|---|---|---|---|---|---|
| 1 | 登录 | 是/是 | `/login` | `POST /auth/login` | accounts auth service | `sys_user`,`sys_refresh_token`,`audit_auth_event` | `test_authentication.py`, Login spec | IMPLEMENTED_AND_TESTED；浏览器 NOT VERIFIED | `3106841`,`396a52f` | API 及 Docker HTTP 登录 SUCCESS |
| 2 | 登录失败提示 | 是/是 | `/login` | `POST /auth/login` | accounts auth service | `audit_auth_event` | auth failure/前端 spec | IMPLEMENTED_AND_TESTED；浏览器 NOT VERIFIED | `3106841` | 错误码与页面错误状态测试 |
| 3 | 刷新后恢复登录 | 是/是 | `/` | `POST /auth/refresh`,`GET /auth/me` | token rotation service | `sys_refresh_token` | refresh/replay/httpClient tests | IMPLEMENTED_AND_TESTED；浏览器 NOT VERIFIED | `3106841`,`396a52f` | 并发 refresh 与 me 自动测试 |
| 4 | 退出登录 | 是/是 | 全局顶栏 | `POST /auth/logout` | revoke refresh service | `sys_refresh_token`,`audit_auth_event` | logout tests/App spec | IMPLEMENTED_AND_TESTED；浏览器 NOT VERIFIED | `3106841`,`396a52f` | Token 撤销自动测试 |
| 5 | Tenant 列表 | 是/是 | `/context` | `GET /context/tenants` | stores context selectors | `org_tenant`,`org_tenant_membership` | context API/store tests | IMPLEMENTED_AND_TESTED | `3106841`,`396a52f` | Docker HTTP tenantCount=1 |
| 6 | Tenant 切换 | 是/是 | `/context` | Tenant 下级查询 | context selectors | org/ads context tables | tenantContext specs、404 tests | IMPLEMENTED_AND_TESTED；多 Tenant 浏览器 NOT VERIFIED | `396a52f` | 切换清空下级组件测试 |
| 7 | Store 选择 | 是/是 | `/context` | `GET .../stores` | store selector | `ads_store` | context tests | IMPLEMENTED_AND_TESTED | `3106841`,`396a52f` | Docker HTTP storeCount=1 |
| 8 | Marketplace 选择 | 是/是 | `/context` | `GET .../marketplaces` | marketplace selector | `ads_store_marketplace`,`ads_marketplace` | context tests | IMPLEMENTED_AND_TESTED | `396a52f` | Docker HTTP marketplaceCount=1 |
| 9 | Profile 选择 | 是/是 | `/context` | `GET .../profiles` | profile scope selector | `ads_advertising_profile`, profile grants | permission/context tests | IMPLEMENTED_AND_TESTED | `396a52f` | Docker HTTP profileCount=1 |
| 10 | Campaign 上传 | 是/是 | `/reports/imports` | `POST .../uploads` | `reports.create_report_import` | report upload/task | report API/组件 tests | IMPLEMENTED_AND_TESTED | `4ebaa82`,`396a52f` | Docker multipart→202→SUCCEEDED |
| 11 | Targeting 上传 | 是/是 | `/reports/imports` | 同上，`TARGETING` | report parser/service | report/ads targeting tables | CSV/XLSX fixture tests | IMPLEMENTED_AND_TESTED；浏览器 NOT VERIFIED | `4ebaa82`,`396a52f` | fixture 集成测试 |
| 12 | Search Term 上传 | 是/是 | `/reports/imports` | 同上，`SEARCH_TERM` | report parser/service | report/ads search term tables | CSV/XLSX fixture tests | IMPLEMENTED_AND_TESTED；浏览器 NOT VERIFIED | `4ebaa82`,`396a52f` | fixture 集成测试 |
| 13 | ImportTask 创建 | 是/是 | `/reports/imports` | upload/task list | report service/selector | `report_import_task` | upload 202 tests | IMPLEMENTED_AND_TESTED | `4ebaa82` | Docker task id=1 |
| 14 | Celery 导入 | 是/是 | 状态轮询 | Celery task | `reports.process_report_import` | report/ads/analytics tables | Celery/report tests | IMPLEMENTED_AND_TESTED | `4ebaa82`，Stage 6 Compose | 当前 Docker worker 处理 SUCCEEDED |
| 15 | 导入状态查看 | 是/是 | `/reports/imports` | `GET .../tasks` | report selector | `report_import_task` | selector/组件 tests | IMPLEMENTED_AND_TESTED | `396a52f` | 轮询到终态 |
| 16 | PARTIAL_SUCCEEDED | 是/是 | `/reports/imports` | task list | parser/service | task/batch/error | partial fixture test | IMPLEMENTED_AND_TESTED；浏览器 NOT VERIFIED | `4ebaa82`,`396a52f` | 1 成功/1 错误集成测试 |
| 17 | 行级错误 | 是/是 | `/reports/imports` | `GET .../errors` | report selector | `report_import_row_error` | task/error API + component | IMPLEMENTED_AND_TESTED；浏览器 NOT VERIFIED | `396a52f` | 错误明细表组件测试 |
| 18 | Campaign 指标 | 是/是 | `/campaigns` | analytics campaign metrics | analytics selector | `analytics_campaign_daily_metric` | analytics/report/component | IMPLEMENTED_AND_TESTED | `f2cc5b5`,`396a52f` | Decimal/currency/API tests |
| 19 | Targeting 指标 | 是/是 | `/targeting` | targeting metrics | analytics selector | `analytics_targeting_daily_metric` | fixture/API/component | IMPLEMENTED_AND_TESTED | `f2cc5b5`,`396a52f` | 独立事实测试 |
| 20 | Search Term 指标 | 是/是 | `/search-terms` | search-term metrics | analytics selector | `analytics_search_term_daily_metric` | fixture/API/component | IMPLEMENTED_AND_TESTED | `f2cc5b5`,`396a52f` | 独立事实测试 |
| 21 | 分母为零 | 是/是 | 三指标页 | analytics APIs | calculation service | 三类 metric/revision | zero denominator tests | IMPLEMENTED_AND_TESTED | `f2cc5b5` | `value:null` + reason |
| 22 | 禁止跨币种汇总 | 是/是 | `/dashboard` | dashboard API | dashboard selector | campaign metric | currency grouping test/spec | IMPLEMENTED_AND_TESTED | `f2cc5b5`,`396a52f` | Marketplace+currency 分组 |
| 23 | 异常列表 | 是/是 | `/campaigns` | campaign metrics | anomaly evaluator/selector | `analytics_anomaly_record` | anomaly/API/component | IMPLEMENTED_AND_TESTED | `f2cc5b5`,`396a52f` | HIGH_ACOS 记录 |
| 24 | 异常详情 | 是/基本 | `/campaigns`,`/campaigns/:id` | metric/detail APIs | analytics selectors | anomaly rule/record | detail API/component | IMPLEMENTED_NOT_FULLY_VERIFIED | `396a52f` | 有规则/版本/说明；无浏览器详情验收 |
| 25 | 四 Agent 运行 | 是/是 | `/analysis` | `POST .../runs` | orchestrator → provider | `agent_run`,`ai_llm_invocation` | schema/orchestrator/API | IMPLEMENTED_AND_TESTED | `f2cc5b5`,`65fc150`,`396a52f` | 4 invocation，重试幂等 |
| 26 | Agent 输出详情 | 部分/部分 | `/analysis` | run list | agent selector | `agent_run`,`ai_llm_invocation` | schema tests | IMPLEMENTED_NOT_FULLY_VERIFIED | `396a52f` | 页面有状态/错误，未完整展示统一输出 |
| 27 | Recommendation 列表 | 是/是 | `/analysis` | recommendations list | recommendation selector | `ai_recommendation` | API/component tests | IMPLEMENTED_AND_TESTED | `f2cc5b5`,`396a52f` | Mock 结构化建议 |
| 28 | Recommendation 详情 | 部分/是 | `/analysis` | list/revision APIs | recommendation service | recommendation/revision | API/component tests | IMPLEMENTED_NOT_FULLY_VERIFIED | `396a52f` | before/after/reason/risk；证据详情不足 |
| 29 | Action Preview | 是/是 | `/analysis`,`/actions` | preview create/list | actions service/selector | preview/version | workflow/API tests | IMPLEMENTED_AND_TESTED | `450b3b2`,`396a52f` | 不可变版本 |
| 30 | 提交审批 | 是/是 | `/actions` | `POST .../submit` | actions service | preview/version/audit | API/component | IMPLEMENTED_AND_TESTED | `450b3b2`,`396a52f` | DRAFT→PENDING |
| 31 | APPROVED | 是/是 | `/actions` | decision | approval service | approval record | workflow/API | IMPLEMENTED_AND_TESTED | `450b3b2`,`396a52f` | 单级审批 |
| 32 | REJECTED | 是/是 | `/actions` | decision | approval service | approval record | workflow/API | IMPLEMENTED_AND_TESTED | `450b3b2`,`396a52f` | 状态守卫 |
| 33 | RETURNED | 是/是 | `/actions` | decision | approval service | approval record | workflow/API | IMPLEMENTED_AND_TESTED | `450b3b2`,`396a52f` | RETURNED 记录 |
| 34 | WITHDRAWN | 是/是 | `/actions` | `POST .../withdraw` | withdraw service | preview/audit | workflow/API | IMPLEMENTED_AND_TESTED | `450b3b2`,`396a52f` | creator 守卫与幂等 |
| 35 | RETURNED 新版本 | 是/是 | `/actions` | `POST .../versions` | returned version service | preview/version | immutable version test | IMPLEMENTED_AND_TESTED | `450b3b2`,`396a52f` | 旧版本只追加 |
| 36 | PERSONAL Owner 自确认 | 是/是 | `/actions` | decision | approval service | tenant/membership/approval | personal owner test | IMPLEMENTED_AND_TESTED | `450b3b2` | 自动测试 |
| 37 | TEAM/COMPANY 禁止自审 | 是/API 是 | `/actions` | decision | approval service | tenant/membership/approval | separation test | IMPLEMENTED_AND_TESTED；浏览器路径 2 NOT VERIFIED | `450b3b2` | 后端返回 403 |
| 38 | 执行 SUCCEEDED | 是/是 | `/actions` | executions | manual execution service | `action_execution_record` | API/workflow | IMPLEMENTED_AND_TESTED | `450b3b2`,`396a52f` | 只追加、实际值 |
| 39 | 执行 FAILED | 是/是 | `/actions` | executions | manual execution service | execution record | workflow/API | IMPLEMENTED_AND_TESTED | `450b3b2`,`396a52f` | 状态枚举/按钮 |
| 40 | 执行 SKIPPED | 是/是 | `/actions` | executions | manual execution service | execution record | workflow/API | IMPLEMENTED_AND_TESTED | `450b3b2`,`396a52f` | 状态枚举/按钮 |
| 41 | 批量部分成功 | 否/否 | 无 | 无批量执行 API | 无 | 无批量表 | 无 | NOT_IMPLEMENTED | — | 当前仅单 Preview 执行回填 |
| 42 | 附件证据 | 是/是 | `/actions` | multipart executions | storage adapter/execution service | execution `evidence_metadata` | evidence size/type/path tests | IMPLEMENTED_AND_TESTED；浏览器 NOT VERIFIED | `450b3b2`,`396a52f` | FileStorage 哈希元数据 |
| 43 | 基础效果评估 | 是/是 | `/actions` | `POST .../evaluations` | evaluate service/task | `action_effect_evaluation` | idempotency/API tests | IMPLEMENTED_AND_TESTED；浏览器 NOT VERIFIED | `450b3b2`,`396a52f` | baseline/observed 只追加 |
| 44 | 审计日志 | 是/是 | `/audit` | `GET /audit/tenants/{id}` | audit selector | `audit_log` | append-only/API/component | IMPLEMENTED_AND_TESTED；浏览器 NOT VERIFIED | `450b3b2`,`396a52f` | 核心事件集合测试 |
| 45 | 跨 Tenant 404 | 是/API 是 | 受保护页 | 各 scope API | authorization service | org/ads scopes | cross-tenant tests | IMPLEMENTED_AND_TESTED | 既有权限提交 | 404 语义自动测试 |
| 46 | Tenant 内权限不足 403 | 是/API 是 | 受保护页 | 各 action API | authorization service | role/grant tables | permission tests | IMPLEMENTED_AND_TESTED | 既有权限提交 | 403 语义自动测试 |
| 47 | 页面无权限状态 | 部分/部分 | 七菜单及业务页 | capabilities + 业务 API | context selector | permission/grant tables | menu/page component tests | IMPLEMENTED_NOT_FULLY_VERIFIED | `396a52f` | 菜单/按钮控制；直接 URL 浏览器未验 |
| 48 | API 无权限状态 | 是/是 | 不适用 | 受保护 APIs | authorization service | permission/grant tables | 403/404/union/owner tests | IMPLEMENTED_AND_TESTED | 既有权限提交 | 后端全量测试 |
| 49 | 页面刷新 | 是/是 | 全部 | refresh/me + 页面查询 | auth/context selectors | refresh token/context tables | store/httpClient tests | IMPLEMENTED_AND_TESTED；浏览器 NOT VERIFIED | `3106841`,`396a52f` | 状态恢复自动测试 |
| 50 | Docker 重启后恢复 | 是/是 | `/reports/imports` | health/auth/task list | runtime + selectors | 持久 MySQL/Redis | HTTP smoke | IMPLEMENTED_AND_TESTED（应用容器） | Stage 6 | 18000 当前源码容器重启后 21 tasks，最新 SUCCEEDED |

## 汇总

- `IMPLEMENTED_AND_TESTED`：44 项（其中多项明确附注浏览器 `NOT VERIFIED`）。
- `IMPLEMENTED_NOT_FULLY_VERIFIED`：5 项。
- `NOT_IMPLEMENTED`：1 项（批量执行部分成功）。
- `BLOCKED_BY_REAL_SAMPLE`：矩阵外的三类真实 Amazon 脱敏报表兼容认证。
- 自动 Playwright：0 passed / 0 browser tests executed；两次均在 global setup
  的旧 SQLite 迁移历史处失败，不能写作业务测试失败或 PASS。

由于第 41 项未实现、两条 Playwright 路径未通过，不满足
`v1-framework-rc2` 的创建条件。
