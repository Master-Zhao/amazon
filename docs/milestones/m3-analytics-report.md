# M3 指标、异常和分析页面报告

## 1. 交付

新增 analytics 模块、三类独立事实表、公式与 null 原因、Campaign/Targeting 快照、Target ACOS 继承、版本化 HIGH_ACOS 规则、Dashboard/Targeting/Search Term API 与 ECharts 页面。

## 2. 依赖和迁移

- 前端新增并精确锁定 `echarts 6.0.0`。
- 新增 `advertising.0003_campaign_target_acos` 与 `analytics.0001_initial`；既有迁移未修改。

## 3. 验证

- SQLite 升级迁移成功，Django check 0 issues，迁移差异 0。
- 后端 76 passed、0 failed、25 warnings；覆盖公式、零分母、快照、血缘、继承、异常和 Campaign 权威聚合。
- 前端 9 files / 31 tests passed；lint/typecheck/build 通过。生产包 701 modules，主 JS 约 1.28 MB（gzip 427.74 kB）并出现 chunk 大小 warning，M6 需通过路由懒加载拆分。
- OpenAPI 校验和 TypeScript 类型生成通过；三套 Compose 静态检查沿用 M2 后未改变服务结构，M6 运行态复验。

## 4. 风险与下一步

真实报表自然键/重述仍待真实样例；当前异常只实现可解释的基础 HIGH_ACOS 版本，其他规则在后续配置扩展。下一步 M4 完成 MockLLM、多 Agent、Recommendation、Preview、审批、执行、效果评估、知识和审计闭环。

