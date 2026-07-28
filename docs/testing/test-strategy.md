# Phase 1 测试策略

## 分层

### 后端单元与 API 测试

默认使用 `config.settings.test` 和 SQLite，快速覆盖：

- 配置加载与业务应用未越界。
- 自定义 User、表名和 email 唯一约束。
- live/ready 成功、数据库异常和 Redis 异常。
- requestId 生成、合法透传、非法值替换。
- 统一响应与异常映射。
- 嵌套对象、数组、分页和错误结构的 camel/snake 转换。
- Decimal、日期时间、UUID 序列化。
- Celery eager smoke。
- OpenAPI Schema 生成。

命令：

```powershell
uv run --project backend pytest backend -q
```

### MySQL 集成

`compose.test.yml` 使用 MySQL 8.4.6 tmpfs 和 Redis 7.4.5。`USE_MYSQL_TESTS=true`，测试数据库复用 `amazon_ads_test`，仅存在于隔离测试 Compose 生命周期。

```powershell
docker compose -f compose.test.yml up -d mysql redis
docker compose -f compose.test.yml run --build --rm backend pytest -q
```

### 前端

Vitest + Vue Test Utils 覆盖应用挂载、路由边界、Pinia、Axios 错误/requestId、诊断页成功和失败状态。

```powershell
pnpm --dir frontend lint
pnpm --dir frontend typecheck
pnpm --dir frontend test
pnpm --dir frontend build
```

### 契约

```powershell
uv run --project backend python backend/manage.py spectacular --file openapi/schema.yaml --validate
pnpm --dir frontend generate:api
```

生成类型前后 SHA-256 必须一致，或将契约变化作为受控差异审阅。

### 容器与浏览器

- 三个 Compose 文件执行 `config --quiet`。
- local 全服务健康。
- 独立迁移从空 MySQL 成功。
- Nginx 提供 Vue 并代理 API。
- readiness 故障/恢复。
- Celery 真实 Broker/Worker/result 往返。
- 应用内浏览器检查首页、诊断页 DOM、控制台错误和实际布局。

## 尚未覆盖

Phase 1 不包含认证、Tenant 隔离、RBAC、报表、状态机、幂等、并发写、E2E 业务流或性能测试。这些测试不能用基础测试数量替代。
