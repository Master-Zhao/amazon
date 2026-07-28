# 三类报表导入设计

```mermaid
sequenceDiagram
  participant U as Vue
  participant A as Django API
  participant S as LocalFileStorage
  participant Q as Celery imports
  participant D as MySQL
  U->>A: multipart CSV/XLSX + Tenant/Profile
  A->>A: 认证、Membership、功能、Store/Profile 校验
  A->>S: 分块保存并计算 SHA-256
  A->>D: 追加 Upload + QUEUED Task
  A-->>U: 202 + taskId
  A->>Q: transaction.on_commit
  Q->>D: 行锁 Task，追加 Batch
  Q->>S: 分块读取/只读 XLSX
  loop 每行隔离
    Q->>D: 标准化并 upsert 当前权威广告对象
    Q->>D: 错误行追加 ImportRowError
  end
  Q->>S: gzip JSONL 标准化清单
  Q->>D: SUCCEEDED/PARTIAL_SUCCEEDED/FAILED
```

## 关键规则

- `ReportUpload`、`ImportTask`、`ImportBatch` 只追加；重处理复用原 Upload 但新建 Task/Batch。
- SHA-256 相同且 Profile/报表类型相同标记 duplicate，但允许处理。
- 文件级不支持/空表头整批失败；行级错误不阻断合法行，混合结果为 `PARTIAL_SUCCEEDED`。
- 文件正文和 gzip JSONL 在 FileStorage；MySQL 只保存元数据、错误、血缘和标准化业务对象。
- `REPORT_FIELD_ALIASES` 可覆盖真实列名映射；当前 fixture 为虚构模板，尚未用真实 Amazon 导出验证。
- 上传当前采用 25 MiB 保守限制，正文默认保留 365 天；真实 P95/P99 和 Excel 工作表规则待样例校准。

## Source Adapter

`FileUploadReportSource` 为可用实现；`ThirdPartyProviderReportSource` 和 `AmazonAdsApiReportSource` 仅公开明确的 unavailable/reserved capability，不发起外部调用。

