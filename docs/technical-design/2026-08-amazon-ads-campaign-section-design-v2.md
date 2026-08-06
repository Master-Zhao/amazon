# Amazon 广告活动列表模块复刻与远程三表聚合技术方案 V2（2026-08-04 修订）

> 文档状态：已按真实库核验并完成本轮三表只读纵向链路（启停写入仍受 D-180 阻塞）
> 编制日期：2026-08-03  
> 适用项目：Amazon 广告智能优化系统 V1  
> 目标模块：完整广告仪表盘页面的广告活动列表、查询筛选、详情入口与启停意图
> 参考页面：C:/Users/admin/Desktop/广告智能投放系统/广告智能投放系统/index.html  
> 参考截图：codex-clipboard-d4976fee-6104-4d2c-9476-25096a62ead1.png、codex-clipboard-0e18fe0a-77aa-4f93-b0fb-00dbc5a2d132.png

---

## 1. 修订说明

本方案根据最新数据库 DDL、参考 HTML 和两张目标截图再次修订。以下修订优先于本文后续仍保留的历史实施快照：

1. Campaign 指标不再只读取 `bi_analyze_ad_campaign`，而是由历史表、实时表和 SCM 活动表三表组成；
2. 日期选择器、活动搜索、截图同款指标筛选菜单、服务端聚合与全筛选合计均为必须实现项；
3. 广告活动名称必须是可访问链接，并跳转到真实详情路由；
4. “启用”开关的最终目标是可点击并真实启停，但当前远程数据库只读和 V1 禁止真实 Amazon 写入的约束仍然有效；未获得合规写通道授权前不得用前端内存或本地覆盖伪造成功；
5. 现有顶部栏和左侧栏保留，“工作台 / 卖家空间 / 广告总览 / 数据中心”等横向目录导航不保留；
6. HTML 只作为视觉和交互参考，数据、合计、筛选、详情和状态变化都必须经过后端。
7. 9 个一级筛选项点击后统一打开参考截图二的居中模态框；多项指标规则允许并存，比例在 API 中继续使用小数、在界面中显示为百分比。

本次修订重点覆盖参考 HTML 最下方的广告活动列表模块及其真实查询链路，不负责：

- 顶部 KPI；
- 表现概览图；
- 风险等级卡片；
- 风险详情弹窗；
- 其他上层仪表盘模块。

本文件继续沿用 V2 文件名，避免复制第二份主技术方案。后续开发以本次修订后的三表、聚合、筛选、详情和写操作边界为准；数据库、安全和权限边界仍以主规格及已确认决策为准。

### 1.1 2026-08-04 真实库核验结论

- 历史表覆盖 88 个业务日，实时表覆盖 50/51 个业务日，两表有 50 个重叠业务日；因此必须按原子粒度覆盖，不能按“整日选历史或实时”切换；
- 历史候选粒度为 33,784 行/33,783 个唯一粒度；实时为 265,108 行/260,543 个唯一粒度。表内存在重复快照，已采用 `ROW_NUMBER()` 按更新时间和 id 稳定选最新；
- 去掉来源后，历史 33,783 个粒度、实时 260,543 个粒度，交集 16,453 个；交集由实时覆盖，单边粒度继续保留；
- 历史 `type` 全 NULL，实时 `type` 为 `SP-Auto`/`SP-Manual`，真实数据证明它不是 DDL 注释声称的 7d/14d/custom 统计窗口；
- 正确连接为事实 `campaign_code -> SCM.code`：当前范围相交 5,908 个；`campaign_id` 相交为 0，不能作为主连接键；
- 当前实现返回历史/实时水位、实时 as-of、字段映射和 `campaign-code-product-asin-realtime-v1` 去重版本，且不输出商户映射。

---

## 2. 目标与范围

### 2.1 页面最终结构

~~~text
┌────────────────────── 顶部栏：保留原内容和交互 ──────────────────────┐
├── 左侧栏：保留 ──┬──────────────── 主内容区 ────────────────────────┤
│                  │                                                  │
│                  │  HTML 风格的 KPI、图表、风险模块                 │
│                  │  不属于本任务开发范围                            │
│                  │                                                  │
│                  ├──────────────────────────────────────────────────┤
│                  │  CampaignSection                                 │
│                  │  工具栏、日期、搜索、筛选、表格、合计、分页、详情 │
└──────────────────┴──────────────────────────────────────────────────┘
~~~

### 2.2 明确删除的页面结构

当前 AppLayout 主内容上方的横向模块导航整体移除：

- 工作台；
- 卖家空间；
- 广告总览；
- 数据中心；
- 广告分析；
- 远程数据；
- 智能优化；
- 审批执行；
- 知识中心；
- 系统管理。

对应当前代码：

    frontend/src/shared/layouts/AppLayout.vue:103-143

移除的是横向导航展示，不代表立即删除其对应 Vue Router 路由或后端业务模块。旧路由是否继续通过直接 URL 访问，应由产品另行决定。

### 2.3 保留范围

严格保留：

- AppLayout 顶部栏；
- 品牌标识；
- 面包屑；
- 当前用户显示；
- 通知；
- 帮助中心；
- 用户头像菜单；
- 退出登录；
- 左侧栏；
- 左侧栏现有创建广告和广告总览入口；
- 登录与刷新机制；
- Tenant、Store、Profile 后端数据隔离；
- 远程数据库只读策略。

### 2.4 本期目标

- 在完整广告仪表盘底部实现 CampaignSection；
- 视觉严格接近截图和 HTML；
- 接入真实远程 Campaign 元数据、历史指标与实时指标；
- 支持搜索、截图同款分层筛选、日期快捷范围/自定义范围、排序、分页和全筛选合计；
- 支持 Campaign 名称跳转到真实详情页；
- 为 Campaign 启停提供真实写契约设计，但只有取得受控写 Provider 和权限授权后才启用开关；
- 支持只读导出；
- 处理加载、暂无数据、失败、无权限和局部缺失；
- 不把前端内存切换、本地数据库覆盖或远程 SQL `UPDATE` 伪装成真实广告状态变化。

### 2.5 非目标

- 不开发 KPI 和表现概览图；
- 不开发风险等级评估；
- 不实现卖家空间页面；
- 不修改顶部栏和左侧栏内容；
- 未经新的明确授权不调用真实 Amazon Ads 写接口；
- 不通过远程数据库 `UPDATE` 模拟广告操作；
- 不复制 HTML 中的 Mock 数据；
- 不新增第二套登录、租户或 Profile 体系；
- 不跨 Profile、Marketplace 或币种汇总。

---

## 3. 已确认事实

### 3.1 技术栈

- Python 3.13；
- Django 5.2；
- Django REST Framework 3.16；
- Vue 3；
- TypeScript；
- Vite；
- Pinia；
- Axios；
- ECharts；
- MySQL；
- Redis；
- Celery；
- pnpm；
- Docker Compose。

### 3.2 当前数据库 aliases

已通过 Django settings 实际确认：

    ['default', 'scm_remote', 'ads_analysis_remote']

| Alias | 用途 | 本模块权限 |
|---|---|---|
| default | 认证、租户、Store、Profile、权限、审计 | 允许系统正常读写；不作为 Campaign 页面数据源 |
| scm_remote | 远程 Campaign 当前元数据 | 只读 |
| ads_analysis_remote | 远程 Campaign 历史指标和实时指标 | 只读 |

本模块使用的三张远程表：

| 数据角色 | Alias / 表 | 作用 | 是否可直接相加 |
|---|---|---|---|
| 当前活动维表 | `scm_remote.eb_ad_campaign` | 名称、状态、投放类型、起止日期、预算、竞价策略 | 否；每个 Campaign 取当前记录 |
| 历史事实表 | `ads_analysis_remote.bi_analyze_ad_campaign` | 已沉淀业务日的历史指标 | 只在完成原子粒度去重后参与聚合 |
| 实时事实表 | `ads_analysis_remote.bi_analyze_ad_campaign_realtime` | 当日/近期滚动更新指标与最新投放字段 | 不得与同原子粒度历史快照重复相加 |

### 3.3 目标 HTML

目标 HTML 是自包含静态演示页面：

- Campaign 数据来自内嵌 JavaScript；
- 日期变化重新生成演示数据；
- Campaign 开关只修改内存，因此不能复制其数据实现；
- 创建按钮仅弹出演示提示；
- 分页是前端数组分页；
- 搜索没有真实后端查询；
- 导出未真实实现；
- 不存在实际 API 网络请求。

因此只能复刻信息架构、视觉和可用交互形式，不能复制其数据实现。

---

## 4. 当前仓库现状

### 4.1 页面与布局

| 文件 | 行号 | 当前作用 | 本方案处理 |
|---|---:|---|---|
| frontend/src/app/App.vue | 1-8 | AppLayout 包裹 RouterView | 保留 |
| frontend/src/shared/layouts/AppLayout.vue | 46-73 | 顶部栏 | 完全保留 |
| frontend/src/shared/layouts/AppLayout.vue | 75-101 | 左侧栏 | 完全保留 |
| frontend/src/shared/layouts/AppLayout.vue | 103-143 | 横向目录导航 | 删除 |
| frontend/src/shared/layouts/AppLayout.vue | 144-146 | 主内容 slot | 保留 |
| frontend/src/features/advertising/pages/AdvertisingOverviewPage.vue | 4-9 | 广告总览占位页 | 改为完整仪表盘容器或接入 CampaignSection |
| frontend/src/features/home/pages/HomePage.vue | 9-42 | 账号工作台和卖家空间入口 | 不作为目标页面 |
| frontend/src/features/analytics/pages/DashboardPage.vue | 102-163 | 现有简单广告分析页 | 不直接复用其页面结构 |

