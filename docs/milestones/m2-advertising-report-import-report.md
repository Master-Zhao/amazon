# M2 广告、产品与三类报表导入报告

## 1. 目标与实现

新增 Product/CatalogItem/Listing、Sponsored Products 广告层级、Campaign/Targeting/Search Term 三类 CSV/XLSX 上传、LocalFileStorage、异步 Task/Batch、文件/行错、部分成功、重复与重处理。

## 2. 文件、依赖和迁移

- 新增 `apps.products`、`apps.advertising`、`apps.reports` 与 `integrations.storage/advertising_data`。
- 新增 6 份虚构 fixtures 和数据中心上传/任务错误页。
- Python 新增并锁定 `openpyxl 3.1.5`（及 `et-xmlfile 2.0.0`）。
- 新迁移：products 0001、advertising 0001/0002、reports 0001；既有迁移未修改。

## 3. API、测试与验证

- `POST /api/v1/reports/uploads` → HTTP 202 + taskId。
- Task 详情、重处理；Campaign、Targeting、Search Term 基础只读 API。
- SQLite 从 M1 数据库升级执行 products 0001、advertising 0001/0002、reports 0001 成功；Django check 0 issues，迁移差异为 0。
- 后端 72 passed、0 failed、25 warnings；OpenAPI 生成/校验无 warning/error。
- 前端 9 files / 31 tests passed，lint/typecheck/build 通过（111 modules）；OpenAPI TypeScript 类型已重新生成。
- local/test/prod 三套 Compose 静态配置检查通过；Docker daemon 运行态与 MySQL 容器集成在当前沙箱未复验，M6 最终复验。
- 覆盖正常、部分错误、Targeting、Search Term、重复、重处理、Profile 不匹配、跨 Tenant、CSV、XLSX 和 Source capability。

## 4. 边界与风险

真实 Amazon 三类导出文件仍未提供，因此列名、编码、标题行、工作表、自然键和归因最终验证为 `BLOCKED_BY_REAL_SAMPLE`。当前实现提供可配置别名、fixture、文件/行错和可重复测试，不虚构真实兼容性。第三方与 Amazon API Source 只预留。

## 5. 启动、演示与下一步

使用 `seed_demo_context` 后登录、选择 Profile、上传 `tests/fixtures/reports/*.csv`，可查看 202、终态计数与错误。下一步 M3 将把三类行指标写入独立 Daily Metric 事实表并提供 Dashboard/分析页。
