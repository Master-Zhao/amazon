# Phase 1 环境变量矩阵

本表描述当前代码实际读取或 Compose/前端构建实际传递的变量。仓库只提交 `.env.example` 的无秘密示例；不得提交真实 `.env`。`local` 默认便于本机开发，`test` 使用隔离值，`prod` 必须由部署系统注入真实秘密。

## Django、数据库与运行标识

| 变量 | 必需 | 代码默认值 | local | test | prod 建议 | 敏感 | 使用位置 |
|---|---|---|---|---|---|---|---|
| `DJANGO_SETTINGS_MODULE` | 是 | 无 | `config.settings.local` | `config.settings.test` | `config.settings.prod` | 否 | Django 入口/Compose |
| `DJANGO_SECRET_KEY` | prod 是 | local-only 不安全值 | 非生产随机值 | 测试固定值 | 密钥管理注入的高熵值 | 是 | Django 签名 |
| `DJANGO_ALLOWED_HOSTS` | prod 是 | `localhost,127.0.0.1` | 本机与容器名 | 测试入口 | 精确生产域名 | 否 | Django Host 校验 |
| `DJANGO_DEBUG` | 否 | local 为 `true` | 按需 `true/false` | 被 test 强制 `false` | 被 prod 强制 `false`，环境变量不能开启 | 否 | `settings/local.py` |
| `LOG_LEVEL` | 否 | `INFO` | `INFO`/`DEBUG` | `INFO` | `INFO` 或受控级别 | 否 | JSON 技术日志 |
| `APP_VERSION` | 否 | `0.1.0` | 开发版本 | 测试版本 | 发布版本 | 否 | API/构建标识 |
| `GIT_COMMIT` | 否 | `unknown` | `development` | `test` | 实际 commit | 否 | API/构建标识 |
| `BUILD_TIME` | 否 | `unknown` | `not-set` | `test` | UTC 构建时间 | 否 | API/构建标识 |
| `DB_NAME` | prod 建议显式 | `amazon_ads` | `amazon_ads` | `amazon_ads_test` | 独立生产库名 | 否 | Django/MySQL |
| `DB_USER` | prod 建议显式 | `amazon_ads` | 本地应用用户 | 测试用户 | 最小权限应用用户 | 否 | Django/MySQL |
| `DB_PASSWORD` | prod 是 | 空 | 仅本地占位值 | 隔离测试值 | 密钥管理注入 | 是 | Django/MySQL |
| `DB_HOST` | 否 | `127.0.0.1` | `mysql` 或混合开发 `127.0.0.1` | `mysql` | `mysql`/受控主机 | 否 | Django 数据库 |
| `DB_PORT` | 否 | `3306` | `3306` | `3306` | 实际端口 | 否 | Django 数据库 |
| `DB_CONN_MAX_AGE` | 否 | `60` | `60` | `60` | 按连接容量调整 | 否 | Django 数据库连接 |
| `DB_TEST_NAME` | test 是 | 跟随 `DB_NAME` | 不使用 | `amazon_ads_test` | 不使用 | 否 | MySQL 集成测试 |
| `USE_MYSQL_TESTS` | test 可选 | `false` | 不使用 | 容器集成时 `true` | 不使用 | 否 | `settings/test.py` |
| `MYSQL_ROOT_PASSWORD` | Compose 是 | 无 | 本地占位值 | 隔离测试值 | 密钥管理注入 | 是 | MySQL 容器初始化 |

独立远程双数据库模式仅由 `compose.remote-db.yml` 设置
`REMOTE_MULTI_DATABASE_MODE=true` 后启用，不改变 `compose.local.yml` 的本地模式：

| 变量 | 必需 | 用途 | 敏感 |
|---|---|---|---|
| `SYSTEM_DB_HOST` / `SYSTEM_DB_PORT` | 是 | 项目自有 Django 系统库地址 | 否 |
| `SYSTEM_DB_NAME` / `SYSTEM_DB_USER` / `SYSTEM_DB_PASSWORD` | 是 | `DATABASES["default"]`，承载用户、Tenant、Token、Session 与审计 | Password 是 |
| `SCM_DB_HOST` / `SCM_DB_PORT` | 是 | 既有 SCM 外部业务库地址 | 否 |
| `SCM_DB_NAME` / `SCM_DB_USER` / `SCM_DB_PASSWORD` | 是 | `DATABASES["scm_remote"]`，只读外部业务数据 | Password 是 |
| `DB_CONN_MAX_AGE` | 否 | 两个连接共享的持久连接秒数，默认 `60` | 否 |
| `REMOTE_SCM_AUTH_ENABLED` | 否 | 默认 `false`；启用 `eb_merchant_admin` 只读认证，要求已配置 `scm_remote` | 否 |

`scm_remote` 使用连接级只读事务、数据库路由拒绝迁移，并禁止与项目模型建立
跨数据库关系。部署时仍必须使用仅有 `SELECT` 权限的 SCM 数据库账号；应用层边界
不能替代数据库最小权限。

远程账号认证只读取账号 ID、商户 ID、账号、bcrypt 哈希和启停/删除状态。密码哈希
不持久化到项目库；首次认证成功后，项目系统库创建本地身份映射。部署前必须先对
项目系统库执行迁移，远程账号登录本身不会获得任何 Tenant/Profile 权限。

## Redis、Celery、HTTP Cookie 与 TLS

