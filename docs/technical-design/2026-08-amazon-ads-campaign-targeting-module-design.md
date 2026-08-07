# 广告活动—广告组—定向策略模块技术方案（基于项目实际架构修订）

> 版本：V1.2（已按远程数据库真实表结构核验修订）
> 日期：2026-08-06
> 适用项目：Amazon 广告智能优化系统 V1
> 目标模块：`backend/apps/advertising`、`backend/apps/analytics`、`frontend/src/features/advertising`
> 上游约束：`codex_master_goal_amazon_ads_v1.md`、`AGENTS.md`、`docs/15-decision-log.md`
> 数据库核验：已实际连接 `192.168.0.75` 的 `wecon_scm_20251228`（SCM）和 `wecon_analyze`（分析）库

---

## 0. 与原草案 V1.0 的主要差异

原草案（`c:\Users\admin\Downloads\广告活动与定向策略模块技术方案.md`）假设数据源为四张 BI 分析表、API 路径为 `/api/v1/ads/campaigns/{campaignId}/...`、URL 使用明文 `campaignId`。本仓库实际架构与此不同，本次修订对齐如下：

| 维度 | 原草案 V1.0 | 本仓库实际（数据库核验） | 本方案处理 |
|---|---|---|---|
| 数据源 | 四张 BI 分析表 | Campaign/广告组/定向策略**各**三表聚合（SCM 维表 + 历史事实表 + 实时事实表），共 9 张远程表 | 改为三层级三表聚合 |
| API 前缀 | `/api/v1/ads/campaigns/{campaignId}/...` | `/api/v1/advertising/tenants/{tenantId}/profiles/{profileId}/campaigns/{campaign_key}` | 对齐现有路由 |
| URL 参数 | 明文 `campaignId`、`adGroupId` | 签名编码 `campaign_key`（`cmp_` 前缀，`django.core.signing`） | 使用 `campaign_key` |
| 前端路由 | `/ads/campaigns/:campaignId` | `/advertising/campaigns/:campaignKey` | 对齐现有路由 |
| 权限 | 未提及 | `require_profile_scope` + `advertising.view` + `ProfileAccessLevel` | 必须校验 |
| 写操作 | 独立操作服务 | 远程数据库只读，启停写入受 D-180 阻塞，已通过 SCM 元数据写入但受约束 | 明确边界 |
| 自动投放 | 紧密/宽泛/同类/关联（4 种） | 实际 6 种 `targeting_match`：Close Match/Loose Match/Substitutes/Complements/Purchases/Views | 按 `targeting_match` 分行展示 |
| `targeting_type` | 未细分 | 实际值：`auto`/`manual-keyword`/`manual-PAT`/`manual-SD` | 按实际枚举 |
| 广告组关联键 | `adGroupId` | `group_id` 全为 NULL，用 `group_code`/`group_name` | 用 `group_code` |
| 建议竞价 | 未提及 | `current_bid`/`suggested_bid`/`suggested_bid_min`/`suggested_bid_max` 存在 | 展示建议竞价范围 |

---

## 1. 方案结论

本次开发在已完成的三表聚合 Campaign 列表与详情基础上，完成"广告活动 → 广告组"的真实下钻；随后实现广告组详情页，**该页面只做定向策略模块（不做广告商品 Tab、否定关键词 Tab 等其他内容）**，并在现有自动投放基础上扩展手动投放。Campaign、广告组、定向策略三个维度的数据**均由远程三表聚合只读提供**（SCM 维表 + 历史事实表 + 实时事实表）。竞价和启停不能直接写入分析表，需要独立操作服务，且受 D-180 决策阻塞约束。

## 2. 核心链路

```text
广告活动列表 → 广告活动详情 → 广告组列表 → 广告组详情 → 定向策略
```

对应现有实现：

- 广告活动列表：`CampaignSection.vue` + `CampaignListView` + `campaign_overview_page`（已完成）
- 广告活动详情：`CampaignDetailPage.vue` + `CampaignDetailView` + `campaign_detail_page`（已完成）
- 广告组列表/详情/定向策略：待实现

## 3. 数据源职责

### 3.1 Campaign 维度（远程三表聚合，只读）

| 数据角色 | Django DB Alias / 表 | 作用 | 是否可直接相加 |
|---|---|---|---|
| 当前活动维表 | `scm_remote.eb_ad_campaign` | 名称、状态、投放类型、起止日期、预算、竞价策略 | 否；每个 Campaign 取当前记录 |
| 历史事实表 | `ads_analysis_remote.bi_analyze_ad_campaign` | 已沉淀业务日的历史指标 | 只在完成原子粒度去重后参与聚合 |
| 实时事实表 | `ads_analysis_remote.bi_analyze_ad_campaign_realtime` | 当日/近期滚动更新指标与最新投放字段 | 不得与同原子粒度历史快照重复相加 |

连接键：事实 `campaign_code -> SCM.code`（`campaign_id` 相交为 0，不能作为主连接键）。

访问入口：`integrations/advertising_data/remote_databases.py::RemoteAdvertisingDataReader` → `remote_campaign_aggregates.py::RemoteCampaignAggregateReader`，经 `remote_scope_for_profile(profile)` 解析 `AdvertisingProfileRemoteScope` 得到 `(merchant_id, merchant_code)`。

#### 3.1.1 `eb_ad_campaign`（SCM 维表）字段

来源：`remote_campaign_aggregates.py:755-787` 的 `_scm_rows` 查询。

| 字段 | 类型 | 用途 |
|---|---|---|
| `id` | BIGINT | 主键 |
| `mer_id` | INT | 商户 ID（隔离键） |
| `mer_code` | VARCHAR | 商户编码（隔离键） |
| `campaign_id` | VARCHAR | Amazon Campaign ID（非主连接键） |
| `code` | VARCHAR | Campaign 业务编码（主连接键，对应事实表 `campaign_code`） |
| `name` | VARCHAR(255) | Campaign 名称 |
| `type` | VARCHAR | 投放类型（`auto`/`manual`） |
| `state` | VARCHAR | 状态（`enabled`/`paused`/`archived` 等） |
| `start_date` | DATE | 开始日期 |
| `end_date` | DATE | 结束日期 |
| `budget` | DECIMAL | 每日预算 |
| `bidding_strategy` | VARCHAR | 竞价策略（`up_and_down`/`down_only`/`fixed_bids`） |
| `create_by`/`create_name`/`create_time` | - | 创建审计 |
| `update_by`/`update_name`/`update_time` | - | 更新审计 |
| `status` | INT | 软删标记（`6` 表示已删除，查询过滤 `COALESCE(status,0) <> 6`） |

#### 3.1.2 `bi_analyze_ad_campaign`（历史事实表）字段

来源：`remote_campaign_aggregates.py:422-441` 的 `required_history` 集合。

| 字段 | 类型 | 用途 |
|---|---|---|
| `id` | BIGINT | 主键 |
| `mer_id`/`mer_code` | - | 商户隔离键 |
| `creation_date` | DATETIME | 业务日期（`DATE(creation_date)` 作为 `business_date`） |
| `campaign_code` | VARCHAR | Campaign 编码（主连接键） |
| `campaign_id` | VARCHAR | Amazon Campaign ID |
| `campaign_name` | VARCHAR | Campaign 名称 |
| `campaign_type` | VARCHAR | 投放类型 |
| `campaign_state` | VARCHAR | 状态 |
| `campaign_bidding_strategy` | VARCHAR | 竞价策略 |
| `campaign_daily_budget` | DECIMAL | 每日预算 |
| `campaign_create_date` | DATE | Campaign 创建日期 |
| `product_id`/`asin` | - | 产品维度（原子粒度组成部分） |
| `imperssion`/`impression` | INT | 展示量（字段名容错映射） |
| `click`/`clicks` | INT | 点击量（字段名容错映射） |
| `spend` | DECIMAL | 花费 |
| `orders` | INT | 订单数 |
| `sales` | DECIMAL | 销售额 |
| `top_of_search_is` | DECIMAL | 搜索结果首页份额 |
| `create_time` | DATETIME | 观察时间（去重排序键） |

#### 3.1.3 `bi_analyze_ad_campaign_realtime`（实时事实表）字段

来源：`remote_campaign_aggregates.py:442-449` 的 `required_realtime` 集合，在历史字段基础上增加：

