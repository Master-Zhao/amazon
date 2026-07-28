# 添加报表解析器

先在决策日志确认真实字段、粒度和自然键，再扩展 `apps.reports.models.ReportType`、
Serializer 选择项、`apps.reports.parsers.iter_rows` 与
`apps.reports.services._normalize_row`。上传仍由 `create_upload_task` 创建
`ReportUpload/ImportTask`，Celery 只调用 `process_task`。

文件经 `FileStorage.save_stream` 流式保存；逐行/分块解析和 `bulk_create`，不得
`read()` 全量加载。每种格式需虚构 CSV/XLSX fixture，覆盖正常、部分错误、编码、
Profile 不匹配、重复上传与重处理。真实 Amazon 导出验证前状态保持
`BLOCKED_BY_REAL_SAMPLE`。

外部来源实现 `integrations.advertising_data.sources.ReportSource`，返回
`ReportFetchResult`，不得绕过 Tenant/Profile 授权或把文件正文写入 MySQL。
