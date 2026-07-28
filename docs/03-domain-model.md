# 03 领域模型

## 1. 领域边界

| 领域 | 核心实体 | 说明 |
|---|---|---|
| 账号与组织 | User、AuthenticationIdentity、Tenant、TenantMembership、Team、TeamMember | User全局、Tenant隔离、Team可选 |
| 权限 | Role、Permission、UserRole、RolePermission、Menu、UserStoreAccess、TeamStoreAccess | 功能权限与数据权限分离 |
| 店铺与商品 | Marketplace、AmazonStore、AdvertisingProfile、Product、MarketplaceCatalogItem、ProductListing、InventorySnapshot、ProfitConfiguration、ProfitConfigurationVersion | 基数和SKU范围部分待确认 |
| 广告结构 | Campaign、AdGroup、Ad、Keyword、Target、SearchTerm、PromotionEvent | 首种广告类型待确认 |
| 报表 | ReportDefinition、ReportSchemaVersion、ReportUpload、ReportFile、ImportTask、ImportBatch、ImportError、FieldMapping、FieldMappingVersion、RawRowManifest | 原始正文不进入MySQL |
| 指标与异常 | DailyMetricFact、MetricAggregationSnapshot、AnomalyRule、AnomalyRecord、RiskAssessment | 事实模型待确认 |
| 智能分析 | AnalysisTask、AnalysisScopeSnapshot、Agent、AgentVersion、AgentRun、AgentStep、Recommendation、RecommendationRevision | 输出结构化且可追溯 |
| 动作工作流 | ActionPreview、ActionPreviewVersion、ActionPreviewItem、ApprovalPolicy、ApprovalStep、ApprovalRecord、ExecutionTask、ExecutionItem、ExecutionRecord、EffectEvaluation、EffectEvaluationSnapshot | 版本和事实只追加 |
| 知识与审计 | UserPreferenceEvent、UserPreference、TeamStrategy、TeamStrategyVersion、KnowledgeDocument、KnowledgeDocumentVersion、KnowledgeRule、KnowledgeRuleVersion、AuditLog、FileAsset、BusinessAttachment | 人工确认知识、不可变审计 |

## 2. 已确认身份关系

- User不含tenant_id。
- User与Tenant通过TenantMembership建立多对多。
- TenantMembership承载成员状态、加入时间等Tenant内属性。
- Team属于一个Tenant；TeamMember只能引用同Tenant的Membership。
- 个人卖家创建Tenant，但无需Team。

## 3. 商品身份

- Product：Tenant内部的业务产品，可跨多个Store。
- MarketplaceCatalogItem：某Marketplace下的ASIN目录对象，候选唯一键为`marketplace_id + asin`。
- ProductListing：Product在一个Store和Marketplace下的Seller SKU，连接内部产品和Amazon目录项。
- ASIN不能代替Product，SKU不能脱离Store/Marketplace范围解释。
- SKU唯一范围和一个ASIN能否关联多个内部Product仍待确认。

## 4. 广告关系

- AdvertisingProfile是Campaign的直接上级业务范围。
- Campaign包含AdGroup。
- AdGroup包含Ad、Keyword或Target；具体组合受广告类型影响。
- Campaign与产品的权威关系优先通过`Ad → ProductListing`表达。
- SearchTerm是被用户实际搜索的词，不等于Keyword。
- SearchTerm不能永久强制关联某个Keyword；当次归因关系保存在带日期、报表来源和粒度的事实数据中。
- PromotionEvent为V1预留，除非首个异常或效果评估明确依赖。

## 5. 报表与事实

- ReportDefinition定义报表业务类型和粒度。
- ReportSchemaVersion冻结字段、类型、必填性和映射版本。
- ReportUpload表示用户上传动作；ReportFile表示具体存储文件。
- ImportTask表示异步生命周期；ImportBatch表示一次可追溯的数据处理批次。
- RawRowManifest只记录原始行对象的存储位置、哈希、数量和解析血缘。
- DailyMetricFact保存权威的每日事实；统一、多表或混合模式待确认。
- MetricAggregationSnapshot只在性能或分析复现有明确需求时实现。

## 6. AI建议与人工修订

- AnalysisTask定义一次业务分析。
- AnalysisScopeSnapshot冻结Tenant、Store、Profile、对象集合、日期和数据版本。
- AgentVersion冻结Agent配置与Prompt版本。
- AgentRun和AgentStep记录运行与结构化证据。
- Recommendation是流程容器。
- AI原始建议是第一条RecommendationRevision。
- 人工每次修改产生新Revision；任何Revision都不允许普通更新。

## 7. Action与不可变性

- ActionPreview是可产生多个版本的业务容器。
- ActionPreviewVersion提交后不可变，保存完整快照和哈希。
- ActionPreviewItem保存逐项强结构动作。
- ApprovalRecord引用具体Version且只追加。
- ExecutionItem从已批准Version生成。
- ExecutionRecord记录一次逐项回填事实且只追加。
- EffectEvaluationSnapshot冻结评估窗口、基线和指标；后续重评创建新快照。

## 8. 数据类别

| 类别 | 代表实体 |
|---|---|
| 主数据 | Tenant、User、Store、Profile、Product、Listing、Campaign、AdGroup、Ad、Keyword、Target |
| 配置数据 | Role、Permission、ReportSchemaVersion、FieldMappingVersion、AnomalyRule、AgentVersion、ApprovalPolicy |
| 事实数据 | DailyMetricFact、InventorySnapshot |
| 流程数据 | ImportTask、AnalysisTask、Recommendation、ActionPreview、ExecutionTask、EffectEvaluation |
| 只追加版本/事件 | RecommendationRevision、ActionPreviewVersion、ApprovalRecord、ExecutionRecord、UserPreferenceEvent、AuditLog |

## 9. 实现阶段

- V1a：身份最小集、Store/Profile、首种报表、首种广告结构、事实和异常。
- V1b：Analysis、Agent、Recommendation。
- V1c：Action、Approval、Execution、附件。
- V1d：Effect、Preference、人工知识。
- 未来：PromotionEvent、复杂聚合快照、多级审批、知识文档高级功能。

详细候选表、字段、约束和生命周期见 [04-database-design.md](04-database-design.md)。
