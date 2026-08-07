# 广告组详情页技术方案（定向策略 Tab）

> 版本：V2.0
> 日期：2026-08-07
> 适用项目：Amazon 广告智能优化系统 V1
> 目标页面：广告组详情页 — 定向策略 Tab（`ad-group-detail.html` 中 `tab-targeting`）
> 目标模块：`backend/apps/advertising`、`backend/apps/analytics`、`frontend/src/features/advertising`
> 上游约束：`codex_master_goal_amazon_ads_v1.md`、`AGENTS.md`、`docs/15-decision-log.md`、`2026-08-amazon-ads-campaign-targeting-module-design.md`
> 参考页面：`C:/Users/admin/Desktop/广告智能投放系统/广告智能投放系统/ad-group-detail.html`
> 实现范围：仅定向策略 Tab（广告/否定投放/搜索词/广告组设置/历史记录 Tab 不在本方案范围）
> 数据库核验：已实际连接 `192.168.0.75` 的 `wecon_scm_20251228`（SCM）和 `wecon_analyze`（分析）库

---

## 0. 方案定位

本方案覆盖**广告组详情页的定向策略 Tab**，即广告组下钻后的定向目标管理界面。与既有方案 `2026-08-amazon-ads-campaign-targeting-module-design.md` 的关系：既有方案定义了定向策略 API 与数据源，本方案补全页面交互细节（KPI 卡片、趋势图、定向策略表格、竞价编辑、批量操作）。

页面其他 Tab（广告、否定投放、搜索词、广告组设置、历史记录）不在本方案范围。

---

## 1. 方案结论

定向策略 Tab 是广告组详情页的核心 Tab，展示该广告组下所有定向目标（关键词/商品目标/自动投放匹配方式）的列表管理界面。页面结构：顶部广告组摘要栏 + KPI 卡片组 + 趋势图表 + 工具栏 + 定向策略表格（含合计行）。

数据原则：
- 广告组摘要与 KPI/趋势：远程三表聚合只读（`eb_ad_group` + `bi_analyze_ad_group` + `bi_analyze_ad_group_realtime`）。
- 定向策略：远程三表聚合只读（`eb_ad_targeting` + `bi_analyze_ad_targeting` + `bi_analyze_ad_targeting_realtime`），SCM 维表提供当前竞价/状态（可写）。

写操作原则：定向竞价/启停落库 SCM 维表 `eb_ad_targeting`，分析事实表永远只读，受 D-180 决策阻塞约束。

---

## 2. 核心链路

```text
广告活动详情（/advertising/campaigns/:campaignKey?tab=adgroups）
  → 广告组详情（/advertising/campaigns/:campaignKey/ad-groups/:adGroupKey?tab=targeting）
      └─ 定向策略 Tab：定向目标列表
```

---

## 3. 页面路由

- `/advertising/campaigns/:campaignKey/ad-groups/:adGroupKey` → `AdGroupDetailPage.vue`
- Tab 通过 URL query `?tab=targeting` 同步，默认选中。
- URL 使用签名编码的 `campaign_key`（`cmp_` 前缀）和 `ad_group_key`（`grp_` 前缀，`django.core.signing`）。

---

## 4. 页面结构（参照 ad-group-detail.html `tab-targeting`）

### 4.1 顶部广告组摘要栏

```text
┌──────────────────────────────────────────────────────────────┐
│ [h1] 广告组: 广告组名称        [开关] [状态徽标]             │
│                              [提供反馈] [← 返回广告活动]     │
└──────────────────────────────────────────────────────────────┘
```

| 元素 | 数据字段 | 来源 |
|---|---|---|
| 标题 | `name` | `eb_ad_group.name` |
| 状态开关 | `enabled` | `eb_ad_group.state` ∈ {enabled, paused} |
| 状态徽标 | `status` | enabled→正在投放(绿)、paused→已暂停(灰) |
| 提供反馈 | 静态链接 | 指向反馈表单 |
| 返回广告活动 | RouterLink | 跳转回 `/advertising/campaigns/:campaignKey` |

### 4.2 KPI 卡片组