### 4.2 路由

当前相关路由：

| 路由 | 当前组件 | 建议 |
|---|---|---|
| / | HomePage | 后续由完整仪表盘集成方案决定 |
| /advertising | AdvertisingOverviewPage | 指向完整广告仪表盘 |
| /advertising/overview | AdvertisingOverviewPage | 指向完整广告仪表盘 |
| /advertising/create | AdvertisingCreatePage | 路由保留，真实写能力未实现 |
| /campaigns | CampaignMetricsPage | 保留现有分析页语义 |
| /campaigns/:campaignId | CampaignDetailPage | 后续可作为活动详情 |

本模块不应通过修改 /campaigns 的既有分析语义来实现广告活动表格。

### 4.3 前端基础能力

| 能力 | 证据 | 处理 |
|---|---|---|
| Axios 统一客户端 | frontend/src/shared/api/httpClient.ts | 复用 |
| withCredentials | httpClient.ts:34-41 | 复用 |
| Token 和 Tenant Header | httpClient.ts:124-181 | 复用 |
| 401 单次刷新 | httpClient.ts:155-181 | 复用 |
| Tenant Context Store | tenantContext.ts:68-222 | 内部复用 |
| Context 自动选择单一选项 | tenantContext.ts:58-66 | 复用 |
| OpenAPI 类型 | shared/api/generated/schema.d.ts | 契约更新后重新生成 |
| UI 组件库 | 未发现大型 UI 组件库 | 使用功能局部 Vue/CSS |

### 4.4 后端基础能力

| 能力 | 文件 | 处理 |
|---|---|---|
| Campaign 实体接口 | backend/apps/advertising/urls.py | 扩展既有接口 |
| Campaign View | backend/apps/advertising/views.py | 增加请求参数与分页 |
| Campaign Selector | backend/apps/advertising/selectors.py | 改为远程只读查询编排 |
| 远程 Reader | backend/integrations/advertising_data/remote_databases.py | 扩展 |
| Profile 权限 | backend/apps/permissions/services.py | 必须复用 |
| 指标计算 | backend/apps/analytics/calculations.py | 复用 |
| 数据库 Router | backend/config/db_routers.py | 保持 |
| OpenAPI | openapi/schema.yaml | 更新 |

---

## 5. 目标模块视觉结构

### 5.1 截图尺寸

本次用户提供的参考截图尺寸为：

    筛选菜单局部：631 × 675
    CampaignSection 全宽：1643 × 685

视觉验收以这两张截图和目标 HTML 同时为准：全宽截图负责工具栏、列、合计与横向密度；
局部截图负责筛选图标、菜单锚点、菜单宽高、层级、阴影与行距。旧的 1865×650 记录只作
历史对比，不再是唯一基线。

### 5.2 工具栏

~~~text
筛选条件  [进行中 ×] [已启用 ×] [删除所有]

广告活动 ▾  [+ 创建广告活动]  [🔍 查找广告活动]  [⊟]
                                              [日期范围] [导出]
~~~

视觉要求：

- 白色背景；
- 高度约 52px；
- 左右分组；
- 左侧控件间距约 8px；
- 右侧日期和导出靠右；
- 主按钮深色背景；
- 普通按钮白底、浅灰边框；
- 搜索框宽度约 184px；
- 搜索框 placeholder 固定为“查找广告活动”，300ms 防抖后执行服务端搜索；
- `⊟` 图标按钮使用与截图一致的方形外观，点击后显示第一层筛选菜单；
- 第一层菜单顺序固定为：状态、展示量、点击量、花费、购买量、单次点击成本、广告销售成本比、点击率、转化率；
- 菜单从筛选图标下方左对齐展开，宽度约 178px，白底、浅阴影、约 40px 行高，右侧使用 `▸` 表示下一层；
- 状态项进入状态多选；数值项进入运算符和值输入，运算符至少包含 `>=`、`<=`、`=`、`between`；
- 日期按钮点击后提供最近 7 天、最近 14 天、最近 30 天和自定义起止日期；
- 不增加与截图不一致的标题或说明。

### 5.3 表格

表格为高密度横向宽表：

- 表头浅灰；
- 表头约 40px；
- 行高约 50px；
- 字体 12px；
- 10 条数据约占 510px；
- 横向滚动；
- 不在窄屏自动隐藏指标列；
- Campaign 名称列允许比其他列更宽；
- 数字使用 tabular-nums；
- 金额和数字右对齐；
- 状态标签绿色；
- 行 Hover 浅灰；
- 合计行浅灰底、顶部加粗分隔线。

### 5.4 目标列

| 顺序 | 页面列 | 是否首期实现 |
|---:|---|---|
| 1 | 行选择框 | 展示为禁用 |
| 2 | 启用开关 | 目标为真实可操作；写通道未授权时必须禁用并解释原因 |
| 3 | 广告活动名称 | 是，使用 RouterLink 跳转真实详情 |
| 4 | 投放类型 | 是 |
| 5 | 状态 | 是 |
| 6 | 竞价方案 | 是 |
| 7 | 开始日期 | 是 |
| 8 | 结束日期 | 是 |
| 9 | 预算金额 | 是 |
| 10 | 展示量 | 是 |
| 11 | 搜索结果首页位置 | 待口径确认 |
| 12 | 花费 | 是 |
| 13 | 点击量 | 是 |
| 14 | 点击率 | 是 |
| 15 | 总成本 | 是，与花费同源 |
| 16 | 购买量 | 是 |
| 17 | 单次点击成本 | 是 |
| 18 | 广告销售成本 ACoS | 是 |
| 19 | 转化率 CVR | 是 |

### 5.5 筛选标签条

HTML 和截图中工具栏上方均存在筛选标签条。

最终处理：

- 默认筛选为“进行中 + 已启用”，因此进入页面时显示两个标签；
- 应用筛选后显示；
- 单个标签可删除；
- 支持“删除所有”；
- 删除最后一个标签后整行隐藏；
- 筛选变化时重新请求后端并将页码归 1。

### 5.6 合计和分页

- 合计表示全部筛选结果，不是当前页；
- 合计展示展示量、花费、点击、CTR、总成本、购买量、CPC、ACoS、CVR；
- 首页位置占比未确认聚合方式时显示 —；
- 分页位于合计行下方；
- 支持总记录数、总页数、当前页、上一页、下一页；
- 默认 pageSize 建议 15；
- 最大 pageSize 建议 100。

---

## 6. 功能边界矩阵

分类：

- A：本期真实实现；
- B：本期只读展示；
- C：本期禁用；
- D：依赖 Amazon Ads 写 API；
- F：依赖产品或数据确认；
- G：不在本期范围。

| 功能 | 页面存在 | 数据来源 | 前端职责 | 后端职责 | 写入 | 分类 | 备注 |
|---|---|---|---|---|---|---|---|
| Campaign 列表 | 是 | 两个 remote alias 内的三张表 | 展示 | 权限、去重、聚合、拼接 | 否 | A | 必须真实数据 |
| 名称搜索 | 是 | name/code | 防抖、URL 状态 | 参数化 LIKE | 否 | A | 页码归 1 |
| 状态筛选 | 是 | SCM state | 标签和菜单 | 枚举映射 | 否 | A | 白名单 |
| 已启用筛选 | 是 | SCM state | 标签 | enabled 映射 | 否 | A | 默认可启用 |
| 指标筛选 | HTML/截图有 | 三表聚合指标 | 分层菜单、规则输入、标签 | 白名单 HAVING | 否 | A | 9 个一级项均需实现 |
| 日期范围 | 是 | 历史/实时 `creation_date` | 快捷范围和自定义日期 | 范围校验 | 否 | A | Profile 时区 |
| 排序 | 截图未突出 | 聚合或元数据 | 表头操作 | 白名单 ORDER BY | 否 | A | 不允许任意字段 |
| 分页 | HTML 有 | 查询结果 | 页码操作 | 服务端分页 | 否 | A | 非前端 slice |
| 合计 | 是 | 分析表聚合 | 合计行 | 全筛选范围聚合 | 否 | A | 非当前页合计 |
| Campaign 详情跳转 | 名称有链接 | 三表聚合详情 API | RouterLink 跳转 | 重新授权并查询 | 否 | A | 不使用 sessionStorage 携带权威数据 |
| 导出 | 是 | 同列表查询 | 下载状态 | CSV 和审计 | 仅审计 | A | 不写远程库 |
| 创建 Campaign | 是 | Amazon Ads API | 禁用按钮 | 不提供接口 | 否 | C+D | 当前 V1 禁止 |
| 启用/暂停 | 开关存在 | 受控 CampaignStateProvider | 乐观交互、确认与回滚 | 权限、幂等、漂移、审计、Provider 调用 | 是 | D（业务要求已确认，写通道阻塞） | 未授权前 disabled，不伪造成功 |
| 修改预算 | 未见编辑器 | Amazon Ads API | 只读文本 | 不提供接口 | 否 | G | 后续阶段 |
| 修改竞价 | 未见编辑器 | Amazon Ads API | 只读文本 | 不提供接口 | 否 | G | 后续阶段 |
| 批量选择 | 复选框存在 | 页面状态 | 禁用 | 无 | 否 | C | 无批量动作 |
| 批量操作 | 无 | Amazon Ads API | 不显示 | 无 | 否 | G | 当前范围外 |

---

## 7. 数据源设计

### 7.1 数据来源原则

CampaignSection 展示的广告活动及指标必须来自远程数据库：

    scm_remote
    ads_analysis_remote