| 字段 | 类型 | 用途 |
|---|---|---|
| `update_time` | DATETIME | 更新时间（去重排序键） |
| `type` | VARCHAR | 投放类型（`SP-Auto`/`SP-Manual`） |
| `campaign_targeting_type` | VARCHAR | Campaign 投放类型（优先于 `campaign_type`） |
| `serving_status` | VARCHAR | 投放状态（优先于 `campaign_state`） |
| `daily_budget` | DECIMAL | 每日预算（优先于 `campaign_daily_budget`） |
| `bidding_strategy` | VARCHAR | 竞价策略（优先于 `campaign_bidding_strategy`） |

#### 3.1.4 三表聚合 SQL 模板

核心 CTE 见 `remote_campaign_aggregates.py:569-647` 的 `_fact_cte`，逻辑：

1. `historical_ranked`：历史表按 `(business_date, campaign_key, product_key, asin_key)` 分区，`ROW_NUMBER()` 按 `create_time DESC` 选最新；
2. `realtime_ranked`：实时表同上，按 `update_time DESC` 选最新；
3. `normalized_facts`：两表 `table_row_number = 1` 的记录 `UNION ALL`；
4. `source_ranked`：按 `(business_date, campaign_key, product_key, asin_key)` 再分区，`source_priority`（实时=2 > 历史=1）优先，选 `source_row_number = 1`；
5. `campaign_totals`：按 `campaign_key` 聚合 `SUM(impressions/clicks/spend/orders/sales)`；
6. `latest_metadata`：取每个 `campaign_key` 最新业务日的元数据；
7. 最终 `INNER JOIN` SCM 维表补充名称/状态/预算，`LEFT JOIN` 历史首页份额。

去重版本：`campaign-code-product-asin-realtime-v1`。

### 3.2 广告组维度（远程三表聚合，只读）

**数据库核验结论（2026-08-06）：** 远程分析库 `wecon_analyze` 实际存在 `bi_analyze_ad_group`（43 列, 246,370 行）和 `bi_analyze_ad_group_realtime`（38 列, 1,903,719 行）；SCM 库存在 `eb_ad_group`（20 列, 55,071 行）。

| 数据角色 | Django DB Alias / 表 | 作用 | 行数 |
|---|---|---|---|
| 广告组维表 | `scm_remote.eb_ad_group` | 广告组当前元数据（名称、状态、默认竞价、类型） | 55,071 |
| 广告组历史事实表 | `ads_analysis_remote.bi_analyze_ad_group` | 已沉淀业务日的广告组历史指标 | 246,370 |
| 广告组实时事实表 | `ads_analysis_remote.bi_analyze_ad_group_realtime` | 当日/近期滚动更新的广告组指标 | 1,903,719 |

连接键：`campaign_code` 关联回 Campaign，`group_code`（历史表）/`group_name`（实时表）关联广告组。**`group_id` 在所有分析表中全为 NULL**，不能作为连接键。

#### 3.2.1 `eb_ad_group`（SCM 维表）字段

| 字段 | 类型 | 用途 |
|---|---|---|
| `id` | INT UNSIGNED | 主键 |
| `mer_id` | INT | 商户隔离键 |
| `campaign_id` | BIGINT | Amazon Campaign ID |
| `campaign_code` | VARCHAR(255) | Campaign 编码（连接键） |
| `ad_group_id` | BIGINT | Amazon AdGroup ID |
| `type` | ENUM('keyword','product','auto') | 广告组类型 |
| `name` | VARCHAR(255) | 广告组名称 |
| `bid` | DECIMAL(10,2) | 默认竞价 |
| `state` | ENUM('paused','enabled') | 状态 |
| `status` | VARCHAR(255) | 软删标记 |
| `create_time`/`update_time` | DATETIME | 审计时间 |

#### 3.2.2 `bi_analyze_ad_group`（历史事实表）关键字段

| 字段 | 类型 | 用途 |
|---|---|---|
| `campaign_code` | VARCHAR(255) | Campaign 连接键 |
| `group_id` | BIGINT | 广告组 ID（**实际全为 NULL**） |
| `group_state` | VARCHAR(45) | 广告组状态 |
| `bid` | DECIMAL(11,5) | 默认竞价 |
| `targeting_type` | VARCHAR(45) | 定向类型（如 `manual-keyword`） |
| `imperssion`/`click`/`spend`/`orders`/`sales` | - | 原始指标 |
| `ctr`/`cpc`/`cvr`/`acos`/`roas` | DECIMAL(11,5) | 预计算指标 |
| `creation_date` | DATETIME | 业务日期 |
| `create_time` | DATETIME | 观察时间（去重排序键） |

#### 3.2.3 `bi_analyze_ad_group_realtime`（实时事实表）额外字段

| 字段 | 类型 | 用途 |
|---|---|---|
| `group_name` | VARCHAR(100) | 广告组名称（注意：历史表无此字段，用 `code`/`name`） |
| `profile_name` | VARCHAR(100) | Profile 名称 |
| `serving_status` | VARCHAR(45) | 投放状态 |
| `add_to_cart` | VARCHAR(45) | 加购 |
| `update_time` | DATETIME | 更新时间（去重排序键） |

### 3.3 定向策略维度（远程三表聚合，只读）

**数据库核验结论（2026-08-06）：** 远程分析库实际存在 `bi_analyze_ad_targeting`（50 列, 1,012,586 行）和 `bi_analyze_ad_targeting_realtime`（46 列, 392,208 行）；SCM 库存在 `eb_ad_targeting`（21 列）。**V1.1 文档错误地声称定向策略使用本地 `TargetingDailyMetric`，实际应使用远程三表聚合。**

| 数据角色 | Django DB Alias / 表 | 作用 | 行数 |
|---|---|---|---|
| 定向维表 | `scm_remote.eb_ad_targeting` | 定向当前元数据（竞价、状态） | - |
| 定向历史事实表 | `ads_analysis_remote.bi_analyze_ad_targeting` | 已沉淀业务日的定向目标历史指标 | 1,012,586 |
| 定向实时事实表 | `ads_analysis_remote.bi_analyze_ad_targeting_realtime` | 当日/近期滚动更新的定向指标 | 392,208 |

连接键：`campaign_code` 关联回 Campaign，`group_code`（历史）/`group_name`（实时）关联广告组，`targeting` 关联定向表达式。

#### 3.3.1 `bi_analyze_ad_targeting` 关键字段

| 字段 | 类型 | 实际值/用途 |
|---|---|---|
| `campaign_code` | VARCHAR(255) | Campaign 连接键（19,606 个不同值） |
| `group_id` | BIGINT | 广告组 ID（**实际全为 NULL**） |
| `group_code` | VARCHAR(100) | 广告组编码（3,328 个不同值，**实际关联键**） |
| `group_state` | VARCHAR(45) | 广告组状态 |
| `targeting` | VARCHAR(512) | 定向表达式，如 `Asin="B08T877M36"`、`Close Match` |
| `targeting_state` | VARCHAR(45) | 定向状态（`enabled` 等） |
| `targeting_type` | VARCHAR(45) | **实际值：`manual-PAT`/`manual-keyword`/`auto`/`manual-SD`** |
| `targeting_match` | VARCHAR(45) | **见下方实际值枚举** |
| `current_bid` | DECIMAL(11,5) | 当前竞价 |
| `suggented_bid` | DECIMAL(11,5) | 建议竞价（注意源表拼写错误） |
| `suggented_bid_min` | DECIMAL(11,5) | 建议竞价下限 |
| `suggested_bid_max` | DECIMAL(11,5) | 建议竞价上限 |
| `imperssion`/`click`/`spend`/`orders`/`sales` | - | 原始指标 |
| `ctr`/`cpc`/`cvr`/`acos`/`roas` | DECIMAL(11,5) | 预计算指标 |
| `top_of_search_is` | DECIMAL(11,5) | 搜索结果首页份额 |
| `creation_date` | DATETIME | 业务日期 |
| `create_time` | DATETIME | 观察时间（去重排序键） |

#### 3.3.2 `bi_analyze_ad_targeting_realtime` 额外字段

| 字段 | 类型 | 用途 |
|---|---|---|
| `group_name` | VARCHAR(100) | 广告组名称（历史表用 `group_code`） |
| `targeting_status` | VARCHAR(45) | 定向投放状态（如 `Campaign out of budget`） |
| `suggested_bid` | DECIMAL(11,5) | 建议竞价（拼写正确） |
| `suggested_bid_min`/`suggested_bid_max` | DECIMAL(11,5) | 建议竞价范围 |
| `add_to_cart` | VARCHAR(45) | 加购 |
| `other_sales`/`other_sales_percent` | DECIMAL(11,5) | 其他销售 |
| `update_time` | DATETIME | 更新时间（去重排序键） |

