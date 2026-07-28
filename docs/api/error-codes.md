# Phase 1 错误码

| code | 常见 HTTP 状态 | 含义 |
|---|---:|---|
| `SUCCESS` | 2xx | 请求成功 |
| `VALIDATION_ERROR` | 400 | 输入校验失败或已处理但无专用映射的 DRF 错误 |
| `AUTHENTICATION_REQUIRED` | 401 | 未认证或认证失败；完整认证尚未实现 |
| `PERMISSION_DENIED` | 403 | 已认证但无动作权限；完整权限体系尚未实现 |
| `RESOURCE_NOT_FOUND` | 404 | 资源不存在 |
| `METHOD_NOT_ALLOWED` | 405 | HTTP 方法不允许 |
| `UNSUPPORTED_MEDIA_TYPE` | 415 | 请求媒体类型不支持 |
| `RATE_LIMITED` | 429 | 请求被限流 |
| `INTERNAL_ERROR` | 500 | 未处理服务器异常；响应不暴露堆栈 |
| `SERVICE_NOT_READY` | 503 | MySQL、Redis 或必需配置未就绪 |

错误示例：

```json
{
  "code": "VALIDATION_ERROR",
  "message": "请求处理失败",
  "data": {
    "errors": {
      "fieldName": ["错误原因"]
    }
  },
  "requestId": "req_xxx"
}
```

readiness 失败只返回 `available` / `unavailable` 或缺失配置项名称，不返回密码、密钥、Redis URL、数据库 DSN 或异常堆栈。新增业务错误码必须稳定、可测试、记录于本文件和 OpenAPI。
