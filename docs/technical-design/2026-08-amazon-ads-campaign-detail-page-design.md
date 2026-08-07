# 广告活动详情页技术方案（广告组 Tab）

> 版本：V2.0
> 日期：2026-08-07
> 适用项目：Amazon 广告智能优化系统 V1
> 目标页面：广告活动详情页 — 广告组 Tab（`campaign-detail.html` 中 `tab-adgroups`）
> 目标模块：`backend/apps/advertising`、`backend/apps/analytics`、`frontend/src/features/advertising`
> 上游约束：`codex_master_goal_amazon_ads_v1.md`、`AGENTS.md`、`docs/15-decision-log.md`、`2026-08-amazon-ads-campaign-targeting-module-design.md`
> 参考页面：`C:/Users/admin/Desktop/广告智能投放系统/广告智能投放系统/campaign-detail.html`
> 实现范围：仅广告组 Tab（竞价调整/广告活动设置/历史记录/智能决策 Tab 不在本方案范围）
> 数据库核验：已实际连接 `192.168.0.75` 的 `wecon_scm_20251228`（SCM）和 `wecon_analyze`（分析）库

---

## 0. 方案定位

本方案覆盖**广告活动详情页的广告组 Tab**，即广告活动下钻后的广告组列表管理界面。与既有方案 `2026-08-amazon-ads-campaign-targeting-module-design.md` 的关系：既有方案定义了广告组列表 API 与下钻链路，本方案补全页面交互细节（KPI 卡片、趋势图、表格、筛选、合计、写操作交互）。

页面其他 Tab（竞价调整、广告活动设置、历史记录、智能决策）不在本方案范围。

---

## 1. 方案结论

广告组 Tab 是广告活动详情页的默认 Tab，展示该 Campaign 下所有广告组的列表管理界面。页面结构：顶部 Campaign 摘要栏 + KPI 卡片组 + 趋势图表 + 工具栏 + 广告组表格（含合计行）。

数据原则：
- Campaign 摘要与 KPI/趋势：远程三表聚合只读（`eb_ad_campaign` + `bi_analyze_ad_campaign` + `bi_analyze_ad_campaign_realtime`），已实现。
- 广告组列表：远程三表聚合只读（`eb_ad_group` + `bi_analyze_ad_group` + `bi_analyze_ad_group_realtime`），按 `campaign_code` 筛选。

写操作原则：广告组启停/竞价落库 SCM 维表 `eb_ad_group`，分析事实表永远只读，受 D-180 决策阻塞约束。

---

## 2. 核心链路

```text
广告活动列表（/advertising/overview）
  → 广告活动详情（/advertising/campaigns/:campaignKey?tab=adgroups）
      └─ 广告组 Tab：广告组列表
          → 点击广告组名称 → 广告组详情页
```

---

## 3. 页面路由

- `/advertising/campaigns/:campaignKey` → `CampaignDetailPage.vue`（已实现概览，本方案改造为含广告组 Tab）
- Tab 通过 URL query `?tab=adgroups` 同步，默认选中。
- URL 使用签名编码的 `campaign_key`（`cmp_` 前缀，`django.core.signing`）。

---

## 4. 页面结构（参照 campaign-detail.html `tab-adgroups`）

### 4.1 顶部 Campaign 摘要栏

```text
┌──────────────────────────────────────────────────────────────┐
│ [h1] Campaign 名称        [开关] [状态徽标]                   │
│ 类型: 自动投放 | 开始日期: 2026-07-21 | 预算: $12.00/日       │
│                                          [提供反馈]           │
└──────────────────────────────────────────────────────────────┘
```

| 元素 | 数据字段 | 来源 |
|---|---|---|
| 标题 | `name` | `eb_ad_campaign.name` |
| 状态开关 | `enabled` | `eb_ad_campaign.state` ∈ {enabled, paused} |
| 状态徽标 | `status` | enabled→投放中(绿)、paused→已暂停(灰)、archived→已归档(红) |
| 类型 | `targeting_type` | `eb_ad_campaign.type`：auto→自动投放、manual→手动投放 |
| 开始日期 | `start_date` | `eb_ad_campaign.start_date` |
| 预算 | `daily_budget` | `eb_ad_campaign.budget`，展示 `{amount} / 日` |
| 提供反馈 | 静态链接 | 指向反馈表单 |

### 4.2 KPI 卡片组

4 个卡片，每个可切换指标（下拉菜单），可切换显隐（色块点击）：

| 卡片 | 默认指标 | 颜色 | 图表类型 | 轴 |
|---|---|---|---|---|
| 1 | `total_cost`（总花费） | `#a78bfa`（紫） | 柱状 | 左 |
| 2 | `clicks`（点击量） | `#ec4899`（粉） | 折线 | 右 |
| 3 | `purchases`（购买量） | `#14b8a6`（青绿） | 折线 | 左 |
| 4 | `impressions`（展示量） | `#fb923c`（橙） | 折线 | 右 |