#### 3.3.3 `targeting_type` 实际枚举（数据库核验）

| 值 | 含义 | 对应投放方式 |
|---|---|---|
| `auto` | 自动投放 | Campaign `targeting_type=AUTO` |
| `manual-keyword` | 手动关键词 | Campaign `targeting_type=MANUAL`，Keyword |
| `manual-PAT` | 手动商品目标 (Product Attribute Targeting) | Campaign `targeting_type=MANUAL`，ProductTarget |
| `manual-SD` | Sponsored Display 手动 | V1 不完整实现，仅展示 |

#### 3.3.4 `targeting_match` 实际枚举（数据库核验）

| 分类 | `targeting_match` 值 | 说明 |
|---|---|---|
| 关键词匹配 | `broad`/`BROAD`、`phrase`/`PHRASE`、`exact`/`EXACT` | 大小写并存 |
| 商品目标 | `Product`、`Category`、`Product-Expanded` | ASIN/类目定向 |
| 自动投放匹配 | `Close Match`、`Loose Match`、`Substitutes`、`Complements`、`Purchases`、`Views` | Amazon 自动匹配方式 |
| Sponsored Display | - | `manual-SD` 类型 |

**重要：** 自动投放实际细分 6 种匹配方式（`Close Match`/`Loose Match`/`Substitutes`/`Complements`/`Purchases`/`Views`），V1.1 文档说"不细分"是错误的。

### 3.4 本地事实表（补充/回填，非主数据源）

本地 `TargetingDailyMetric`（`analytics_targeting_daily_metric`）和 `AdGroup`/`Keyword`/`ProductTarget` 模型仍然存在，但**不是定向策略展示的主数据源**。它们的职责：

- `TargetingDailyMetric`：用户手动上传 Targeting Report 后的本地归档，用于离线分析和重述版本管理。
- `AdGroup`/`Keyword`/`ProductTarget`：用户上传报表导入的实体归档。
- 远程三表聚合是定向策略页面的**主数据源**，与 Campaign 列表一致。

**前置条件已满足：** 远程 `bi_analyze_ad_targeting` 和 `bi_analyze_ad_targeting_realtime` 表已存在且有数据；`group_code` 可作为广告组关联键（`group_id` 全为 NULL 不可用）。

### 3.5 SCM 维表写操作用途（默认竞价、商品、定向实体）

**数据库核验结论（2026-08-06）：** SCM 库的 `eb_ad_group`、`eb_ad_targeting`、`eb_ad_negative_targeting`、`eb_ad_product` 四张维表承担**当前元数据读取和写操作落库**职责，与远程分析库的只读事实表配合使用。

#### 3.5.1 `eb_ad_group`（广告组维表，55,071 行）

| 字段 | 类型 | 实际值/用途 |
|---|---|---|
| `campaign_code` | VARCHAR(255) | Campaign 连接键 |
| `ad_group_id` | BIGINT | Amazon AdGroup ID |
| `type` | ENUM('keyword','product','auto') | 广告组类型（**决定默认竞价和定向方式**） |
| `name` | VARCHAR(255) | 广告组名称 |
| `bid` | DECIMAL(10,2) | **默认竞价**（页面展示和修改） |
| `state` | ENUM('paused','enabled') | 启停状态 |
| `status` | VARCHAR(255) | 软删标记（`3`=有效） |

**用途：**
- 广告组列表/详情页展示**默认竞价**（`bid` 字段）和状态（`state`）
- 修改默认竞价 → `UPDATE eb_ad_group SET bid=%s, update_time=NOW() WHERE ...`
- 启停广告组 → `UPDATE eb_ad_group SET state=%s, update_time=NOW() WHERE ...`
- 新建广告组 → `INSERT INTO eb_ad_group (mer_id, campaign_code, ad_group_id, type, name, bid, state, ...)`

#### 3.5.2 `eb_ad_targeting`（定向维表，406,210 行）

| 字段 | 类型 | 实际值/用途 |
|---|---|---|
| `campaign_code` | VARCHAR(255) | Campaign 连接键 |
| `group_id` | BIGINT | 广告组 ID（SCM 库有值，与分析库不同） |
| `type` | VARCHAR(45) | **实际值：`manual`/`auto`/`keyword`/`product`** |
| `target_id` | VARCHAR(45) | Amazon Target ID |
| `targeting` | VARCHAR(255) | 定向表达式（关键词文本或 `Asin="B08T877M36"`） |
| `match` | VARCHAR(255) | **匹配类型，实际值：`phrase`/`exact`/`broad`/`Close Match`/`Loose Match`/`Substitutes`/`Complements`/`Product`/`Category`/`Product-Expanded`** |
| `bid` | DECIMAL(10,2) | **关键词/目标竞价**（页面展示和修改） |
| `state` | VARCHAR(255) | **实际值：`enabled`/`paused`** |
| `status` | VARCHAR(255) | 软删标记 |

**用途：**
- 定向策略页面展示每个关键词/商品目标的**当前竞价**（`bid`）和状态（`state`）
- 修改关键词竞价 → `UPDATE eb_ad_targeting SET bid=%s, update_time=NOW() WHERE campaign_code=%s AND target_id=%s`
- 启停关键词/目标 → `UPDATE eb_ad_targeting SET state=%s, update_time=NOW() WHERE ...`
- 添加关键词 → `INSERT INTO eb_ad_targeting (mer_id, campaign_code, group_id, type, target_id, targeting, match, bid, state, ...)`
- 添加商品目标 → 同上，`type='product'`，`targeting='Asin="xxx"'`

#### 3.5.3 `eb_ad_negative_targeting`（否定定向维表，1,384,050 行）

| 字段 | 类型 | 实际值/用途 |
|---|---|---|
| `type` | ENUM('campaign','adgroup') | **否定级别：Campaign 级或 AdGroup 级** |
| `targeting` | VARCHAR(255) | 否定表达式（如 `gold charm neckalce`） |
| `match` | VARCHAR(255) | 匹配类型（如 `Negative Exact`） |
| `state` | VARCHAR(190) | 状态 |
| `target_id` | BIGINT | Amazon Target ID |

**用途：** 添加/删除 Negative Keyword，区分 Campaign 级和 AdGroup 级。

#### 3.5.4 `eb_ad_product`（广告商品维表，72,713 行）

| 字段 | 类型 | 用途 |
|---|---|---|
| `asin` | VARCHAR(45) | ASIN |
| `win` | VARCHAR(45) | WIN |
| `fnsku` | VARCHAR(64) | FNSKU |
| `sku_id` | BIGINT | SKU ID |
| `state` | VARCHAR(45) | 状态 |
| `adid` | VARCHAR(45) | 广告 ID |

**用途：** `eb_ad` 表存储广告商品（Ad）数据，含 ASIN、SKU、状态。本次广告组详情页只做定向策略，不展示广告商品列表，此表供后续扩展使用。

#### 3.5.5 SCM 表与分析表的配合关系

```text
页面展示数据流：
  SCM 维表（eb_ad_group/eb_ad_targeting）  →  当前竞价、状态、默认竞价（可写）
  分析事实表（bi_analyze_ad_group/targeting）  →  历史指标、趋势（只读）
  合并展示  →  竞价 + 状态 + 指标

写操作数据流：
  页面修改竞价/启停  →  Service  →  UPDATE SCM 维表  →  审计日志
  （分析事实表永远只读，不通过 UPDATE 模拟状态变化）
```

## 4. 自动与手动投放

**数据库核验结论（2026-08-06）：** 远程 `bi_analyze_ad_targeting.targeting_type` 实际值为 `auto`/`manual-keyword`/`manual-PAT`/`manual-SD`；`targeting_match` 实际值覆盖关键词、商品目标和自动投放 6 种匹配方式。

- **Campaign 级别投放类型**：`Campaign.targeting_type`（通过 `_normalized_targeting_type` 归一化为 `AUTO`/`MANUAL`/`UNKNOWN`），来源于远程 SCM 维表 `eb_ad_campaign.type` enum('auto','manual')。
- **自动投放**（`targeting_type = "auto"`）：Amazon 自动匹配，实际细分 6 种 `targeting_match`：
  - `Close Match`（紧密匹配）
  - `Loose Match`（宽泛匹配）
  - `Substitutes`（同类商品）
  - `Complements`（关联商品）
  - `Purchases`（购买）
  - `Views`（浏览）
  定向策略页面按 `targeting_match` 分行展示每种匹配方式的指标。
