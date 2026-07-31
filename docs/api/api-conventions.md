# API 约定

## 路径与契约

- 业务版本前缀：`/api/v1/`
- OpenAPI Schema：`/api/schema/`
- Swagger UI：`/api/docs/`
- 健康检查：`/health/live`、`/health/ready`
- 仓库契约快照：`openapi/schema.yaml`

`/api/v1/` 包含认证、四级上下文、权限、报表、广告、分析、Recommendation、
Action、知识和审计接口。真实 Amazon/第三方/LLM 不在可调用路径中。

## 响应信封

```json
{
  "code": "SUCCESS",
  "message": "操作成功",
  "data": {},
  "requestId": "req_xxx"
}
```

HTTP 状态表达传输结果，`code` 表达稳定的应用结果。错误详情位于 `data.errors`。健康检查也使用相同信封。

## 命名转换

- Python、数据库和内部服务使用 `snake_case`。
- JSON 请求字段通过公共 Parser 递归转为 `snake_case`。
- multipart 请求通过 `CamelCaseMultiPartParser` 转换字段；历史报表上传 Serializer
  直接声明 camelCase wire 字段并使用 DRF `MultiPartParser`。
- JSON 响应通过公共 Renderer 递归转为 `camelCase`。
- 转换覆盖嵌套对象、数组、元组、分页结构与错误结构；Serializer 不手工转换。

## requestId

客户端可发送由字母、数字、`.`、`_`、`:`、`-` 组成且不超过 128 字符的 `X-Request-ID`。合法值原样透传到：

- 响应头 `X-Request-ID`
- 响应体 `requestId`
- 结构化日志上下文

缺失或非法值由 Django 生成 `req_<uuid hex>`。Nginx 只透传客户端头，不自行覆盖；缺失时由 Django 负责生成。

## 类型

- API ID 在序列化时使用字符串；公共 `ObjectIdentifierField` 与 `ObjectIdentifierListField` 供 Serializer 显式声明 `id`、`user_id/userId`、`tenant_id/tenantId`、`store_id/storeId`、`profile_id/profileId` 等对象标识符。
- 不按字段值类型全局改写普通整数；clicks、orders、page、pageSize、total 等业务数值保持 JSON number。
- Decimal 序列化为十进制字符串。
- `date` / `datetime` 使用 ISO 8601。
- UUID 序列化为字符串。
- 金额业务接口同时提供 Profile/Marketplace 的 currency，不跨币种直接汇总。

`GET /api/v1/auth/me`、业务 UUID 和外部广告 ID 均输出字符串。

## 客户端

前端统一通过 `shared/api/httpClient.ts` 调用。Access Token 由 Pinia 认证 Store
仅保存在内存，并同时以 `Authorization: Bearer <token>` 和
`X-Token: <token>` 注入已认证请求；后端兼容任一标头，两者并存时必须一致。
Refresh Token 由浏览器作为 HttpOnly Cookie 管理，Vue 不读取其值。

受保护请求收到 401 时，客户端最多刷新一次；并发 401 合并为同一个刷新请求。
登录、刷新和退出接口不触发自动刷新，防止循环。刷新失败会清空认证内存态并
跳转登录页。当前 Tenant 通过 `X-Tenant-ID` 发送，Store/Marketplace/Profile
通过路径或查询/请求字段传递；客户端上下文不能替代后端对象归属校验。

集合分页与异步轮询见 `pagination-and-tasks.md`；认证细节见
`authentication.md`。

## 认证接口与 Cookie

| 方法 | 路径 | 认证/凭据 | 成功结果 |
|---|---|---|---|
| POST | `/api/v1/auth/login` | JSON 邮箱、密码 | JSON 返回 Access Token 与基本用户；设置 Refresh Cookie |
| POST | `/api/v1/auth/refresh` | Refresh HttpOnly Cookie | JSON 返回新 Access Token；按配置轮换 Cookie |
| POST | `/api/v1/auth/logout` | Refresh HttpOnly Cookie（可缺失） | 撤销已有刷新会话并清除 Cookie；可重复调用 |
| GET | `/api/v1/auth/me` | Bearer 或 `X-Token` Access Token | 返回当前用户基本信息 |

Refresh Cookie 默认名称 `refresh_token`，Path 为 `/api/v1/auth/`，HttpOnly 必须为真；Secure 和 SameSite 由环境配置。生产配置强制 Secure 与 HttpOnly 为真。Cookie 不出现在 OpenAPI 响应体，API 契约以说明文字标记其传输方式。