可切换指标池（10 个）：`total_cost, clicks, purchases, impressions, cpc, ctr, acos, roas, sales, cpa`

KPI 数值来自 Campaign 维度三表聚合（整个 Campaign 在日期范围内的汇总指标，非广告组聚合）。

### 4.3 趋势图表

- 类型：SVG 组合图（柱状 + 折线），双 Y 轴
- 数据：Campaign 每日指标趋势（`trend` 数组）
- 交互：鼠标悬停显示 tooltip（日期 + 各指标值）
- 图例项可点击切换显隐

### 4.4 工具栏

| 元素 | 功能 |
|---|---|
| 日期范围按钮 | 预设（7/14/30 天）+ 自定义日期范围 |
| 刷新按钮 | 重新请求数据 |
| 筛选按钮 | 弹出筛选侧边栏 |
| 导出下拉 | 导出 CSV/XLSX |

### 4.5 广告组表格

**表头（15 列）：**

| 列 | 字段 | 类型 | 说明 |
|---|---|---|---|
| 复选框 | - | checkbox | 全选/行选 |
| 启用 | `enabled` | switch | 启停开关，受 D-180 阻塞时置灰 |
| 广告组名称 | `name` | link | 点击跳转广告组详情页 |
| 状态 | `status` | badge | 投放中/已暂停/已归档 |
| 默认竞价 | `default_bid` | input | 可编辑，$ 前缀，min=0.02 |
| 商品 | `product_count` | number | 广告组下商品数量 |
| 展示量 | `metrics.impressions` | number | - |
| 点击量 | `metrics.clicks` | number | - |
| 总成本 | `metrics.total_cost` | currency | - |
| CPC | `metrics.cpc` | currency | - |
| 购买量 | `metrics.orders` | number | - |
| 销售额 | `metrics.sales` | currency | - |
| ACOS | `metrics.acos` | percent | - |
| ROAS | `metrics.roas` | ratio | - |

**合计行：** 各指标列汇总，"合计：N 个广告组"。

**行内交互：**
- 启用开关：`PATCH .../ad-groups/{key}/enabled` → 落库 `eb_ad_group.state`
- 默认竞价编辑：弹窗确认 → `PATCH .../ad-groups/{key}/bid` → 落库 `eb_ad_group.bid`
- 广告组名称链接：`RouterLink` → `/advertising/campaigns/:campaignKey/ad-groups/:adGroupKey`

### 4.6 筛选侧边栏

点击"筛选"按钮弹出侧边栏，含：
- 进行中开关筛选
- 9 个范围筛选：默认竞价/展示量/点击量/点击率/总成本/CPC/购买量/销售额/ACOS/ROAS
- 每个筛选：操作符（gte/lte/eq/between）+ 数值
- 重置/应用按钮

筛选参数透传到 API 的 `metricFilters` 参数（分号分隔，格式 `field:operator:value[:value2]`，最多 9 条）。

---

## 5. 数据源

### 5.1 Campaign 维度（顶部摘要 + KPI + 趋势，已实现）

| 数据角色 | Django DB Alias / 表 | 作用 |
|---|---|---|
| 当前活动维表 | `scm_remote.eb_ad_campaign` | 名称、状态、投放类型、起止日期、预算、竞价策略 |
| 历史事实表 | `ads_analysis_remote.bi_analyze_ad_campaign` | 已沉淀业务日的历史指标 |
| 实时事实表 | `ads_analysis_remote.bi_analyze_ad_campaign_realtime` | 当日/近期滚动更新指标 |

连接键：事实 `campaign_code -> SCM.code`。三表聚合去重版本 `campaign-code-product-asin-realtime-v1`。

### 5.2 广告组维度（表格，本方案核心）

| 数据角色 | Django DB Alias / 表 | 作用 | 行数 |
|---|---|---|---|
| 广告组维表 | `scm_remote.eb_ad_group` | 广告组当前元数据（名称、状态、默认竞价、类型） | 55,071 |
| 广告组历史事实表 | `ads_analysis_remote.bi_analyze_ad_group` | 已沉淀业务日的广告组历史指标 | 246,370 |
| 广告组实时事实表 | `ads_analysis_remote.bi_analyze_ad_group_realtime` | 当日/近期滚动更新的广告组指标 | 1,903,719 |

连接键：`campaign_code` 关联回 Campaign，`group_code`（历史表）/`group_name`（实时表）关联广告组。**`group_id` 在所有分析表中全为 NULL，不能作为连接键。**

**读取广告组当前元数据（SCM 库 `eb_ad_group`）：**