- **手动关键词**（`targeting_type = "manual-keyword"`）：`targeting_match` 为 `broad`/`BROAD`、`phrase`/`PHRASE`、`exact`/`EXACT`（大小写并存，展示时归一化）。`targeting` 字段存储关键词文本。
- **手动商品目标**（`targeting_type = "manual-PAT"`）：`targeting_match` 为 `Product`/`Category`/`Product-Expanded`。`targeting` 字段存储表达式如 `Asin="B08T877M36"`。
- **Sponsored Display**（`targeting_type = "manual-SD"`）：V1 不完整实现，仅只读展示。
- **建议竞价**：`current_bid`（当前竞价）、`suggested_bid`/`suggented_bid`（建议竞价）、`suggested_bid_min`/`suggented_bid_min`、`suggested_bid_max`（建议范围），用于竞价建议展示。
- **Negative Keyword**：支持 Campaign 级和 AdGroup 级（V1 主规格已确认），SCM 库 `eb_ad_negative_targeting` 表已存在。
- **本地模型**：`Keyword`/`ProductTarget`/`AdGroup` 模型仍保留，用于上传报表归档；`TargetingDailyMetric.target_type` 为 `KEYWORD`/`PRODUCT_TARGET`（本地枚举与远程 `targeting_type` 不同，需映射）。

## 5. 统一指标

由 `apps.analytics.services.metric_formulas` 确定性计算，已实现：

- `CTR = clicks / impressions`
- `CPC = spend / clicks`
- `CVR = orders / clicks`
- `ACOS = spend / sales`
- `ROAS = sales / spend`

无有效分母时返回 `null` 并保存原因（`NO_SALES`、`NO_SPEND`、`NO_CLICKS`），不返回 0 或无穷大。聚合时使用 `SUM` 后再计算比率：

- `CTR = SUM(clicks) / SUM(impressions)`
- `CPC = SUM(spend) / SUM(clicks)`
- `CVR = SUM(orders) / SUM(clicks)`
- `ACOS = SUM(spend) / SUM(sales)`
- `ROAS = SUM(sales) / SUM(spend)`

禁止对每日百分比直接求和或简单平均。不同 Marketplace 或不同 currency 的金额指标不直接相加。

## 6. 权限与隔离

所有接口必须通过 `apps.permissions.services.require_profile_scope` 校验：

1. 已认证用户。
2. 有效 `TenantMembership`（`tenant_id` 路径参数）。
3. 功能权限 `advertising.view`（定向策略展示）或 `advertising.operate`（竞价/启停，受 D-180 阻塞）。
4. `ProfileAccessLevel.VIEW`（只读）或 `OPERATE`（写操作）。
5. Store/Profile 数据范围：`profile_id` 路径参数必须属于当前 Tenant。
6. 跨 Tenant 或完全不在数据范围中的对象返回 404；当前 Tenant 内对象存在但缺少操作权限时返回 403。

远程数据范围通过 `remote_scope_for_profile(profile)` 解析为 `(merchant_id, merchant_code)`，确保不同 Profile 映射到不同远程商户，禁止串租户。

## 7. 页面路由

### 7.1 现有路由（已完成）

- `/advertising` → `AdvertisingOverviewPage`（含 `CampaignSection`）
- `/advertising/overview` → `AdvertisingOverviewPage`
- `/advertising/create` → `AdvertisingCreatePage`
- `/advertising/campaigns/:campaignKey` → `CampaignDetailPage`

### 7.2 待新增路由

- `/advertising/campaigns/:campaignKey/ad-groups` → 广告组列表页
- `/advertising/campaigns/:campaignKey/ad-groups/:adGroupKey` → 广告组详情页（即定向策略页，无多 Tab）

URL 使用签名编码的 `campaign_key`（`cmp_` 前缀）和 `ad_group_key`（待定义，建议 `grp_` 前缀）；`sessionStorage` 只能做缓存，不能作为权威来源。路由守卫仅控制体验，后端校验不可替代。

## 8. 核心 API

统一响应格式：

```json
{
  "code": "SUCCESS",
  "message": "操作成功",
  "data": {},
  "requestId": "req_xxx"
}
```

金额字段统一为 `{ "amount": "100.00", "currency_code": "USD" }`，ID 使用字符串，比率使用字符串。

### 8.1 现有 API（已完成）

#### 8.1.1 Campaign 列表

`GET /api/v1/advertising/tenants/{tenantId}/profiles/{profileId}/campaigns` → `CampaignListView`

请求参数（`CampaignListQuerySerializer`，`serializers.py:41`）：

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `startDate` | DATE | 与 endDate 同进同出 | 开始日期 |
| `endDate` | DATE | 与 startDate 同进同出 | 结束日期（范围 ≤ 90 天） |
| `enabled` | BOOL | 否 | `true`/`false` 筛选 |
| `status` | STRING | 否 | 逗号分隔，可选 `enabled/paused/archived/applying/nothing/refuse/ended/unknown` |
| `targetingType` | ENUM | 否 | `AUTO`/`MANUAL` |
| `search` | STRING | 否 | 名称搜索（≤ 100 字符） |
| `metricFilters` | STRING | 否 | 分号分隔，格式 `field:operator:value[:value2]`，最多 9 条 |
| `ordering` | ENUM | 否 | 默认 `-spend`，支持 `±name/±spend/±clicks/±ctr/±acos` 等 |
| `page` | INT | 否 | 默认 1 |
| `pageSize` | INT | 否 | 默认 15，最大 100 |
| `includeSummary` | BOOL | 否 | 默认 true |

`metricFilters` 支持字段：`impressions/clicks/spend/orders/cpc/acos/ctr/cvr`；支持操作符：`gte/lte/eq/between`。

响应（`CampaignOverviewResponseSerializer`，`serializers.py:323`）：

```json
{
  "items": [
    {
      "campaign_key": "cmp_xxx",
      "name": "Campaign A",
      "reference_code": "CODX-US-xxx",
      "enabled": true,
      "targeting_type": "MANUAL",
      "status": "DELIVERING",
      "bidding_strategy": "UP_AND_DOWN",
      "start_date": "2026-07-01",
      "end_date": null,
      "daily_budget": { "amount": "50.00", "currency_code": "USD" },
      "metrics": {
        "impressions": 12000,
        "top_of_search_share": "0.32",
        "spend": { "amount": "120.50", "currency_code": "USD" },
        "sales": { "amount": "480.00", "currency_code": "USD" },
        "clicks": 300,
        "ctr": "0.025",
        "total_cost": { "amount": "120.50", "currency_code": "USD" },
        "orders": 12,
        "cpc": { "amount": "0.40", "currency_code": "USD" },
        "acos": "0.2510",
        "cvr": "0.04"
      },
      "metadata_matched": true,
      "has_metrics": true,
      "partial_fields": []
    }
  ],
  "summary": { /* 同 metrics 结构 */ },
  "dashboard": {
    "trend": [{ "date": "2026-08-01", "metrics": { /* ... */ } }],
    "risk_levels": [{ "level": "HIGH", "count": 3 }],
    "evaluated_campaigns": 42,
    "target_acos": "0.30",
    "unavailable_rule_codes": ["BUDGET_EARLY_EXHAUSTION"],
    "risk_semantics": "SYSTEM_RULES_AGGREGATED"
  },
  "pagination": { "page": 1, "page_size": 15, "total": 42, "total_pages": 3 },
  "meta": {
    "source": "REMOTE_MYSQL_COMPOSITE",
    "currency_code": "USD",
    "timezone": "America/Los_Angeles",
    "start_date": "2026-07-01",
    "end_date": "2026-08-01",
    "data_through_date": "2026-08-01",
    "history_through_date": "2026-08-01",
    "realtime_through_date": "2026-08-06",
    "realtime_as_of": "2026-08-06T10:00:00Z",
    "deduplication_version": "campaign-code-product-asin-realtime-v1",
    "field_mappings": { "historicalImpressions": "imperssion" },
    "total_cost_semantics": "SPEND_ALIAS",
    "attribution_semantics": "REMOTE_FIELDS_UNVERIFIED",
    "status_filter_semantics": "SCM_CURRENT_STATE_WITH_FACT_FALLBACK"
  }
}
```

#### 8.1.2 Campaign 详情

`GET /api/v1/advertising/tenants/{tenantId}/profiles/{profileId}/campaigns/{campaign_key}` → `CampaignDetailView`

请求参数（`CampaignDetailQuerySerializer`）：`startDate`/`endDate`（同进同出，≤ 90 天）。

响应（`CampaignDetailResponseSerializer`）：`{ item, trend, meta }`，`item` 同列表项，`trend` 为每日指标数组。