禁止：

- 使用 HTML 内嵌数据；
- 使用随机生成数据；
- 使用前端静态数组；
- 使用 fixtures 冒充远程生产数据；
- 在远程失败时回退到本地 ads_campaign；
- 通过远程数据库 UPDATE 模拟广告操作。

### 7.2 SCM Campaign 元数据

表：

    scm_remote.eb_ad_campaign

已确认字段：

- mer_id；
- mer_code；
- campaign_id；
- code；
- name；
- type；
- state；
- start_date；
- end_date；
- budget；
- bidding_strategy；
- update_time 等时间字段。

用途：

- Campaign 名称；
- 辅助代码；
- 当前投放类型；
- 当前状态；
- 竞价策略；
- 开始/结束日期；
- 当前每日预算。

### 7.3 历史广告分析事实

表：

    ads_analysis_remote.bi_analyze_ad_campaign

本次 DDL 确认的关键字段包括：`mer_id`、`mer_code`、`type`、`creation_date`、
`campaign_id`、`campaign_code`、`product_id`、`asin`、`imperssion`、`click`、
`spend`、`orders`、`sales`、`sales_units`、`top_of_search_is`、`create_time`，以及
若干已计算比率字段。应用层把拼写错误的 `imperssion` 规范化为 `impressions`。

不得再引用当前 Schema 不存在的 `orders_7d`、`sales_7d`、`sale_units_7d`、
`other_sales_7d`。DDL 对 `type` 的 7d/14d/自定义注释与真实数据不符：历史表该字段
全为 NULL，不能用作统计窗口，也不能作为去重粒度或筛选条件。

### 7.4 实时广告分析事实

表：

    ads_analysis_remote.bi_analyze_ad_campaign_realtime

本次 DDL 确认的关键字段包括：`mer_id`、`mer_code`、`type`、`creation_date`、
`campaign_id`、`campaign_code`、`product_id`、`asin`、`impression`、`click`、
`spend`、`orders`、`sales`、`campaign_state`、`serving_status`、`daily_budget`、
`bidding_strategy`、`create_time`、`update_time`。应用层把 `impression` 规范化为
`impressions`。

实时表可能保存滚动快照，不得把同一原子粒度的多次快照相加。每个原子粒度只取
`COALESCE(update_time, create_time)` 最新、再以 `id` 最大者稳定打破并列。

### 7.5 历史与实时的去重、覆盖和聚合

三表查询必须按下列顺序执行：

1. 服务端从已授权 Profile 得到固定 `mer_id + mer_code`，前端不得传入；
2. 历史表和实时表分别映射为统一字段集；`type` 不作为统计窗口；
3. 先在各表内部按原子粒度去重；
4. 将两表规范化结果合并后，对相同原子粒度给予实时表更高优先级；
5. 只对去重后的绝对值字段 `SUM`；
6. 在 Campaign 聚合结果上重新计算 CTR、CPC、CVR、ACoS、ROAS；
7. 最后批量读取 `eb_ad_campaign` 补充当前名称、状态、起止日期、预算和竞价策略；
8. 表格、KPI、趋势、风险、合计、导出和详情必须复用同一个筛选对象与同一聚合服务。

Campaign 集合必须取 SCM 当前活动键与历史/实时事实活动键的并集：

- SCM 存在但选定日期无指标的 Campaign 仍显示，指标为 null/`—`，不能被事实表基集漏掉；
- 事实存在但 SCM 未匹配的 Campaign 仍显示分析表名称/代码，并返回 `metadataMatched=false`；
- 只有当前元数据筛选（如状态）依赖 SCM；指标筛选只在有指标的 Campaign 上成立；
- Summary 仅汇总有事实值的记录，不能把“无事实”与“事实为 0”混为一类。

候选原子粒度：

    (mer_id, mer_code, business_date, campaign_key,
     COALESCE(product_id, 0), COALESCE(asin, ''))

该粒度已使用真实只读重复度查询核验；历史和实时仍分别存在表内重复，因此采用更新时间
与 id 的稳定窗口排序选最新，不能用 `DISTINCT` 静默丢数据。

覆盖规则：同一原子粒度同时出现在历史和实时时，保留实时记录；只存在于其中一表时
保留该表记录。禁止 `historical UNION ALL realtime` 后直接聚合。

服务端响应必须包含以下可观测元数据：

- `source = REMOTE_MYSQL_COMPOSITE`；
- `historyThroughDate`；
- `realtimeThroughDate`；
- `realtimeAsOf`；
- `deduplicationVersion`；
- `fieldMappings`（包含 `campaign_code->code`）；
- `attributionSemantics = REMOTE_FIELDS_UNVERIFIED`，直到数据负责人确认 `orders/sales` 归因口径。

### 7.6 Campaign 唯一范围键

远程查询范围键固定包含 `(mer_id, mer_code)`；跨表 Campaign 连接键固定为
`fact.campaign_code = scm.code`。只有事实 `campaign_code` 为空时，事实内部键才受控回退
到 `campaign_id`，该回退键通常无法匹配 SCM，不得把裸 `campaign_id` 当作跨表连接键。

API 向前端返回服务端生成的 campaignKey，不暴露远程商户映射逻辑。

---

## 8. 字段与指标映射

### 8.1 元数据字段

| 页面字段 | 首选来源 | 回退来源 | 规则 |
|---|---|---|---|
| enabled | SCM state | 分析 campaign_state | enabled 为 true，其他为 false |
| name | SCM name | 分析 campaign_name | 空值显示 — |
| referenceCode | SCM code | 分析 campaign_code | 名称下方辅助标识 |
| targetingType | SCM type | 分析 campaign_type | auto/manual 规范化 |
| status | SCM state | 分析 campaign_state | 统一状态枚举 |
| biddingStrategy | SCM bidding_strategy | 分析字段 | 统一中文展示 |
| startDate | SCM start_date | 分析 campaign_create_date | Profile 业务日期 |
| endDate | SCM end_date | 无 | null 显示“无结束日期” |
| dailyBudget | SCM budget | 分析最新预算快照 | 不跨日期求和 |

### 8.2 绝对值字段

以下字段必须先在完整筛选范围内分别执行 SUM。不得先计算每日比率后再平均。

| 业务字段 | 应用字段 | 历史字段 | 实时字段 | 强制统计公式 | 说明 |
|---|---|---|---|---|---|
| 曝光 Impressions | impressions | `imperssion` | `impression` | SUM(impressions) | 日期范围内所有曝光次数 |
| 点击 Clicks | clicks | `click` | `click` | SUM(clicks) | 日期范围内所有点击次数 |
| 花费 Spend | spend | `spend` | `spend` | SUM(spend) | 日期范围内总花费 |
| 订单 Orders | orders | `orders` | `orders` | SUM(orders) | 归因语义未确认，响应必须标记 |
| 销售额 Sales | sales | `sales` | `sales` | SUM(sales) | 归因语义未确认，响应必须标记 |
| 售出件数 Sale Units | saleUnits | `sales_units` | 无 | 仅历史来源且覆盖完整时 SUM | 不能用 0 冒充实时缺字段 |
| 其他销售额 OtherSales | otherSales | 无 | 无 | 不计算 | 当前三表无法提供，返回 null |

数据空值处理：

- 某日位于筛选范围内但该日字段为空时，该日按 0 计入 SUM；
- 某个 Campaign 在整个筛选范围内完全没有对应事实数据时，前端显示 —；
- 不能因为某一天无数据而把整个 Campaign 指标标记为无数据；
- 所有金额和比例计算使用 Decimal，不使用 float；
- 最终展示统一保留两位小数。

### 8.3 比率与衍生指标强制公式

所有比率和衍生指标必须使用 8.2 中已经 SUM 后的总值重新计算。

| 指标 | 强制公式 | 分母为 0 | 展示 |
|---|---|---|---|
| CTR 点击率 | 总点击 ÷ 总曝光 × 100% | 显示 — | 两位小数 |
| CPC 每次点击费用 | 总花费 ÷ 总点击 | 显示 — | 币种，两位小数 |
| CVR 转化率 | 总订单 ÷ 总点击 × 100% | 显示 — | 两位小数 |
| ACoS 广告销售成本 | 总花费 ÷ 总销售额 × 100% | 显示 — | 两位小数 |
| ROAS 广告支出回报率 | 总销售额 ÷ 总花费 | 显示 — | 两位小数 |
| CPA 每次转化费用 | 总花费 ÷ 总订单 | 显示 — | 币种，两位小数 |
| AOV 平均订单价值 | 总销售额 ÷ 总订单 | 显示 — | 币种，两位小数 |
| ASP 平均售价 | 总销售额 ÷ 总售出件数 | 显示 — | 币种，两位小数 |
| OtherSalesPercent 其他销售占比 | 当前三表缺少 otherSales，暂不计算 | 返回 null | 显示 — |

本项目统一采用截图中建议的零分母规则：

- CTR、CPC、CVR、ACoS、ROAS、CPA、AOV、ASP 的分母为 0 时返回 null，前端显示 —；
- OtherSalesPercent 在字段缺失期间返回 null，并显示 —；
- API 内部比率建议返回十进制比例，例如 CTR 5.00% 返回 0.0500；
- 百分号只在前端展示层添加；
- 后端响应可同时提供 reason=ZERO_DENOMINATOR，便于解释空值。

严禁以下计算：

- 每日 CTR 求平均；
- 每日 CPC 求平均；
- 每日 CVR 求平均；
- 每日 ACoS 求平均；
- 每日 ROAS 求平均；
- 对已有比率字段直接 SUM；
- 使用未汇总的单日比率代替完整日期范围结果。