4 个卡片，每个含下拉菜单可切换指标：

| 卡片 | 默认指标 | 颜色 | 形状 |
|---|---|---|---|
| 1 | `purchases`（购买量） | circle | - |
| 2 | `sales`（销售额） | diamond | - |
| 3 | `clicks`（点击量） | square | - |
| 4 | `total_cost`（总成本） | triangle | - |

KPI 数值来自广告组维度三表聚合（该广告组在日期范围内的汇总指标）。

### 4.3 趋势图表

- 类型：SVG 折线图，双 Y 轴 + 右二轴
- 4 系列：购买量/销售额/点击量/总成本
- 数据：广告组每日指标趋势
- 交互：鼠标悬停 tooltip

### 4.4 工具栏

| 元素 | 功能 |
|---|---|
| 筛选按钮 | 弹出筛选侧边栏 |
| 批量操作按钮 | 批量启停/竞价 |
| 视图下拉 | 默认/紧凑/展开 |
| 列设置 | 显示/隐藏列 |
| 日期范围 | 日期筛选 |
| 导出链接 | 导出 CSV/XLSX |

### 4.5 定向策略表格

**表头（15 列）：**

| 列 | 字段 | 类型 | 说明 |
|---|---|---|---|
| 复选框 | - | checkbox | 全选/行选 |
| 进行中 | `enabled` | switch | 启停开关，受 D-180 |
| 自动投放组 | `targeting_group` | text | 主名称 + 子名称（如"紧密匹配/近似匹配"） |
| 投放匹配类型 | `targeting_match` | text | Close Match/Loose Match/broad/phrase/exact/Product/Category 等 |
| 状态 | `targeting_state` | badge | 进行中/已暂停 |
| 建议竞价 | `suggested_bid` | text | 推荐值 + 区间（min-max） |
| 竞价 | `bid` | input+应用 | 可编辑，含"0 条规则已生效"提示 |
| 展示量 | `metrics.impressions` | number | - |
| 首页首位展示量 | `metrics.top_of_search_share` | percent | 如 <5% |
| 点击量 | `metrics.clicks` | number | - |
| 总成本 | `metrics.total_cost` | currency | - |
| CPC | `metrics.cpc` | currency | - |
| 购买量 | `metrics.orders` | number | - |
| 销售额 | `metrics.sales` | currency | - |
| ROAS | `metrics.roas` | ratio | - |

**合计行：** 各指标列汇总，"总计: N"。

**数据行示例（4 行，自动投放）：**

| 自动投放组 | 投放匹配类型 | 状态 | 建议竞价 | 竞价 |
|---|---|---|---|---|
| 紧密匹配 | Close Match | 进行中 | US$1.00-1.50 | 1.40 |
| 宽泛匹配 | Loose Match | 已暂停 | US$0.73 | 0.75 |
| 关联商品 | Complements | 已暂停 | US$1.14 | 0.75 |
| 同类商品 | Substitutes | 已暂停 | US$1.14 | 0.75 |

---

## 5. `targeting_type` 与 `targeting_match` 枚举

### 5.1 `targeting_type`（数据库核验）

| 值 | 含义 | 对应投放方式 |
|---|---|---|
| `auto` | 自动投放 | Campaign `targeting_type=AUTO` |
| `manual-keyword` | 手动关键词 | Campaign `targeting_type=MANUAL`，Keyword |
| `manual-PAT` | 手动商品目标 (Product Attribute Targeting) | Campaign `targeting_type=MANUAL`，ProductTarget |
| `manual-SD` | Sponsored Display 手动 | V1 不完整实现，仅展示 |

### 5.2 `targeting_match`（数据库核验）

| 分类 | `targeting_match` 值 | 说明 |
|---|---|---|
| 关键词匹配 | `broad`/`BROAD`、`phrase`/`PHRASE`、`exact`/`EXACT` | 大小写并存 |
| 商品目标 | `Product`、`Category`、`Product-Expanded` | ASIN/类目定向 |
| 自动投放匹配 | `Close Match`、`Loose Match`、`Substitutes`、`Complements`、`Purchases`、`Views` | Amazon 自动匹配方式 |
| Sponsored Display | - | `manual-SD` 类型 |

