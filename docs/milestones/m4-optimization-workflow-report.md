# M4 优化工作流报告

## 1. 本阶段目标

用 MockLLMProvider 打通四 Agent、结构化建议、不可变动作预览、单级审批、人工执行回填、效果评估、知识库和业务审计纵向链路。

## 2. 检查的现有文件

复核 M0—M3 提交、主规格、连续执行目标、决策日志、权限 Service、指标 Selector、OpenAPI 和既有认证代码；未读取隔离目录。

## 3. 修改文件

修改配置、API v1 路由、测试设置、前端 Router/Layout/公共样式、README、PLANS、OpenAPI 和生成类型。

## 4. 新增文件

新增 `agents`、`recommendations`、`actions`、`knowledge`、`audit` 模块，`integrations/llm`，M4 后端测试，优化/知识/审计前端页面及三份架构文档。

## 5. 依赖变化

无新增依赖；演示只启用 MockLLMProvider，不配置真实模型密钥。

## 6. 数据库迁移

新增五个模块的 `0001_initial`，以及 `knowledge.0002_seed_knowledge`。既有迁移未修改；SQLite 升级迁移成功，迁移差异为 0。

## 7. 新增接口

新增分析任务创建/查询、建议列表、预览创建/提交/审批、执行回填、知识列表和审计列表 API。

## 8. 新增页面

新增优化闭环、知识库、审计日志页面，全部调用真实后端 API。

## 9. 更新文档

新增 AI Agent、动作工作流、安全审计设计和本报告；更新覆盖矩阵、README、PLANS。

## 10. 实际执行的命令

执行 Django migrate/check/makemigrations dry-run/pytest、OpenAPI 生成验证、前端 lint/typecheck/test/build/类型生成，以及 local/test/prod 三套 Compose 静态检查。

## 11. 测试通过/失败/跳过数量

后端 80 passed、0 failed；前端 9 files / 31 tests passed、0 failed；lint、typecheck、build、OpenAPI 和三套 Compose 静态检查通过。

## 12. 未执行或无法验证内容

未运行真实 LLM、真实 Amazon Ads API、真实报表样例、MySQL 容器集成和浏览器 E2E。生产构建存在主 JS 1.286 MB 警告，M5 用路由懒加载处理。

## 13. 对既有契约的影响

只新增 `/api/v1/analysis`、`recommendations`、`actions`、`knowledge`、`audit` 契约；认证与 M1—M3 接口未撤销。

## 14. 遗留风险

11 类动作目前具备白名单与基础确定性校验，但币种/对象类型全部分支、并发版本冲突和 Provider 故障矩阵需 M5/M6 补齐；效果评估只建立 baseline。

## 15. 当前启动方法

继续按 README 使用 Compose 启动，或本机分别运行 Django、Celery 和 Vite；需先迁移新增表。

## 16. 当前演示链路

可从已导入 Campaign 指标运行四 Agent，查看建议，冻结并提交 Preview，按 Tenant 类型审批，生成并回填人工执行项，查询审计与知识文章。

## 17. 下一阶段计划

M5 完成全业务前端状态、权限菜单、执行清单交互、契约测试和可重复浏览器 E2E，然后自动进入 M6。