### 8.4 强制计算示例

假设筛选范围内有两天数据：

| 日期 | 曝光 | 点击 | 花费 | orders | sales |
|---|---:|---:|---:|---:|---:|
| 第一天 | 100 | 5 | 10.00 | 1 | 45.00 |
| 第二天 | 200 | 10 | 20.00 | 2 | 90.00 |

必须先 SUM：

    总曝光 = 100 + 200 = 300
    总点击 = 5 + 10 = 15
    总花费 = 10.00 + 20.00 = 30.00
    总订单 = 1 + 2 = 3
    总销售额 = 45.00 + 90.00 = 135.00

再计算：

    CTR  = 15 ÷ 300 × 100% = 5.00%
    CPC  = 30.00 ÷ 15 = 2.00
    CVR  = 3 ÷ 15 × 100% = 20.00%
    ACoS = 30.00 ÷ 135.00 × 100% = 22.22%
    ROAS = 135.00 ÷ 30.00 = 4.50
    CPA  = 30.00 ÷ 3 = 10.00
    AOV  = 135.00 ÷ 3 = 45.00

该示例必须固化为后端单元测试和前端格式化测试。

### 8.5 格式化

- 金额 API 使用 Decimal 字符串；
- 页面使用 Profile currency；
- 不同 Profile 或币种不合计；
- 金额显示建议保留币种规定的小数位；
- 整数使用千位分隔；
- CTR、ACoS、CVR 显示两位百分比；
- CPC 使用币种格式；
- 日期以 Profile 业务日期展示；
- null 显示 —；
- endDate 为 null 显示“无结束日期”。

### 8.6 待确认指标

以下字段不得在未确认时擅自定义：

- top_of_search_is 的原始单位；
- 首页位置占比跨日聚合；
- SCM 与分析表状态冲突时的最终优先级；
- campaign_daily_budget 的快照语义。

当前三表共同可用口径为 `orders`、`sales`；历史表额外提供 `sales_units`。这些字段的
归因窗口仍未由数据负责人确认，当前实现必须返回
`attributionSemantics=REMOTE_FIELDS_UNVERIFIED`，不得宣称为 7 日归因。

---

## 9. 权限与数据隔离

### 9.1 授权链

~~~mermaid
flowchart TD
    U["登录用户"]
    M["TenantMembership"]
    S["可访问 Store"]
    P["可访问 AdvertisingProfile"]
    X["Profile external_profile_id"]
    R["服务端远程映射"]
    K["mer_id + mer_code"]
    DB["远程只读查询"]

    U --> M --> S --> P --> X --> R --> K --> DB
~~~

### 9.2 前端目录移除与权限的关系

删除横向“卖家空间”等目录导航，不等于删除：

- TenantMembership；
- Store/Profile 范围；
- Profile access level；
- 功能权限；
- X-Tenant-ID；
- 服务端 Profile→Merchant 映射。

这些是后端安全边界，必须保留。

### 9.3 请求约束

前端只允许提供：

- tenantId 路径参数；
- profileId 路径参数；
- 日期；
- 搜索；
- 状态；
- 排序；
- 分页。

前端不得提供：

- mer_id；
- mer_code；
- 数据库 alias；
- 任意表名；
- 任意 SQL 字段；
- 未签名的远程 Campaign Scope。

后端必须重新验证 tenantId/profileId，不信任 Context Store。

### 9.4 HTTP 状态

- 跨 Tenant/Store/Profile：404；
- 当前范围内缺 advertising.view：403；
- 未登录：401；
- 远程映射缺失：503 或受控配置错误；
- 远程数据库不可用：503；
- 无数据：200，items 为空。

---

## 10. 总体架构

~~~mermaid
flowchart LR
    B["Browser"]
    L["Existing AppLayout"]
    C["CampaignSection"]
    A["Axios Client"]
    V["DRF CampaignListView"]
    P["Permission Scope"]
    S["Campaign Selector"]
    R["RemoteCampaignAggregateReader"]
    SCM[("scm_remote")]
    HIS[("history: bi_analyze_ad_campaign")]
    RT[("realtime: bi_analyze_ad_campaign_realtime")]
    SYS[("default")]

    B --> L --> C --> A --> V --> P --> S --> R
    P --> SYS
    R --> SCM
    R --> HIS
    R --> RT
~~~

调用链：

    Vue CampaignSection
    → 功能 API 模块
    → 统一 Axios
    → 现有 Django 认证
    → DRF View
    → Query Serializer
    → Permission Service
    → Selector
    → Remote Reader
     → 三张远程只读表

---

## 11. 前端设计

### 11.1 组件树

~~~text
CampaignSection
├── CampaignFilterChips
├── CampaignToolbar
│   ├── CampaignTitle
│   ├── DisabledCreateCampaignButton
│   ├── CampaignSearchInput
│   ├── CampaignFilterMenu
│   ├── CampaignMetricRuleEditor
│   ├── CampaignDateRangePicker
│   └── CampaignExportButton
├── CampaignTable
│   ├── CampaignTableHeader
│   ├── CampaignTableSkeleton
│   ├── CampaignTableRow（名称 RouterLink + 启停控件）
│   ├── CampaignSummaryRow
│   ├── CampaignEmptyState
│   └── CampaignErrorState
└── CampaignPagination
~~~

### 11.2 建议目录

    frontend/src/features/advertising/
      api/
        campaignApi.ts
      components/
        CampaignSection.vue
        CampaignFilterChips.vue
        CampaignFilterMenu.vue
        CampaignMetricRuleEditor.vue
        CampaignToolbar.vue
        CampaignDateRangePicker.vue
        CampaignTable.vue
        CampaignTableRow.vue
        CampaignSummaryRow.vue
        CampaignPagination.vue
      pages/
        AdvertisingOverviewPage.vue
        CampaignDetailPage.vue
      composables/
        useCampaignList.ts
      types/
        campaign.ts

按需创建，不提前生成空组件。

### 11.3 状态归属

| 状态 | 存放位置 |
|---|---|
| 登录用户 | Auth Store |
| Tenant/Profile | 现有 Tenant Context Store |
| 日期、搜索、状态、指标规则、排序、页码 | URL Query |
| 列表、合计 | 页面 composable |
| Loading/Error/requestId | 页面 composable |
| 导出中 | CampaignSection 局部状态 |
| 行 Hover | CSS |
| 行选择 | 无批量动作时禁用 |
| 启停提交中与错误 | Campaign 行局部状态；成功后重新拉取服务端状态 |
| 远程 Merchant 范围 | 仅后端 |

不建议创建保存服务器 Campaign 事实的长期 Pinia Store。

### 11.4 URL 状态

示例：

    /advertising/overview
      ?startDate=2026-07-04
      &endDate=2026-08-03
      &enabled=true
      &search=
      &filter=impressions:gte:1000
      &filter=acos:lte:0.30
      &ordering=-spend
      &page=1
      &pageSize=15

规则：

- 搜索、筛选、日期、排序变化时 page=1；
- 浏览器刷新后恢复状态；
- 前进/后退恢复列表；
- 不在 URL 中保存 mer_id、mer_code。
- `filter` 可重复出现，但字段和运算符必须来自后端白名单；百分比在 API 中使用十进制比例。
- Campaign 名称跳转到 `/campaigns/{campaignKey}`，详情页重新请求后端，不把列表行存入 sessionStorage 作为权威数据。

### 11.5 请求竞态

- 搜索输入建议 300ms 防抖；
- 使用 AbortController 取消旧请求；
- 使用请求序号丢弃乱序响应；
- 列表刷新时保留旧表并显示轻量加载遮罩；
- 首次加载显示 Skeleton；
- 导出 Loading 与列表 Loading 分离；
- 401 使用现有统一刷新机制。

### 11.6 横向滚动

参考 HTML 的列宽合计约 1894px。

实现要求：

- CampaignTable 外层 overflow-x:auto；
- 不让父级 main-area 溢出；
- 不将宽表撑开整个 AppLayout；
- 表头与数据行使用相同 grid-template-columns；
- 合计行使用相同列模板；
- 手机端保留横向滚动，不隐藏关键列。

---

## 12. 后端设计

### 12.1 复用现有接口

扩展：

    GET /api/v1/advertising/tenants/{tenant_id}/profiles/{profile_id}/campaigns

不新建第二个 Campaign 列表接口。

当前接口响应简单数组。V2 需要扩展为：

    data.items
    data.summary
    data.pagination
    data.meta

该变更会影响：

- backend/apps/advertising/views.py；
- backend/apps/advertising/selectors.py；
- backend/apps/advertising/serializers.py；
- openapi/schema.yaml；
- frontend generated schema；
- 现有后端测试；
- 旧 campaignApi.ts。

### 12.2 请求 Serializer

建议增加 CampaignListQuerySerializer：

| 参数 | 类型 | 默认 | 校验 |
|---|---|---|---|
| startDate | date | 远程最新日往前 30 天 | 与 endDate 成对 |
| endDate | date | 远程最新可用日 | 不早于 startDate |
| enabled | bool | true | 严格布尔 |
| status | enum list | 空 | 白名单 |
| targetingType | enum | 空 | auto/manual |
| search | string | 空 | trim，最长 100 |
| metricFilters | string | 默认无指标规则 | `field:operator:value[:value2]`，多规则以 `;` 分隔，字段唯一且最多 9 条 |
| ordering | string | -spend | 白名单 |
| page | int | 1 | 最小 1 |
| pageSize | int | 15 | 最大 100 |
| includeSummary | bool | true | 严格布尔 |

建议最大日期范围 90 天，最终以真实查询计划为准。