**重要：** 自动投放实际细分 6 种匹配方式，页面按 `targeting_match` 分行展示每种匹配方式的指标。直接显示数据库原始值，不归一化大小写。

---

## 6. 数据源

### 6.1 广告组维度（顶部摘要 + KPI + 趋势）

| 数据角色 | Django DB Alias / 表 | 作用 |
|---|---|---|
| 广告组维表 | `scm_remote.eb_ad_group` | 广告组当前元数据 |
| 广告组历史事实表 | `ads_analysis_remote.bi_analyze_ad_group` | 已沉淀业务日的历史指标 |
| 广告组实时事实表 | `ads_analysis_remote.bi_analyze_ad_group_realtime` | 当日/近期滚动更新指标 |

连接键：`campaign_code` + `group_code`（历史）/`group_name`（实时）。`group_id` 全为 NULL 不可用。

### 6.2 定向策略维度（表格，本方案核心）

| 数据角色 | Django DB Alias / 表 | 作用 | 行数 |
|---|---|---|---|
| 定向维表 | `scm_remote.eb_ad_targeting` | 定向当前元数据（竞价、状态） | 406,210 |
| 定向历史事实表 | `ads_analysis_remote.bi_analyze_ad_targeting` | 已沉淀业务日的定向目标历史指标 | 1,012,586 |
| 定向实时事实表 | `ads_analysis_remote.bi_analyze_ad_targeting_realtime` | 当日/近期滚动更新的定向指标 | 392,208 |

连接键：`campaign_code` + `group_code`（历史）/`group_name`（实时）+ `targeting`。

**读取定向目标当前元数据（SCM 库 `eb_ad_targeting`）：**

```sql
SELECT targeting, match, bid, state
FROM eb_ad_targeting
WHERE mer_id = %s
  AND campaign_code = %s
  AND group_id = %s
  AND COALESCE(status, '0') <> '6';
```

**读取定向目标历史指标（分析库 `bi_analyze_ad_targeting`）：**

```sql
SELECT campaign_code, group_code, targeting, targeting_type, targeting_match,
       targeting_state, current_bid,
       suggented_bid, suggented_bid_min, suggested_bid_max,
       SUM(imperssion) AS impressions, SUM(click) AS clicks,
       SUM(spend) AS spend, SUM(orders) AS orders, SUM(sales) AS sales
FROM bi_analyze_ad_targeting
WHERE mer_id = %s AND campaign_code = %s AND group_code = %s
  AND DATE(creation_date) BETWEEN %s AND %s
GROUP BY campaign_code, group_code, targeting, targeting_type, targeting_match,
         targeting_state, current_bid, suggented_bid, suggented_bid_min, suggested_bid_max;
```

**读取定向目标实时指标（分析库 `bi_analyze_ad_targeting_realtime`）：**

```sql
SELECT campaign_code, group_name, targeting, targeting_type, targeting_match,
       targeting_state, targeting_status, current_bid,
       suggested_bid, suggested_bid_min, suggested_bid_max,
       SUM(imperssion) AS impressions, SUM(click) AS clicks,
       SUM(spend) AS spend, SUM(orders) AS orders, SUM(sales) AS sales
FROM bi_analyze_ad_targeting_realtime
WHERE mer_id = %s AND campaign_code = %s AND group_name = %s
  AND DATE(creation_date) BETWEEN %s AND %s
GROUP BY campaign_code, group_name, targeting, targeting_type, targeting_match,
         targeting_state, targeting_status, current_bid,
         suggested_bid, suggested_bid_min, suggested_bid_max;
```

页面数据流：
- SCM `eb_ad_targeting` 提供当前竞价（`bid`）、状态（`state`）、匹配类型（`match`）、定向表达式（`targeting`）
- 分析事实表提供历史/实时指标、建议竞价范围
- 两表按 `targeting` 表达式关联

---

## 7. 核心 API

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

### 7.1 已有 API（复用）

