# 模块接口交接规范

## 1. 交接完成条件

任何前后端或跨模块交接必须同时提供：

1. 用例与权限编码。
2. Tenant/StoreMarketplace/Profile 作用域和 403/404 规则。
3. OpenAPI 请求/响应、错误码、分页、幂等和版本字段。
4. 状态机前置、守卫、后置动作和审计事件。
5. Model/迁移影响与只追加约束。
6. 成功、失败、部分失败和并发测试证据。
7. 示例必须来自 seed/fixtures；不得用硬编码假成功。

## 2. 核心交接链

| 提供方 → 使用方 | 交付接口 | 使用方约束 | 验收证据 |
|---|---|---|---|
| 成员 2 → 全员 | 配置、统一响应/异常、requestId、OpenAPI、Celery 基线 | 不创建旁路客户端/响应格式 | smoke、Schema 校验、requestId 传播 |
| 成员 3 → 成员 4/5 | RequestContext、Membership/RBAC、Store/Profile 授权 Service/Selector | 每次业务访问重新校验作用域 | 跨 Tenant/Store/Profile 测试 |
| 成员 3 → 成员 6 | 登录/刷新/退出、上下文、菜单/权限 API | Access 内存优先，Refresh HttpOnly；前端守卫不是授权 | 登录和上下文 E2E |
| 成员 4 → 成员 5 | 授权指标/异常 Selector、对象快照、来源版本 | Agent 只能消费冻结范围，不直接 ORM | Scope 越界与数据版本测试 |
| 成员 4 → 成员 6 | 上传/任务/错误、Campaign/Targeting/Search Term、Dashboard API | 轮询退避；金额带币种；三粒度不相加 | 三类 fixture 联调 |
| 成员 5 → 成员 6 | Analysis、Recommendation、Preview、Approval、Execution、Knowledge、Audit API | 明确不可变版本、部分失败和冲突状态 | Mock 闭环 E2E |
| 成员 6 → 成员 2/3/4/5 | 类型消费、UI 状态、E2E 失败和演示反馈 | 反馈必须带 requestId/taskId 和复现步骤 | 构建、组件、E2E 报告 |

## 3. 公共 API 契约

- 前缀 `/api/v1`。
- 统一成功/错误体含 `code/message/data/requestId`。
- ID 为字符串；JSON camelCase；时间 ISO 8601。
- 金额结构必须含 Decimal 字符串和 currency。
- 异步创建返回 202、taskId、taskUrl、pollAfterSeconds。
- 列表分页并限制最大 pageSize。
- 上传使用 multipart/form-data。
- 幂等命令接受 Idempotency-Key；冲突返回 409。
- 跨作用域对象对外返回 404；已知当前范围对象缺动作权限返回 403。

## 4. 状态与事件交接

- Service 是状态转换唯一入口。
- Celery Task 只接收业务 ID，重新加载对象并调用 Service。
- Task 消息在数据库事务提交后派发。
- RecommendationRevision、ActionPreviewVersion、ApprovalRecord、ExecutionRecord、AuditLog 不允许普通更新或删除。
- 前端展示后端返回状态，不自行推导正式结论。
- 退回后引用新版本；审批和执行始终显示具体版本。

## 5. 数据交接

- 成员 4 的报表字段映射不能泄漏到上层业务字段；上层只消费标准化模型。
- 三类 Daily Metric 通过统一查询接口暴露，但保持各自权威粒度。
- 成员 5 提交给 LLM 的输入必须来自成员 4 的授权 Selector，保留数据版本和证据引用。
- 文件正文通过 FileStorage；数据库和 API 只暴露授权元数据或受控下载。

## 6. 变更流程

1. 提供方提出契约差异和兼容性影响。
2. 成员 2 检查 OpenAPI、错误码、状态、权限和迁移。
3. 使用方更新类型/Mock/测试。
4. 双方运行契约与联调测试。
5. 破坏性变化写决策日志并提供迁移说明。
6. 未完成交接前不得以临时静态数据宣布功能完成。