### 12.3 排序白名单

    name
    targetingType
    status
    biddingStrategy
    startDate
    endDate
    dailyBudget
    impressions
    spend
    clicks
    ctr
    totalCost
    orders
    cpc
    acos
    cvr

首页位置占比口径未确认前不开放排序。

### 12.4 查询流程

~~~mermaid
flowchart TD
    A["GET Campaigns"]
    B["Query Serializer"]
    C["require_profile_scope"]
    D["Profile→mer_id+mer_code"]
    E["历史/实时分别规范化和表内去重"]
    F["实时优先覆盖同原子粒度历史"]
    G["Campaign 聚合"]
    H["SCM 全量候选键并集与当前元数据覆盖"]
    I["状态/搜索/聚合指标白名单筛选"]
    J["排序分页 + 确定性比率 + 全筛选 Summary"]
    K["返回 items + summary + pagination + freshness meta"]

    A --> B --> C --> D --> E --> F --> G --> H --> I --> J --> K
~~~

### 12.5 数据拼接

推荐：

1. 历史表和实时表分别在 `ads_analysis_remote` 内规范化并按候选原子粒度去重；
2. 合并两表，实时记录覆盖同一原子粒度的历史记录；
3. 按 Campaign 聚合绝对值并重新计算比率；
4. 批量读取 SCM 候选键，与事实 Campaign 键取并集并补充当前元数据；
5. 对合并结果应用状态/指标筛选，完成 count、排序和服务端分页；
6. 单独以完全相同的三表合成和筛选条件计算 Summary；
7. KPI、趋势、风险、导出和详情调用相同聚合服务，不各写一套 SQL。

禁止对每一行单独查询 SCM，避免 N+1；禁止历史与实时直接 `UNION ALL` 后求和。

---

## 13. API 契约

### 13.1 请求

    GET /api/v1/advertising/tenants/{tenant_id}/profiles/{profile_id}/campaigns
        ?startDate=2026-07-04
        &endDate=2026-08-03
        &enabled=true
        &search=
        &metricFilters=impressions:gte:1000;acos:lte:0.30
        &ordering=-spend
        &page=1
        &pageSize=15

权限：

- IsAuthenticated；
- 有效 TenantMembership；
- advertising.view；
- Profile access level 至少 VIEW；
- Store/Profile 数据范围校验。

详情读取：

    GET /api/v1/advertising/tenants/{tenant_id}/profiles/{profile_id}/campaigns/{campaign_key}

详情响应复用列表聚合口径，并额外返回按业务日趋势和当前 SCM 元数据。服务端必须在当前
授权范围内解析 `campaignKey`；不能信任前端传入 `campaignId`、`mer_id` 或 `mer_code`。

### 13.2 成功响应示例

示例为虚构数据：

~~~json
{
  "code": "SUCCESS",
  "message": "操作成功",
  "requestId": "req_demo_campaign_001",
  "data": {
    "items": [
      {
        "campaignKey": "cmp_demo_001",
        "name": "演示广告活动",
        "referenceCode": "DEMO-CAMPAIGN-001",
        "enabled": true,
        "targetingType": "AUTO",
        "status": "DELIVERING",
        "biddingStrategy": "FIXED_BIDS",
        "startDate": "2026-07-16",
        "endDate": null,
        "dailyBudget": {
          "amount": "10.00",
          "currencyCode": "USD"
        },
        "metrics": {
          "impressions": 1234,
          "topOfSearchShare": null,
          "spend": {
            "amount": "42.31000",
            "currencyCode": "USD"
          },
          "clicks": 23,
          "ctr": "0.018638",
          "totalCost": {
            "amount": "42.31000",
            "currencyCode": "USD"
          },
          "orders": 2,
          "cpc": {
            "amount": "1.83957",
            "currencyCode": "USD"
          },
          "acos": "0.211550",
          "cvr": "0.086957"
        },
        "hasMetrics": true,
        "metadataMatched": true,
        "partialFields": ["topOfSearchShare"]
      }
    ],
    "summary": {
      "impressions": 1234,
      "spend": {
        "amount": "42.31000",
        "currencyCode": "USD"
      },
      "clicks": 23,
      "ctr": "0.018638",
      "totalCost": {
        "amount": "42.31000",
        "currencyCode": "USD"
      },
      "orders": 2,
      "cpc": {
        "amount": "1.83957",
        "currencyCode": "USD"
      },
      "acos": "0.211550",
      "cvr": "0.086957",
      "topOfSearchShare": null
    },
    "pagination": {
      "page": 1,
      "pageSize": 15,
      "total": 1,
      "totalPages": 1
    },
    "meta": {
      "source": "REMOTE_MYSQL_COMPOSITE",
      "currencyCode": "USD",
      "timezone": "America/Los_Angeles",
      "startDate": "2026-07-04",
      "endDate": "2026-08-03",
      "dataThroughDate": "2026-08-03",
      "historyThroughDate": "2026-08-03",
      "realtimeThroughDate": "2026-08-03",
      "realtimeAsOf": "2026-08-03T15:30:00+08:00",
      "deduplicationVersion": "campaign-code-product-asin-realtime-v1",
      "fieldMappings": {
        "historicalImpressions": "imperssion",
        "realtimeImpressions": "impression",
        "campaignJoinKey": "campaign_code->code"
      },
      "attributionSemantics": "REMOTE_FIELDS_UNVERIFIED",
      "totalCostSemantics": "SPEND_ALIAS"
    }
  }
}
~~~

### 13.3 空数据

远程查询成功且无记录：

~~~json
{
  "code": "SUCCESS",
  "message": "操作成功",
  "requestId": "req_demo_empty_001",
  "data": {
    "items": [],
    "summary": null,
    "pagination": {
      "page": 1,
      "pageSize": 15,
      "total": 0,
      "totalPages": 0
    },
    "meta": {
      "source": "REMOTE_MYSQL_COMPOSITE",
      "currencyCode": "USD",
      "timezone": "America/Los_Angeles"
    }
  }
}
~~~

页面显示：

    暂无数据

### 13.4 错误码

| HTTP | Code | 场景 |
|---:|---|---|
| 400 | INVALID_QUERY_PARAMETER | 参数格式错误 |
| 400 | INVALID_DATE_RANGE | 日期范围错误 |
| 400 | PAGE_OUT_OF_RANGE | 页码越界 |
| 401 | AUTHENTICATION_REQUIRED | 登录过期 |
| 403 | PERMISSION_DENIED | 范围内缺权限 |
| 404 | RESOURCE_NOT_FOUND | 越出 Tenant/Profile |
| 422 | EXPORT_TOO_LARGE | 导出超过上限 |
| 503 | REMOTE_PROFILE_MAPPING_MISSING | Profile 映射缺失 |
| 503 | REMOTE_DATA_UNAVAILABLE | 远程数据库不可用 |

---

## 14. 搜索、筛选与分页

### 14.1 搜索

搜索字段：

- SCM Campaign name；
- SCM Campaign code；
- 分析表 campaign_name；
- 分析表 campaign_code。

要求：

- 参数化查询；
- 转义百分号和下划线等 LIKE 特殊字符；
- 最长 100 字符；
- 前端 300ms 防抖；
- 搜索变化后 page=1。

### 14.2 状态

远程可能状态：

- enabled；
- paused；
- archived；
- applying；
- nothing；
- refuse；
- ended。

统一页面状态建议：

| 远程值 | 页面值 |
|---|---|
| enabled | 正在投放 |
| paused | 已暂停 |
| archived | 已归档 |
| ended | 已结束 |
| applying | 审核中 |
| refuse | 已拒绝 |
| nothing | 未知/未开始 |

状态冲突时 SCM 当前状态优先，具体规则需写入决策日志。

截图中的筛选图标不是普通“展开表单”按钮，而是分层菜单。一级菜单固定为：

1. 状态；
2. 展示量；
3. 点击量；
4. 花费；
5. 购买量；
6. 单次点击成本；
7. 广告销售成本比；
8. 点击率；
9. 转化率。

数值规则映射：

| 页面项 | API 字段 | 聚合阶段 |
|---|---|---|
| 展示量 | impressions | SUM 后 HAVING |
| 点击量 | clicks | SUM 后 HAVING |
| 花费 | spend | SUM 后 HAVING |
| 购买量 | orders | SUM 后 HAVING |
| 单次点击成本 | cpc | SUM 后重算，再 HAVING |
| 广告销售成本比 | acos | SUM 后重算，再 HAVING |
| 点击率 | ctr | SUM 后重算，再 HAVING |
| 转化率 | cvr | SUM 后重算，再 HAVING |

筛选标签必须显示可读规则，例如“展示量 ≥ 1,000”“ACoS 10%—30%”；删除标签后
重新请求服务端并回到第 1 页。所有规则同时应用于列表、合计、KPI、趋势、风险和导出。

### 14.3 日期

- 日期首尾均包含；
- 日期按钮可点击，弹层包含最近 7 天、最近 14 天、最近 30 天以及自定义起止日期；
- 自定义日期仅在点击“应用”且校验通过后请求；
- 页面显示 Profile 业务日期；
- 默认范围以历史表和实时表的最大可用业务日为终点；
- 浏览器日期不直接决定数据时区；
- 远程 creation_date 时区未确认前禁止自动按 UTC 转换。

### 14.4 分页

- 服务端分页；
- 默认 15；
- 最大 100；
- count 使用相同筛选；
- 页码越界不静默返回错误数据；
- 合计不受分页影响。

---

## 15. 合计设计

合计行计算范围：

    当前 Profile
    + 当前日期
    + 当前状态
    + 当前关键词
    + 当前高级筛选
    + 全部匹配 Campaign

