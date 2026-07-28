# Phase 1 模块设计

## 后端

```text
backend/
  config/                  # URL、WSGI/ASGI、Celery、local/test/prod settings
  api/v1/                  # 版本入口；当前仅平台元数据
  apps/core/               # 跨模块技术能力
  apps/accounts/           # 首次自定义 User
  tests/                   # Phase 1 自动化测试
```

`core` 当前只承担公共技术职责：

- `middleware.py`：生成、校验、保存并返回 `X-Request-ID`。
- `responses.py`：统一响应信封。
- `exceptions.py` / `errors.py`：异常映射与稳定错误码。
- `parsers.py` / `renderers.py` / `case_conversion.py`：请求 camelCase 转内部 snake_case，响应反向转换，递归处理对象、列表、元组和错误结构。
- `serialization.py`：Decimal、日期时间、UUID 和 Django Promise 的安全 JSON 序列化。
- `health.py` / `views.py`：liveness、readiness 和平台入口。
- `tasks.py`：唯一无业务含义的 Celery smoke task。

`accounts` 仅包含全局 `User(AbstractUser)`、Admin 注册和 `0001_initial`。不得在本模块提前实现 TenantMembership 或完整认证流程。

## 前端

```text
frontend/src/
  app/                     # 根组件、Router、应用初始化
  shared/
    api/                   # Axios、健康 API、OpenAPI 生成类型
    layouts/               # 基础布局
    stores/                # Phase 1 平台上下文扩展点
    styles/                # 全局样式
  features/
    home/                  # 如实说明阶段边界的首页
    diagnostics/           # live/ready 诊断页
```

Axios 客户端预留 Access Token、`X-Tenant-ID`、Refresh Token 和 requestId 扩展点，但默认值均为空，不伪造登录或 Tenant。401、403、超时和网络错误统一转为 `ApiClientError`。

## 契约

后端通过 `/api/schema/` 暴露契约，仓库快照位于 `openapi/schema.yaml`。前端执行 `pnpm --dir frontend generate:api` 生成 `src/shared/api/generated/schema.d.ts`。生成前后哈希已验证一致。

## Phase 边界

当前只有 `core` 和 `accounts` 两个 Django 应用，以及 `home`、`diagnostics` 两个前端 feature。其余目标目录必须在对应阶段随真实纵向链路按需创建。
