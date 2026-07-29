# DEMO-MILESTONE 验证报告

> 历史检查点说明：本文件记录 `3023e84` / `demo-milestone` 当时的结果，
> 不代表当前 HEAD 的重新验收。2026-07-28 当前复核的 Playwright 为
> `NOT VERIFIED`；请以根目录 `V1_VERIFIED_DELIVERY_REPORT.md` 和
> `V1_ACCEPTANCE_MATRIX.md` 为准。

版本基线：`9f1806c feat: complete v1 frontend workflow`  
验证日期：2026-07-28  
数据：全部为 `.invalid` 演示账号和仓库内虚构 fixture。

## 演示检查结果

| # | 检查项 | 实际验证方式 | 结果 | 证据/限制 |
|---|---|---|---|---|
| 1 | 登录、刷新恢复、退出 | Chrome Playwright + 后端认证测试 | PASS | E2E reload 触发 refresh/me，末尾 logout 回登录页 |
| 2 | 四级上下文选择 | Chrome Playwright + 权限测试 | PASS | 显式选择 Tenant、Store、Marketplace、Profile |
| 3 | Campaign 正常导入 | Chrome Playwright + 报表测试 | PASS | `campaign-anomalous.csv` 1 行完整成功 |
| 4 | Campaign 部分错误导入 | 后端集成测试 | PASS | `campaign-partial-errors.csv` 验证合法行和错误行并存 |
| 5 | Campaign 指标 | Chrome Playwright + analytics 测试 | PASS | Dashboard 读取真实 DailyMetric |
| 6 | ACOS 异常 | Chrome Playwright +规则边界测试 | PASS | 页面显示 High ACOS Campaign 与“异常” |
| 7 | Mock Recommendation | Chrome Playwright + Schema/API 测试 | PASS | 四 Agent、统一 Schema、预算建议 |
| 8 | Action Preview | Chrome Playwright + API 集成测试 | PASS | 内容哈希、版本冻结 |
| 9 | 单级审批 | Chrome Playwright + PERSONAL/TEAM 测试 | PASS | PERSONAL Owner 通过；TEAM 自批拒绝由后端测试证明 |
| 10 | 人工执行回填 | Chrome Playwright +幂等 API 测试 | PASS | SUCCEEDED 回填，不调用 Amazon API |
| 11 | 审计日志 | Chrome Playwright +只追加测试 | PASS | 页面查询 `EXECUTION_RECORDED`；删除被拒绝 |

## 启动与账号

```powershell
docker compose -f compose.local.yml up -d mysql redis
docker compose -f compose.local.yml --profile tools run --rm migrate

$env:DEMO_USER_PASSWORD = Read-Host "输入本机临时演示密码"
docker compose -f compose.local.yml run --rm -e DEMO_USER_PASSWORD backend python manage.py seed_demo_context --email demo@example.invalid
Remove-Item Env:DEMO_USER_PASSWORD

docker compose -f compose.local.yml up -d backend celery-worker celery-beat frontend nginx
docker compose -f compose.local.yml ps
```

访问 `http://localhost:8080/`，邮箱为 `demo@example.invalid`，密码是操作者刚输入且未写入仓库的临时值。

## Fixtures

- 正常多 Campaign：`tests/fixtures/reports/campaign-valid.csv`
- 高 ACOS 演示：`tests/fixtures/reports/campaign-anomalous.csv`
- 部分错误：`tests/fixtures/reports/campaign-partial-errors.csv`
- Targeting：`tests/fixtures/reports/targeting-valid.csv`
- Search Term：`tests/fixtures/reports/search-term-valid.csv`

## 备用演示方案

浏览器不可用时，执行后端全量测试和 `backend/tests/test_optimization_workflow.py` 的 API 闭环测试，并用 `pnpm --dir frontend test` 验证页面逻辑。Docker 不可用时，可运行 `pnpm --dir frontend test:e2e`；它使用独立 SQLite、隔离端口 18000/15173 和本机 Chrome。

## 未充分验证

真实 Amazon 导出列名/编码/工作表仍被真实样例阻塞；只验证 Chrome，未验证 Firefox/WebKit；未调用真实 LLM、第三方来源或 Amazon Ads 写接口；性能目标尚未实测。
