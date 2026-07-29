# Amazon 广告智能优化系统 V1 · 一页摘要

**目标**：把三类 Amazon Ads 手工导出报表变成可解释、可审批、可人工执行和可审计的优化闭环。

**已实现**：JWT 双 Token；Tenant/Store/Marketplace/Profile 与 RBAC；Campaign/Targeting/Search Term CSV/XLSX 导入；三类日事实；CTR/CPC/CVR/ACOS/ROAS；目标 ACOS 与 HIGH_ACOS 异常；四 Mock Agent；Recommendation；不可变 Action Preview；PERSONAL/TEAM 审批规则；人工执行回填；知识库；AuditLog；七个真实前端菜单。

**架构**：Vue 3 + TypeScript + Vite，Django 5.2 + DRF，Celery，MySQL 8.4，Redis 7，Nginx，Docker Compose。模块化单体；View → Serializer → Service → ORM，复杂读走 Selector。

**安全**：Access Token 仅内存，Refresh 仅 HttpOnly Cookie；每次业务请求重新校验 Membership、功能权限、Store/Profile 和对象归属；LLM 不裁决指标、金额、权限和状态；不保存隐藏思维过程。

**当前复核证据**：后端 112 项、前端 46 项、Compose/健康和 Docker
HTTP/Celery/MySQL Campaign 链路通过。Chrome E2E 本轮两次均在浏览器启动前
因旧固定 SQLite 迁移历史失败，修复后未第三次执行，必须标记 NOT VERIFIED。

**明确边界**：不调用 Amazon Ads 写 API；不接真实 LLM/第三方来源；不跨币种汇总；不做多级审批、微服务、复杂 RAG、库存或财务。

**未充分验证**：真实 Amazon 导出样例；参考 8C16G 环境性能；当前机器最终 Docker 运行态将在 M6 如实复验。
