# 本地开发

## 前置条件

- Docker Desktop / Docker Engine + Compose v2
- Node.js 24 与 pnpm 11（仅宿主机前端开发需要）
- uv；uv 可按 `backend/pyproject.toml` 自动选择 Python 3.13

本机默认 Python 3.12 不应直接运行后端。使用 `uv run --project backend ...` 或容器中的 Python 3.13。

完整变量、默认值与敏感性见 [环境变量矩阵](environment-variables.md)。`config.settings.local` 明确读取 `DJANGO_DEBUG`，未设置时默认为 `true`；test 与 prod 始终关闭 DEBUG。

## 全容器模式

```powershell
# 检查配置
docker compose -f compose.local.yml config --quiet

# 启动依赖
docker compose -f compose.local.yml up -d mysql redis

# 首次或有新迁移时单独执行
docker compose -f compose.local.yml --profile tools run --rm migrate

# 启动应用
docker compose -f compose.local.yml up -d backend celery-worker celery-beat frontend nginx

# 状态与日志
docker compose -f compose.local.yml ps
docker compose -f compose.local.yml logs -f backend celery-worker celery-beat frontend nginx
```

入口：

- 应用：`http://localhost:8080/`
- 运行诊断：`http://localhost:8080/diagnostics/health`
- OpenAPI UI：`http://localhost:8080/api/docs/`
- 后端直连：`http://localhost:8000/`
- Vite 直连：`http://localhost:5173/`

停止服务但保留数据：

```powershell
docker compose -f compose.local.yml stop
```

移除项目容器和网络但保留命名卷：

```powershell
docker compose -f compose.local.yml down
```

只有明确要丢弃本地 MySQL/Redis 数据时才可另行使用 `down --volumes`；它是破坏性操作，不是日常命令。

## 混合开发

容器运行 MySQL/Redis：

```powershell
docker compose -f compose.local.yml up -d mysql redis
```

宿主机后端需设置 `DB_HOST=127.0.0.1`、本地 DB 密码及 localhost Redis URL，然后：

```powershell
uv sync --project backend --frozen
uv run --project backend python backend/manage.py migrate
uv run --project backend python backend/manage.py runserver
```

前端：

```powershell
pnpm --dir frontend install --frozen-lockfile
pnpm --dir frontend dev
```

不要把 `.env.example` 中的占位凭据用于共享或生产环境。