#### 8.1.3 Campaign 启停

`PATCH /api/v1/advertising/tenants/{tenantId}/profiles/{profileId}/campaigns/{campaign_key}/enabled` → `CampaignEnabledUpdateView`

请求体：`{ "enabled": true, "start_date": "2026-07-01", "end_date": "2026-08-01" }`

响应：`{ item }`（同列表项）。受 D-180 阻塞，未授权前不伪造成功。

#### 8.1.4 Campaign 导出

`GET /api/v1/advertising/tenants/{tenantId}/profiles/{profileId}/campaigns/export` → `CampaignExportView`

响应：`text/csv`（UTF-8 BOM），超过 10,000 行返回 422。

#### 8.1.5 Targeting 实体列表

`GET /api/v1/advertising/tenants/{tenantId}/profiles/{profileId}/targeting` → `TargetingListView`

响应（`TargetingRowSerializer`，`serializers.py:356`）：

```json
[
  {
    "id": "1",
    "target_type": "KEYWORD",
    "external_target_id": "kw-xxx",
    "target_text": "wireless earbuds",
    "match_type": "BROAD",
    "state": "ENABLED",
    "bid": "0.75",
    "campaign_id": "10",
    "campaign_name": "Campaign A",
    "ad_group_id": "20",
    "ad_group_name": "AdGroup 1",
    "source_batch_id": "5"
  }
]
```

### 8.2 待新增 API

#### 8.2.1 广告组列表

`GET /api/v1/advertising/tenants/{tenantId}/profiles/{profileId}/campaigns/{campaign_key}/ad-groups`

请求参数：`startDate`/`endDate`/`page`/`pageSize`/`ordering`。

响应：

```json
{
  "items": [
    {
      "ad_group_key": "grp_xxx",
      "name": "AdGroup 1",
      "state": "ENABLED",
      "default_bid": { "amount": "0.75", "currency_code": "USD" },
      "metrics": { /* 同 CampaignOverviewMetricsSerializer */ },
      "has_metrics": true
    }
  ],
  "pagination": { /* 同上 */ },
  "meta": { "source": "REMOTE_MYSQL_COMPOSITE", "currency_code": "USD" }
}
```

数据来源：远程三表聚合 `eb_ad_group` + `bi_analyze_ad_group` + `bi_analyze_ad_group_realtime`，按 `campaign_code` 筛选，按 `group_code`/`group_name` 聚合（`SUM(impressions/clicks/spend/orders/sales)`）。`group_id` 全为 NULL 不可用。

#### 8.2.2 广告组详情

`GET /api/v1/advertising/tenants/{tenantId}/profiles/{profileId}/campaigns/{campaign_key}/ad-groups/{ad_group_key}`

响应：`{ item, trend, meta }`，`item` 同列表项，`trend` 为每日指标。

#### 8.2.3 定向策略指标

`GET /api/v1/advertising/tenants/{tenantId}/profiles/{profileId}/campaigns/{campaign_key}/ad-groups/{ad_group_key}/targeting/metrics`

请求参数：`startDate`/`endDate`/`targetType`（`KEYWORD`/`PRODUCT_TARGET`）/`page`/`pageSize`。

响应（参照 `analytics/selectors.py:340` 的 `targeting_metric_rows`）：

```json
[
  {
    "id": "100",
    "campaign_id": "10",
    "campaign_name": "Campaign A",
    "ad_group_id": "20",
    "ad_group_name": "AdGroup 1",
    "target_type": "KEYWORD",
    "target_id": "kw-xxx",
    "target_text": "wireless earbuds",
    "match_type": "BROAD",
    "report_date": "2026-08-01",
    "currency_code": "USD",
    "impressions": 5000,
    "clicks": 120,
    "spend": "48.00",
    "orders": 6,
    "sales": "240.00",
    "calculation_reasons": {},
    "bid_snapshot": "0.75",
    "state_snapshot": "ENABLED",
    "ctr": { "value": "0.024", "reason": null },
    "cpc": { "value": "0.40", "reason": null },
    "cvr": { "value": "0.05", "reason": null },
    "acos": { "value": "0.20", "reason": null },
    "roas": { "value": "5.00", "reason": null },
    "source_batch_id": "5"
  }
]
```

#### 8.2.4 定向策略趋势

`GET /api/v1/advertising/tenants/{tenantId}/profiles/{profileId}/campaigns/{campaign_key}/ad-groups/{ad_group_key}/targeting/trend`

响应：`[{ "date": "2026-08-01", "metrics": { /* 同上 */ } }]`。

#### 8.2.5 定向目标实体

`GET /api/v1/advertising/tenants/{tenantId}/profiles/{profileId}/campaigns/{campaign_key}/ad-groups/{ad_group_key}/targets`

响应：`Keyword` 和 `ProductTarget` 实体列表，含 `bid`/`state`/`match_type`/`expression`。

## 8A. 页面功能与交互实现

### 8A.1 广告活动列表页（已实现，`CampaignSection.vue`）

参照现有 `CampaignSection.vue`（1,884 行）的交互模式，作为广告组和定向策略页面的实现基准。

| 功能 | 实现方式 | 涉及 API/表 |
|---|---|---|
| 创建广告活动 | 弹窗表单（名称/投放类型/预算/竞价策略/起止日期/启用开关）→ `createCampaign` | `POST .../campaigns` → `eb_ad_campaign` INSERT |
| 启停开关 | 乐观更新 + `toggleCampaignEnabled` → `updateCampaignEnabled` | `PATCH .../campaigns/{key}/enabled` → `eb_ad_campaign` UPDATE |
| 搜索 | `v-model="search"` → 重新请求 | `GET .../campaigns?search=` |
| 状态筛选 | 模态框下拉（进行中/已暂停/已归档等） | `GET .../campaigns?status=enabled,paused` |
| 指标筛选 | 模态框（9 种指标 × 4 种操作符，最多 9 条） | `GET .../campaigns?metricFilters=spend:gte:100;acos:between:0.1:0.3` |
| 日期选择 | 预设（7/14/30 天）+ 自定义日期范围 | `GET .../campaigns?startDate=&endDate=` |
| 排序 | 点击列头 `setOrdering` | `GET .../campaigns?ordering=-spend` |
| 导出 CSV | `exportCampaigns` → Blob 下载 | `GET .../campaigns/export` |
| 行选择 | `toggleRowSelection`/`toggleVisibleSelection` | 前端状态 |
| 名称链接 | `RouterLink` → `advertising-campaign-detail` | 路由跳转 |
| 分页 | 页码切换 | `GET .../campaigns?page=&pageSize=` |
| 状态展示 | 加载骨架屏/空数据/错误重试/无权限 | - |

### 8A.2 广告活动详情页（已实现，`CampaignDetailPage.vue`）

展示单个 Campaign 的概览信息和每日趋势图（ECharts），含日期范围选择和返回列表。

### 8A.3 广告组列表页（待实现）

#### 读取数据（具体 SQL）

**数据库：** `scm_remote`（SCM 库 `wecon_scm_20251228`）+ `ads_analysis_remote`（分析库 `wecon_analyze`）

**读取广告组当前元数据（SCM 库 `eb_ad_group`）：**

```sql
-- 库：scm_remote (wecon_scm_20251228)
-- 表：eb_ad_group
SELECT
    ad_group_id, campaign_code, type, name, bid, state
FROM eb_ad_group
WHERE mer_id = %s
  AND campaign_code = %s
  AND COALESCE(status, '0') <> '6'
ORDER BY update_time DESC, id DESC;
```

**读取广告组历史指标（分析库 `bi_analyze_ad_group`）：**

```sql
-- 库：ads_analysis_remote (wecon_analyze)
-- 表：bi_analyze_ad_group
SELECT
    campaign_code, group_state, bid, targeting_type,
    SUM(imperssion) AS impressions, SUM(click) AS clicks,
    SUM(spend) AS spend, SUM(orders) AS orders, SUM(sales) AS sales
FROM bi_analyze_ad_group
WHERE mer_id = %s AND mer_code = %s
  AND creation_date >= %s AND creation_date < %s
  AND campaign_code = %s
GROUP BY campaign_code, group_state, bid, targeting_type;
```

**读取广告组实时指标（分析库 `bi_analyze_ad_group_realtime`）：**

