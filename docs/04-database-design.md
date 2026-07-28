# 04 数据库逻辑设计

## 1. 文档边界

本文只定义逻辑候选表，不是SQL、Django Model或迁移。是否“立即实现”按V1阶段判断；标记“否”的实体不得仅因出现在本表中就提前建表。

## 2. 全局约定

- 主键建议为内部`id: bigint`，API一律以字符串输出；是否采用UUID可在实现评审时决定。
- Amazon外部ID统一为`varchar`，不得用数值主键表达。
- 金额为`decimal`并配套`currency: char(3)`；JSON金额是字符串。
- 时间点为带UTC语义的`datetime`；Amazon业务日期为`date`并保留Marketplace时区来源。
- `tenant_id`、`store_id`等隔离字段建议显式保存，不只通过多层关系推导。
- 所有外键关系必须校验同Tenant；广告业务关系还要校验同Store/Profile。
- 软删除建议使用`archived_at`或业务状态，不统一使用含义模糊的`is_deleted`。
- 只追加表禁止普通UPDATE、DELETE和软删除；修正以新事件/版本表达。
- 事实表唯一键不得依赖多个可空列在MySQL中的NULL唯一语义，建议使用非空确定性`grain_key`。

## 3. 字典阅读方式

每行覆盖要求的24项：

1. 表名；2. Django模块；3. 职责；4. 阶段；5. 是否立即实现；6. 核心字段；7. 类型；8. 主键；9. 外键；10. 唯一约束；11. 索引；12—15. T/S/M/P作用域；16—19. 更新/删除/软删/只追加；20. 生命周期；21. 增长；22. 查询；23. 关系；24. 待确认。

缩写：

- `T/S/M/P`：是否包含tenant_id/store_id/marketplace_id/profile_id。
- `是/否/条件`表示字段必要性。
- `更新`：是否允许普通业务更新；`删除`：是否允许普通物理删除；`软删`：是否采用归档；`追加`：是否只追加。
- “立即”是指所属V1阶段开始时需要实现，不表示本次创建。

## 4. sys_：系统、用户、租户与权限

