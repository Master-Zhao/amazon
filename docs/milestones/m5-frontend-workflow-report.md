# M5 完整前端与 E2E 报告

## 1. 本阶段目标

完成 V1 真实业务页面、七个权限菜单、页面状态、OpenAPI 类型、自动化浏览器 E2E 和演示主链路。

## 2. 检查的现有文件

检查 M0—M4 五个里程碑提交、当前 Git 状态、已有页面/API、统一 Axios 客户端、权限码、OpenAPI 与 Compose 配置；未进入隔离目录或读取未知 DOCX。

## 3. 修改文件

修改分析、报表、动作 API 查询，修正 JSON Parser 与写入 Serializer 的 snake_case 内部契约；修改 Router、Layout、公共样式和既有页面。

## 4. 新增文件

新增 Campaign 列表详情、审批执行中心、Playwright 配置/E2E、异常 Campaign fixture 和本报告。

## 5. 依赖变化

新增并精确锁定 `@playwright/test 1.61.1`；使用系统现有 Chrome，不下载浏览器。

## 6. 数据库迁移

无新增迁移。E2E 使用独立 `backend/e2e.sqlite3`，执行完整迁移、flush 和虚构 seed；该数据库被 Git 忽略。

## 7. 新增接口

为导入任务、分析任务和 Action Preview/审批/执行提供受 Tenant/Profile 授权保护的列表查询；既有写接口路径不变。

## 8. 新增页面

新增 Campaign 列表/详情和审批执行中心；完善数据中心任务历史、分析任务、Recommendation、Preview、执行回填、审计与系统入口。

## 9. 更新文档

更新 README、PLANS、需求覆盖矩阵和本里程碑报告。

## 10. 实际执行的命令

执行 Django check/migration dry-run/pytest/OpenAPI，前端 lint/typecheck/unit/build/type generation，Playwright E2E，以及 Git 范围和 diff 检查。

## 11. 测试通过/失败/跳过数量

后端 81 passed；前端 9 files / 31 tests passed；lint、typecheck、production build、OpenAPI 校验与类型生成通过。Playwright 1 条真实闭环通过；API 集成包含分析到审计完整链路。

## 12. 未执行或无法验证内容

真实 Amazon 导出、真实 LLM、Amazon Ads 写接口不在范围。不同浏览器矩阵未执行；E2E 只验证本机 Chrome。

## 13. 对既有契约的影响

只新增 GET 列表能力；修复 M4 JSON 写 Serializer 与全局 snake_case Parser 不一致的问题。前端继续消费 Renderer 输出的 camelCase。

## 14. 遗留风险

复杂角色页面状态和所有非法动作 UI 分支未逐一做浏览器覆盖；后端权限/状态测试仍是权威安全证据。路由懒加载后入口 JS 为 51.41 kB；按需 Dashboard/ECharts chunk 为 508.92 kB（gzip 170.27 kB），仍有 Vite 500 kB 警告。

## 15. 当前启动方法

按 README 启动；E2E 使用 Django `18000`、Vite `15173`，不会占用或终止 `8000` 上的未知进程。

## 16. 当前演示链路

登录/恢复 → 四级上下文 → 上传异常 Campaign fixture → ImportTask → Dashboard 异常 → 四 Agent → Recommendation → Preview → 审批 → 人工回填 → AuditLog → 退出。

## 17. 下一阶段计划

先建立并打标签 `demo-milestone`，随后只执行最小 M6：必要索引/N+1、幂等保护复核、Compose/健康验证、部署与最终文档、压测脚本和诚实验收。
