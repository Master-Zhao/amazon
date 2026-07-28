# M0 状态保护与认证收口报告

## 1. 目标与现状保护

检查 Git 后确认 Phase 2A 已在 `deec11e feat: implement JWT authentication` 提交，工作区没有未提交认证代码。保留该提交的全部正确实现，未回滚或重写 Phase 1/2A 迁移。`.arts/`、隔离目录和来源不明 DOCX 未读取、修改或暂存。

## 2. 实现、迁移、接口与页面

- 认证实现沿用并验证：自定义 User、邮箱登录、Access Token、HttpOnly Refresh Cookie、轮换、吊销、重放拒绝、退出、`/auth/me`、禁用用户和只追加认证审计。
- 迁移保持 `accounts.0001_initial` 与 `accounts.0002_authentication`，`makemigrations --check` 无差异。
- 接口：`POST /api/v1/auth/login|refresh|logout`、`GET /api/v1/auth/me`。
- 页面：真实登录页、刷新恢复、内存 Access Token、并发 401 合并刷新、刷新失败清理会话。

## 3. 修改与依赖

- 新增覆盖矩阵和本报告；同步 `PLANS.md`、confirmed scope 的连续执行状态。
- 将项目发起人提供并明确指定的 `CODEX_FULL_V1_EXECUTION_GOAL.md` 纳入版本控制。
- 无依赖和数据库变更，无破坏性 API 变化。

## 4. 实际命令与结果

- `uv sync --project backend --frozen`：通过（使用仓库 `.uv-cache`）。
- Django check：0 issues。
- `makemigrations --check --dry-run`：No changes detected；检查默认 local MySQL 历史时因未提供本机密码发出 warning，不影响差异检查。
- `pytest backend -q`：51 passed，0 failed，25 warnings。
- OpenAPI 生成/校验：通过，与受控 Schema 无差异。
- `pnpm install --frozen-lockfile`、lint、typecheck：通过。
- 宿主沙箱内 Vitest 因 Node `spawn EPERM` 失败；按规则改为获准的沙箱外执行后 8 files / 28 tests 全通过。
- production build：通过，101 modules。
- Docker daemon API 在当前沙箱内拒绝访问；M0 未重复声称 Compose 复验，采用 `docs/phase-2a-report.md` 已记录的 MySQL 8.4 与 Compose 证据。

## 5. 契约、风险、启动与演示

统一响应与认证 OpenAPI 无变化。生产 HTTPS/真实域名 Cookie 和自动浏览器 E2E 尚未在 M0 复验；M5/M6 继续验证。当前可演示登录→me→refresh 轮换→logout→旧 Refresh 拒绝。启动方法保持 README 的 local Compose 流程。

## 6. 下一里程碑

自动进入 M1：Tenant、Team、Store、Marketplace、AdvertisingProfile、RBAC、数据授权、四级前端上下文与跨 Tenant 403/404 测试。