| 表名 | 模块；阶段；立即 | 职责与核心字段/类型 | PK/FK | 唯一与索引 | T/S/M/P | 更新/删除/软删/追加 | 生命周期、增长、查询、关系、待确认 |
|---|---|---|---|---|---|---|---|
| `sys_user` | accounts；V1a；是 | 全局账号；email varchar、password_hash varchar、status code、last_login_at datetime | id；无Tenant FK | normalized_email唯一；status+created_at | 否/否/否/否 | 是/否/否/否 | 长期、低；登录/账号状态；经Membership关联Tenant；认证载体待确认 |
| `sys_authentication_identity` | accounts；V1a；是 | 登录身份；user_id、type code、normalized_identifier varchar、verified_at | id；user | type+identifier唯一；user_id | 否/否/否/否 | 条件/否/归档/否 | 长期、低；按标识登录；属于User；V1是否只保留email待确认 |
| `sys_tenant` | organizations；V1a；是 | 卖家主体；name varchar、code varchar、status code、default_currency char(3) | id | code唯一；status | 否/否/否/否 | 是/否/归档/否 | 长期、低；当前Tenant；拥有Membership/Store；默认币种不得用于无currency金额 |
| `sys_tenant_membership` | organizations；V1a；是 | User加入Tenant；tenant_id、user_id、status、joined_at | id；tenant、user | tenant+user唯一；user+status、tenant+status | 是/否/否/否 | 是/否/归档/否 | 长期、低中；用户Tenant列表；TeamMember/UserRole基于它；成员停用规则待确认 |
| `sys_team` | organizations；V1a预留；条件 | 可选团队；tenant_id、name、status | id；tenant | tenant+规范化name有效期唯一；tenant+status | 是/否/否/否 | 是/否/是/否 | 长期、低；团队管理；关联TeamMember/TeamStoreAccess；V1a是否开放团队UI待确认 |
| `sys_team_member` | organizations；V1a预留；条件 | Membership加入Team；tenant_id、team_id、membership_id、status | id；tenant、team、membership | team+membership唯一；membership+status | 是/否/否/否 | 是/否/归档/否 | 长期、低中；计算团队授权；同Tenant守卫；无Team个人卖家不创建 |
| `sys_role` | permissions；V1a；是 | Tenant内角色或系统模板；tenant_id可空、code、name、scope code、status | id；tenant可空 | scope+tenant+code候选唯一；tenant+status | 条件/否/否/否 | 是/否/归档/否 | 长期、低；角色管理；关联UserRole；租户自定义开放时间待确认 |
| `sys_permission` | permissions；V1a；是 | 稳定权限目录；code、resource、action、description | id | code全局唯一；resource+action | 否/否/否/否 | 受控/否/否/否 | 随版本、低；权限校验；关联RolePermission；编码只增不随意改 |
| `sys_user_role` | permissions；V1a；是 | TenantMembership的角色；tenant_id、membership_id、role_id、valid_from/to | id；tenant、membership、role | tenant+membership+role+有效期候选唯一；membership | 是/否/否/否 | 条件/否/归档/否 | 长期、低中；功能权限计算；角色必须在同作用域 |
| `sys_role_permission` | permissions；V1a；是 | 角色权限关系；role_id、permission_id | id；role、permission | role+permission唯一；permission_id | 条件/否/否/否 | 是/是/否/否 | 配置期、低；加载权限；删除仅限未使用配置且需审计 |
| `sys_menu` | permissions；V1a；是 | 前端菜单目录；parent_id、code、route_name、permission_code、order | id；parent自引用 | code唯一；parent+order | 否/否/否/否 | 受控/否/归档/否 | 随版本、低；动态菜单；不作为后端授权依据 |
| `sys_user_store_access` | permissions；V1a；是 | 用户直接Store授权；tenant_id、membership_id、store_id、valid_from/to、status | id；tenant、membership、ads_store | tenant+membership+store有效期候选唯一；membership+status、store+status | 是/是/否/否 | 是/否/归档/否 | 长期、低中；Store范围并集；同Tenant强校验 |
| `sys_team_store_access` | permissions；V1a预留；条件 | 团队Store授权；tenant_id、team_id、store_id、valid_from/to、status | id；tenant、team、ads_store | tenant+team+store有效期候选唯一；team+status、store+status | 是/是/否/否 | 是/否/归档/否 | 长期、低中；Store范围并集；Team功能启用时实现 |

## 5. ads_：店铺、商品与广告结构

