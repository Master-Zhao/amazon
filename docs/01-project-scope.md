# 01 项目范围

> **历史方案说明（已取代）**：本文原始 V1a—V1d 切分保留用于追溯，但其中“一种待确认报表/广告类型”、邮箱密码登录、`UserStoreAccess` 授权、单 Store 分析和“商业级高并发排除”等描述，已被 `codex_master_goal_amazon_ads_v1.md` 的当前确认规格取代，不再作为实施依据。

## 当前有效结论（2026-07-28）

- V1 完整支持 Sponsored Products，以及 Campaign、Targeting、Search Term 三类报表；真实脱敏样例仍是字段与粒度的最终验证条件。
- 认证采用 JWT 双 Token：Access 短期且前端内存优先，Refresh 使用 HttpOnly Cookie；Phase 1 只预留配置，不实现登录。
- 数据范围按 `Tenant → AmazonStore → StoreMarketplace → Marketplace → AdvertisingProfile` 校验；User/Team 的 Store/Profile 白名单和 RBAC 在 Phase 2 实现。
- Campaign、Targeting、Search Term 分别使用独立 Daily Metric 事实表，不使用旧统一事实表。
- V1 包含可压测的高并发框架与 Phase 6 真实压测，但不得在测试前声明任何性能结果。
- 当前仅授权 Phase 1 定向收口，Phase 2—7 仍未实现。

以下内容均为历史记录：

## 1. 历史范围原则

- 每个阶段必须形成可演示、可测试、可审计的垂直切片。
- 列入领域模型不等于立即建表或立即实现。
- 后续阶段只能依赖已验收的前置阶段。
- 涉及待确认规则的功能在决策完成前保持阻塞。

## 2. V1a：确定性数据闭环

### 范围内

- 全局邮箱密码登录和当前Tenant选择；认证载体待确认。
- 自定义User、Tenant、TenantMembership。
- 无Team个人卖家通过UserStoreAccess正常使用。
- Marketplace、AmazonStore、AdvertisingProfile最小主数据。
- 一种待确认Amazon广告类型和一种待确认核心报表。
- 文件上传、异步校验、解析、字段映射、去重和入库。
- 原始文件元数据、哈希、血缘和导入错误。
- 确定性指标与基础异常。
- Campaign列表、趋势和导入审计。

### 阶段出口

- 脱敏样例报表可以稳定重复导入。
- 相同文件、相同行和重述数据按已确认规则处理。
- 用户只能看到当前Tenant及授权Store的数据。

## 3. V1b：智能建议闭环

### 范围内

- AnalysisTask和不可变AnalysisScopeSnapshot。
- 数据分析、异常诊断、预算分析和综合策略Agent。
- AnalysisOrchestrator。
- LLMProvider和MockLLMProvider。
- 结构化Recommendation。
- AI原始Revision和人工Revision只追加。
- 证据、工具结果、错误和AgentVersion可追溯。

### 阶段出口

- Mock Agent可从V1a数据生成符合Schema的建议。
- 不合格输出不能进入审批链。
- Agent不能扩大Tenant、Store或分析对象范围。

## 4. V1c：单级审批与人工执行闭环

### 范围内

- Action Preview容器、不可变版本和逐项动作。
- 待确认的少量动作类型。
- 单级审批、退回、拒绝和撤回控制。
- 人工执行清单。
- 逐项实际值、结果、时间、执行人及可选/强制证据。
- 全链路AuditLog。

### 阶段出口

- 审批和执行始终引用同一不可变版本。
- 执行结果不能覆盖预览值。
- 非法状态转换和重复提交被拒绝。

## 5. V1d：效果与知识闭环

### 范围内

- 待确认观察窗口与基线窗口。
- 执行前后指标快照。
- 初步EffectEvaluation。
- UserPreferenceEvent。
- 候选偏好及人工确认后的UserPreference。
- 人工审核的TeamStrategy和KnowledgeRule版本。

### 阶段出口

- 评估公式和数据窗口可复现。
- 数据不足得到INCONCLUSIVE，不由大模型强行下结论。
- 单次行为不会自动升级为团队知识。

## 6. V1明确排除

| 排除项 | 原因 |
|---|---|
| 真实Amazon Advertising API | V1人工执行 |
| AI自动投放 | 违反人工控制边界 |
| 多级审批 | V1只做单级 |
| 多广告类型并行 | 先验证一种类型 |
| 全部Amazon报表 | 数据模型和解析范围过大 |
| 跨Store分析 | 固定原则要求明确Store范围 |
| 跨币种直接汇总 | 汇率和口径未定义 |
| 复杂知识图谱 | 非闭环最小需要 |
| Agent自改代码、Prompt或规则 | 安全与可追溯性风险 |
| 单次行为自动成为团队知识 | 容易固化偶然选择 |
| 微服务 | 模块化单体足够 |
| 商业级高并发 | V1目标是正确性和闭环 |

## 7. 范围变更规则

任何新增能力必须说明所属阶段、依赖、验收标准、数据隔离、审计要求和是否引入待确认业务规则。未经评审不得以“预留字段”方式悄然扩大范围。