```sql
SELECT ad_group_id, campaign_code, type, name, bid, state
FROM eb_ad_group
WHERE mer_id = %s
  AND campaign_code = %s
  AND COALESCE(status, '0') <> '6'
ORDER BY update_time DESC, id DESC;
```

**读取广告组历史指标（分析库 `bi_analyze_ad_group`）：**

```sql
SELECT campaign_code, group_state, bid, targeting_type,
       SUM(imperssion) AS impressions, SUM(click) AS clicks,
       SUM(spend) AS spend, SUM(orders) AS orders, SUM(sales) AS sales
FROM bi_analyze_ad_group
WHERE mer_id = %s AND campaign_code = %s
  AND DATE(creation_date) BETWEEN %s AND %s
GROUP BY campaign_code, group_state, bid, targeting_type;
```

实时表 `bi_analyze_ad_group_realtime` 同理，按 `update_time DESC` 去重。两表按原子粒度 UNION ALL 后按 `source_priority`（实时>历史）选最新。

---

## 6. 核心 API

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

### 6.1 已有 API（复用）

| API | 方法 | 说明 |
|---|---|---|
| `.../campaigns/{campaign_key}` | GET | Campaign 详情（含 item + trend + meta），已实现 |
| `.../campaigns/{campaign_key}/enabled` | PATCH | Campaign 启停，已实现 |

### 6.2 广告组列表 API

`GET /api/v1/advertising/tenants/{tenantId}/profiles/{profileId}/campaigns/{campaign_key}/ad-groups` → `AdGroupListView`

请求参数：

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `startDate` | DATE | 与 endDate 同进同出 | 开始日期 |
| `endDate` | DATE | 与 startDate 同进同出 | 结束日期（范围 ≤ 90 天） |
| `search` | STRING | 否 | 广告组名称搜索（≤ 100 字符） |
| `status` | STRING | 否 | 逗号分隔，enabled/paused/archived |
| `metricFilters` | STRING | 否 | 分号分隔，格式 `field:operator:value[:value2]`，最多 9 条 |
| `ordering` | ENUM | 否 | 默认 `-spend`，支持 `±name/±spend/±clicks/±ctr/±acos` 等 |
| `page` | INT | 否 | 默认 1 |
| `pageSize` | INT | 否 | 默认 15，最大 100 |
| `includeSummary` | BOOL | 否 | 默认 true |

`metricFilters` 支持字段：`impressions/clicks/spend/orders/cpc/acos/ctr/cvr`；支持操作符：`gte/lte/eq/between`。

响应：

```json
{
  "items": [
    {
      "ad_group_key": "grp_xxx",
      "name": "AdGroup 1",
      "state": "ENABLED",
      "status": "DELIVERING",
      "default_bid": { "amount": "0.75", "currency_code": "USD" },
      "product_count": 1,
      "metrics": {
        "impressions": 3600,
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
  "pagination": { "page": 1, "page_size": 15, "total": 1, "total_pages": 1 },
  "meta": {
    "source": "REMOTE_MYSQL_COMPOSITE",
    "currency_code": "USD",
    "deduplication_version": "ad-group-campaign-code-realtime-v1"
  }
}
```

数据来源：远程三表聚合 `eb_ad_group` + `bi_analyze_ad_group` + `bi_analyze_ad_group_realtime`，按 `campaign_code` 筛选，按 `group_code`/`group_name` 聚合。

### 6.3 广告组启停

`PATCH .../campaigns/{campaign_key}/ad-groups/{ad_group_key}/enabled` → `AdGroupEnabledUpdateView`

请求体：`{ "enabled": true }`

落库 `eb_ad_group.state`，记录审计日志。受 D-180 阻塞，未授权前不伪造成功。

### 6.4 广告组竞价修改

`PATCH .../campaigns/{campaign_key}/ad-groups/{ad_group_key}/bid` → `AdGroupBidUpdateView`

请求体：`{ "bid": { "amount": "1.50", "currency_code": "USD" } }`

落库 `eb_ad_group.bid`，记录审计日志。受 D-180 阻塞。

### 6.5 广告组导出

`GET .../campaigns/{campaign_key}/ad-groups/export` → `AdGroupExportView`

响应：`text/csv`（UTF-8 BOM），超过 10,000 行返回 422。

---

## 7. 写操作边界

### 7.1 当前约束

- 远程分析表（`bi_analyze_ad_group` / `_realtime`）永远只读。
- V1 不真实调用 Amazon Ads API。
- 启停/竞价写入受 D-180 决策阻塞，落库 SCM 维表 `eb_ad_group`。
- 未获得受控写 Provider 授权前，前端开关和编辑框置灰，不伪造成功。

### 7.2 写操作清单