| 表名 | 模块；阶段；立即 | 职责与核心字段/类型 | PK/FK | 唯一与索引 | T/S/M/P | 更新/删除/软删/追加 | 生命周期、增长、查询、关系、待确认 |
|---|---|---|---|---|---|---|---|
| `ads_marketplace` | stores；V1a；是 | Amazon站点参考；code varchar、country_code、default_currency、timezone | id | code唯一；country_code | 否/否/否/否 | 受控/否/否/否 | 系统长期、极低；站点解析；被Store/CatalogItem引用；代码和时区需样例确认 |
| `ads_store` | stores；V1a；是 | Tenant下店铺；tenant_id、name、external_seller_id varchar、status | id；tenant | 候选tenant+external_seller_id+marketplace；tenant+status | 是/条件/条件/否 | 是/否/归档/否 | 长期、低；Store选择；基数关系待确认，故marketplace字段和唯一键阻塞 |
| `ads_advertising_profile` | stores；V1a；是 | 广告Profile；tenant_id、store_id、marketplace_id、external_profile_id varchar、currency、timezone、status | id；tenant、store、marketplace | tenant+external_profile_id唯一；tenant+store+status | 是/是/是/是(自身) | 是/否/归档/否 | 长期、低；广告范围；Store/Profile基数待确认 |
| `ads_product` | products；V1a按报表；条件 | Tenant内部产品；tenant_id、internal_code、name、status | id；tenant | tenant+internal_code唯一；tenant+status | 是/否/否/否 | 是/否/归档/否 | 长期、低中；跨Store产品分析；一个ASIN多Product待确认 |
| `ads_marketplace_catalog_item` | products；V1a按报表；条件 | Marketplace下ASIN；marketplace_id、asin varchar、title、status | id；marketplace | marketplace+asin唯一；asin | 否/否/是/否 | 是/否/归档/否 | 长期、中；ASIN查找；被Listing引用；目录来源待确认 |
| `ads_product_listing` | products；V1a按报表；条件 | Store/Marketplace下SKU；tenant_id、store_id、marketplace_id、product_id、catalog_item_id、seller_sku varchar、price decimal、currency、status | id；tenant/store/marketplace/product/catalog | 候选tenant+store+marketplace+sku；store+sku、marketplace+asin间接 | 是/是/是/否 | 是/否/归档/否 | 长期、中；SKU/ASIN查询；连接Product、Ad；SKU唯一范围待确认 |
| `ads_inventory_snapshot` | products；未来或V1d；否 | 某时点库存；tenant/store/marketplace/listing、snapshot_at、quantity decimal、source | id；上述FK | listing+snapshot_at+source唯一；store+snapshot_at | 是/是/是/否 | 否/否/否/是 | 按保留期、高；库存趋势；是否纳入V1异常待确认 |
| `ads_profit_configuration` | products；未来或V1b；否 | 当前利润配置容器；tenant_id、product/listing作用域、status、current_version | id；tenant，product/listing可空 | tenant+作用域有效配置唯一；tenant+status | 是/条件/条件/否 | 是/否/归档/否 | 长期、低；预算/利润分析；配置粒度待确认 |
| `ads_profit_configuration_version` | products；未来或V1b；否 | 不可变利润版本；configuration_id、version、cost decimal、fees decimal、currency、effective_at | id；configuration | configuration+version唯一；configuration+effective_at | 是(建议冗余)/条件/条件/否 | 否/否/否/是 | 长期、中；按日期取版本；币种和成本口径待确认 |
| `ads_campaign` | advertising；V1a；是 | Campaign主数据；tenant/store/marketplace/profile、external_campaign_id varchar、name、type、status、budget decimal、currency | id；scope FK | tenant+profile+external_id唯一；tenant+store+profile+status | 是/是/是/是 | 是/否/归档/否 | 长期、中；列表/趋势；首种广告类型待确认 |
| `ads_ad_group` | advertising；V1a按报表；条件 | AdGroup；scope、campaign_id、external_ad_group_id、name、status、default_bid decimal/currency | id；scope/campaign | tenant+profile+external_id唯一；campaign+status | 是/是/是/是 | 是/否/归档/否 | 长期、中；Campaign详情；报表是否提供待确认 |
| `ads_ad` | advertising；V1a按报表；条件 | 具体广告及Listing关系；scope、ad_group_id、product_listing_id、external_ad_id、status | id；scope/ad_group/listing | tenant+profile+external_id唯一；ad_group+status、listing | 是/是/是/是 | 是/否/归档/否 | 长期、中高；Campaign产品关系；首种广告类型影响结构 |
| `ads_keyword` | advertising；V1a按报表；条件 | 关键词投放对象；scope、ad_group_id、external_keyword_id、text、match_type、bid、status | id；scope/ad_group | tenant+profile+external_id唯一；ad_group+status、text+match_type | 是/是/是/是 | 是/否/归档/否 | 长期、中高；关键词趋势；首种类型/报表待确认 |
| `ads_target` | advertising；V1a按报表；条件 | 商品/自动等Target；scope、ad_group_id、external_target_id、expression json/varchar、target_type、bid、status | id；scope/ad_group | tenant+profile+external_id；ad_group+type+status | 是/是/是/是 | 是/否/归档/否 | 长期、中高；Target趋势；expression规范待样例确认 |
| `ads_search_term` | advertising；V1a按报表；条件 | 规范化搜索词词典；tenant/store/marketplace/profile、normalized_text、display_text | id；scope | 候选tenant+profile+normalized_text；store+text | 是/是/是/是 | 受控/否/否/否 | 长期、高；搜索词查询；不永久强绑Keyword |
| `ads_promotion_event` | advertising；未来；否 | 促销/外部事件；tenant/store/marketplace、name、start/end、type、source | id；scope | tenant+store+name+start候选唯一；store+start+end | 是/是/是/否 | 是/否/归档/否 | 长期、中；效果解释；V1不立即实现 |

