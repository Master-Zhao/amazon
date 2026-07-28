# V1 演示脚本

## 演示前检查

```powershell
docker compose -f compose.local.yml config --quiet
docker compose -f compose.local.yml ps
curl.exe http://localhost:8080/health/live
curl.exe http://localhost:8080/health/ready
```

演示账号不提供内置密码。用 `DEMO_USER_PASSWORD` 临时环境变量执行：

```powershell
docker compose -f compose.local.yml run --rm -e DEMO_USER_PASSWORD backend python manage.py seed_demo_context --email demo@example.invalid
```

主 fixture：`tests/fixtures/reports/campaign-anomalous.csv`。备用：`campaign-valid.csv`、`campaign-partial-errors.csv`。

## 17 步主演示

1. 打开 `/login`。输入 `demo@example.invalid` 和现场临时密码。页面进入工作台；后端签发内存 Access Token 和 HttpOnly Refresh Cookie。讲解：“Token 不落 localStorage。”
2. 刷新页面。仍显示工作台；后端执行 refresh → me。讲解：“这是会话恢复，不是前端假登录。”
3. 点击“选择卖家空间”。依次选择 Tenant、Store、Marketplace、Profile。讲解：“所有选项来自后端授权集合。”
4. 点击“数据中心”。选择 Campaign Report。
5. 上传 `campaign-anomalous.csv`。页面显示任务 ID；后端流式保存并在事务提交后派发 Celery。
6. 查看任务变为 `SUCCEEDED`、失败行 0。若 Worker 延迟，等待后刷新；不要口头宣称成功。
7. 点击工作台中的 Campaign 列表，查看 `High ACOS Campaign` 和 USD 预算。
8. 点击“广告分析”，查看 Spend、Sales、ACOS 和趋势图。讲解：“Dashboard 只汇总 Campaign 事实。”
9. 查看 Campaign 行的“异常”。后端依据版本化 HIGH_ACOS 规则产生，不由 LLM 判定。
10. 点击“智能优化”，点击“运行四 Agent 分析”。页面显示 SUCCEEDED、Agent 数 4。
11. 查看 `UPDATE_CAMPAIGN_BUDGET` Recommendation、before/after、风险和原因。
12. 勾选建议，点击“冻结版本并提交审批”。后端创建 Preview、内容哈希并冻结版本。
13. 页面显示 `PENDING_APPROVAL`。讲解：“提交后的版本不可修改。”
14. PERSONAL 演示账号点击“审批通过”。页面显示 `APPROVED`。说明 TEAM/COMPANY 提交人自批会返回 403。
15. 点击“审批执行”，查看版本、审批记录和人工执行清单。强调系统没有调用 Amazon。
16. 点击“确认成功”。页面显示执行项 `SUCCEEDED`，后端写只追加 ExecutionRecord。
17. 打开 `/audit` 查看 `EXECUTION_RECORDED`，然后退出登录。讲解：“requestId 串起动作链；退出会撤销 Refresh。”

## 异常与备用

- 部分错误：上传 `campaign-partial-errors.csv`，预期 `PARTIAL_SUCCEEDED`、成功 1、失败 1，并显示行错误。
- 浏览器不可用：运行 `pnpm --dir frontend test:e2e`；仍失败时展示 API 集成测试结果与本脚本。
- Docker 不可用：不要改 8000 未知进程；E2E 使用 18000/15173。
- Demo 数据已存在：重复文件会标记 duplicate，但创建新 Upload/Task；如需干净演示，应使用新的本地演示数据库，不删除未知数据。
