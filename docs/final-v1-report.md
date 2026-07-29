# Amazon 广告智能优化系统 V1 最终报告

> 历史报告：其中旧测试数量和 E2E PASS 只描述原里程碑。当前重新验收结果由
> 根目录 `V1_VERIFIED_DELIVERY_REPORT.md` 取代；当前 Playwright 是
> `NOT VERIFIED`，不得引用本文件宣称当前 HEAD 的浏览器链路通过。

## 交付结论

M0—M6 已按授权完成并停止扩展。系统可以用虚构 fixtures 和 `MockLLMProvider` 演示：

登录与刷新恢复 → Tenant/Store/Marketplace/Profile → Campaign 导入与 ImportTask → 指标/ACOS 异常 → Mock 分析与 Recommendation → Action Preview → 单级审批 → 人工执行回填 → 审计日志 → 退出。

稳定演示检查点为提交 `3023e84` 和注解标签 `demo-milestone`。M6 在标签之后完成最终交付，不改写标签历史。

## M6 变化

- Action Preview 创建、重复提交、重复审批和执行回填具备幂等保护与唯一约束。
- AnalysisTask、Recommendation、ActionPreview 的真实列表过滤字段增加复合索引；既有列表继续使用 `select_related` / `prefetch_related` 和 100 条上限。
- 修复 MySQL 8.4 的 SearchTerm 自然键长度兼容问题；保留旧迁移，新增 squash 安装路径和前向迁移。
- test Compose 只读挂载 fixtures，使容器内全量测试可重复。
- 新增系统上下文、备份恢复、性能计划、最终验收、M6 阶段报告和 AI 开发记录。

## 验收摘要

- 后端：SQLite 82 passed；MySQL 8.4 从零 82 passed；均 25 warnings。
- 前端：lint/typecheck/build PASS；9 files / 31 tests PASS。
- 契约：OpenAPI validate 和 TypeScript 生成 PASS。
- E2E：已安装 Chrome，Django 18000 / Vite 15173，完整链路 1 passed。
- Docker：local/test/prod 静态校验 PASS；test Compose 7 服务 healthy，8081 live/ready/前端 PASS。
- 性能：10 RPS × 5 秒只读烟雾 50/50；正式容量目标 NOT VERIFIED。

## Framework Baseline 收口

在不改写 M0—M6 和 `demo-milestone` 的前提下，本次补充统一分页、Tenant/User
限流、Tenant 缓存键、监控 Sink、正式 Adapter、流式规范化输出、11 类动作
确定性校验、RETURNED 新版本、附件证据、基础效果评估和开发者文档。

Framework Baseline 全量结果：后端 103 passed / 25 warnings；前端
10 files / 33 tests；lint、typecheck、production build、OpenAPI validate、
类型生成、核心 Chrome E2E 1 passed 和三套 Compose 静态检查通过。Compose 文件
未变化，未重复完整拉取/构建，运行证据继续引用 M6 的 MySQL 8.4 全量测试和
test Compose 7 服务 healthy。

## Requirement Coverage Matrix

共 60 项：`IMPLEMENTED_AND_TESTED` 44、`IMPLEMENTED_NOT_FULLY_VERIFIED` 6、
`RESERVED_BY_CONFIRMED_SCOPE` 7、`BLOCKED_BY_REAL_SAMPLE` 3、
`NOT_IMPLEMENTED` 0。原唯一 `PERF-004` 已增加真实限流、缓存隔离键和监控扩展
接口，因多实例/生产 exporter/告警未验证而保持 `IMPLEMENTED_NOT_FULLY_VERIFIED`。

## 明确边界

- `RESERVED_BY_CONFIRMED_SCOPE`：第三方/Amazon 报表 Adapter、Sponsored Brands/Display、CRITICAL 规则、跨 Marketplace/币种汇总、真实 LLM、库存/采购/物流/财务。
- `BLOCKED_BY_REAL_SAMPLE`：Campaign、Targeting、Search Term 三类真实 Amazon 脱敏导出验证。
- 未充分验证：所有页面失败状态的逐项浏览器覆盖、正式规模查询基线、多实例
  限流/缓存/监控、完整效果归因、正式 TLS/备份恢复、5×100,000 行及
  300 用户/200 RPS/10 分钟容量。11 类 Service 校验、退回基础 UI 和附件上传已
  自动测试；11 类逐项浏览器 E2E 仍列正式 backlog。

未知 `.arts/` 和两份 DOCX 始终未读取、修改或纳入提交；隔离目录、Node/build/E2E/coverage/临时数据库/上传文件和真实环境文件均未纳入交付。