合计不包含：

- 当前页限制；
- 用户未授权 Profile；
- 不同币种；
- HTML Mock 数据。

聚合公式：

    totalCtr  = totalClicks / totalImpressions
    totalCpc  = totalSpend / totalClicks
    totalAcos = totalSpend / totalSales
    totalCvr  = totalOrders / totalClicks

其中：

    totalOrders    = SUM(deduplicated.orders)
    totalSales     = SUM(deduplicated.sales)
    totalSaleUnits = SUM(deduplicated.history.sales_units)  # 仅覆盖完整时
    totalOtherSales = null  # 当前三表无此字段

其他衍生指标：

    totalRoas = totalSales / totalSpend
    totalCpa = totalSpend / totalOrders
    totalAov = totalSales / totalOrders
    totalAsp = totalSales / totalSaleUnits
    totalOtherSalesPercent = null

不能对每行百分比做算术平均。

---

## 16. 导出设计

接口建议：

    GET /api/v1/advertising/tenants/{tenant_id}/profiles/{profile_id}/campaigns/export

规则：

- 使用与列表一致的筛选；
- 忽略分页；
- CSV UTF-8 BOM；
- 建议同步最大 10,000 行；
- 超限返回 EXPORT_TOO_LARGE；
- 不静默截断；
- Content-Disposition 使用安全文件名；
- Cache-Control: no-store；
- 防止 CSV 公式注入；
- 不导出 mer_id、mer_code、内部 Tenant ID；
- 不在 MySQL 保存 CSV 正文；
- 导出审计写 default；
- 远程数据库仍然只读。

导出按钮状态：

- 默认可用；
- 导出中禁用；
- 失败后恢复；
- 显示 requestId；
- 无数据时禁用或返回空文件需产品确认。

---

## 17. 写操作边界与 Campaign 启停

产品目标已经调整为“启用开关可点击并能真实开启/关闭 Campaign”。这是一项真实写操作，
不能通过修改 Vue 内存、写本地 shadow 状态或更新远程数据库来伪造。

当前约束存在明确冲突：

- D-154 要求 `scm_remote` 与 `ads_analysis_remote` 只读；
- 主规格禁止 V1 真实调用 Amazon Ads API 或自动修改广告；
- 当前仓库没有已授权、可验证的 Campaign 状态写 Provider。

因此当前实现状态必须是：开关展示远程真实状态，但 `disabled`，并通过 tooltip 说明
“尚未配置广告状态写通道”。只有项目发起人单独批准写通道、凭据管理、权限、幂等、
审计和回滚方案后，才能启用以下契约：

    POST /api/v1/advertising/tenants/{tenant_id}/profiles/{profile_id}/campaigns/{campaign_key}/state

~~~json
{
  "targetState": "ENABLED",
  "expectedCurrentState": "PAUSED",
  "idempotencyKey": "uuid"
}
~~~

后端处理顺序固定为：认证 → TenantMembership → `advertising.operate` → Profile 至少
`OPERATE` → Campaign 归属 → 当前状态漂移检查 → 幂等检查 → 受控
`CampaignStateProvider` → ExecutionRecord/AuditLog 同事务记录 → 重新读取远程状态。

前端行为：点击后弹出确认；行开关进入提交中；成功后重新请求服务端；Provider 未确认或
超时则恢复原状态并显示 requestId；不得只凭 HTTP 202/前端局部值显示最终成功。

其他控件：

| 控件 | 当前行为 |
|---|---|
| 创建广告活动 | disabled |
| 启用开关 | 写通道未授权前 disabled；授权后按上述契约真实执行 |
| 行复选框 | 无批量动作时 disabled |
| 修改预算 | 不提供 |
| 修改竞价 | 不提供 |
| 批量操作 | 不提供 |

始终禁止：

- 点击后显示伪成功；
- 修改本地状态假装远程成功；
- `UPDATE scm_remote`；
- `UPDATE ads_analysis_remote`；
- 调用未确认的 Amazon Ads API；
- 在浏览器直接修改远程数据库。

授权后的写操作架构：

~~~mermaid
flowchart LR
    UI["浏览器写操作"]
    API["Django Write API"]
    P["权限 + Scope"]
    I["幂等"]
    A["审批 + 审计"]
    T["Celery Task"]
    AZ["Authorized Amazon Ads API"]
    R["ExecutionRecord"]

    UI --> API --> P --> I --> A --> T --> AZ --> R
~~~

---

## 18. 页面状态

| 状态 | 展示 |
|---|---|
| 首次加载 | 10 行 Skeleton，保持表头和列宽 |
| 刷新中 | 保留旧数据，显示遮罩 |
| 无数据 | 表体居中“暂无数据” |
| API 失败 | 错误说明、重试、requestId |
| 401 | 统一刷新一次，失败回登录 |
| 403 | 无权限状态，不显示旧数据 |
| 404 | 通用不存在，不泄露 Profile |
| 远程映射缺失 | 配置错误，不显示暂无数据 |
| 远程库不可用 | 503 错误，不回退本地数据 |
| 局部字段缺失 | 单格显示 — |
| 日期非法 | 控件内联错误 |
| 分页越界 | 自动回最后页一次或显示受控错误 |
| 导出中 | 导出按钮 Loading |
| 导出失败 | 错误提示和 requestId |
| 实时数据较旧 | 显示数据截至时间，不冒充实时 |
| 启停写通道未配置 | 开关禁用并给出原因 |
| 启停提交失败 | 回滚开关、保留原状态、显示 requestId |

---

## 19. 性能设计

### 19.1 当前表规模

information_schema 近似规模：

| 表 | 近似行数 |
|---|---:|
| scm_remote.eb_ad_campaign | 约 4.1 万 |
| ads_analysis_remote.bi_analyze_ad_campaign | 约 25.6 万（旧记录，需重新核验） |
| ads_analysis_remote.bi_analyze_ad_campaign_realtime | DDL AUTO_INCREMENT 已达约 1.7 亿量级，实际行数需 `information_schema`/DBA 核验 |

这是元数据估算，不是性能承诺。

### 19.2 SQL

当前远程 Reader 只查历史表且使用 `DATE(creation_date)` 过滤，既漏掉实时表，也可能影响索引使用。

建议：

    creation_date >= :start_datetime
    AND creation_date < :end_next_day_datetime

但必须先确认远程时间语义。

### 19.3 索引

建议 DBA 基于 EXPLAIN 评估：

    history:  (mer_id, mer_code, creation_date, campaign_code, product_id, asin)
    realtime: (mer_id, mer_code, creation_date, campaign_code, product_id, asin, update_time)

本项目不能在远程只读库自行创建索引。

### 19.4 查询控制

- 最大日期范围建议 90 天；
- 默认 pageSize 15；
- 最大 pageSize 100；
- SCM 元数据一次批量查询；
- 禁止 N+1；
- 合计使用数据库聚合；
- 不把全部结果拉到前端分页；
- 导出限制行数；
- 行详情延迟加载。
- 必须分别对历史去重、实时去重、合并覆盖、聚合筛选、summary 和详情执行 `EXPLAIN`；
- 实时表不得先全量拉到 Python 再去重；窗口函数/分组必须在远程数据库完成；
- 若现有索引不足，只能提交 DBA 索引建议，应用不得自行修改远程表。

### 19.5 缓存

首期建议不做跨请求缓存，先取得真实性能基线。

如后续增加缓存，Key 必须包含：

- tenantId；
- profileId；
- 服务端远程映射版本；
- 日期；
- 搜索；
- 全部筛选；
- 排序；
- 页码；
- pageSize；
- 数据水位；
- Schema 版本。

---

## 20. 安全设计

1. 前端不连接数据库；
2. 远程数据库只读；
3. 不在远程库执行 migrate；
4. 数据库 alias 由服务端固定；
5. SQL 使用参数绑定；
6. 排序字段使用白名单；
7. 不记录数据库密码；
8. 不记录 Token、Cookie、Authorization Header；
9. 不记录完整商户映射；
10. 越权 Profile 返回 404；
11. 范围内缺权限返回 403；
12. 导出重新授权；
13. 导出文件防 CSV 公式注入；
14. 错误不泄露 SQL、表名和主机；
15. 不以删除横向导航替代后端授权；
16. 不使用目标 HTML 中的真实或私有记录；
17. 日志中的 merchant 标识应脱敏。

---

## 21. 测试方案

### 21.1 前端

- CampaignSection 挂载；
- 工具栏布局；
- 19 列顺序；
- 横向滚动；
- 名称与辅助代码；
- 搜索防抖；
- 筛选标签显示/隐藏；
- 删除单个筛选；
- 删除全部筛选；
- 日期快捷范围；
- 自定义日期应用与校验；
- 截图同款 9 项分层筛选菜单；
- 指标运算符和值编辑；
- 日期非法；
- 排序；
- 分页；
- 合计行；
- Loading；
- 暂无数据；
- API 失败；
- 401；
- 403；
- 局部缺失；
- 导出中和失败；
- 创建按钮 disabled；
- 名称 RouterLink 与详情刷新；
- 开关未授权禁用、授权后提交/回滚状态；
- 横向目录导航已移除；
- 顶部栏和左侧栏未回归。

### 21.2 后端

