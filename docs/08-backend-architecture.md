# 08 后端架构

## 1. 逻辑目录

本目录仅为后续初始化规划，本次未创建backend目录。

```text
backend/
  config/
  apps/
    core/
    accounts/
    organizations/
    permissions/
    stores/
    products/
    reports/
    advertising/
    analytics/
    agents/
    recommendations/
    actions/
    knowledge/
    audit/
  integrations/
    llm/
    storage/
    amazon_ads/
  api/
    v1/
```

数据库表名仍严格使用规定的九组前缀，不跟随Django应用名。

## 2. 标准调用链

`DRF View → Serializer参数校验 → Service业务逻辑 → Django ORM → MySQL`

复杂读取：

`DRF View → Query Serializer → Selector/查询服务 → Django ORM → MySQL`

## 3. 职责边界

### View

- HTTP方法、认证入口、请求上下文和响应映射。
- 调用Serializer、Permission/Scope检查和Service。
- 不编排领域细节，不直接写Model状态。

### Serializer

- 请求形状、字段类型、格式和局部跨字段校验。
- 响应序列化与snake_case/camelCase边界配合。
- 不承担跨聚合事务、权限裁决或状态机。

### Service

- 一个业务用例的唯一入口。
- 校验权限、数据范围、业务不变量和状态守卫。
- 定义事务边界。
- 写业务实体、不可变版本、AuditLog和任务派发意图。

### Model

- 持久化映射、数据库约束和局部不变量。
- 提供不绕过Service的最小安全方法。
- 不发网络请求，不调用LLM。

### Selector/查询服务

- 复杂只读查询、授权范围过滤、预取和聚合。
- 不能产生业务副作用。
- 防止View散落ORM逻辑和遗漏tenant/store过滤。

### Celery Task

- 轻量任务入口、反序列化业务任务ID、建立requestId上下文。
- 重新加载权限/业务范围，调用Service。
- 管理基础设施级重试，不直接改核心状态。

### 权限服务

- 计算RBAC权限编码。
- 判定动作权限。
- 不与Store范围混为一个布尔字段。

### 数据范围服务

- 计算UserStoreAccess与TeamStoreAccess并集。
- 为Selector提供强制tenant/store过滤。
- 验证对象关系同Tenant、同Store。

### 状态机服务

- 持有合法转换矩阵、守卫、并发版本和后置动作。
- 产生稳定错误码。
- 记录状态转换审计。

### 文件适配器

- 保存、读取、删除/生命周期管理和生成受控下载。
- 返回稳定storage_key、哈希和元数据。
- 业务模块不依赖本地路径或具体云厂商。

### LLM适配器

- 统一调用、超时、重试、用量、模型引用和结构化响应。
- 实现真实Provider和MockLLMProvider。
- 不决定业务权限、金额和状态。

## 4. 模块依赖方向

- `core`提供无业务含义的基础类型和通用能力。
- `accounts/organizations/permissions`不能依赖广告业务。
- `stores/products/advertising/reports/analytics`可依赖通用平台。
- `agents/recommendations/actions/knowledge`可调用广告业务Service/Selector。
- `integrations`实现由上层定义的端口，不让业务层引用具体SDK。
- 禁止循环依赖；跨模块写操作通过公开Service。

## 5. 事务与异步

- 状态变更、不可变版本、审批/执行记录和AuditLog应在同一数据库事务。
- Celery消息不能早于事务提交被消费者看到。
- 可使用事务提交后回调；若可靠性要求提高，可引入数据库outbox，但不在V1无依据扩展。
- 外部存储写入不能与MySQL形成原子事务，必须设计幂等和孤立文件补偿。
- 长任务按业务attempt记录，Celery重试不能悄然覆盖历史运行。

## 6. 异常处理

- 领域异常映射到稳定错误码和适当HTTP状态。
- 未预期异常对客户端隐藏堆栈和敏感信息。
- 日志包含requestId、tenantId、storeId、业务对象和任务ID，但不记录密码、Token或完整敏感报表行。
- 部分成功必须使用明确业务结果，不能只依赖异常有无。

## 7. requestId

- HTTP入口建立requestId。
- Service、数据库审计、Celery消息和AgentRun传播。
- 后台定时任务自行生成requestId，并记录父任务/调度ID。

## 8. 审计

审计由Service在业务事务中写入，记录actor、Tenant、Store、动作编码、对象、版本、变更摘要、requestId和时间。技术日志不能代替AuditLog。

## 9. Amazon适配器

- `integrations/amazon_ads`在V1只定义端口、Mock或人工执行导出能力。
- 不配置真实凭据，不发送真实投放请求。
- 未来真实实现也必须由Execution Service调用，Agent永远不能直接调用。

## 10. 测试目录规划

每个应用建议包含：

- 单元测试：Service、规则、状态机和计算公式。
- Model/约束测试。
- Selector隔离测试。
- API契约与权限测试。
- Task幂等/重试测试。

项目级测试规划：

```text
backend/tests/
  contract/
  integration/
  security/
  e2e/
  fixtures/
```

测试不得调用真实LLM或真实Amazon服务。

## 11. 不采用Repository层

V1不强制Repository。Django ORM由Service和Selector使用；只有未来出现多个持久化实现或复杂边界时再通过决策记录引入。
