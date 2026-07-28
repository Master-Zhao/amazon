# V1 技术方案

系统是模块化单体：Nginx 将页面交给 Vue，将 `/api`、`/health` 交给
Django/DRF；MySQL 保存权威业务事实，Redis 仅承载 Celery、缓存和短期协调；
文件正文通过 `FileStorage` 保存。生产 Django 使用 Gunicorn，迁移由独立
`migrate` 服务执行。

技术基线为 Python 3.13、Django 5.2、DRF 3.16、Celery 5.6、MySQL 8.4、
Redis 7、Node 24、Vue 3、TypeScript、Vite 8、pnpm 11、Nginx 与 Compose。
依赖分别锁定在 `backend/uv.lock` 和 `frontend/pnpm-lock.yaml`。

## 调用与数据边界

- 写入：View → Serializer → Service → ORM；跨模块写入调用公开 Service。
- 复杂读取：View → Selector → ORM。
- 异步：Celery Task → Service，事务提交后派发。
- Agent：Orchestrator → `AnalysisTask.scope_snapshot` 最小快照 → Agent →
  LLMProvider；Agent 无 ORM。
- 外部能力：`ReportSource`、`FileStorage`、`LLMProvider`、
  `AmazonAdsExecutionAdapter` 与 `MonitoringSink`。
- 授权：所有受保护对象经 `apps.permissions.services.authorize` 同时校验身份、
  Membership、功能码、Store/Profile 范围、对象归属和动作等级。

三类 Daily Metric 独立存储；金额使用 Decimal，不跨 Marketplace/currency
汇总。上传正文不写 MySQL。Action Preview 版本、审批、执行和审计保持冻结/
只追加语义，并通过事务、行锁、唯一约束与幂等键防止重复。

## 运行与验证边界

`local/test/prod` 设置显式选择。`/health/live` 只证明进程存活，
`/health/ready` 检查数据库、Redis 与必需配置。V1 已实现上传报表、Mock 分析和
人工执行闭环，但不调用真实 Amazon、第三方或真实 LLM。

生产 TLS、监控 exporter、真实备份恢复、正式容量与真实 Amazon 导出兼容仍需
生产等价环境验证，详见 `docs/requirements/framework-backlog.md`。
