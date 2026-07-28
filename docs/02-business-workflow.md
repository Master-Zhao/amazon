# 02 业务流程

## 1. 登录与上下文

1. 用户以全局唯一邮箱和密码提交登录。
2. 系统校验账号状态并加载有效TenantMembership。
3. 无有效Membership则拒绝进入业务系统。
4. 只有一个Tenant时自动设置当前Tenant；多个Tenant时要求选择。
5. 系统计算当前Tenant内的功能权限和Store授权并集。
6. 每个业务请求重新验证当前Tenant和目标Store。

认证载体是Cookie Session还是Access/Refresh Token仍为待确认。

## 2. 报表导入

1. 用户选择当前Tenant和一个授权Store。
2. 用户上传Excel或CSV，并声明报表类型、Profile等必要上下文。
3. 后端检查功能权限、Store权限、扩展名、大小和基本元数据。
4. 文件保存到存储适配器，MySQL记录哈希、位置和上传记录。
5. Service创建ImportTask并返回HTTP 202、taskId和查询地址。
6. Celery调用导入Service执行校验、解析、字段映射和标准化。
7. 系统依据报表Schema版本生成自然粒度键和行去重键。
8. 原始行保存到文件/对象存储，MySQL保存RawRowManifest。
9. 权威事实按待确认的迟到/重述规则写入。
10. 系统计算确定性指标并执行版本化异常规则。
11. 用户通过轮询查看任务、错误、部分成功和最终结果。

## 3. 分析与建议

1. 用户在一个Store范围内选择Campaign等对象和日期范围。
2. Service创建AnalysisTask和不可变AnalysisScopeSnapshot。
3. Orchestrator加载已授权、已快照的数据，不接受Agent自行扩展范围。
4. 数据分析、异常诊断和预算分析Agent分别返回结构化结果。
5. 综合策略Agent只消费受验证的上游结构化结果。
6. 任一输出Schema校验失败时阻止建议进入正式流程。
7. 系统保存AgentVersion、工具结果、证据、错误和结构化结论。
8. 系统创建Recommendation及AI原始RecommendationRevision。
9. 操作员接受、修改或拒绝；修改创建新Revision，不覆盖原始内容。

## 4. Action Preview与审批

1. 操作员基于已接受/修订的RecommendationRevision生成草稿。
2. 系统对每个动作执行确定性Schema、权限、对象归属和业务守卫校验。
3. 提交时生成不可变ActionPreviewVersion和内容哈希。
4. ApprovalRecord始终引用具体版本。
5. 审批人只能在拥有权限和目标Store范围时批准、拒绝或退回。
6. 退回后不能修改旧版本；操作员从容器创建新版本。
7. V1只支持单级审批。

## 5. 人工执行

1. 已批准且满足执行前校验的版本进入READY_TO_EXECUTE。
2. Service生成ExecutionTask和逐项ExecutionItem。
3. 执行人员在Amazon后台手工操作。
4. 执行人员逐项填写实际值、结果、执行时间和说明。
5. 高风险动作是否强制截图为待确认。
6. 附件通过FileAsset和BusinessAttachment关联。
7. ExecutionRecord只追加，不能覆盖预览值或历史回填。
8. 任务确认后进入效果观察。

V1只能证明“系统记录的回填与指定预览版本一致”，不能通过API证明Amazon最终状态。

## 6. 效果评估与知识

1. 执行确认时建立观察计划和执行前指标快照。
2. 到达待确认观察窗口后创建评估运行。
3. 使用冻结的基线和观察期数据进行确定性比较。
4. 数据不足时结果为INCONCLUSIVE。
5. 用户接受、拒绝和修改行为先形成UserPreferenceEvent。
6. 达到候选条件后生成候选UserPreference。
7. 用户偏好和TeamStrategy只有经人工确认后生效。
8. 每次评估和知识变更保存版本与AuditLog。

## 7. 失败与补偿原则

- 异步重试创建新的attempt/运行记录，不改写历史尝试。
- 文件保存成功但数据库创建失败时，由补偿任务清理孤立对象；规则需在实现期细化。
- 数据库事务提交后再派发Celery任务，或使用事务后回调/outbox等可靠方式。
- 审批、执行和审计写入失败时，核心状态不得提前推进。
- 部分导入、部分Agent失败和部分执行必须显式展示，不得伪装成完整成功。
