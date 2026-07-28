# Docker Compose 部署

## Compose 文件

| 文件 | 用途 | 应用运行方式 |
|---|---|---|
| `compose.local.yml` | 本地开发 | Django runserver + Vite dev server |
| `compose.test.yml` | 隔离测试 | Gunicorn + 生产前端镜像 + tmpfs MySQL |
| `compose.prod.yml` | 生产结构 | Gunicorn + 静态 Nginx 前端 |

三个文件均包含 MySQL、Redis、migrate、backend、celery-worker、celery-beat、frontend、nginx。`migrate` 使用 `tools` profile，必须显式调用。

## 固定镜像

- `python:3.13.3-slim-bookworm`
- `node:24.10.0-alpine3.22`
- `mysql:8.4.6`
- `redis:7.4.5-alpine3.21`
- `nginx:1.28.0-alpine`

本地构建镜像使用项目版本标签 `0.1.0-local`、`0.1.0-test`、`0.1.0`，没有 `latest`。

## 常用命令

```powershell
# 构建
docker compose -f compose.local.yml build backend frontend

# 重建并启动
docker compose -f compose.local.yml up -d --build

# 独立迁移
docker compose -f compose.local.yml --profile tools run --rm migrate

# Celery 验证
docker compose -f compose.local.yml exec backend python manage.py celery_smoke --timeout 30

# Nginx 配置
docker compose -f compose.local.yml exec nginx nginx -t

# 查看状态
docker compose -f compose.local.yml ps
```

## 健康与依赖

- MySQL：`mysqladmin ping`
- Redis：`redis-cli ping`
- backend：`/health/ready`
- frontend：本地请求 `/`；生产镜像请求 `/frontend-health`
- nginx：代理 `/health/live`

backend、worker 和 beat 等待 MySQL/Redis 健康，但不会执行迁移。部署系统必须在切流前显式运行迁移并检查退出码。