## 6. report_：报表与导入

| 表名 | 模块；阶段；立即 | 职责与核心字段/类型 | PK/FK | 唯一与索引 | T/S/M/P | 更新/删除/软删/追加 | 生命周期、增长、查询、关系、待确认 |
|---|---|---|---|---|---|---|---|
| `report_definition` | reports；V1a；是 | 报表类型/粒度；code、name、ad_type、grain、status | id | code唯一；ad_type+status | 否/否/否/否 | 受控/否/归档/否 | 随版本、低；类型选择；首种报表/广告类型待确认 |
| `report_schema_version` | reports；V1a；是 | 字段Schema版本；definition_id、version、columns json、effective_at、checksum | id；definition | definition+version唯一；definition+effective_at | 否/否/否/否 | 否/否/否/是 | 长期、低；解析器选版；真实脱敏样例缺失 |
| `report_upload` | reports；V1a；是 | 用户上传动作；tenant/store/marketplace/profile、uploader_id、report_definition_id、status、created_at | id；scope/user/definition | 可选幂等键唯一；tenant+store+status+created | 是/是/是/条件 | 仅状态Service/否/否/否 | 按保留策略、中高；上传列表；一次多文件规则待确认 |
| `report_file` | reports；V1a；是 | 上传中的具体文件；upload_id、file_asset_id、sha256、original_name、size、media_type | id；upload/file_asset | upload+file_asset唯一；tenant+sha256经upload查询 | 是(建议显式)/是/是/条件 | 否/否/否/是 | 随文件保留、中高；文件血缘；最大尺寸/编码/工作表待确认 |
| `report_import_task` | reports；V1a；是 | 异步任务当前态；tenant/store/upload_id、status、progress、attempt、error_summary | id；scope/upload | upload+attempt唯一；tenant+store+status+created | 是/是/是/条件 | 仅Service/否/否/否 | 运营期、中高；轮询/队列；重试新attempt |
| `report_import_batch` | reports；V1a；是 | 一次不可变处理批次；tenant/store/profile、task_id、schema_version_id、parser_version、started/finished、counts | id；scope/task/schema | task唯一或task+subbatch；store+finished | 是/是/是/条件 | 完成前受控/否/否/完成后追加 | 长期、中高；追溯导入；迟到/重述规则待确认 |
| `report_import_error` | reports；V1a；是 | 行/文件错误；tenant/store/batch_id、row_number、field、code、message、raw_ref | id；scope/batch | 无业务唯一；batch+row_number、batch+code | 是/是/是/条件 | 否/否/否/是 | 按保留期、高；错误明细；敏感值脱敏规则待确认 |
| `report_field_mapping` | reports；V1a；是 | 映射容器；definition_id、tenant_id可空、name、status,current_version | id；definition/tenant | definition+tenant+name有效唯一；definition+status | 条件/否/否/否 | 是/否/归档/否 | 长期、低；选择映射；系统模板与租户覆盖 |
| `report_field_mapping_version` | reports；V1a；是 | 不可变映射版本；mapping_id、version、rules json、checksum | id；mapping | mapping+version唯一；mapping+version | 条件/否/否/否 | 否/否/否/是 | 长期、低中；复现解析；规则格式待首份样例确认 |
| `report_raw_row_manifest` | reports；V1a；是 | 原始行对象清单；tenant/store/batch_id、storage_key、sha256、row_count、encoding、format | id；scope/batch | batch+storage_key唯一；batch、sha256 | 是/是/是/条件 | 否/否/否/是 | 待确认保留期、中；重新解析/审计；正文在对象/文件存储 |

