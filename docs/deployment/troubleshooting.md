# 故障排查

## Docker Engine 不可用或无权限

症状：Compose 无法连接 Docker Desktop/Engine，或命名管道返回权限错误。

处理：

1. 启动 Docker Desktop。
2. 等待 `docker info` 返回 Server 信息。
3. 确认当前用户有访问 Docker Engine 的权限。

## readiness 返回 503

```powershell
curl.exe -i http://localhost:8080/health/ready
docker compose -f compose.local.yml ps
docker compose -f compose.local.yml logs --tail 100 mysql redis backend
```

响应只会标记 database、redis 或 configuration 是否可用。检查容器环境，不要把密码或连接串贴入公共日志。

## MySQL `Access denied`

宿主机运行管理命令时，Compose 内的 `DB_HOST=mysql` 不适用；应使用 `127.0.0.1` 并显式提供本地开发密码。Phase 1 实测一次未设置 `DB_PASSWORD` 的 `migrate --check` 因 `using password: NO` 失败，补充正确本地环境变量后通过。

## Vitest/Vite `spawn EPERM`

受限执行环境可能禁止 esbuild 子进程。确认依赖锁定后，在允许子进程的本机或 CI 环境执行：

```powershell
pnpm --dir frontend test
pnpm --dir frontend build
```

本项目 Phase 1 已在允许子进程的环境中实际通过。

## uv 无法访问缓存或 PyPI

为当前工作区设置可写缓存目录：

```powershell
$env:UV_CACHE_DIR = 'C:\path\to\workspace\.uv-cache'
uv sync --project backend --frozen
```

网络受限时，首次安装或 PEP 517 隔离构建仍需要可访问的包源。不得删除锁文件来绕过。

## Celery 没有结果

```powershell
docker compose -f compose.local.yml ps redis celery-worker
docker compose -f compose.local.yml logs --tail 100 celery-worker
docker compose -f compose.local.yml exec backend python manage.py celery_smoke --timeout 30
```

local Worker 以开发镜像 root 用户运行会产生 Celery 安全警告；生产镜像使用 uid 10001。该警告不应在生产结构中忽略。

## Nginx 未透传 requestId

当前配置使用 `$http_x_request_id`，由 Django 在缺失或非法时生成。修改配置后：

```powershell
docker compose -f compose.local.yml exec nginx nginx -t
docker compose -f compose.local.yml exec nginx nginx -s reload
```
