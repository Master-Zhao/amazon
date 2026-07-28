# 生产部署基线

本文件说明 Phase 1 的单机 Compose 结构，不是高可用或性能承诺。

## 配置准备

复制 `.env.example` 为受控的生产环境文件，并替换所有 `replace-with-*` 值。至少设置：

- `DJANGO_SECRET_KEY`
- `DJANGO_ALLOWED_HOSTS`
- `DB_NAME`、`DB_USER`、`DB_PASSWORD`、`MYSQL_ROOT_PASSWORD`
- `REDIS_URL`、`CELERY_BROKER_URL`、`CELERY_RESULT_BACKEND`
- 最小化的 `CORS_ALLOWED_ORIGINS`、`CSRF_TRUSTED_ORIGINS`
- `APP_VERSION`、`GIT_COMMIT`、`BUILD_TIME`
- Cookie 与 TLS 相关选项
- JWT TTL、Refresh Cookie、轮换与吊销预留选项

生产必须使用 `config.settings.prod`、`DEBUG=False`。真实密钥不得提交 Git、进入镜像构建参数或打印到日志。
完整 local/test/prod 变量矩阵和校验规则见 [环境变量矩阵](environment-variables.md)。Phase 1 只预留并校验 JWT 配置，不实现认证或 Token 签发。

## 发布顺序

```powershell
docker compose --env-file .env.prod -f compose.prod.yml config --quiet
docker compose --env-file .env.prod -f compose.prod.yml build backend frontend
docker compose --env-file .env.prod -f compose.prod.yml up -d mysql redis
docker compose --env-file .env.prod -f compose.prod.yml --profile tools run --rm migrate
docker compose --env-file .env.prod -f compose.prod.yml up -d backend celery-worker celery-beat frontend nginx
docker compose --env-file .env.prod -f compose.prod.yml ps
```

迁移失败时不得继续启动或切流。生产后端镜像以 uid 10001 的 `appuser` 运行，使用 Gunicorn；生产前端是构建后的静态文件，不运行 Vite。

## TLS 与边界

Compose 中的 Nginx 当前监听 HTTP 80。正式生产应由可信负载均衡器或补充的 TLS 配置终止 HTTPS，并正确传递 `X-Forwarded-Proto=https`。启用 `SECURE_SSL_REDIRECT` 前必须确认代理头，否则会产生重定向问题。

MySQL 和上传目录使用持久卷。Redis 即使持久化也不能承载唯一业务事实。备份与恢复步骤见 [备份与恢复](backup-and-restore.md)，但真实恢复演练尚未完成；TLS 证书、监控、告警、滚动发布、多实例 Beat 选主与灾难恢复不在本次最小 M6 实施范围。

## 回滚

- 应用回滚：保留上一版本镜像标签，将 Compose 引用切回并重新创建应用容器。
- 数据库回滚：默认采用前向修复；迁移发布前必须备份。不得擅自逆转有数据损失风险的迁移。
- 静态资源回滚：前端镜像与应用版本一起回退。

Phase 1 只有初始 User 迁移，尚无业务数据迁移。

## Phase 1 最终运行证据

2026-07-28 使用 `.env.example` 的无秘密占位值和临时 `SECURE_SSL_REDIRECT=false` 完成独立 prod Compose 验收：

- MySQL 从零迁移成功。
- backend 以 uid 10001 运行 Gunicorn master 与 3 个 workers。
- frontend 运行 Nginx 并提供 Vite production build，不运行 Vite dev server。
- 外层 Nginx 的 `/`、`/health/live`、`/health/ready` 均返回 HTTP 200，健康接口 requestId 头/体一致。
- 验收后执行 `docker compose ... down` 停止 prod 容器和网络；local 服务未受影响。

该证据只验证 Phase 1 单机生产结构，不代表 TLS、高可用、监控、备份或性能目标已经完成。