```sql
-- 库：ads_analysis_remote (wecon_analyze)
-- 表：bi_analyze_ad_group_realtime
SELECT
    campaign_code, group_name, group_state, serving_status,
    SUM(impression) AS impressions, SUM(click) AS clicks,
    SUM(spend) AS spend, SUM(orders) AS orders, SUM(sales) AS sales
FROM bi_analyze_ad_group_realtime
WHERE mer_id = %s AND mer_code = %s
  AND creation_date >= %s AND creation_date < %s
  AND campaign_code = %s
GROUP BY campaign_code, group_name, group_state, serving_status;
```

**合并逻辑：** SCM `eb_ad_group` 提供名称/状态/默认竞价/类型，分析库提供指标，按 `campaign_code` 关联。

#### 页面功能

| 功能 | 交互方式 | 读取/写入 |
|---|---|---|
| 广告组列表 | 表格（名称/状态/默认竞价/投放类型/指标） | 读：`scm_remote.eb_ad_group` + `ads_analysis_remote.bi_analyze_ad_group` + `_realtime` |
| 投放类型显示 | **直接显示 `eb_ad_group.type` 原始值**（`keyword`/`auto`/`product`） | 读：`scm_remote.eb_ad_group.type` |
| 状态显示 | **直接显示 `eb_ad_group.state` 原始值**（`enabled`/`paused`） | 读：`scm_remote.eb_ad_group.state` |
| 修改默认竞价 | 行内编辑 → 提交 | 写：`scm_remote.eb_ad_group.bid` |
| 启停广告组 | 开关按钮 | 写：`scm_remote.eb_ad_group.state` |
| 名称链接 | 跳转广告组详情（定向策略页） | 路由跳转 |

### 8A.4 广告组详情页 = 定向策略页（待实现）

**广告组详情页只做定向策略，不做其他 Tab。** 页面直接展示该广告组下所有定向目标（关键词/商品目标/自动投放匹配方式），可修改竞价、启停、添加。

#### 读取数据（具体 SQL）

**读取定向目标当前元数据（SCM 库 `eb_ad_targeting`）：**

```sql
-- 库：scm_remote (wecon_scm_20251228)
-- 表：eb_ad_targeting
SELECT
    id, campaign_code, group_id, type, target_id,
    targeting, match, bid, state
FROM eb_ad_targeting
WHERE mer_id = %s
  AND campaign_code = %s
  AND COALESCE(status, '0') <> '6'
ORDER BY update_time DESC, id DESC;
```

**读取定向目标历史指标（分析库 `bi_analyze_ad_targeting`）：**

```sql
-- 库：ads_analysis_remote (wecon_analyze)
-- 表：bi_analyze_ad_targeting
SELECT
    campaign_code, group_code, targeting, targeting_type, targeting_match,
    targeting_state, current_bid,
    suggented_bid, suggented_bid_min, suggested_bid_max,
    SUM(imperssion) AS impressions, SUM(click) AS clicks,
    SUM(spend) AS spend, SUM(orders) AS orders, SUM(sales) AS sales
FROM bi_analyze_ad_targeting
WHERE mer_id = %s AND mer_code = %s
  AND creation_date >= %s AND creation_date < %s
  AND campaign_code = %s
GROUP BY campaign_code, group_code, targeting, targeting_type, targeting_match,
         targeting_state, current_bid, suggented_bid, suggented_bid_min, suggested_bid_max;
```

**读取定向目标实时指标（分析库 `bi_analyze_ad_targeting_realtime`）：**

```sql
-- 库：ads_analysis_remote (wecon_analyze)
-- 表：bi_analyze_ad_targeting_realtime
SELECT
    campaign_code, group_name, targeting, targeting_type, targeting_match,
    targeting_state, targeting_status, current_bid,
    suggested_bid, suggested_bid_min, suggested_bid_max,
    SUM(impression) AS impressions, SUM(click) AS clicks,
    SUM(spend) AS spend, SUM(orders) AS orders, SUM(sales) AS sales
FROM bi_analyze_ad_targeting_realtime
WHERE mer_id = %s AND mer_code = %s
  AND creation_date >= %s AND creation_date < %s
  AND campaign_code = %s
GROUP BY campaign_code, group_name, targeting, targeting_type, targeting_match,
         targeting_state, targeting_status, current_bid,
         suggested_bid, suggested_bid_min, suggested_bid_max;
```

**合并逻辑：**
- SCM `eb_ad_targeting` 提供当前竞价（`bid`）、状态（`state`）、匹配类型（`match`）、定向表达式（`targeting`）
- 分析库 `bi_analyze_ad_targeting` + `_realtime` 提供历史指标和建议竞价范围
- 按 `campaign_code` + `targeting`（定向表达式）关联

#### 列表展示

| 列 | 数据来源（库.表.字段） | 说明 |
|---|---|---|
| 启用开关 | `scm_remote.eb_ad_targeting.state` | `enabled`/`paused`，直接显示 |
| 投放类型 | `scm_remote.eb_ad_targeting.type` | **直接显示原始值**：`manual`/`auto`/`keyword`/`product` |
| 定向表达式 | `scm_remote.eb_ad_targeting.targeting` | 关键词文本或 `Asin="B08T877M36"` 或 `Close Match` |
| 匹配类型 | `scm_remote.eb_ad_targeting.match` | **直接显示原始值**：`phrase`/`exact`/`broad`/`Product`/`Category`/`Close Match` 等 |
| 当前竞价 | `scm_remote.eb_ad_targeting.bid` | 可修改，`DECIMAL(10,2)` |
| 建议竞价 | `ads_analysis_remote.bi_analyze_ad_targeting.suggented_bid` | 只读，历史表字段名有拼写错误 |
| 建议竞价范围 | `suggented_bid_min` ~ `suggested_bid_max`（历史）/ `suggested_bid_min` ~ `suggested_bid_max`（实时） | 只读展示 |
| 状态 | `scm_remote.eb_ad_targeting.state` | **直接显示原始值**：`enabled`/`paused` |
| 展示量 | `ads_analysis_remote.bi_analyze_ad_targeting.imperssion` | SUM 聚合 |
| 花费 | `.spend` | SUM 聚合 |
| 点击 | `.click` | SUM 聚合 |
| CTR | 计算 `SUM(click)/SUM(imperssion)` | 后端 `metric_formulas` |
| ACoS | 计算 `SUM(spend)/SUM(sales)` | 后端 `metric_formulas` |
| ROAS | 计算 `SUM(sales)/SUM(spend)` | 后端 `metric_formulas` |

#### 操作功能与写库 SQL

##### 修改竞价

**交互：** 点击竞价单元格 → 行内编辑输入新值 → 校验 → 提交

**写入数据库（SCM 库 `eb_ad_targeting`）：**

```sql
-- 库：scm_remote (wecon_scm_20251228)
-- 表：eb_ad_targeting
-- 字段：bid
UPDATE eb_ad_targeting
SET bid = %s,
    update_by = %s,
    update_name = %s,
    update_time = NOW()
WHERE mer_id = %s
  AND campaign_code = %s
  AND target_id = %s
  AND COALESCE(status, '0') <> '6';
```

**API：** `PATCH /api/v1/advertising/tenants/{tenantId}/profiles/{profileId}/campaigns/{campaign_key}/ad-groups/{ad_group_key}/targets/{target_key}/bid`

**请求体：** `{ "bid": "0.85" }`

**校验：** 新竞价 > 0，精度 2 位小数；若建议竞价范围存在则提示，超出范围警告但允许提交。

##### 启停目标

**交互：** 点击启用开关 → 乐观更新 → 提交

**写入数据库（SCM 库 `eb_ad_targeting`）：**

```sql
-- 库：scm_remote (wecon_scm_20251228)
-- 表：eb_ad_targeting
-- 字段：state
UPDATE eb_ad_targeting
SET state = %s,  -- 'enabled' 或 'paused'
    update_by = %s,
    update_name = %s,
    update_time = NOW()
WHERE mer_id = %s
  AND campaign_code = %s
  AND target_id = %s
  AND COALESCE(status, '0') <> '6';
```

**API：** `PATCH .../targets/{target_key}/enabled`，请求体 `{ "enabled": true }`

##### 添加关键词

**交互：** 点击"添加关键词"按钮 → 弹窗（关键词文本/匹配类型/竞价）→ 提交

**写入数据库（SCM 库 `eb_ad_targeting`）：**

