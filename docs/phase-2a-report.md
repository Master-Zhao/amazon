# Phase 2A 完成报告：账号认证与 JWT 双 Token

日期：2026-07-28

## 1. 本阶段目标

在 Phase 1 自定义 User 基础上完成真实账号认证纵向链路：登录、Access Token、HttpOnly Refresh Cookie、刷新轮换与撤销、当前用户、退出、前端会话恢复及认证审计基础。严格不进入 Phase 2B。

## 2. 检查的现有文件

已检查主规格、`AGENTS.md`、`PLANS.md`、Phase 1 报告、范围文档、决策日志，以及 accounts/core/API、前端 Router/Pinia/Axios、Compose 和 OpenAPI 现状。未读取隔离目录和来源不明 DOCX。

## 3. 修改文件

- 后端：accounts User/配置/API/Core 错误映射、测试、`pyproject.toml` 与 `uv.lock`。
- 前端：认证页面、API、Store、Router、Axios、布局、首页、样式与测试。
- 契约：`openapi/schema.yaml` 与生成 TypeScript 类型。
- 文档：README、API 约定/错误码、验收清单、认证设计、决策日志和本报告。

## 4. 新增文件

新增认证 Service、Serializer、View、URL、Bearer Authentication、异常、Schema 扩展、UserManager、seed 命令、`0002_authentication` 迁移、前后端认证测试与认证设计文档。

## 5. 依赖变化

新增 `djangorestframework-simplejwt>=5.5.1,<5.6`，锁定为 5.5.1；其 PyJWT 传递依赖由 `uv.lock` 固定。用途仅为成熟 JWT 签名和校验。

## 6. 数据库迁移

新增 `accounts.0002_authentication`，未修改 `0001_initial`。迁移规范化邮箱并增加大小写无关唯一约束，创建 `sys_refresh_token` 和 `audit_auth_event`。SQLite 与 MySQL 8.4 从零迁移均通过。

## 7. 新增接口

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`

## 8. 新增页面

新增真实 `/login` 页面；账号首页显示真实 `/auth/me` 用户；支持初始化恢复和退出。没有 Tenant 选择器或权限菜单。

## 9. 更新文档

更新 README、API 约定、错误码、验收清单、PLANS 和决策日志；新增认证设计与本报告。

## 10. 实际执行的关键命令

- `backend\.venv\Scripts\pytest.exe backend -q`
- `docker compose -f compose.test.yml run --rm backend pytest --create-db -q`
- `pnpm --dir frontend lint`
- `pnpm --dir frontend typecheck`
- `pnpm --dir frontend test`
- `pnpm --dir frontend build`
- 三套 `docker compose ... config --quiet`
- local Compose build/start、`accounts.0002` migrate、`seed_demo_user`
- HTTP login/me/refresh/logout/旧 Refresh 重放脚本

## 11. 测试通过/失败/跳过数量

- 后端 SQLite：51 passed，0 failed。
- 后端 MySQL 8.4：51 passed，0 failed；首次复用旧测试库时因缺少 `0002` 表失败，使用 `--create-db` 从零迁移后全通过。
- 前端：8 files / 28 tests passed，0 failed。
- lint、typecheck、production build：PASS；Vite 101 modules。

## 12. 未执行或无法验证内容

自动浏览器验收：`NOT VERIFIED`。原因：Codex 浏览器控制工具初始化和连接失败；按强制收口要求未继续尝试。正式 TLS、跨站 Cookie 部署和真实生产域名未验证。

## 13. 对既有契约的影响

保留统一响应信封和 requestId；新增七个稳定认证错误码与 Bearer OpenAPI 安全定义。用户 ID 以字符串输出。Refresh Token 从不进入 JSON。

## 14. 遗留风险

浏览器级交互尚需后续在工具可用时单独验证；生产反向代理必须提供 HTTPS。完整租户和授权校验尚未实现，因此当前 Token 只证明 User 身份。

## 15. 当前启动方法

按 README 启动 local Compose、执行 migrate，再用 `DEMO_USER_PASSWORD` 或 `--password` 手动运行 `seed_demo_user`。生产环境没有自动 seed。

## 16. 当前演示链路可走到哪一步

HTTP 链路已验证：演示用户登录 → Access Token → `/auth/me` → Refresh 轮换 → logout → 旧 Refresh 返回 `AUTH_TOKEN_REVOKED`。Set-Cookie 含 HttpOnly，登录 JSON 不含 Refresh Token。

## 17. 下一阶段计划

Phase 2B 未获授权，不启动、不预实现。等待项目发起人另行明确授权。
