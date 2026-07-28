# API 约定

## 路径与契约

- 业务版本前缀：`/api/v1/`
- OpenAPI Schema：`/api/schema/`
- Swagger UI：`/api/docs/`
- 健康检查：`/health/live`、`/health/ready`
- 仓库契约快照：`openapi/schema.yaml`

Phase 1 的 `/api/v1/` 仅返回平台版本和 `businessCapabilities: "not_implemented"`，不是业务接口。

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
- 金额业务接口未来必须同时提供 currency，Phase 1 未定义金额接口。

Phase 1 测试使用真实 `User.BigAutoField` 整数主键验证顶层、嵌套和列表 ID 输出为字符串；不是预先构造字符串测试数据。当前仍没有业务 ID API。

## 客户端

前端统一通过 `shared/api/httpClient.ts` 调用。Access Token、Tenant、刷新流程均为显式扩展点，当前不提供默认值。禁止绕过统一客户端伪造认证上下文。