```sql
-- 库：scm_remote (wecon_scm_20251228)
-- 表：eb_ad_targeting
INSERT INTO eb_ad_targeting (
    mer_id, campaign_id, campaign_code, group_id,
    type, target_id, targeting, match, bid, state,
    create_by, create_name, create_time, update_by, update_name, update_time, status
) VALUES (
    %s,  -- mer_id（商户 ID，从 remote_scope 获取）
    %s,  -- campaign_id
    %s,  -- campaign_code
    %s,  -- group_id
    'keyword',  -- type
    %s,  -- target_id（Amazon Keyword ID）
    %s,  -- targeting（关键词文本，如 "wireless earbuds"）
    %s,  -- match（匹配类型：'phrase'/'exact'/'broad'）
    %s,  -- bid（竞价）
    'enabled',  -- state
    %s,  -- create_by（用户 ID）
    %s,  -- create_name（用户名）
    NOW(),  -- create_time
    %s,  -- update_by
    %s,  -- update_name
    NOW(),  -- update_time
    '0'  -- status（有效）
);
```

**API：** `POST .../targets`，请求体：

```json
{
  "type": "keyword",
  "targeting": "wireless earbuds",
  "match": "phrase",
  "bid": "0.85"
}
```

##### 添加商品目标

**交互：** 点击"添加商品目标"按钮 → 弹窗（ASIN/Category 表达式/竞价）→ 提交

**写入数据库（SCM 库 `eb_ad_targeting`）：**

```sql
-- 库：scm_remote (wecon_scm_20251228)
-- 表：eb_ad_targeting
INSERT INTO eb_ad_targeting (
    mer_id, campaign_id, campaign_code, group_id,
    type, target_id, targeting, match, bid, state,
    create_by, create_name, create_time, update_by, update_name, update_time, status
) VALUES (
    %s, %s, %s, %s,
    'product',  -- type
    %s,  -- target_id（Amazon Target ID）
    %s,  -- targeting（表达式，如 'Asin="B08T877M36"'）
    %s,  -- match（'Product'/'Category'）
    %s,  -- bid
    'enabled',
    %s, %s, NOW(), %s, %s, NOW(), '0'
);
```

**API：** `POST .../targets`，请求体：

```json
{
  "type": "product",
  "targeting": "Asin=\"B08T877M36\"",
  "match": "Product",
  "bid": "1.20"
}
```

##### 批量修改竞价

**交互：** 勾选多行 → 点击"批量修改竞价" → 输入新竞价 → 提交

**写入数据库（SCM 库 `eb_ad_targeting`，事务）：**

```sql
-- 库：scm_remote (wecon_scm_20251228)
-- 表：eb_ad_targeting
-- 对每个选中的 target_id 执行
UPDATE eb_ad_targeting
SET bid = %s, update_by = %s, update_name = %s, update_time = NOW()
WHERE mer_id = %s AND campaign_code = %s AND target_id = %s
  AND COALESCE(status, '0') <> '6';
```

**API：** `PATCH .../targets/batch-bid`，请求体 `{ "targetKeys": ["t1","t2"], "bid": "0.80" }`

##### 批量启停

**交互：** 勾选多行 → 点击"批量启用/暂停"

**写入数据库（SCM 库 `eb_ad_targeting`，事务）：**

```sql
UPDATE eb_ad_targeting
SET state = %s, update_by = %s, update_name = %s, update_time = NOW()
WHERE mer_id = %s AND campaign_code = %s AND target_id IN (%s, %s, ...)
  AND COALESCE(status, '0') <> '6';
```

**API：** `PATCH .../targets/batch-enabled`，请求体 `{ "targetKeys": ["t1","t2"], "enabled": true }`

#### 筛选功能

| 筛选 | 交互 | SQL 条件 |
|---|---|---|
| 按投放类型 | 下拉（全部/manual/auto/keyword/product） | `WHERE type = %s`（SCM `eb_ad_targeting.type`） |
| 按匹配类型 | 下拉（全部/phrase/exact/broad/Product/Category/Close Match/...） | `WHERE match = %s`（SCM `eb_ad_targeting.match`） |
| 按状态 | 下拉（全部/enabled/paused） | `WHERE state = %s`（SCM `eb_ad_targeting.state`） |
| 按表达式搜索 | 文本框 | `WHERE targeting LIKE %s`（SCM `eb_ad_targeting.targeting`） |

#### 自动投放显示

自动投放广告组（`eb_ad_group.type = 'auto'`）的定向目标 `eb_ad_targeting.match` 为 6 种匹配方式，**直接按数据库原始值分行展示**：

| `eb_ad_targeting.match` 值 | 页面显示 | 可操作 |
|---|---|---|
| `Close Match` | Close Match | 可修改竞价、启停 |
| `Loose Match` | Loose Match | 可修改竞价、启停 |
| `Substitutes` | Substitutes | 可修改竞价、启停 |
| `Complements` | Complements | 可修改竞价、启停 |
| `Purchases` | Purchases | 可修改竞价、启停 |
| `Views` | Views | 可修改竞价、启停 |

**不归一化、不翻译，直接显示数据库原始值。**

#### 手动投放显示

手动投放广告组（`eb_ad_group.type = 'keyword'` 或 `'product'`）的定向目标：

| `eb_ad_targeting.type` | `eb_ad_targeting.match` | 页面显示 |
|---|---|---|
| `keyword` | `phrase`/`exact`/`broad` | 关键词行，显示 `targeting` 文本 + `match` 值 |
| `product` | `Product`/`Category`/`Product-Expanded` | 商品目标行，显示 `targeting` 表达式 + `match` 值 |

**直接显示数据库原始值，不归一化大小写。**

#### 竞价修改校验规则

1. 新竞价必须 > 0，精度 2 位小数（`DECIMAL(10,2)`）。
2. 若 `suggented_bid_min`/`suggested_bid_max` 存在，提示建议范围；超出范围时警告但允许提交。
3. 校验 `ProfileAccessLevel.OPERATE` 权限。
4. 校验对象归属（Tenant/Profile/Campaign/AdGroup）。
5. 记录审计日志（`before`/`after` 竞价值），写入 `default` 库 `audit_log` 表。
6. 受 D-180 阻塞时，前端开关和编辑框置灰，提示"写操作未授权"。

### 8A.5 前端组件结构（待实现）

```text
frontend/src/features/advertising/
├── components/
│   ├── CampaignSection.vue          # 已实现
│   ├── AdGroupSection.vue           # 待实现：广告组列表
│   ├── TargetingSection.vue         # 待实现：定向策略（广告组详情页核心）
│   ├── TargetingEditDialog.vue      # 待实现：添加关键词/商品目标弹窗
│   ├── BidEditDialog.vue            # 待实现：修改竞价弹窗
│   └── RemotePerformanceChart.vue   # 已实现
├── pages/
│   ├── AdvertisingOverviewPage.vue  # 已实现
│   ├── CampaignDetailPage.vue       # 已实现
│   ├── AdGroupListPage.vue          # 待实现
│   └── AdGroupDetailPage.vue        # 待实现（= 定向策略页）
├── api/
│   ├── campaignApi.ts               # 已实现
│   ├── adGroupApi.ts                # 待实现
│   └── targetingApi.ts              # 待实现
└── types/
    ├── campaign.ts                  # 已实现
    ├── adGroup.ts                   # 待实现
    └── targeting.ts                 # 待实现
```

## 9. 写操作边界

### 9.1 当前约束

- 远程数据库（`scm_remote`、`ads_analysis_remote`）对分析表只读，不得通过 `UPDATE` 模拟广告状态变化。
- V1 不真实调用 Amazon Ads API、不直接修改 Amazon 后台广告。
- 启停写入受 D-180 决策阻塞，当前 `update_campaign_enabled_state` 通过 SCM 元数据表写入并记录审计日志，但未获得受控写 Provider 授权前不得用前端内存或本地覆盖伪造成功。
- 竞价和启停不能直接写入 `bi_analyze_ad_campaign` 或 `bi_analyze_ad_campaign_realtime` 分析表。

### 9.2 操作服务设计

竞价/启停操作必须通过独立 Service，不得在 Selector 或 View 中直接写远程表。**写操作落库到 SCM 维表，分析事实表永远只读。**

#### 已实现

- `apps.advertising.services.update_campaign_enabled_state` → `UPDATE eb_ad_campaign SET state=%s`
- `apps.advertising.services.create_remote_campaign` → `INSERT INTO eb_ad_campaign`

#### 待实现 — 广告组操作（落库 `eb_ad_group`）

- `update_ad_group_bid` → `UPDATE eb_ad_group SET bid=%s, update_time=NOW() WHERE mer_id=%s AND campaign_code=%s AND ad_group_id=%s`
- `update_ad_group_enabled_state` → `UPDATE eb_ad_group SET state=%s, update_time=NOW() WHERE ...`
- `create_ad_group` → `INSERT INTO eb_ad_group (mer_id, campaign_code, ad_group_id, type, name, bid, state, create_by, create_name, create_time, status)`

