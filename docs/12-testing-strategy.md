# 12 测试策略

> **历史方案说明（已取代）**：本文保留 Phase 0 时的全 V1 测试设想，其中旧 `UserStoreAccess`、单 Store Agent、首种报表待确认、统一事实口径和“本轮尚未初始化工程”等描述，已被 `codex_master_goal_amazon_ads_v1.md` 与当前 Phase 1 工程状态取代。

## 当前有效结论（2026-07-28）

- Phase 1 当前执行 Django check、迁移差异/应用检查、完整 pytest、OpenAPI、前端 lint/typecheck/unit/build、三套 Compose 静态校验和真实运行健康检查。
- API ID 仅通过显式公共标识符字段字符串化；clicks、orders、分页数等普通数字保持 JSON number，Decimal/UUID 保持字符串。
- readiness 必须覆盖 MySQL/Redis/config 故障、503、响应 requestId、同 requestId JSON 告警和敏感连接信息不泄漏。
- Worker 通过进程存活、Broker/inspect ping 验证；Beat 通过 PID1 和真实 beat 命令行验证。
- 认证、Tenant/Store/Profile/RBAC 和三类报表属于后续授权阶段，测试目标保留但尚未实现。
- 自动化浏览器 E2E 不作为 Phase 1 的 20 项阻塞条件；本次不新增 E2E 依赖，后续业务联调和 Phase 7 再落地。此前真实浏览器验收证据仍有效，但不得称为可重复自动化 E2E。

以下第 1—11 节为历史测试设计：

## 1. 历史原则

- 优先测试业务不变量、隔离、状态转换和不可变历史。
- 确定性算法使用表格驱动和边界测试。
- 所有外部边界使用Mock/Fake；自动化测试不调用真实LLM、Amazon或真实对象存储。
- 每个缺陷应补充能阻止回归的最低层测试。

## 2. 测试分层

| 层次 | 目标 |
|---|---|
| 单元测试 | 公式、规则、状态机、权限合并、Schema校验 |
| Model/数据库测试 | 外键、唯一约束、只追加保护、同Tenant/Store不变量 |
| Service测试 | 事务、状态守卫、AuditLog、幂等、版本冲突 |
| Selector测试 | Tenant/Store过滤、聚合粒度、防重复汇总 |
| API契约测试 | HTTP、响应结构、错误码、camelCase、OpenAPI |
| Task测试 | Celery重试、取消、幂等、事务提交后派发 |
| 前端单元/组件测试 | 状态展示、权限控件、前后值对比 |
| 端到端测试 | 从登录到效果评估的V1闭环 |
| 安全测试 | 越权、文件攻击、敏感日志、认证边界 |
| 新环境复现 | 干净环境安装、迁移、构建、健康检查 |

## 3. 身份与权限

- 自定义User从首次迁移可用，User无tenant_id。
- 全局唯一规范化邮箱。
- User加入多个Tenant。
- 只有一个Tenant自动进入，多个Tenant要求选择。
- 无Team个人卖家通过UserStoreAccess操作。
- RBAC允许和拒绝矩阵。
- 用户直接Store授权与团队授权并集。
- Membership、Team或Access失效。
- 有功能权限无Store权限；有Store权限无功能权限。
- 跨Tenant详情返回不泄露信息的404。
- 跨Store列表、详情、附件、任务和审计隔离。

## 4. 报表导入

- 支持的扩展名、MIME和魔数。
- 最大文件、编码、工作表规则在决策后测试。
- 缺字段、错字段、重复字段、非法日期、非法Decimal和currency缺失。
- 报表Store/Profile归属不匹配。
- FieldMappingVersion和SchemaVersion追溯。
- 完全重复文件、重复行和跨批次重复。
- 迟到与重述规则在确认后建立场景。
- PARTIAL_SUCCEEDED计数一致。
- RawRowManifest哈希、行数和血缘。
- 重试创建新attempt，不覆盖旧批次。

## 5. 指标和异常

每个指标覆盖正常值、零分母、负值、极大值、Decimal精度、空值和跨币种：

- CTR = clicks / impressions。
- CPC = spend / clicks。
- CVR的订单/点击口径待首种报表确认。
- ACOS = spend / sales。
- ROAS = sales / spend。

零分母不得产生Infinity/NaN，也不得未经规则定义伪造为0。

异常规则测试：

- 阈值边界前、等于、超过。
- 数据不足。
- 规则版本变化不改写历史命中。
- 相同数据和规则不重复生成记录。

## 6. 状态机

每个状态测试：

- 所有合法前置状态。
- 每个非法前置状态。
- 权限不足。
- Store越权。
- 守卫失败。
- 重复命令/幂等键。
- 乐观锁冲突。
- 后置动作失败时事务回滚。
- AuditLog与业务状态一致。
- 终态不可退回运行态。

覆盖报表导入、AnalysisTask、AgentRun、Recommendation、Action Preview、审批、人工执行和EffectEvaluation。

## 7. AI与Mock

- MockLLMProvider固定结果可重复。
- 模拟超时、限流、无效结构、Schema错误和服务不可用。
- AgentVersion/Prompt版本记录。
- Agent对象ID越出ScopeSnapshot时拒绝。
- Agent试图输出未允许动作时拒绝。
- 不合格结果不能创建Recommendation或进入审批。
- AI原始Revision不可修改；人工修订追加版本。
- 不调用真实Provider，不保存隐藏思维过程。

## 8. Action、审批与执行

- Preview从指定RecommendationRevision生成。
- 每个PreviewItem before/after和currency完整。
- 提交生成不可变Version和稳定hash。
- Version、ApprovalRecord和ExecutionRecord不能普通更新/删除。
- 单级审批批准、拒绝、退回和撤回。
- 重复审批返回`APPROVAL_ALREADY_DECIDED`。
- 审批人Store范围和待确认自批规则。
- ExecutionItem与批准Version逐项对应。
- 实际值不覆盖预览值。
- 证据附件权限、类型、哈希和下载隔离。
- 部分执行与失败展示规则在确认后测试。

## 9. 效果与知识

- 观察窗口未到不能评估。
- 基线、观察期和数据版本固定。
- 六个评估终态可按规则进入。
- 数据不足为INCONCLUSIVE。
- 重评创建新Snapshot。
- 单个UserPreferenceEvent不直接生成生效团队知识。
- 人工确认者、版本和AuditLog完整。

## 10. API与前端

- OpenAPI有效且无未评审破坏性变化。
- JSON camelCase、ID字符串、ISO 8601、金额字符串+currency。
- 统一成功/错误、字段错误和requestId。
- 204与文件响应例外。
- 202包含taskId、taskUrl和轮询提示。
- 前端类型检查通过。
- 前端生产构建通过。
- 加载、空、部分失败、完全失败、403、404、409页面状态。
- AI Revision和Action前后值对比。

## 11. 新环境复现

在版本基线确认和项目初始化后，CI应从干净环境验证：

1. 安装锁定依赖。
2. 创建测试配置。
3. 执行全部迁移。
4. 运行后端测试和OpenAPI检查。
5. 运行前端类型检查、测试和生产构建。
6. 启动所需服务并执行健康检查。
7. 使用Mock完成端到端流程。

本轮尚未初始化工程，因此未执行上述命令。
