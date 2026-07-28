# 编码约定

- Python 3.13，金额使用 `Decimal`，外部 ID 使用字符串，UTC 存储时间。
- API 输入在 Serializer 校验，输出经统一 envelope 和 camelCase renderer。
- 写业务放 Service，复杂查询放 Selector；查询必须从 tenant/profile 范围开始。
- 状态变更使用 `transaction.atomic`、行锁、唯一约束或幂等键。
- `ApprovalRecord`、`ExecutionRecord`、`AuditLog` 和冻结后的
  `ActionPreviewVersion` 只追加。
- Vue 页面只经 feature API → Axios 客户端访问后端，不持久化 Refresh Token。
- 新文件附相应测试和文档；不以 TODO、静态成功响应或页面假数据宣称完成。
