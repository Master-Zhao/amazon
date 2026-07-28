# 分页与异步任务

集合接口接受 `page`（从 1 开始）和 `pageSize`（1–100），响应 `data` 保留资源
数组并增加：

```json
{"pagination":{"page":1,"pageSize":20,"total":42,"totalPages":3}}
```

参数由 `apps.core.pagination.page_spec` 统一校验，QuerySet 通过
`paginate_queryset` 切片。所有 ID 输出字符串。

上传/分析接口返回 202 和 taskId；客户端按返回 task URL 查询，不从 Redis 推断
正式状态。任务状态由 Service 写入数据库，Celery Task 只调用 Service。重复请求
使用 `Idempotency-Key`，轮询应使用退避并处理 401、403、404、409 与失败状态。