## 7. analytics_：指标与异常

| 表名 | 模块；阶段；立即 | 职责与核心字段/类型 | PK/FK | 唯一与索引 | T/S/M/P | 更新/删除/软删/追加 | 生命周期、增长、查询、关系、待确认 |
|---|---|---|---|---|---|---|---|
| `analytics_daily_metric_fact` | analytics；V1a；是 | 权威日事实；scope、report_definition/schema/batch、business_date、grain_type、grain_key、维度FK、impressions/clicks/orders、spend/sales decimal、currency、derived metrics decimal | id；scope/report/batch及维度FK | tenant+store+definition+date+grain_key唯一；store+date、campaign+date、target维度+date | 是/是/是/是 | 按重述策略受控/否/否/否或版本追加 | 高增长；趋势/异常；事实模型与重述规则待确认 |
| `analytics_metric_aggregation_snapshot` | analytics；未来或V1b；否 | 聚合/分析快照；scope、source_range、grain、payload/指标、generated_at、source_version | id；scope | scope+grain+range+source_version候选唯一；store+generated_at | 是/是/是/条件 | 否/否/否/是 | 可过期、中高；性能/复现；明确用途前不实现 |
| `analytics_anomaly_rule` | analytics；V1a；是 | 确定性异常规则；code、version、scope、parameters json、severity、status | id | code+version唯一；status+scope | 条件/否/否/否 | 否/否/归档/版本追加 | 长期、低；规则加载；阈值来源和租户覆盖待确认 |
| `analytics_anomaly_record` | analytics；V1a；是 | 规则命中事实；scope、rule_id、metric_fact/ref、object_type/id、detected_at、severity、evidence json、status | id；scope/rule/事实可选 | rule+object+data_window+source_version去重；store+status+detected | 是/是/是/是 | 仅处置状态Service/否/否/事实追加 | 高；异常列表；状态处置范围待确认 |
| `analytics_risk_assessment` | analytics；V1b或未来；否 | 多信号综合风险快照；scope、object、as_of、score decimal、level、evidence、rule_versions | id；scope | object+as_of+source_version唯一；store+level+as_of | 是/是/是/条件 | 否/否/否/是 | 中高；风险排序；与Anomaly边界需实现前确认 |

## 8. ai_：分析、Agent与建议

