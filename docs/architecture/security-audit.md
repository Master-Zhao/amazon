# 安全与审计

业务请求依次校验认证、有效 TenantMembership、功能权限、Store/Profile 范围、对象归属、权限等级和状态守卫。完全越出数据范围返回 404，当前范围内缺动作权限返回 403。

关键动作写入 `audit_log`：预览创建、提交、审批、执行回填等记录 actor、Tenant、事件、对象、before/after、requestId 和时间。模型实例删除与 QuerySet 批量删除都被拒绝；外键使用 PROTECT。认证事件继续保留在认证专用只追加表中。

Access Token 仅在前端内存，Refresh Token 仅使用 HttpOnly Cookie。日志和审计不得包含密码、JWT、Cookie、密钥、真实账号或未脱敏报表正文。报表正文由 FileStorage 保存，MySQL 只保存元数据、哈希、位置和血缘。

