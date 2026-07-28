# 技术答辩常见问题

1. **为什么不用微服务？** V1 的一致性边界集中在审批、执行和审计，模块化单体更易保持事务正确性；主规格也明确禁止提前拆分。
2. **LLM 会不会越权？** Agent 无 ORM 权限，只接收 Orchestrator 裁剪的数据；输出还要由 Service 重新校验对象、金额、beforeValue 和权限。
3. **为什么演示用 Mock？** 可重复、无密钥、无外部数据泄露；真实 Provider 属于确认的预留范围。
4. **会自动改 Amazon 广告吗？** 不会。批准后只生成人工执行清单并回填证据。
5. **如何隔离租户？** 每个请求同时验证有效 Membership、功能权限、Store/Profile 白名单和对象归属；越界返回 404。
6. **不同币种会合计吗？** 不会。Profile 绑定 currency，V1 禁止跨 Marketplace/currency 直接汇总。
7. **三类报表为何分事实表？** Campaign、Targeting、Search Term 粒度不同，分表防止重复汇总。
8. **部分坏行怎么办？** 合法行入库，错误行记录；任务状态为 PARTIAL_SUCCEEDED。
9. **如何防止重复审批或执行？** 行锁、状态守卫、不可变版本、幂等键和唯一约束共同保护。
10. **审计可以删除吗？** 模型实例删除和 QuerySet 批量删除都被拒绝，外键为 PROTECT。
11. **Refresh Token 放哪里？** 只在 HttpOnly Cookie；Access Token 只驻留前端内存。
12. **真实报表兼容性如何？** 当前只对虚构/脱敏 fixtures 验证；真实列名、编码和工作表仍是 BLOCKED_BY_REAL_SAMPLE。
13. **当前性能是多少？** 尚无参考环境实测，不能声称达到 200 RPS；仓库只会提供可重复计划和脚本。
14. **为何 Redis 不能存审批事实？** Redis 只用于队列、短缓存和锁；审批、执行、审计必须由 MySQL 持久化。
15. **回滚怎么做？** 迁移只追加；规则/Schema/Agent 版本可停用；历史审批和审计不重写。

