# 端到端验收

自动链路：

```powershell
pnpm --dir frontend test:e2e
```

Playwright 在 18000/15173 启动隔离 Django/Vite，执行登录、刷新恢复、四级上下文、
上传 `tests/fixtures/reports/campaign-anomalous.csv`、查询导入、指标/ACOS 异常、
Mock 分析、Recommendation、Preview、审批、人工执行回填和审计日志。

RETURNED 新版本、11 类 Action 的确定性校验、附件存储调用和效果评估基础任务由
后端自动测试验证；它们尚未全部进入单条浏览器链路。真实 Amazon CSV/XLSX、
真实 Provider、TLS、生产备份恢复与正式容量压测不在此验收中。