- Query Serializer；
- 日期范围；
- 搜索长度和特殊字符；
- 排序白名单；
- page/pageSize；
- Tenant 隔离；
- Store/Profile 越权；
- advertising.view；
- Profile access level；
- Profile→mer_id+mer_code；
- 固定 remote alias；
- 参数化 SQL；
- 历史表字段映射 `imperssion -> impressions`；
- 实时表字段映射 `impression -> impressions`；
- 历史/实时表内去重；
- 同原子粒度实时覆盖历史；
- 不同 `type` 不混算；
- 禁止直接 `UNION ALL + SUM`；
- SCM 批量查询；
- 聚合公式；
- `orders`、`sales` 和仅历史 `sales_units` 字段映射；
- 先 SUM 后计算比率；
- 强制计算示例结果；
- 禁止每日比率平均；
- 零分母；
- Summary 不受分页；
- 空结果；
- 局部元数据缺失；
- 远程异常；
- 导出权限；
- CSV 注入；
- 查询次数；
- 远程只读约束。
- 详情接口重新授权；
- 启停接口在 Feature Flag 关闭时不可用；
- 若写通道获批：权限、幂等、漂移、Provider 失败、审计和回读测试。

### 21.3 契约

- OpenAPI 校验；
- TypeScript 类型生成；
- 生成差异检查；
- 现有 Campaign API 调用方回归；
- 错误包络；
- Decimal 字符串；
- camelCase 响应。

---

## 22. 视觉验收

主要参考截图视口：

    1643 × 685

| 项目 | 验收要求 |
|---|---|
| 工具栏高度 | 目标约 52px，误差不超过 2px |
| 表头高度 | 目标约 40px，误差不超过 2px |
| 数据行高 | 目标约 50px，误差不超过 2px |
| 列数量 | 19 列全部存在 |
| 名称列 | 名称和辅助代码两行 |
| 状态标签 | 颜色、尺寸和圆角接近截图 |
| 开关 | 约 34×18px |
| 搜索框 | placeholder、宽度、图标和边框与截图一致 |
| 筛选按钮 | 方形图标按钮，不显示大号“筛选”文字按钮 |
| 筛选菜单 | 9 项顺序、约 178px 宽、锚点、阴影和行距与 631×675 局部截图一致 |
| 日期选择 | 工具栏右侧按钮可打开 7/14/30 天和自定义范围 |
| 名称链接 | 蓝色、两行布局、点击进入真实详情 |
| 横向滚动 | 最右 ACoS/CVR 可访问 |
| 合计 | 与所有筛选结果一致 |
| 数字对齐 | 数字和金额右对齐 |
| Hover | 浅灰背景 |
| 空数据 | 明确显示“暂无数据” |
| 外壳回归 | 顶部栏和左侧栏不变 |
| 导航移除 | 横向目录不再占用页面空间 |

必须截图回归的视口/裁剪：

- 1643×685（本次主参考）；
- 631×675（筛选菜单局部）；
- 1865×650（旧参考回归）；
- 1440×900。

---

## 23. 联调验收矩阵

| 场景 | 操作 | 预期请求 | 预期结果 |
|---|---|---|---|
| 进入页面 | 打开广告总览 | GET campaigns | Skeleton 后显示远程数据 |
| 无数据 | 选择无记录日期 | GET campaigns | 暂无数据 |
| 搜索 | 输入名称 | search + page=1 | 结果和合计更新 |
| 状态筛选 | 选择状态 | status + page=1 | 仅显示匹配状态 |
| 清除筛选 | 删除标签 | 更新 Query | 列表恢复 |
| 日期 | 最近 30 天 | start/end | 重新查询 |
| 排序 | 点击表头 | ordering | 服务端排序 |
| 翻页 | 下一页 | page+1 | 合计保持 |
| 导出 | 点击导出 | GET export | 下载 CSV |
| 登录过期 | Access 过期 | refresh 一次 | 恢复或回登录 |
| 越权 | 修改 profileId | GET | 404 |
| 缺权限 | 无 advertising.view | GET | 403 |
| 远程异常 | 模拟连接失败 | GET | 503，不显示暂无数据 |
| 部分缺失 | SCM 不匹配 | GET | 缺失字段 — |
| 写控件 | 点击创建/开关 | 不发写请求 | 保持禁用 |
| 名称跳转 | 点击活动名称 | GET campaign detail | 进入真实详情，不依赖列表缓存 |
| 指标筛选 | 点击 `⊟` 并选择指标规则 | GET campaigns + repeated filter | 列表、合计和标签同步更新 |
| 启停（未授权） | 点击/聚焦开关 | 不发请求 | 明确提示写通道未配置 |
| 启停（获批后） | 确认目标状态 | POST campaign state | 成功回读；失败回滚并显示 requestId |

---

## 24. 实施任务拆解

| 编号 | 任务 | 涉及文件 | 前置依赖 | 产出 | 复杂度 |
|---|---|---|---|---|---|
| C2-01 | 确认 Campaign 键 | 决策日志 | 数据负责人 | 唯一键规则 | M |
| C2-02 | 核验三表粒度、`type`、时间和重复度 | 决策日志/只读 SQL 证据 | 远程库 | 指标与去重字典 | XL |
| C2-03 | 移除横向目录导航 | AppLayout.vue、样式、测试 | 产品确认 | 新主框架 | S |
| C2-04 | 定义列表 OpenAPI | schema、Serializer | C2-01/02 | API 契约 | M |
| C2-05 | 扩展三表聚合 Reader | remote_databases.py | C2-02/SQL 评审 | 历史+实时去重覆盖查询 | XL |
| C2-06 | 权限与 Profile Scope | permission service、selector | 远程映射 | 安全范围 | M |
| C2-07 | 列表 Selector | advertising selectors | C2-05/06 | items | L |
| C2-08 | Summary 聚合 | selector/repository | 指标口径 | summary | L |
| C2-09 | 扩展 Campaign View | views/serializers | C2-04/07 | GET API | M |
| C2-10 | CampaignSection 容器 | Vue 页面和组件 | 页面集成点 | 模块框架 | M |
| C2-11 | 截图同款工具栏 | CampaignToolbar | API 参数 | 搜索、图标筛选、日期、导出 | M |
| C2-12 | 分层筛选与标签 | FilterMenu/RuleEditor/Chips | URL 状态 | 9 项筛选 UI | L |
| C2-13 | 日期选择器 | DateRangePicker | 时区口径 | 日期 UI | M |
| C2-14 | 19 列表格 | CampaignTable | 响应契约 | 宽表 | L |
| C2-15 | 合计和分页 | Summary/Pagination | API | 完整底部 | M |
| C2-16 | 页面状态 | Empty/Error/Skeleton | 错误码 | 全状态 | M |
| C2-17 | 只读导出 | export API/client | 权限和上限 | CSV | L |
| C2-18 | OpenAPI 类型生成 | generated schema | API 完成 | TS 类型 | S |
| C2-19 | 前端测试 | specs | UI 完成 | 自动化测试 | L |
| C2-20 | 后端测试 | backend tests | API 完成 | 隔离/聚合测试 | XL |
| C2-21 | 视觉回归 | 截图测试 | UI 完成 | 三视口基线 | M |
| C2-22 | 外壳回归 | AppLayout tests | C2-03 | 顶部/侧栏不变 | M |
| C2-23 | 性能验证 | EXPLAIN 文档 | 查询完成 | 查询基线 | L |
| C2-24 | 文档同步 | 模块文档、决策日志 | 全部完成 | 最终文档 | M |
| C2-25 | Campaign 详情链路 | detail API/route/page | C2-05/06 | 名称可点击跳转 | L |
| C2-26 | Campaign 启停链路 | Provider/Service/API/UI | 单独写授权 | 真实启停与审计 | XL/阻塞 |

复杂度仅使用 S/M/L/XL，不代表具体人天。

---

## 25. 风险与待确认

| 事项 | 当前状态 | 影响 | 阻塞级别 |
|---|---|---|---|
| W0765 默认 Profile | 运行记录未验证 | 无 Profile 时无法加载真实数据 | 高 |
| Campaign 连接键 | 已确认使用 `campaign_code -> SCM.code`；签名 campaignKey 绑定 Profile 远程范围 | 去重和详情跳转 | 已控制 |
| Marketplace 远程隔离键 | 未确认 | 可能混合站点 | 高 |
| top_of_search_is 口径 | 未确认 | 该列暂时显示 — | 高 |
| 7 日归因字段实际可用性 | 2026-08-04 已验证为缺失；只有未确认归因语义的 `orders`/`sales` 及 1 日字段 | 订单、销售额、售出件数和衍生指标；当前 API 显式标记未验证 | 高 |
| 历史/实时原子粒度 | 已用真实重复度查询确认并通过窗口函数处理表内重复 | 错误粒度会重复或漏算 | 已控制；真实样例语义仍需持续验证 |
| `type` 字段 | 已确认不是统计窗口；历史 NULL、实时为 SP-Auto/SP-Manual | 错误按窗口过滤会漏数 | 已纠正 |
| 实时快照完整性与更新频率 | 未确认 | 最新日可能不完整或重复 | 高 |
| 历史/实时日期重叠 | 已核验存在 50 个重叠业务日，并实现同粒度实时覆盖 | 直接相加会重复计数 | 已控制 |
| 远程 creation_date 时区 | 未确认 | 日期边界 | 高 |
| SCM/分析状态优先级 | 已确认 SCM 当前状态优先，事实状态回退 | 启用和状态展示 | 已控制 |
| 无指标 Campaign 是否显示 | 已确认显示，指标为 null/`—`，返回 `hasMetrics=false` | 主集合选择 | 已控制 |
| 导出独立权限 | 当前未定义 | 是否新增 migration | 中 |
| 导出上限 | 建议 10,000 | 超限处理 | 中 |
| 横向导航移除后的旧页面入口 | 未确认 | 旧功能可发现性 | 中 |
| 远程复合索引 | 未发现 | 搜索和日期查询性能 | 中 |
| Campaign 启停写 Provider | 当前无授权且与只读/V1 边界冲突 | 开关不能真实可用 | 阻塞 |

