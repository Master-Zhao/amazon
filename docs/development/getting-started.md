# 开发者起步

先阅读根目录 `README.md`、`AGENTS.md`、主规格和
`docs/requirements/requirement-coverage-matrix.md`。运行锁定依赖：

```powershell
uv sync --project backend --frozen
pnpm --dir frontend install --frozen-lockfile
```

推荐日常方式是 Compose 运行 MySQL/Redis，宿主运行 Django/Vite；完整命令见
README。创建演示上下文使用 `seed_demo_context`，报表 fixture 位于
`tests/fixtures/reports/`。提交前按 `testing-a-change.md` 选择受影响检查。

不要进入 `amazon-ads-operations-0.1.1`，不要提交 `.env`、SQLite、media、
测试报告或真实报表。Windows 和 Unix 环境变量语法差异见 README。