| API | 方法 | 说明 |
|---|---|---|
| `.../ad-groups/{ad_group_key}` | GET | 广告组详情（含 item + trend + meta） |
| `.../ad-groups/{ad_group_key}/enabled` | PATCH | 广告组启停 |

### 7.2 定向策略指标

`GET .../ad-groups/{ad_group_key}/targeting/metrics` → `TargetingMetricsView`

请求参数：

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `startDate` | DATE | 与 endDate 同进同出 | 开始日期 |
| `endDate` | DATE | 与 startDate 同进同出 | 结束日期（范围 ≤ 90 天） |
| `targetingType` | STRING | 否 | 筛选：auto/manual-keyword/manual-PAT/manual-SD |
| `targetingMatch` | STRING | 否 | 筛选：Close Match/Loose Match/broad/phrase/exact/Product/Category 等 |
| `search` | STRING | 否 | 定向表达式搜索 |
| `metricFilters` | STRING | 否 | 分号分隔，最多 9 条 |
| `ordering` | ENUM | 否 | 默认 `-spend` |
| `page` | INT | 否 | 默认 1 |
| `pageSize` | INT | 否 | 默认 15，最大 100 |
| `includeSummary` | BOOL | 否 | 默认 true |

响应：

```json
{
  "items": [
    {
      "target_key": "tgt_xxx",
      "targeting_type": "auto",
      "targeting_match": "Close Match",
      "targeting_group": "紧密匹配",
      "targeting": "Close Match",
      "state": "ENABLED",
      "status": "DELIVERING",
      "bid": { "amount": "1.40", "currency_code": "USD" },
      "suggested_bid": { "amount": "1.24", "currency_code": "USD" },
      "suggested_bid_min": { "amount": "1.00", "currency_code": "USD" },
      "suggested_bid_max": { "amount": "1.50", "currency_code": "USD" },
      "metrics": {
        "impressions": 3595,
        "top_of_search_share": "0.04",
        "clicks": 26,
        "spend": { "amount": "39.60", "currency_code": "USD" },
        "orders": 2,
        "sales": { "amount": "39.96", "currency_code": "USD" },
        "ctr": "0.0072",
        "cpc": { "amount": "1.52", "currency_code": "USD" },
        "acos": "0.9910",
        "roas": "1.01"
      },
      "has_metrics": true
    }
  ],
  "summary": { /* 同 metrics 结构 */ },
  "pagination": { "page": 1, "page_size": 15, "total": 4, "total_pages": 1 },
  "meta": {
    "source": "REMOTE_MYSQL_COMPOSITE",
    "currency_code": "USD",
    "deduplication_version": "targeting-campaign-group-realtime-v1"
  }
}
```

数据来源：远程三表聚合 `eb_ad_targeting` + `bi_analyze_ad_targeting` + `bi_analyze_ad_targeting_realtime`，按 `campaign_code` + `group_code`/`group_name` 筛选。

### 7.3 定向策略趋势

`GET .../ad-groups/{ad_group_key}/targeting/trend` → `TargetingTrendView`

请求参数：`startDate`/`endDate`。

响应：`[{ "date": "2026-07-22", "metrics": { /* 同上 */ } }]`。

### 7.4 定向目标实体列表

`GET .../ad-groups/{ad_group_key}/targets` → `TargetEntityView`

响应：`Keyword` 和 `ProductTarget` 实体列表，含 `bid`/`state`/`match_type`/`expression`。

### 7.5 定向竞价修改

`PATCH .../ad-groups/{ad_group_key}/targets/{target_key}/bid` → `TargetBidUpdateView`

请求体：`{ "bid": { "amount": "1.50", "currency_code": "USD" } }`

落库 `eb_ad_targeting.bid`，记录审计日志。受 D-180 阻塞。

### 7.6 定向启停

`PATCH .../ad-groups/{ad_group_key}/targets/{target_key}/enabled` → `TargetEnabledUpdateView`

请求体：`{ "enabled": true }`

落库 `eb_ad_targeting.state`，记录审计日志。受 D-180 阻塞。

### 7.7 批量竞价

`PATCH .../ad-groups/{ad_group_key}/targets/batch-bid` → `TargetBatchBidView`

