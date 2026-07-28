# Phase 1 技术方案

## 当前有效范围

本文件描述 Phase 1 已实现的基础工程，不代表 Phase 2—7 业务能力已交付。唯一主规格仍是根目录 `codex_master_goal_amazon_ads_v1.md`。

系统采用前后端分离的模块化单体：

```text
Browser
  → Nginx :8080
    → /api、/health → Django/DRF :8000 → MySQL 8.4
    → /             → Vue/Vite :5173
  → Django/Celery → Redis 7 → Celery Worker
                           ↘ Celery Beat
```

生产镜像中 Django 使用 Gunicorn，Vue 构建为静态资源并由独立 Nginx 提供。数据库迁移是独立 `migrate` 服务，不由 backend、worker 或 beat 自动执行。

## 已实现技术基线

| 层 | 实际基线 |
|---|---|
| 后端 | Python 3.13.3、Django 5.2.16、DRF 3.16.1、Celery 5.6.3 |
| 数据 | MySQL 8.4.6、Redis 7.4.5 |
| 前端 | Node 24.10.0、Vue 3.5.40、TypeScript 5.9.3、Vite 8.1.5 |
| 依赖 | `backend/pyproject.toml` + `uv.lock`；`frontend/package.json` + `pnpm-lock.yaml` |
| 边缘 | Nginx 1.28.0、Gunicorn 23.0.0、Docker Compose |
| 契约 | drf-spectacular 生成 OpenAPI 3.0.3；openapi-typescript 生成 TypeScript 类型 |

镜像和锁文件均未使用 `latest`。本机默认 `python` 仍为 3.12.4，项目测试使用 uv 管理的 Python 3.13.3 和 Python 3.13.3 容器，未降低目标版本。

## 环境

- `config.settings.local`：MySQL、Redis、开发服务器、显式本地配置。
- `config.settings.test`：默认 SQLite 单元测试；`USE_MYSQL_TESTS=true` 时使用 MySQL 集成测试。
- `config.settings.prod`：`DEBUG=False`，要求密钥、数据库密码和 Allowed Hosts，支持安全 Cookie 与 HTTPS 重定向。

选择由 `DJANGO_SETTINGS_MODULE` 明确完成，不根据主机名或其他模糊条件推断。

## 数据与安全边界

- 第一份迁移已经创建全局自定义 `accounts.User`，内部表为 `sys_user`，不含 `tenant_id`。
- Phase 1 没有 Tenant、Team、Role、Store、Profile、广告、报表、Agent、Recommendation 或 Action 模型。
- `.env.example` 仅含占位值；没有真实账号、Amazon API、第三方数据服务或 LLM 密钥。
- Redis 仅用于 Broker、短期结果和运行检查，不是正式业务数据存储。
- API 错误不向客户端返回堆栈、密码或连接串。

## 已验证链路

`Nginx → Vue`、`Nginx → Django → MySQL/Redis`、`Django 管理命令 → Redis → Celery Worker → Redis result backend` 均已在 Compose 环境实测。Redis 停止时 readiness 返回 503，恢复后返回 200。

## 尚未实现

认证、JWT、Tenant 数据隔离、RBAC、上传导入、广告领域、AI 分析、建议、动作预览、审批与执行均属于后续阶段。当前首页和诊断页只陈述基础工程事实。