| 变量 | 必需 | 代码默认值 | local | test | prod 建议 | 敏感 | 使用位置 |
|---|---|---|---|---|---|---|---|
| `REDIS_URL` | 是 | `redis://127.0.0.1:6379/0` | `redis://redis:6379/0` | 同 local | 受控 Redis URL；凭据视为秘密 | 条件敏感 | readiness/应用 |
| `CELERY_BROKER_URL` | 是 | 跟随 `REDIS_URL` | DB 0 | DB 0 | 受控 broker URL | 条件敏感 | Celery broker |
| `CELERY_RESULT_BACKEND` | 否 | `redis://127.0.0.1:6379/1` | DB 1 | DB 1 | 独立短期结果 DB | 条件敏感 | Celery result |
| `CELERY_TASK_TIME_LIMIT` | 否 | `30` | `30` | `30` | 按任务类型受控调整 | 否 | Celery task |
| `CELERY_TASK_SOFT_TIME_LIMIT` | 否 | `20` | `20` | `20` | 小于 hard limit | 否 | Celery task |
| `CELERY_RESULT_EXPIRES` | 否 | `3600` | `3600` | `3600` | 有限 TTL | 否 | Celery result |
| `CORS_ALLOWED_ORIGINS` | 否 | 空 | 本机入口 | 测试入口 | 最小允许源集合 | 否 | django-cors-headers |
| `CSRF_TRUSTED_ORIGINS` | 否 | 空 | 本机入口 | 测试入口 | 精确 HTTPS 源 | 否 | Django CSRF |
| `SESSION_COOKIE_SECURE` | 否 | `false` | `false` | `false` | `true` | 否 | Django session Cookie |
| `CSRF_COOKIE_SECURE` | 否 | `false` | `false` | `false` | `true` | 否 | Django CSRF Cookie |
| `SESSION_COOKIE_SAMESITE` | 否 | `Lax` | `Lax` | `Lax` | `Lax`/经评审值 | 否 | Django session Cookie |
| `CSRF_COOKIE_SAMESITE` | 否 | `Lax` | `Lax` | `Lax` | `Lax`/经评审值 | 否 | Django CSRF Cookie |
| `SECURE_SSL_REDIRECT` | 否 | prod 为 `true` | `false` | `false` | 正确代理 HTTPS 后 `true` | 否 | `settings/prod.py` |

## JWT 后续配置位置

这些变量在 Phase 1 只读取与校验，不会创建登录接口、签发 Token 或引入硬编码 JWT 密钥。

| 变量 | 必需 | 默认值 | local | test | prod 建议 | 敏感 | 使用位置 |
|---|---|---|---|---|---|---|---|
| `JWT_ACCESS_TOKEN_TTL_MINUTES` | 否 | `15` | `15` | `15` | 安全评审后正整数 | 否 | Django settings 预留 |
| `JWT_REFRESH_TOKEN_TTL_DAYS` | 否 | `7` | `7` | `7` | 安全评审后正整数 | 否 | Django settings 预留 |
| `JWT_REFRESH_COOKIE_NAME` | 否 | `refresh_token` | 默认 | 默认 | 独立、非空名称 | 否 | Refresh Cookie 预留 |
| `JWT_REFRESH_COOKIE_PATH` | 否 | `/api/v1/auth/` | 默认 | 默认 | 最小绝对路径 | 否 | Refresh Cookie 预留 |
| `JWT_COOKIE_SECURE` | 否 | `false` | `false` | `false` | `true` | 否 | Refresh Cookie 预留 |
| `JWT_COOKIE_HTTP_ONLY` | 否 | `true` | `true` | `true` | `true` | 否 | Refresh Cookie 预留 |
| `JWT_COOKIE_SAME_SITE` | 否 | `Lax` | `Lax` | `Lax` | `Lax`/`Strict`；`None` 必须同时 Secure | 否 | Refresh Cookie 预留 |
| `JWT_ROTATE_REFRESH_TOKENS` | 否 | `true` | `true` | `true` | `true` | 否 | Refresh 轮换预留 |
| `JWT_BLACKLIST_AFTER_ROTATION` | 否 | `true` | `true` | `true` | `true` | 否 | Refresh 吊销预留 |

## 前端构建与 Compose

| 变量 | 必需 | 默认值 | local | test | prod 建议 | 敏感 | 使用位置 |
|---|---|---|---|---|---|---|---|
| `VITE_API_BASE_URL` | 否 | 空（同源） | 空/本机 API | 空 | 同源优先 | 否 | Axios 构建配置 |
| `VITE_DEV_PROXY_TARGET` | 否 | `http://backend:8000` | 容器 backend | 不使用 | 不使用 | 否 | Vite 开发代理 |
| `VITE_APP_VERSION` | 否 | `0.1.0` | 开发版本 | 测试版本 | 发布版本 | 否 | 前端构建标识 |
| `VITE_GIT_COMMIT` | 否 | `development` | 开发值 | `test` | 实际 commit | 否 | 前端构建标识 |
| `VITE_BUILD_TIME` | 否 | `not-set` | 开发值 | `test` | UTC 构建时间 | 否 | 前端构建标识 |
| `COMPOSE_PROJECT_NAME` | 否 | Compose 文件内固定 name | 可覆盖 | 可覆盖 | 避免与其他部署冲突 | 否 | Docker Compose |

## 校验规则

- 布尔值只接受 `true/false`、`1/0`、`yes/no`、`on/off`，无效值会明确失败。
- JWT TTL 必须为正整数；Cookie 名称非空；Cookie path 必须以 `/` 开头。
- `JWT_COOKIE_SAME_SITE=None` 时必须同时设置 `JWT_COOKIE_SECURE=true`。
- `config.settings.prod` 始终强制 `DEBUG=False`，即使 `DJANGO_DEBUG=true`。
- 技术日志只记录失败依赖名称、非敏感状态和 requestId，不记录数据库/Redis 连接串、密码、Cookie 或密钥。