| 表名 | 模块；阶段；立即 | 职责与核心字段/类型 | PK/FK | 唯一与索引 | T/S/M/P | 更新/删除/软删/追加 | 生命周期、增长、查询、关系、待确认 |
|---|---|---|---|---|---|---|---|
| `ai_analysis_task` | agents；V1b；是 | 分析任务当前态；tenant/store/profile、creator、status、requested_range、current_attempt | id；scope/user | 可选idempotency_key唯一；tenant+store+status+created | 是/是/是/条件 | 仅Service/否/否/否 | 长期、中高；任务列表；V1禁止跨Store |
| `ai_analysis_scope_snapshot` | agents；V1b；是 | 不可变数据范围；task_id、tenant/store/profile、object_refs json、date_range、metric_source_versions、hash | id；task/scope | task+version唯一；task | 是/是/是/条件 | 否/否/否/是 | 长期、中高；复现分析；快照详细格式待确认 |
| `ai_agent` | agents；V1b；是 | Agent登记；code、name、purpose、status、current_version | id | code唯一；status | 否/否/否/否 | 受控/否/归档/否 | 随版本、低；编排选择；不允许Agent自改 |
| `ai_agent_version` | agents；V1b；是 | Agent/Prompt版本；agent_id、version、input_schema、output_schema、allowed_tools、prompt_ref/hash、status | id；agent | agent+version唯一；agent+status | 否/否/否/否 | 否/否/否/是 | 长期、低；追溯；LLM可接收数据待确认 |
| `ai_agent_run` | agents；V1b；是 | 一次Agent运行；tenant/store/task、agent_version、status、attempt、started/finished、provider/model ref、usage | id；scope/task/version | task+agent_version+attempt唯一；task+status | 是/是/是/条件 | 仅Service/否/否/完成后追加 | 高；运行追踪；输入输出保存期待确认 |
| `ai_agent_step` | agents；V1b；是 | 结构化步骤/工具结果；tenant/store/run、sequence、type、input_ref、output_ref、evidence、error | id；scope/run | run+sequence唯一；run+type | 是/是/条件/条件 | 否/否/否/是 | 很高、按保留期；诊断；不保存隐藏思维过程 |
| `ai_recommendation` | recommendations；V1b；是 | 建议流程容器；tenant/store/profile/task、status,current_revision、created_by_type | id；scope/task | task+业务对象候选去重；store+status+created | 是/是/是/条件 | 仅Service/否/否/否 | 长期、中高；建议工作台；状态语义见状态机 |
| `ai_recommendation_revision` | recommendations；V1b；是 | AI原始/人工修订；tenant/store/recommendation、version、author、source_type、content json、evidence_refs、hash | id；scope/recommendation/user可空 | recommendation+version唯一；recommendation+created | 是/是/是/条件 | 否/否/否/是 | 长期、高；版本对比；AI原始内容不可覆盖 |

## 9. action_：预览、审批、执行与评估

| 表名 | 模块；阶段；立即 | 职责与核心字段/类型 | PK/FK | 唯一与索引 | T/S/M/P | 更新/删除/软删/追加 | 生命周期、增长、查询、关系、待确认 |
|---|---|---|---|---|---|---|---|
| `action_preview` | actions；V1c；是 | Action Preview容器；tenant/store/profile、recommendation_revision、status,current_version,creator | id；scope/revision/user | revision+活动preview候选唯一；store+status+created | 是/是/是/条件 | 仅Service/否/否/否 | 长期、中高；预览列表；动作类型待确认 |
| `action_preview_version` | actions；V1c；是 | 不可变提交版本；preview_id、version、source_revision、snapshot json、content_hash、created_by | id；preview/revision/user | preview+version唯一、content_hash索引；preview | 是(建议冗余)/是/是/条件 | 否/否/否/是 | 长期、高；审批/执行核验；提交后绝对不可变 |
| `action_preview_item` | actions；V1c；是 | 逐项强结构动作；version_id、sequence、action_type、target_type/id、before/after json、currency、risk_level | id；version | version+sequence唯一；target_type+target_id、risk | 是(建议冗余)/是/是/条件 | 否/否/否/是 | 长期、高；前后值对比；支持动作待确认 |
| `action_approval_policy` | actions；V1c；是 | 审批策略容器；tenant_id可空、code、name、status | id；tenant可空 | scope+tenant+code唯一；status | 条件/否/否/否 | 是/否/归档/否 | 长期、低；选择策略；V1固定单级 |
| `action_approval_step` | actions；V1c；是 | 策略步骤；policy_id、step_no、required_permission、conditions json | id；policy | policy+step_no唯一；permission | 条件/否/否/否 | 是(未使用前)/否/归档/否 | 长期、低；构造审批；V1仅step_no=1 |
| `action_approval_record` | actions；V1c；是 | 审批事实；tenant/store/version、step、attempt、decision、approver、comment、decided_at | id；scope/version/step/user | version+step+attempt唯一；approver+decision+date、store+date | 是/是/是/条件 | 否/否/否/是 | 长期、高；审批历史；必须只追加 |
| `action_execution_task` | actions；V1c；是 | 人工执行任务当前态；tenant/store/version、status、assignee、created_at | id；scope/version/user | version+active_task候选唯一；assignee+status、store+status | 是/是/是/条件 | 仅Service/否/否/否 | 长期、中高；待执行列表；部分结果状态待确认 |
| `action_execution_item` | actions；V1c；是 | 从Preview复制的执行项；task_id、preview_item_id、sequence、expected_before/after、risk | id；task/preview_item | task+preview_item唯一；task+sequence | 是(建议冗余)/是/是/条件 | 否/否/否/是 | 长期、高；执行清单；与批准版本一一对应 |
| `action_execution_record` | actions；V1c；是 | 一次逐项回填；tenant/store/item、attempt、operator、actual_value json、result、executed_at、note | id；scope/item/user | item+attempt唯一；item+executed_at、operator+date | 是/是/是/条件 | 否/否/否/是 | 长期、高；执行证据；截图强制规则待确认 |
| `action_effect_evaluation` | actions；V1d；是 | 评估流程当前态；tenant/store/execution_task、status、observation_due、current_snapshot | id；scope/execution | execution+evaluation_round唯一；status+due_at | 是/是/是/条件 | 仅Service/否/否/否 | 长期、中高；到期评估；窗口待确认 |
| `action_effect_evaluation_snapshot` | actions；V1d；是 | 不可变评估结果；evaluation_id、version、baseline_window、observation_window、metrics_before/after、result、method_version、evidence | id；evaluation | evaluation+version唯一；result+created | 是(建议冗余)/是/是/条件 | 否/否/否/是 | 长期、中高；评估复现；基线/观察窗口待确认 |

