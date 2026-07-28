# 00 项目总览

## 1. 项目定位

“亚马逊广告智能投放系统”面向个人卖家、品牌卖家、跨境电商企业及其广告运营、数据分析、审批、人工执行和只读查看人员。

系统核心目标是把分散的Amazon广告报表和人工经验转换成一条可审计、可回溯、可人工控制的优化闭环，而不是让AI直接控制广告账户。

## 2. 核心能力

1. 接收并校验Amazon广告Excel/CSV报表。
2. 标准化数据、识别重复和重述数据。
3. 使用确定性算法计算CTR、CPC、CVR、ACOS、ROAS等指标。
4. 以规则识别异常和风险。
5. 通过受控多智能体形成带证据的结构化建议。
6. 允许操作员接受、修改或拒绝建议。
7. 将确认后的建议生成不可变Action Preview版本。
8. 执行单级审批。
9. 生成待人工执行清单并逐项回填结果和证据。
10. 在观察周期后执行初步效果评估。
11. 将行为先保存为事件，经人工确认后形成偏好或团队知识。

## 3. 参与者

| 参与者 | 主要职责 |
|---|---|
| 个人卖家 | 管理自己的Tenant和Store，可不创建Team |
| Tenant管理员 | 管理成员、角色、权限、Team和Store授权 |
| 广告运营 | 导入报表、创建分析、修订建议、执行动作 |
| 数据分析人员 | 查看指标、异常、证据和分析结果 |
| 审批人员 | 对指定Action Preview版本作单级审批 |
| 人工执行人员 | 在Amazon后台执行并逐项回填 |
| 只读人员 | 在授权Store范围内查看 |
| 系统任务 | 执行解析、计算、Agent编排和效果评估 |

## 4. 核心上下文

- User为全局账号，邮箱全局唯一。
- User通过TenantMembership加入Tenant。
- 登录后必须具有明确的当前Tenant；只有一个Tenant时自动进入，多个Tenant时选择。
- Team属于Tenant且可选。
- 功能权限与Store数据范围分开计算。
- 当前Store必须属于当前Tenant，并位于用户有效授权集合。

## 5. 四层架构

| 层次 | 内容 |
|---|---|
| 基础设施层 | MySQL、Redis、Celery、存储、LLM适配、可观测性 |
| 通用平台层 | 账号、Tenant、Team、RBAC、Store范围、文件、审计 |
| 广告业务层 | 店铺、商品、广告结构、报表、指标、异常 |
| 智能应用层 | 分析、Agent、建议、预览、审批、执行、评估、知识 |

## 6. 非目标

- V1不连接真实Amazon Advertising API。
- V1不允许AI自动修改广告。
- V1不支持多级审批、跨Store分析和跨币种直接汇总。
- V1不同时支持多种广告类型或全部报表。
- V1不拆微服务、不建设复杂知识图谱或商业级高并发平台。

## 7. 关键术语

| 术语 | 定义 |
|---|---|
| Tenant | 独立卖家主体及业务隔离边界 |
| TenantMembership | User加入Tenant的成员关系 |
| Store | Amazon店铺，和Marketplace/Profile基数待确认 |
| Marketplace | Amazon站点参考数据 |
| AdvertisingProfile | 广告Profile/账户 |
| Product | Tenant内部产品概念 |
| MarketplaceCatalogItem | 某Marketplace下的ASIN目录对象 |
| ProductListing | Product在Store和Marketplace下的Seller SKU |
| Recommendation | AI生成建议的业务容器 |
| RecommendationRevision | AI原始内容或人工修订的不可变版本 |
| Action Preview | 待审批动作集合 |
| ActionPreviewVersion | 提交、审批和执行所引用的不可变版本 |

## 8. 待确认入口

所有未决事项集中登记在 [15-decision-log.md](15-decision-log.md)。未确认项不得被实现为隐含业务规则。
