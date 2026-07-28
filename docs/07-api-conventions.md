# 07 API通信规范

## 1. 基础约定

- API前缀固定为`/api/v1`。
- 生产环境只使用HTTPS；本地开发可使用HTTP。
- REST资源使用复数、小写、连字符风格，例如`/report-uploads`。
- JSON和TypeScript使用camelCase；Python和数据库使用snake_case。
- ID在JSON中使用字符串。
- 时间点使用ISO 8601并带时区，例如`2026-07-28T08:30:00Z`。
- 服务端时间点以UTC存储；报表业务日期按Marketplace/Profile时区解释。
- 金额使用十进制字符串并显式携带currency。
- 百分比使用小数、百分数还是基点仍为待确认；确认前字段必须在Schema中明确单位。

## 2. HTTP方法

| 方法 | 用途 |
|---|---|
| GET | 无副作用读取资源、列表或下载授权 |
| POST | 创建资源、发起异步任务或执行命令 |
| PATCH | 修改允许编辑的普通字段或草稿，必须带乐观锁版本 |
| DELETE | 仅对明确允许删除的资源；核心历史不用DELETE |

核心状态不得通过通用PATCH直接赋值。使用命令式子资源，例如：

- `POST /analysis-tasks/{id}/submit`
- `POST /action-previews/{id}/submit`
- `POST /action-preview-versions/{id}/approve`
- `POST /execution-tasks/{id}/confirm`

## 3. 成功响应

```json
{
  "code": "SUCCESS",
  "message": "操作成功",
  "data": {},
  "requestId": "req_xxx"
}
```

## 4. 错误响应

```json
{
  "code": "STABLE_ERROR_CODE",
  "message": "可读错误说明",
  "data": {
    "errors": {}
  },
  "requestId": "req_xxx"
}
```

字段级错误的`errors`按camelCase字段组织。`code`稳定、可供客户端分支；`message`可本地化且不能作为程序判断依据。

## 5. HTTP状态码

| 状态码 | 用途 |
|---|---|
| 200 | 成功读取或命令成功且有响应 |
| 201 | 同步创建成功 |
| 202 | 异步任务已接受 |
| 204 | 成功且无正文，作为统一包装例外 |
| 400 | 请求语法或通用参数错误 |
| 401 | 未认证或认证失效 |
| 403 | 已认证但无动作权限，且不会泄露资源存在性 |
| 404 | 不存在，或跨Tenant/Store时隐藏资源存在性 |
| 409 | 幂等冲突、状态冲突或版本冲突 |
| 413 | 文件过大 |
| 415 | 文件/媒体类型不支持 |
| 422 | 业务字段或守卫校验失败 |
| 429 | 请求过频 |
| 500 | 未预期服务器错误 |
| 503 | 依赖暂不可用 |

## 6. 分页、排序和筛选

请求参数：

- `page`从1开始。
- `pageSize`默认20，最大值待性能验证后冻结。
- `sort`只能使用接口声明的白名单字段；降序使用明确约定。
- 筛选字段逐接口定义，不接受任意ORM表达式。

响应：

```json
{
  "code": "SUCCESS",
  "message": "查询成功",
  "data": {
    "items": [],
    "pagination": {
      "page": 1,
      "pageSize": 20,
      "total": 0,
      "totalPages": 0
    }
  },
  "requestId": "req_xxx"
}
```

大数据游标分页是未来扩展，不属于V1默认契约。

## 7. 异步任务

异步创建返回HTTP 202：

```json
{
  "code": "TASK_ACCEPTED",
  "message": "任务已受理",
  "data": {
    "taskId": "123",
    "taskUrl": "/api/v1/import-tasks/123",
    "pollAfterSeconds": 2
  },
  "requestId": "req_xxx"
}
```

- V1使用轮询；客户端遵守`pollAfterSeconds`并指数退避。
- 任务查询返回status、stage、progress、计数、错误摘要、是否可取消和更新时间。
- taskId是业务任务ID，不暴露Celery内部ID作为唯一业务标识。
- 页面离开后仍可重新加载任务状态。

## 8. 幂等与防重复

- 上传创建、分析提交、Preview提交、审批决定和执行确认接受`Idempotency-Key`。
- 相同Key、相同用户、Tenant、端点和请求摘要返回原结果。
- 相同Key但不同请求摘要返回409和`IDEMPOTENCY_KEY_REUSED`。
- 服务端还要以业务唯一约束防止绕过客户端的重复提交。

## 9. 乐观锁

- 可变容器返回`version`整数。
- PATCH和命令请求携带`version`或`If-Match`。
- 不匹配返回409、`VERSION_CONFLICT`和最新可见版本摘要。
- 不可变Revision/Version/Record不允许PATCH。

## 10. 文件上传与下载

- 上传使用`multipart/form-data`。
- 报表类型、Store、Profile等元数据作为明确字段。
- 最大尺寸、编码和工作表选择规则待确认。
- 服务端验证扩展名、MIME、魔数、哈希和权限；扩展名不能作为唯一依据。
- 文件下载先校验Tenant、Store、业务对象和文件关联权限。
- 文件正文响应、重定向或短期授权URL是统一JSON包装的例外。
- Content-Disposition文件名必须安全编码，禁止路径穿越。

## 11. 认证与Tenant上下文

- 全局邮箱密码登录已确认。
- Cookie Session与Access/Refresh Token待确认。
- 当前Tenant上下文不得仅由请求正文决定。
- 切换Tenant必须验证有效Membership，并刷新功能权限和Store集合。
- Cookie方案必须定义CSRF、SameSite和跨域策略。
- Token方案必须定义短期Access、Refresh轮换、吊销和安全存储。

## 12. 403/404防泄露

- 跨Tenant或跨Store的详情访问返回404。
- 无权查看集合中的对象直接不出现在列表。
- 对明确存在的当前范围对象缺少动作权限可返回403。
- 错误响应不返回目标Tenant、Store、对象所有者或内部查询条件。

## 13. requestId与审计

- 网关或后端为每个请求生成/校验requestId。
- 响应、应用日志、Celery派发、AgentRun和AuditLog传播同一关联ID。
- 不信任过长或非法格式的客户端requestId；必要时生成新值并记录父关联。

## 14. OpenAPI与兼容性

- OpenAPI是请求/响应Schema、枚举、错误码和权限说明的契约来源。
- CI验证Schema有效性、破坏性变更和前后端类型一致性。
- V1内新增可选字段通常兼容；删除字段、改类型、改单位、改枚举语义属于破坏性变更。
- 废弃字段先标记deprecated，提供迁移说明和支持窗口。
- 任何状态或权限编码变化必须同步决策日志、状态机和测试。

## 15. 公共稳定错误码

- `VALIDATION_ERROR`
- `AUTHENTICATION_REQUIRED`
- `PERMISSION_DENIED`
- `RESOURCE_NOT_FOUND`
- `TENANT_CONTEXT_REQUIRED`
- `STORE_ACCESS_DENIED`
- `INVALID_STATE_TRANSITION`
- `STATE_GUARD_FAILED`
- `VERSION_CONFLICT`
- `IDEMPOTENCY_KEY_REUSED`
- `FILE_TOO_LARGE`
- `FILE_TYPE_UNSUPPORTED`
- `IMPORT_SCHEMA_MISMATCH`
- `TASK_NOT_CANCELLABLE`
- `AGENT_OUTPUT_INVALID`
- `APPROVAL_ALREADY_DECIDED`

具体领域错误可以扩展，但不得复用同一编码表达不同含义。
