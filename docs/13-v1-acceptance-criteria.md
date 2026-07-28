# 13 V1验收标准

## 1. 总体验收原则

- 每项必须有可重复的测试证据。
- “页面能显示”不能代替后端约束、权限和审计验证。
- 所有待确认项在相关阶段开发前必须转为已确认决策。
- 端到端验收只使用脱敏样例和Mock外部服务。

## 2. V1a验收

### 身份与隔离

- [ ] Django首次初始化即使用自定义User。
- [ ] User不含tenant_id，邮箱全局唯一。
- [ ] TenantMembership支持同一User加入多个Tenant。
- [ ] 一个Tenant自动进入，多个Tenant要求选择。
- [ ] 无Team个人卖家通过UserStoreAccess正常使用。
- [ ] RBAC和Store授权并集按文档计算。
- [ ] 跨Tenant和跨Store的列表、详情、任务和附件均被阻止。

### 报表与指标

- [ ] 已人工确认首种广告类型、首种报表和脱敏样例。
- [ ] 文件类型、最大尺寸、编码和工作表规则已冻结。
- [ ] 上传返回202、taskId和查询地址。
- [ ] 异步完成校验、解析、字段映射、去重和入库。
- [ ] 完全成功、部分成功、失败和取消按状态机工作。
- [ ] 重复文件、重复行、迟到和重述按确认规则处理。
- [ ] 原始正文不进入MySQL，哈希和血缘可追溯。
- [ ] CTR、CPC、CVR、ACOS、ROAS及零分母测试通过。
- [ ] Campaign列表、趋势和基础异常只显示授权Store。
- [ ] 导入和敏感操作产生AuditLog。

## 3. V1b验收

- [ ] AnalysisTask只允许单Store范围。
- [ ] AnalysisScopeSnapshot不可变并可复现。
- [ ] 四类Agent和Orchestrator按固定结构通信。
- [ ] Agent不互相自由调用，不扩大数据范围。
- [ ] 所有调用经过LLMProvider。
- [ ] 自动化测试只使用MockLLMProvider。
- [ ] 每次运行记录AgentVersion、结构化证据、工具结果和错误。
- [ ] 无效输出Schema被拒绝且不能进入审批。
- [ ] AI原始RecommendationRevision不可修改。
- [ ] 操作员修改产生新Revision并支持对比。
- [ ] 不保存或展示隐藏思维过程。

## 4. V1c验收

- [ ] 已确认V1允许的Action类型。
- [ ] PreviewItem逐项包含目标、before、after、currency、风险和来源。
- [ ] 提交产生不可变ActionPreviewVersion和内容hash。
- [ ] 审批明确引用具体Version。
- [ ] V1仅单级审批。
- [ ] 批准、拒绝、退回、撤回和过期符合状态机。
- [ ] 重复审批、非法转换和版本冲突被拒绝。
- [ ] 批准版本生成逐项人工执行清单。
- [ ] 实际执行结果不覆盖预览值。
- [ ] ExecutionRecord只追加。
- [ ] 证据附件按Tenant/Store授权下载。
- [ ] 全链路AuditLog可按requestId和业务对象查询。

## 5. V1d验收

- [ ] 观察窗口和基线窗口已人工确认。
- [ ] 执行前后数据版本和评估方法可复现。
- [ ] 六个效果终态有确定性判定规则。
- [ ] 数据不足得到INCONCLUSIVE。
- [ ] 重评创建新的EffectEvaluationSnapshot。
- [ ] 接受、修改和拒绝先形成UserPreferenceEvent。
- [ ] 单次事件不会自动成为UserPreference或TeamStrategy。
- [ ] 生效偏好、策略和知识均有人工确认及版本。

## 6. 横向质量验收

- [ ] OpenAPI与实际接口一致。
- [ ] JSON字段、ID、时间、金额和currency符合API规范。
- [ ] 状态只能经Service转换。
- [ ] 只追加表不能普通更新、删除或软删除。
- [ ] Redis故障不会丢失审批、执行和审计权威数据。
- [ ] 后端测试、前端类型检查和前端生产构建通过。
- [ ] 干净环境可复现安装、迁移、测试、构建和Mock端到端流程。
- [ ] 仓库不含密码、Token、密钥、真实账号或未脱敏报表。

## 7. V1端到端验收场景

1. 用户登录。
2. 进入唯一Tenant或选择当前Tenant。
3. 选择授权Store。
4. 上传一种已确认Amazon广告报表。
5. 收到202并轮询异步导入。
6. 查看成功/部分成功结果和错误。
7. 查看Campaign指标、趋势和异常。
8. 创建单Store AnalysisTask。
9. Mock Agent生成通过Schema的结构化建议。
10. 操作员创建人工RecommendationRevision。
11. 从指定Revision创建Action Preview。
12. 提交不可变Version进行单级审批。
13. 审批通过并生成执行清单。
14. 执行人员逐项回填结果和所需证据。
15. 确认执行，审计链完整。
16. 进入观察周期。
17. 到期生成初步EffectEvaluationSnapshot。
18. 生成偏好事件，但不自动发布团队知识。

## 8. 验收阻塞条件

- 首种报表无真实脱敏样例。
- Store/Marketplace/Profile基数未确认。
- 事实模型、重述规则、SKU唯一范围未确认。
- Action类型、评估窗口、LLM数据边界未确认。
- 认证方式和运行时版本未冻结。
