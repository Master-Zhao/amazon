# 认证接口

接口为 `/api/v1/auth/login`、`refresh`、`logout`、`me`。Access Token 只通过
JSON 返回并保存在前端内存；Refresh Token 只在认证路径下的 HttpOnly Cookie
传输。刷新会轮换并撤销旧 token，重放被拒绝；退出撤销当前 refresh。

受保护请求使用 `Authorization: Bearer <access>`。401 表示身份失效；登录后仍需
由 `apps.permissions.services.authorize` 校验 Membership、权限与数据范围。
生产必须启用 TLS 和 Secure Cookie；该域名级配置尚未在生产环境验证。
