# 认证接口

接口为 `/api/v1/auth/login`、`refresh`、`logout`、`me`。登录推荐提交
`{"identifier": "<账号或邮箱>", "password": "<hidden>"}`；旧客户端的
`email` 字段暂时兼容，但不能和 `identifier` 同时提供。Access Token 只通过
JSON 返回并保存在前端内存；Refresh Token 只在认证路径下的 HttpOnly Cookie
传输。刷新会轮换并撤销旧 token，重放被拒绝；退出撤销当前 refresh。

启用 `REMOTE_SCM_AUTH_ENABLED=true` 时，未命中本地账号的 identifier 会进入
`scm_remote.eb_merchant_admin` 只读认证。远程密码只在请求内用于 bcrypt 校验，
不会写入项目库或日志；首次成功后项目 `default` 库创建不可使用本地密码的
`sys_user` 与 `sys_external_identity` 映射，用于 JWT、Refresh Token 和审计。
本地同名账号不会被远程账号自动接管。

受保护请求由前端同时发送 `Authorization: Bearer <access>` 与
`X-Token: <access>`。后端兼容只发送其中一个；若两者同时存在则必须完全一致，
否则返回 `AUTH_TOKEN_INVALID`。登录和首次 Refresh 在取得 Access Token 前不会
伪造 `X-Token`。401 表示身份失效；登录后仍需
由 `apps.permissions.services.authorize` 校验 Membership、权限与数据范围。
远程账号首次登录不会自动获得 Membership、Store 或 Profile 权限。
生产必须启用 TLS 和 Secure Cookie；该域名级配置尚未在生产环境验证。

登录请求本身发生在 Access Token 签发之前，因此不会携带 `X-Token`。登录响应
返回 Access Token 后，前端立即请求一次 `GET /api/v1/auth/me`；这条请求及后续
已认证请求都会携带双标头，可直接在浏览器 Network 面板检查。后端所有响应都会
显式返回包含 `X-Token` 的 `Access-Control-Allow-Headers`。