## 10. knowledge_：偏好、策略与知识

| 表名 | 模块；阶段；立即 | 职责与核心字段/类型 | PK/FK | 唯一与索引 | T/S/M/P | 更新/删除/软删/追加 | 生命周期、增长、查询、关系、待确认 |
|---|---|---|---|---|---|---|---|
| `knowledge_user_preference_event` | knowledge；V1d；是 | 用户行为事件；tenant/store/user、event_type、object_ref、source_revision/action、payload、occurred_at | id；scope/user/source | 可选source+event_type幂等；user+occurred_at | 是/条件/否/条件 | 否/否/否/是 | 按策略、高；候选偏好；单次事件不直接生效 |
| `knowledge_user_preference` | knowledge；V1d；是 | 人工确认偏好当前态；tenant_id、user_id、key、value、confidence、status、confirmed_by | id；tenant/user | tenant+user+key有效唯一；user+status | 是/条件/否/否 | Service受控/否/归档/否 | 长期、中；Agent上下文；晋升阈值待确认 |
| `knowledge_team_strategy` | knowledge；V1d；是 | Team/Tenant策略容器；tenant_id、team_id可空、code、status,current_version | id；tenant/team | tenant+team+code唯一；tenant+status | 是/条件/否/否 | Service受控/否/归档/否 | 长期、低中；策略选择；必须人工审核 |
| `knowledge_team_strategy_version` | knowledge；V1d；是 | 不可变策略版本；strategy_id、version、content、approved_by、effective_at | id；strategy/user | strategy+version唯一；effective_at | 是(建议冗余)/条件/否/否 | 否/否/否/是 | 长期、中；追溯策略；生效流程待确认 |
| `knowledge_document` | knowledge；未来；否 | 知识文档容器；tenant/team、title、status,current_version | id；tenant/team | tenant+team+title候选唯一；status | 是/条件/否/否 | 是/否/归档/否 | 长期、中；文档列表；V1不做复杂知识库 |
| `knowledge_document_version` | knowledge；未来；否 | 文档版本；document_id、version、file_asset/content_ref、hash、author | id；document/file/user | document+version唯一；hash | 是(建议冗余)/条件/否/否 | 否/否/否/是 | 长期、中高；追溯/检索；正文存储策略待确认 |
| `knowledge_rule` | knowledge；V1d或未来；条件 | 人工确认规则容器；tenant/team、code、status,current_version | id；tenant/team | tenant+team+code唯一；status | 是/条件/否/否 | Service受控/否/归档/否 | 长期、低中；分析上下文；V1可仅预留 |
| `knowledge_rule_version` | knowledge；V1d或未来；条件 | 不可变规则版本；rule_id、version、conditions/actions json、approved_by、effective_at | id；rule/user | rule+version唯一；effective_at | 是(建议冗余)/条件/否/否 | 否/否/否/是 | 长期、中；规则追溯；不得由Agent自行发布 |