| 操作 | API | 落库 | Service | 受 D-180 |
|---|---|---|---|---|
| 广告组启停 | `PATCH .../ad-groups/{key}/enabled` | `eb_ad_group.state` | `update_ad_group_enabled_state` | 是 |
| 广告组竞价 | `PATCH .../ad-groups/{key}/bid` | `eb_ad_group.bid` | `update_ad_group_bid` | 是 |

**Service SQL：**

```sql
-- 启停
UPDATE eb_ad_group SET state=%s, update_time=NOW()
WHERE mer_id=%s AND campaign_code=%s AND ad_group_id=%s;

-- 竞价
UPDATE eb_ad_group SET bid=%s, update_time=NOW()
WHERE mer_id=%s AND campaign_code=%s AND ad_group_id=%s;
```

所有写操作必须：
1. 校验 `ProfileAccessLevel.OPERATE` 权限。
2. 校验对象归属（Tenant/Profile/Campaign/AdGroup）。
3. 校验状态、修改前值、金额上下限（竞价 > 0，精度 2 位小数，min=0.02）。
4. 落库 SCM 维表，分析事实表永远只读。
5. 记录 `AuditLog`（只追加，脱敏 before/after），写入 `default.audit_log`。
6. 不物理删除，用暂停或软删（`status='6'`）替代。
7. 受 D-180 阻塞时返回 403，前端置灰。

---

## 8. 前端组件结构

```text
frontend/src/features/advertising/
├── components/
│   ├── CampaignDetailTabs.vue           # 待实现：Tab 容器（本方案仅含广告组 Tab）
│   ├── CampaignAdGroupTab.vue           # 待实现：广告组 Tab（核心）
│   ├── KpiCardGrid.vue                  # 待实现：KPI 卡片组
│   ├── TrendChart.vue                   # 已实现（RemotePerformanceChart）
│   ├── FilterSidebar.vue                # 待实现：筛选侧边栏
│   └── BidEditDialog.vue                # 待实现：竞价编辑弹窗
├── pages/
│   └── CampaignDetailPage.vue           # 改造：含广告组 Tab
├── api/
│   ├── campaignApi.ts                   # 已实现
│   └── adGroupApi.ts                    # 待实现
└── types/
    └── adGroup.ts                       # 待实现
```

---

## 9. 交互状态处理

| 状态 | 处理 |
|---|---|
| 加载中 | 骨架屏 |
| 空数据 | 空状态插画 + "暂无广告组" |
| 部分失败 | 错误提示 + 可用数据展示 |
| 完全失败 | 错误提示 + 重试按钮 |
| 无权限 | 403 提示 |
| D-180 阻塞 | 启用开关和竞价编辑框置灰 + "写操作未授权"提示 |

---

## 10. 必须确认

**已由数据库核验确认（2026-08-06）：**

1. `eb_ad_group`（55,071 行）、`bi_analyze_ad_group`（246,370 行）、`bi_analyze_ad_group_realtime`（1,903,719 行）存在。
2. `group_id` 在所有分析表中全为 NULL，必须用 `group_code`（历史）/`group_name`（实时）作为广告组关联键。

**仍需确认：**

3. `ad_group_key` 签名编码方案（建议 `grp_` 前缀，salt 含 `campaign_key`，参照 `_campaign_key` 实现）。
4. 竞价/启停操作是否解除 D-180 阻塞；未解除前前端置灰。
5. 远程表去重策略：`bi_analyze_ad_group` 和 `_realtime` 是否存在同 Campaign+group+date 的重复快照，需参照 Campaign 三表的 `ROW_NUMBER()` 去重方案。

---

## 11. 验收标准

1. 广告活动列表 → 广告活动详情页广告组 Tab 可真实展示广告组列表。
2. KPI 卡片展示 Campaign 汇总指标，可切换指标与显隐。
3. 趋势图展示 Campaign 每日指标，悬停显示 tooltip。
4. 广告组表格展示名称/状态/默认竞价/指标，含合计行。
5. 启用开关可切换（受 D-180），落库 `eb_ad_group.state`。
6. 默认竞价可编辑（受 D-180），落库 `eb_ad_group.bid`。
7. 广告组名称链接可跳转到广告组详情页。
8. 筛选侧边栏 9 个指标筛选可应用，透传 `metricFilters`。
9. 日期范围/搜索/排序/分页/导出均可用。
10. 所有接口校验 Tenant/Profile 隔离，跨租户返回 404。
11. 远程分析表只读，写操作落库 SCM 维表。
12. 审计日志只追加，记录脱敏 before/after。
13. 前端页面处理加载、空数据、部分失败、完全失败、无权限、D-180 阻塞状态。
14. OpenAPI 契约同步 TypeScript 类型。

---

## 12. 后续扩展

- 解除 D-180 阻塞后，启用真实写操作。
- 广告活动详情页其他 Tab（竞价调整/活动设置/历史记录/智能决策）另行实现。
- 接入真实 Amazon Ads API。