请求体：`{ "items": [{ "target_key": "tgt_xxx", "bid": { "amount": "1.50", "currency_code": "USD" } }] }`

落库 `eb_ad_targeting.bid` 批量（事务），记录审计日志。受 D-180 阻塞。

### 7.8 批量启停

`PATCH .../ad-groups/{ad_group_key}/targets/batch-enabled` → `TargetBatchEnabledView`

请求体：`{ "items": [{ "target_key": "tgt_xxx", "enabled": true }] }`

落库 `eb_ad_targeting.state` 批量（事务），记录审计日志。受 D-180 阻塞。

### 7.9 定向策略导出

`GET .../ad-groups/{ad_group_key}/targeting/export` → `TargetingExportView`

响应：`text/csv`（UTF-8 BOM），超过 10,000 行返回 422。

---

## 8. 写操作边界

### 8.1 当前约束

- 远程分析表（`bi_analyze_ad_targeting` / `_realtime`）永远只读。
- V1 不真实调用 Amazon Ads API。
- 竞价/启停写入受 D-180 决策阻塞，落库 SCM 维表 `eb_ad_targeting`。
- 未获得受控写 Provider 授权前，前端开关和编辑框置灰，不伪造成功。

### 8.2 写操作清单

| 操作 | API | 落库 | Service | 受 D-180 |
|---|---|---|---|---|
| 定向竞价 | `PATCH .../targets/{key}/bid` | `eb_ad_targeting.bid` | `update_target_bid` | 是 |
| 定向启停 | `PATCH .../targets/{key}/enabled` | `eb_ad_targeting.state` | `update_target_enabled_state` | 是 |
| 批量竞价 | `PATCH .../targets/batch-bid` | `eb_ad_targeting.bid` 批量 | `batch_update_target_bid` | 是 |
| 批量启停 | `PATCH .../targets/batch-enabled` | `eb_ad_targeting.state` 批量 | `batch_update_target_enabled_state` | 是 |

**Service SQL：**

```sql
-- 竞价
UPDATE eb_ad_targeting SET bid=%s, update_time=NOW()
WHERE mer_id=%s AND campaign_code=%s AND target_id=%s;

-- 启停
UPDATE eb_ad_targeting SET state=%s, update_time=NOW()
WHERE mer_id=%s AND campaign_code=%s AND target_id=%s;
```

### 8.3 竞价修改校验规则

1. 新竞价必须 > 0，精度 2 位小数（`DECIMAL(10,2)`）。
2. 若 `suggested_bid_min`/`suggested_bid_max` 存在，提示建议范围；超出范围时警告但允许提交。
3. 校验 `ProfileAccessLevel.OPERATE` 权限。
4. 校验对象归属（Tenant/Profile/Campaign/AdGroup）。
5. 记录审计日志（`before`/`after` 竞价值），写入 `default.audit_log`。
6. 受 D-180 阻塞时，前端开关和编辑框置灰，提示"写操作未授权"。

所有写操作必须：
1. 校验 `ProfileAccessLevel.OPERATE` 权限。
2. 校验对象归属（Tenant/Profile/Campaign/AdGroup）。
3. 校验状态、修改前值、金额上下限。
4. 落库 SCM 维表，分析事实表永远只读。
5. 记录 `AuditLog`（只追加，脱敏 before/after），写入 `default.audit_log`。
6. 不物理删除，用暂停或软删（`status='6'`）替代。
7. 受 D-180 阻塞时返回 403，前端置灰。

---

## 9. 前端组件结构

```text
frontend/src/features/advertising/
├── components/
│   ├── AdGroupDetailTabs.vue           # 待实现：Tab 容器（本方案仅含定向策略 Tab）
│   ├── TargetingSection.vue            # 待实现：定向策略 Tab（核心）
│   ├── KpiCardGrid.vue                 # 待实现：KPI 卡片组
│   ├── TrendChart.vue                  # 已实现（RemotePerformanceChart）
│   ├── FilterSidebar.vue               # 待实现：筛选侧边栏
│   └── BidEditDialog.vue               # 待实现：竞价编辑弹窗
├── pages/
│   └── AdGroupDetailPage.vue           # 待实现：含定向策略 Tab
├── api/
│   ├── adGroupApi.ts                   # 待实现
│   └── targetingApi.ts                 # 待实现
└── types/
    └── targeting.ts                    # 待实现
```

