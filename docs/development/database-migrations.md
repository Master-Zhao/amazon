# 数据库迁移

模型修改后运行：

```powershell
uv run --project backend python backend/manage.py makemigrations
uv run --project backend python backend/manage.py makemigrations --check --dry-run
uv run --project backend python backend/manage.py migrate
```

再用 `compose.test.yml` 从空 MySQL 8.4 执行测试。已在共享环境执行的迁移不能
编辑，只能新增。表名必须使用项目允许的前缀；自然键、Tenant/Profile 外键、
查询索引和回滚风险必须在迁移审阅中说明。数据迁移应幂等，批量处理并避免一次
加载全部数据。