## 11. audit_与file_

| 表名 | 模块；阶段；立即 | 职责与核心字段/类型 | PK/FK | 唯一与索引 | T/S/M/P | 更新/删除/软删/追加 | 生命周期、增长、查询、关系、待确认 |
|---|---|---|---|---|---|---|---|
| `audit_log` | audit；V1a起；是 | AuditLog不可变业务审计；tenant/store、actor_user、action_code、object_type/id、object_version、before/after摘要、request_id、ip/user_agent、occurred_at | id；scope/user可空 | 可选request+sequence唯一；tenant+object+time、actor+time、request_id | 是/条件/条件/条件 | 否/否/否/是 | 按法规长期、极高；审计检索；保留期/敏感字段待确认 |
| `file_asset` | core/files；V1a；是 | 通用文件元数据；tenant_id、storage_provider/key、sha256、size、media_type、original_name、status | id；tenant | tenant+storage_key唯一；tenant+sha256、status | 是/否/否/否 | 仅生命周期Service/受控物理清理/否/否 | 按业务保留、高；下载/血缘；正文不在MySQL |
| `file_business_attachment` | core/files；V1c；是 | 文件与业务对象关系；tenant/store、file_asset、object_type/id、attachment_type、created_by | id；scope/file/user | file+object+type候选唯一；object_type+object_id | 是/条件/条件/条件 | 否/受保留策略/否/是 | 随业务记录、高；执行证据；高风险截图规则待确认 |

## 12. 关键建模结论

1. User不直接包含tenant_id，TenantMembership连接User和Tenant。
2. Team可选，个人卖家不创建占位Team。
3. Product是Tenant内部产品；MarketplaceCatalogItem是Marketplace下ASIN；ProductListing是Store/Marketplace下SKU。
4. Campaign产品关系优先由Ad到ProductListing表达。
5. SearchTerm不永久强制关联Keyword或Target；归因进入带时间、来源和粒度的事实记录。
6. 原始文件和原始行正文在文件/对象存储；MySQL保存清单、哈希和血缘。
7. AI原始建议不能被人工Revision覆盖。
8. RecommendationRevision、ActionPreviewVersion、ApprovalRecord、ExecutionRecord和AuditLog只追加。
9. AuditLog不允许普通删除或软删除。

## 13. 推荐索引与隔离原则

- 高频列表以`tenant_id + store_id + status + created_at`为主。
- 指标趋势以`tenant_id + store_id + 业务对象ID + business_date`为主。
- 外部实体以`tenant_id + profile_id + external_id`保持唯一。
- 审计以`tenant_id + object_type + object_id + occurred_at`和`request_id`检索。
- 所有索引需在获得脱敏样例和真实查询后通过执行计划验证，当前不设计分区。

## 14. 待确认造成的实现阻塞

- Store/Marketplace/Profile基数未确认：阻塞`ads_store`和下游外键最终约束。
- 首种报表/广告类型未确认且无样例：阻塞广告结构最小表集、Schema和事实粒度。
- 事实模型与重述规则未确认：阻塞`analytics_daily_metric_fact`唯一键和更新策略。
- SKU/ASIN关系未确认：阻塞Listing唯一约束。
- 保留期未确认：阻塞文件、RawRow、Agent输入输出和审计归档任务。