---

## 26. 文件影响清单

### 26.1 预计修改

    frontend/src/shared/layouts/AppLayout.vue
    frontend/src/shared/styles/base.css
    frontend/src/features/advertising/pages/AdvertisingOverviewPage.vue
    frontend/src/features/advertising/api/campaignApi.ts
    frontend/src/shared/api/generated/schema.d.ts
    backend/apps/advertising/views.py
    backend/apps/advertising/selectors.py
    backend/apps/advertising/serializers.py
    backend/integrations/advertising_data/remote_databases.py
    openapi/schema.yaml
    backend/tests/test_report_imports.py

### 26.2 预计新增

    frontend/src/features/advertising/components/CampaignSection.vue
    frontend/src/features/advertising/components/CampaignToolbar.vue
    frontend/src/features/advertising/components/CampaignFilterChips.vue
    frontend/src/features/advertising/components/CampaignDateRangePicker.vue
    frontend/src/features/advertising/components/CampaignTable.vue
    frontend/src/features/advertising/components/CampaignTableRow.vue
    frontend/src/features/advertising/components/CampaignSummaryRow.vue
    frontend/src/features/advertising/components/CampaignPagination.vue
    frontend/src/features/advertising/composables/useCampaignList.ts
    frontend/src/features/advertising/types/campaign.ts

具体文件按纵向链路需要创建，不提前生成空壳。

---

## 27. 实施顺序

1. 先只读核验三表的 Campaign 键、原子粒度、`type`、日期重叠、快照频率、Marketplace 隔离和时区；
2. 扩展现有 Campaign API 为历史+实时去重覆盖的统一聚合；
3. 完成远程分页、指标筛选、合计和权限测试；
4. 生成 OpenAPI TypeScript 类型；
5. 创建/修正 CampaignSection；
6. 完成截图同款工具栏、分层筛选、日期、表格、合计、分页；
7. 接入 Loading、暂无数据和错误状态；
8. 接入 Campaign 详情跳转与只读导出；
9. 移除横向目录导航；
10. 运行前端、后端、OpenAPI 和视觉回归；
11. 确认顶部栏、左侧栏无回归；
12. 更新决策日志和模块文档；
13. Campaign 启停作为独立门禁：只有写 Provider 获得明确授权后实施并验证，否则保持禁用。

不得先使用静态数组把页面做成“看起来完成”，再延后数据接入。首个实现必须是可测试的远程只读纵向链路。

---

## 28. 结论摘要

1. 顶部栏保留；
2. 左侧栏保留；
3. 工作台、卖家空间、广告总览等横向目录导航整体移除；
4. 本任务聚焦 HTML 最底部的 CampaignSection，并包含其详情入口；
5. CampaignSection 包括截图同款工具栏、日期、搜索、9 项分层筛选、19 列表格、合计、分页和导出；
6. 初始显示“进行中”和“已启用”筛选标签；
7. 表格采用高密度宽表和横向滚动；
8. Campaign 当前元数据来自 `scm_remote.eb_ad_campaign`；
9. Campaign 指标由 `bi_analyze_ad_campaign` 历史事实和 `bi_analyze_ad_campaign_realtime` 实时事实去重覆盖后聚合；
10. 不使用 HTML Mock 数据或本地静态数组；
11. 无远程数据时显示“暂无数据”；
12. 远程错误不能伪装成暂无数据；
13. Tenant、Store、Profile 权限隔离仍然保留；
14. Campaign 名称必须跳转到真实详情页；
15. Campaign 启停是已提出的真实业务目标，但在只读远程库和 V1 禁止真实 Amazon 写入的现状下处于阻塞；未授权前必须禁用，不能伪造；
16. `orders_7d`、`sales_7d`、`sale_units_7d`、`other_sales_7d` 在当前 Schema 中不存在；当前订单/销售及衍生指标必须保持“远程字段语义未验证”标记；Marketplace 隔离键、时区和首页位置占比仍是待确认项，原子粒度与 `type` 假设已由真实只读核验纠正。

---

## 29. 2026-08-04 实施快照

> 修订注：本节仅记录本轮实现前的历史快照。该快照时点仍只查询
> `bi_analyze_ad_campaign`；本轮完成状态以第 30 节和实际 OpenAPI 契约为准。

- 开发前 Git 快照：`bdb553c`，标签 `checkpoint-before-campaign-section-20260804`；
- CampaignSection 已接入现有 AppLayout 下的 `/advertising/overview`；
- 已按本方案移除 AppLayout 的旧横向业务导航，保留顶部栏、面包屑和左侧广告入口；
- 页面显式携带筛选、排序和分页参数，不使用 HTML Mock 数据，不回退本地 `ads_campaign`；
- 远程只读试查结果：W0765 最近 30 天全状态 156 个 Campaign；页面默认“已启用”范围 68 个，首页 15 条、Summary/30 天趋势/风险统计可用；该结果是 2026-08-04 运行验证记录，不是性能承诺；
- 已实现 19 列宽表、横向滚动、工具栏、筛选标签、日期、服务端排序/分页/合计、状态页和只读 CSV 导出审计；
- “创建广告活动”、行选择和启停开关保持禁用/只读；
- 2026-08-04 已使用项目 Playwright 实际渲染桌面参考 `index.html` 并生成 1280px 整页截图，确认页面结构为搜索栏、8 个 KPI、表现概览、风险评估、筛选条和底部 CampaignSection；随后项目发起人明确授权扩展为完整页面。
- 完整页面的 KPI、每日趋势、五档风险与 CampaignSection 使用同一远程只读筛选范围；没有引入 HTML Mock 数据。
- 已增加 `ads_profile_remote_scope` 显式映射及 `sync_remote_account_context` 管理命令；W0765 的认证身份已绑定到远程 merchant code `W0765`，账号具体业务数据不写入代码。
- 五档风险复用现有异常规则和 Profile→Tenant 目标 ACoS；缺少小时级预算快照的预算提前耗尽规则在 API 中显式列为不可用。
- 2026-08-04 浏览器真实验收通过：`/advertising/overview` 返回 8 个 KPI、30 天趋势、风险计数和当前页 15 条远程 Campaign，无页面告警；截图为 `w0765-remote-dashboard.png`。

## 30. 本轮实现状态（2026-08-04）

| 项目 | 当前代码 | 本次目标 | 状态 |
|---|---|---|---|
| 数据源 | 历史 + 实时 + SCM 三表复合 Reader | 历史 + 实时 + SCM 三表 | 已实现并真实只读试查 |
| 历史/实时去重 | 表内窗口去重 + 同粒度实时覆盖历史 | 表内最新快照 + 实时覆盖同原子粒度历史 | 已实现并有算法测试 |
| `type` 语义 | 真实数据证明不是统计窗口 | 不按窗口筛选，投放类型受控规范化 | 已纠正 |
| 日期 | 截图同款按钮、7/14/30 天、自定义应用 | 同左 | 已实现 |
| 搜索 | 已有，300ms 服务端搜索 | 保留并匹配截图 | 已有功能，视觉待修 |
| 指标筛选 | 9 项分层菜单 + 聚合后白名单规则 + chips | 同左 | 已实现 |
| 活动名称 | RouterLink 到签名 campaignKey 的真实详情 API | 同左 | 已实现 |
| 启停 | `aria-readonly` 展示 | 真实 Provider 写入；未授权前禁用并解释 | 阻塞 |
| 视觉 | 高密度 19 列表格、蓝色筛选 chips、弹出菜单、日期按钮已对齐参考 | 三视口截图回归 | 浏览器视觉复核待本轮执行 |

启停仍是唯一明确功能阻塞：远程连接保持只读，且主规格禁止 V1 直接调用真实 Amazon Ads API；在 D-180 所列 Provider、权限、幂等、漂移、审计和回读机制获批前，前端开关保持禁用并说明原因。

## 31. 2026-08-05 复核与交互修订

- 通过全容器模式重新构建并启动 MySQL、Redis、Django、Celery、Vue 和 Nginx；live/ready 健康检查均返回 `SUCCESS`，数据库无待执行迁移；
- W0765 已授权 Profile 的远程三表 Reader 在当前最近可用 30 天返回 172 个已启用 Campaign，第一页 15 条；历史水位为 2025-12-28，实时水位为 2026-07-17。本条是当次只读运行证据，不是固定数据量或性能承诺；
- 同一范围通过 TenantMembership/Profile 权限 Selector 和 DRF Campaign API 复核：HTTP 200、`code=SUCCESS`、`source=REMOTE_MYSQL_COMPOSITE`、15 个当前页 items、172 个总数，未回退本地 `ads_campaign`；
- 9 个一级筛选项改为统一模态框编辑；已有指标规则可重新编辑，多指标规则以 `;` 分隔并存，比例值显示为百分比但按小数契约发送；
- 强制两日计算示例已固化为后端测试：先得到 300 impressions、15 clicks、30.00 spend、3 orders、135.00 sales，再计算 CTR 5%、CPC 2.00、CVR 20%、ACoS 22.22%、ROAS 4.50；
- 本轮浏览器控制会话初始化失败，因此没有把单元测试或 API 证据描述为新的浏览器视觉回归；截图级视觉验收仍需在可用浏览器控制会话中补跑；
- 创建 Campaign 和真实启停仍受 D-180 阻塞，未启用本地假状态、远程 SQL 写入或未授权 Amazon Ads 调用。