#### 待实现 — 定向操作（落库 `eb_ad_targeting`）

- `update_target_bid` → `UPDATE eb_ad_targeting SET bid=%s, update_time=NOW() WHERE mer_id=%s AND campaign_code=%s AND target_id=%s`
- `update_target_enabled_state` → `UPDATE eb_ad_targeting SET state=%s, update_time=NOW() WHERE ...`
- `create_keyword_target` → `INSERT INTO eb_ad_targeting (mer_id, campaign_code, group_id, type='keyword', target_id, targeting=%s, match=%s, bid=%s, state='enabled', ...)`
- `create_product_target` → `INSERT INTO eb_ad_targeting (mer_id, campaign_code, group_id, type='product', target_id, targeting='Asin="xxx"', bid=%s, state='enabled', ...)`
- `batch_update_target_bid` → 批量 `UPDATE eb_ad_targeting`（事务）
- `batch_update_target_enabled_state` → 批量 `UPDATE eb_ad_targeting`（事务）

#### 待实现 — 对应 API

| API | 方法 | Service | 写入库.表.字段 |
|---|---|---|---|
| `.../ad-groups/{key}/bid` | PATCH | `update_ad_group_bid` | `scm_remote.eb_ad_group.bid` |
| `.../ad-groups/{key}/enabled` | PATCH | `update_ad_group_enabled_state` | `scm_remote.eb_ad_group.state` |
| `.../ad-groups` | POST | `create_ad_group` | `scm_remote.eb_ad_group` INSERT |
| `.../targets/{key}/bid` | PATCH | `update_target_bid` | `scm_remote.eb_ad_targeting.bid` |
| `.../targets/{key}/enabled` | PATCH | `update_target_enabled_state` | `scm_remote.eb_ad_targeting.state` |
| `.../targets` | POST | `create_keyword_target`/`create_product_target` | `scm_remote.eb_ad_targeting` INSERT |
| `.../targets/batch-bid` | PATCH | `batch_update_target_bid` | `scm_remote.eb_ad_targeting.bid` 批量 |
| `.../targets/batch-enabled` | PATCH | `batch_update_target_enabled_state` | `scm_remote.eb_ad_targeting.state` 批量 |

所有写操作必须：
1. 校验 `ProfileAccessLevel.OPERATE`。
2. 校验对象归属（Tenant/Profile/Campaign/AdGroup）。
3. 校验当前对象状态、修改前值、金额上下限（竞价 > 0，精度 2 位小数）。
4. 通过 SCM 维表写入（`scm_remote.eb_ad_group`/`scm_remote.eb_ad_targeting`），**分析事实表（`ads_analysis_remote`）永远只读**。
5. 记录 `AuditLog`（只追加，脱敏 before/after），写入 `default.audit_log`。
6. 不物理删除 Campaign、AdGroup、Keyword、Target，用暂停或软删（`status='6'`）替代。
7. 受 D-180 阻塞时返回 403 或特定错误码，前端置灰。

## 10. 现有实现状态

### 10.1 已完成

- `backend/apps/advertising/models.py`：`Campaign`、`AdGroup`、`Ad`、`Keyword`、`ProductTarget`、`SearchTerm` 模型，含 `MatchType`、`EntityState`、`AdProductType` 枚举。
- `backend/apps/analytics/models.py`：`CampaignDailyMetric`、`TargetingDailyMetric`（含 `ad_group` 外键）、`SearchTermDailyMetric` 事实表，含快照、重述版本、异常规则。
- `backend/apps/advertising/views.py`：`CampaignListView`、`CampaignDetailView`、`CampaignEnabledUpdateView`、`CampaignExportView`、`TargetingListView`、`SearchTermListView`。
- `backend/apps/advertising/selectors.py`：`campaign_overview_page`、`campaign_detail_page`、`update_campaign_enabled_state`、`create_remote_campaign`、`campaign_rows`、`targeting_rows`、`search_term_rows`。
- `backend/integrations/advertising_data/remote_databases.py`：`RemoteAdvertisingDataReader`、`remote_scope_for_profile`，三表聚合读取。
- `frontend/src/features/advertising/components/CampaignSection.vue`：广告活动列表组件。
- `frontend/src/features/advertising/pages/CampaignDetailPage.vue`：广告活动详情页（未提交）。
- `frontend/src/features/advertising/api/campaignApi.ts`：前端 API 模块。

### 10.2 待实现

- 广告组列表 API、Selector、Serializer、View、前端页面。
- 广告组详情 API、Selector、Serializer、View、前端页面。
- 定向策略 metrics/trend/targets API、Selector、Serializer、View。
- 定向策略前端组件（广告组详情页核心内容）。
- `ad_group_key` 签名编码/解码工具（参照 `_campaign_key`/`_raw_campaign_key`）。
- Keyword/ProductTarget 竞价/启停操作 Service（受 D-180 阻塞）。

## 11. 必须确认

**已由数据库核验确认（2026-08-06）：**

1. ~~远程 `bi_analyze_ad_campaign` / `bi_analyze_ad_campaign_realtime` 是否包含 `ad_group_id` / `ad_group_name` 维度~~ → **已确认：Campaign 表不含广告组维度；但远程库存在独立的 `bi_analyze_ad_group` / `bi_analyze_ad_group_realtime` / `eb_ad_group` 表，广告组列表从这三表聚合。**
2. ~~本地 `TargetingDailyMetric` 是否已有足够数据~~ → **已确认：定向策略主数据源是远程 `bi_analyze_ad_targeting` + `bi_analyze_ad_targeting_realtime` + `eb_ad_targeting`，非本地表。**
3. ~~定向策略 tab 是否需要区分 AUTO/MANUAL 展示~~ → **已确认：`targeting_type` 实际值为 `auto`/`manual-keyword`/`manual-PAT`/`manual-SD`；自动投放细分 6 种 `targeting_match`（Close Match/Loose Match/Substitutes/Complements/Purchases/Views），需分行展示。**
4. ~~`group_id` 是否可用~~ → **已确认：`group_id` 在所有分析表中全为 NULL，必须用 `group_code`（历史）/`group_name`（实时）作为广告组关联键。**
5. ~~建议竞价是否存在~~ → **已确认：`current_bid`/`suggested_bid`/`suggested_bid_min`/`suggested_bid_max` 字段存在且有数据。**

**仍需确认：**

6. `ad_group_key` 签名编码方案（建议 `grp_` 前缀，salt 含 `campaign_key`，参照 `_campaign_key` 实现）。
7. 竞价/启停操作服务是否解除 D-180 阻塞；未解除前前端开关置灰并提示。
8. `targeting` 字段（如 `Asin="B08T877M36"`）是否需要结构化解析以区分 ASIN/Category/Brand，或直接字符串展示。
9. `targeting_match` 大小写并存（`broad`/`BROAD`）的归一化策略。
10. SCM `eb_ad_targeting` 表的完整字段结构（21 列，本次核验输出被截断，需补充查询）。
11. 远程表去重策略：`bi_analyze_ad_targeting` 和 `bi_analyze_ad_targeting_realtime` 是否存在同 Campaign+group+targeting+date 的重复快照，需参照 Campaign 三表的 `ROW_NUMBER()` 去重方案。

## 12. 验收标准

1. 广告活动列表 → 广告活动详情 → 广告组列表 → 广告组详情 → 定向策略链路可真实走通。
2. 所有接口校验 Tenant/Profile 隔离，跨租户访问返回 404。
3. 指标计算使用 `metric_formulas`，零分母返回 null 和原因。
4. 不同 Marketplace 或 currency 不直接相加。
5. 远程分析表只读，不通过 `UPDATE` 伪造状态变化。
6. 竞价/启停操作受 D-180 约束，未授权前不伪造成功。
7. 审计日志只追加，记录脱敏 before/after。
8. 前端页面处理加载、空数据、部分失败、完全失败、无权限状态。
9. OpenAPI 契约同步 TypeScript 类型。
10. 相关测试覆盖权限隔离、指标计算、状态转换、幂等性。

## 13. 后续扩展

- 解除 D-180 阻塞后，启用真实竞价/启停写操作。
- 接入真实 Amazon Ads API（V1 之外）。
- 扩展 Sponsored Brands、Sponsored Display 广告类型。
- 扩展 `ProductTarget.expression` 结构化解析（ASIN/Category/Brand）。
- 跨 Marketplace 汇总需先明确汇率来源、汇率日期、原币金额、目标币种。