---

## 10. 交互状态处理

| 状态 | 处理 |
|---|---|
| 加载中 | 骨架屏 |
| 空数据 | 空状态插画 + "暂无定向目标" |
| 部分失败 | 错误提示 + 可用数据展示 |
| 完全失败 | 错误提示 + 重试按钮 |
| 无权限 | 403 提示 |
| D-180 阻塞 | 启用开关和竞价编辑框置灰 + "写操作未授权"提示 |

---

## 11. 必须确认

**已由数据库核验确认（2026-08-06）：**

1. `eb_ad_targeting`（406,210 行）、`bi_analyze_ad_targeting`（1,012,586 行）、`bi_analyze_ad_targeting_realtime`（392,208 行）存在。
2. `group_id` 在所有分析表中全为 NULL，必须用 `group_code`（历史）/`group_name`（实时）作为广告组关联键。
3. `targeting_type` 实际值为 `auto`/`manual-keyword`/`manual-PAT`/`manual-SD`。
4. `targeting_match` 覆盖关键词、商品目标和自动投放 6 种匹配方式（Close Match/Loose Match/Substitutes/Complements/Purchases/Views）。
5. `current_bid`/`suggested_bid`/`suggested_bid_min`/`suggested_bid_max` 字段存在且有数据。

**仍需确认：**

6. `ad_group_key` 签名编码方案（建议 `grp_` 前缀，salt 含 `campaign_key`，参照 `_campaign_key` 实现）。
7. 竞价/启停操作是否解除 D-180 阻塞；未解除前前端置灰。
8. `targeting` 字段（如 `Asin="B08T877M36"`）是否需要结构化解析以区分 ASIN/Category/Brand，或直接字符串展示。
9. `targeting_match` 大小写并存（`broad`/`BROAD`）的归一化策略。
10. SCM `eb_ad_targeting` 表的完整字段结构（21 列，需补充查询）。
11. 远程表去重策略：`bi_analyze_ad_targeting` 和 `_realtime` 是否存在同 Campaign+group+targeting+date 的重复快照，需参照 Campaign 三表的 `ROW_NUMBER()` 去重方案。

---

## 12. 验收标准

1. 广告活动详情 → 广告组详情页定向策略 Tab 可真实展示定向目标列表。
2. KPI 卡片展示广告组汇总指标，可切换指标。
3. 趋势图展示广告组每日指标，悬停显示 tooltip。
4. 定向策略表格按 `targeting_type` 和 `targeting_match` 分行展示，含合计行。
5. 建议竞价列展示推荐值 + 区间（min-max）。
6. 竞价列可编辑（受 D-180），落库 `eb_ad_targeting.bid`。
7. 启停开关可切换（受 D-180），落库 `eb_ad_targeting.state`。
8. 批量竞价/启停可用（受 D-180），事务执行。
9. 筛选/搜索/排序/分页/导出均可用。
10. 自动投放 6 种匹配方式（Close Match/Loose Match/Substitutes/Complements/Purchases/Views）分行展示。
11. 所有接口校验 Tenant/Profile 隔离，跨租户返回 404。
12. 远程分析表只读，写操作落库 SCM 维表。
13. 审计日志只追加，记录脱敏 before/after。
14. 前端页面处理加载、空数据、部分失败、完全失败、无权限、D-180 阻塞状态。
15. OpenAPI 契约同步 TypeScript 类型。

---

## 13. 后续扩展

- 解除 D-180 阻塞后，启用真实写操作。
- 广告组详情页其他 Tab（广告/否定投放/搜索词/广告组设置/历史记录）另行实现。
- 接入真实 Amazon Ads API。
- `targeting` 字段结构化解析（ASIN/Category/Brand）。
- Sponsored Display（`manual-SD`）完整实现。
