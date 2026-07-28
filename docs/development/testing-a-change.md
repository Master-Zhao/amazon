# 测试变更

最小检查：

```powershell
uv run --project backend python backend/manage.py check
uv run --project backend python backend/manage.py makemigrations --check --dry-run
uv run --project backend pytest backend -q
pnpm --dir frontend lint
pnpm --dir frontend typecheck
pnpm --dir frontend test
pnpm --dir frontend build
uv run --project backend python backend/manage.py spectacular --file openapi/schema.yaml --validate
pnpm --dir frontend generate:api
git diff --check
```

认证/权限/业务闭环变更再运行 `pnpm --dir frontend test:e2e`。数据库约束或查询
变更必须用 `compose.test.yml` 验证空 MySQL 迁移；Compose 文件变化时检查三套
config 并运行受影响环境。测试报告必须写真实 passed/failed/skipped 和未执行
原因，不把 SQLite、烟雾或计划命令描述为生产验证。
