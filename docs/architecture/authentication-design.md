# Phase 2A 认证设计

## 范围

认证结果始终落到项目系统库中的全局 `accounts.User`。JWT 只证明用户身份，
不携带或替代 TenantMembership、角色、Store、Marketplace、AdvertisingProfile
或业务权限。启用远程 SCM 认证时，SCM 身份只作为登录凭据来源，不成为权限来源。

## Token 与 Cookie

- 使用 `djangorestframework-simplejwt 5.5.x` 完成 HS256 JWT 签名、到期和类型校验；项目不实现加密算法。
- Access Token 默认 15 分钟，只通过 JSON 返回给前端并保存在内存，以 Bearer Header 发送。
- Refresh Token 默认 7 天，只通过 HttpOnly Cookie 传输，不进入 JSON、Pinia、localStorage、sessionStorage 或日志。
- Cookie 默认 Path 为 `/api/v1/auth/`，SameSite 为 `Lax`。local/test 的 Secure 默认关闭以支持 HTTP；prod 强制 Secure 与 HttpOnly 为真。
- 所有 JWT 时间声明和数据库时间使用 UTC。

## 刷新会话与撤销

Simple JWT 只负责令牌密码学。项目用 `sys_refresh_token` 保存 Refresh Token 的 SHA-256 摘要、用户、UTC 到期时间、撤销时间和轮换后继关系，不保存原始 Token。

刷新在事务和行锁内完成：

1. 校验签名、到期时间和 `token_type=refresh`。
2. 按 Token 摘要查询活动会话并校验用户、到期时间与 `is_active`。
3. 生成新的 Access Token。
4. `JWT_ROTATE_REFRESH_TOKENS=true` 时签发新 Refresh Token。
5. 同时启用 `JWT_BLACKLIST_AFTER_ROTATION` 时撤销旧记录；旧 Token 重放返回 `AUTH_TOKEN_REVOKED`。

退出会撤销当前已知 Refresh 会话并以相同 Cookie 属性写入过期 Cookie。缺少、伪造、过期或已经撤销的 Cookie 也能安全重复退出。

## 账号或邮箱登录

- 登录推荐使用 `identifier`，支持本地 `User.username` 或 `User.email`；旧
  `email` 请求字段保持兼容，两者同时出现时明确拒绝。
- identifier 只执行 `strip`，不擅自改变用户名大小写；邮箱查询保持大小写不敏感。
- 创建、保存和 seed 的邮箱继续执行 `strip + casefold`。
- `sys_user.email` 保留原有唯一约束，并新增 `Lower(email)` 唯一约束。
- `accounts.0002_authentication` 先规范化已有邮箱，再增加约束；发现规范化后重复时迁移明确失败，不静默合并账号。
- 账号不存在和密码错误统一返回 `AUTH_INVALID_CREDENTIALS` 与相同提示。
- 登录、刷新和 Access Token 校验都拒绝 `is_active=false` 用户。

### 远程 SCM 身份

- `REMOTE_SCM_AUTH_ENABLED=true` 时，未命中本地账号或已绑定 SCM 身份的账号通过
  `scm_remote.eb_merchant_admin` 验证。
- 查询固定为参数化 `SELECT`，账号精确匹配且必须唯一；只接受
  `status=1`、`is_del=0` 的账号。
- bcrypt 哈希只在进程内用于单次校验，不写入项目表、响应、审计或日志。
- 首次成功登录在 `default` 创建 `sys_user` 与 `sys_external_identity`；本地用户
  设置不可用密码，后续仍回到 SCM 验证。
- 本地同名用户不会自动绑定，防止远程账号接管现有本地身份。
- 远程身份不会自动获得 TenantMembership 或数据权限。

## 前端恢复与并发刷新

浏览器启动时先调用 `/auth/refresh`，成功后把新 Access Token 放入内存，再调用 `/auth/me` 恢复当前用户。失败时进入匿名状态。

统一 Axios 客户端：

- 每次请求读取当前内存 Access Token；
- 普通受保护请求遇到 401 时最多重放一次；
- 同一时刻的多个 401 共享一个 Refresh Promise；
- 登录、刷新和退出不会触发自动 Refresh；
- Refresh 失败会清空内存状态并跳转登录页；
- 后端错误中的 requestId 保留给页面展示和排障。

## 安全日志与审计基础

`audit_auth_event` 只追加记录登录、刷新和退出的事件、结果、用户可空外键、邮箱 SHA-256、requestId、来源 IP 和 UTC 时间。它不保存密码、JWT、Cookie 或完整邮箱。结构化 HTTP 日志只记录方法、路径、状态和 requestId。

这是认证审计基础，不是完整 AuditLog 业务模块。

## 配置

| 环境变量 | 默认值 | 说明 |
|---|---|---|
| `JWT_ACCESS_TOKEN_TTL_MINUTES` | `15` | Access Token 有效分钟数 |
| `JWT_REFRESH_TOKEN_TTL_DAYS` | `7` | Refresh Token 有效天数 |
| `JWT_REFRESH_COOKIE_NAME` | `refresh_token` | Cookie 名称 |
| `JWT_REFRESH_COOKIE_PATH` | `/api/v1/auth/` | Cookie Path |
| `JWT_COOKIE_SECURE` | local/test `false`，prod `true` | prod 不能关闭 |
| `JWT_COOKIE_HTTP_ONLY` | `true` | prod 不能关闭 |
| `JWT_COOKIE_SAME_SITE` | `Lax` | `Lax`、`Strict` 或 `None`；`None` 要求 Secure |
| `JWT_ROTATE_REFRESH_TOKENS` | `true` | 刷新时是否轮换 |
| `JWT_BLACKLIST_AFTER_ROTATION` | `true` | 轮换时是否撤销旧 Token |
| `REMOTE_SCM_AUTH_ENABLED` | `false` | 启用 SCM 商户管理员只读认证；要求存在 `scm_remote` 别名 |

## 明确未实现

尚未实现远程账号到 TenantMembership、Store、AdvertisingProfile 权限的自动映射；
这些权限必须在项目系统库中显式授予。没有真实 Amazon API 或真实 LLM 调用。
