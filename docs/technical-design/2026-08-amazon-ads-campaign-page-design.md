# Amazon 广告活动列表页复刻与数据接入技术方案

> 文档状态：评审稿  
> 编制日期：2026-08-03  
> 适用系统：Amazon 广告智能优化系统 V1  
> 本文基于当前仓库、目标截图、本地目标 HTML 和参考技术方案的只读分析编写。

---

## 1. 文档信息

| 项目 | 内容 |
|---|---|
| 方案名称 | Amazon 广告活动列表页复刻与数据接入技术方案 |
| 目标页面 | 登录后主框架内的“广告活动列表”内容区 |
| 当前建议路由 | /advertising/overview |
| 当前实施范围 | 只读列表、筛选、聚合、分页、条件性行展开、只读导出 |
| 数据原则 | 广告活动业务数据只能来自远程只读数据库；无记录时显示“暂无数据” |
| 写操作原则 | 不直接更新远程数据库；当前 V1 不实现 Amazon Ads 写操作 |
| 页面壳约束 | 现有顶部栏、侧边栏、目录、通知、帮助中心、退出登录等内容和交互全部保持不变 |
| 事实优先级 | 仓库代码 → 目标 DOM/静态行为 → Django settings/路由 → 截图 → 已确认背景 → 显式推测 |

### 1.1 参考技术方案结构总结

已读取《2026-07-30-oauth-token-design.md》。其组织方式以“代码证据—流程—契约—数据—安全”为主线，主要包括：

1. 接口概览；
2. 路由及实际代码入口；
3. 总体调用流程；
4. 请求参数与分支逻辑；
5. 数据表及字段；
6. 配置项；
7. 成功与失败响应；
8. 安全约束；
9. 关联接口；
10. 后续扩展点。

本文沿用这种证据优先的组织方式、表格密度和流程图表达，但不复用其 OAuth 业务逻辑。

### 1.2 分析限制

目标链接是本机 file:// 页面。Codex 内置浏览器因 URL 安全策略拒绝导航，未绕过该限制。随后对本地 HTML、DOM、CSS 和脚本进行了只读静态分析。

确认结果：

- 目标目录仅包含一个自包含 index.html；
- 未发现 fetch、Axios、XMLHttpRequest、WebSocket、外部脚本或外部样式请求；
- 页面数据来自 HTML 内嵌演示数据；
- 筛选、分页、开关等动作仅修改浏览器内存；
- 因而不存在可供核实的真实网络请求或响应契约；
- 不能把该离线演示页的本地行为当作卖家系统真实 API 行为。

截图和 HTML 中可能包含的业务名称、负责人等信息未写入本文。

---

## 2. 项目背景

当前系统已经具备：

- Vue 3 登录后应用框架；
- Django/DRF API；
- JWT Access Token 与 HttpOnly Refresh Cookie 登录链路；
- Tenant、AmazonStore、Marketplace、AdvertisingProfile 上下文；
- 远程 SCM 与广告分析数据库只读接入；
- Campaign、Ad Group、Targeting、Search Term 分析表；
- 认证、租户成员、Store/Profile 范围校验；
- OpenAPI 与 TypeScript 受控同步能力。

本功能不是新建第二套广告系统，而是在现有应用壳、认证、权限和数据源边界中，将广告概览占位页升级为接近参考页面信息架构和视觉密度的只读广告活动列表。

---

## 3. 目标与非目标

### 3.1 目标

- 复刻参考页面中广告活动列表区域的布局、字段顺序、密度和只读交互；
- 使用现有 /advertising/overview 内容区；
- 复用现有认证、租户和 Profile 权限链路；
- 从 ads_analysis_remote 获取统计指标；
- 从 scm_remote 补充 Campaign 名称、状态、日期、预算和竞价信息；
- 支持服务端筛选、排序、分页和全筛选结果合计；
- 支持安全的只读导出；
- 正确覆盖 Loading、Empty、Error、403、401、部分缺失等状态；
- 为后续合法 Amazon Ads 写操作预留边界，但本期不实现。

### 3.2 非目标

- 不修改现有顶部栏、侧边栏、目录或账号菜单；
- 不复制目标页面的品牌素材或私有源码；
- 不连接或调用真实 Amazon Ads 写接口；
- 不通过 UPDATE 远程业务表模拟启停、预算或竞价修改；
- 不把本地 ads_campaign 或 fixtures 冒充远程广告活动；
- 不创建第二套认证、Tenant 或 Profile 上下文；
- 不实现跨 Profile、跨 Marketplace、跨币种合计；
- 不完整实现 Sponsored Brands、Sponsored Display；
- 不执行迁移、DDL、Seed 或远程写入。

---

## 4. 已确认事实

### 4.1 当前数据库 aliases

实际只读检查命令：

    backend/.venv/Scripts/python.exe backend/manage.py shell -c "from django.conf import settings; print(list(settings.DATABASES.keys()))"

实际结果：

    ['default', 'scm_remote', 'ads_analysis_remote']

| Alias | 已确认职责 | 本页面使用方式 |
|---|---|---|
| default | Django 系统库；用户、租户、权限、Profile、审计等 | 认证、范围校验；必要时写导出审计 |
| scm_remote | SCM 远程业务库 | 只读 Campaign 当前元数据 |
| ads_analysis_remote | 广告分析远程库 | 只读 Campaign/Ad Group/Targeting/Search Term 指标 |

### 4.2 其他已确认事实

1. 远程数据库连接带只读 Session 初始化，数据库 Router 禁止远程 alias 迁移。
2. Profile 到远程商户的映射由服务端配置完成：

       AdvertisingProfile.external_profile_id
       → REMOTE_AD_PROFILE_MERCHANT_MAP
       → mer_id + mer_code

3. 前端不得直接提交或决定 mer_id、mer_code。
4. 当前仓库已有广告实体列表接口：

       GET /api/v1/advertising/tenants/{tenant_id}/profiles/{profile_id}/campaigns

   但当前接口读取 default 中的标准化 Campaign，不满足本页面“全部来自远程数据库”的要求，且尚无服务端分页、排序、合计和完整页面字段。
5. 当前已有远程 Campaign 日指标接口：

       GET /api/v1/analytics/tenants/{tenant_id}/profiles/{profile_id}/remote-campaigns

   该接口面向远程数据诊断/分析，不应再创建一个功能重复的页面接口。
6. 参考 HTML 是静态演示页，不是实际卖家网络应用。
7. W0765 的认证代码路径已确认；由于本机 Docker 引擎未运行且宿主机无法解析 Compose 内部 mysql 主机名，本次无法只读核验其实际 Tenant、Store、Profile 数量。该项属于运行环境未验证，不代表账号链路异常。

---

## 5. 当前代码现状

### 5.1 前端

| 层级 | 实际文件 | 类/函数/组件 | 行号 | 当前作用 | 本方案处理 |
|---|---|---|---:|---|---|
| 应用入口 | frontend/src/app/App.vue | AppLayout、RouterView | 1–8 | 所有登录后页面共用布局 | 不修改 |
| 路由 | frontend/src/app/router.ts | /advertising、/advertising/overview | 45–71 | 指向广告概览页 | 复用 /advertising/overview |
| 路由 | 同上 | /campaigns、/campaigns/:campaignId | 112–150 | 分析指标列表与详情 | 不改造为本页面 |
| 路由守卫 | 同上 | beforeEach | 384–399 | 登录状态校验 | 复用 |
| 主框架 | frontend/src/shared/layouts/AppLayout.vue | 顶部栏、侧边栏、模块导航 | 40–147 | 用户、通知、帮助、退出、目录 | 严格保持不变 |
| 全局样式 | frontend/src/shared/styles/base.css | .topbar、.sidebar、.module-nav、.main-area | 60–280 | 当前应用视觉基础 | 仅增加功能局部样式 |
| 页面 | frontend/src/features/advertising/pages/AdvertisingOverviewPage.vue | AdvertisingOverviewPage | 1–10 | 当前占位页 | 改为广告活动列表内容 |
| 旧页面 | frontend/src/features/campaigns/pages/CampaignsPage.vue | CampaignsPage | 1–64 | 未注册的旧列表实现 | 不直接复用 |
| 旧 API | frontend/src/features/campaigns/api/campaignApi.ts | list | 1–19 | 请求路径与当前后端路由不一致 | 实施时更正或替换 |
| 远程诊断页 | frontend/src/features/analytics/pages/RemoteCampaignDataPage.vue | 页面加载、日期状态 | 1–147 | 使用现有远程日指标接口 | 仅参考请求及格式化方式 |
| Analytics API | frontend/src/features/analytics/api/analyticsApi.ts | getRemoteCampaignMetrics | 190–201 | 远程 Campaign 日指标 | 保留，不与页面接口混用 |
| HTTP | frontend/src/shared/api/httpClient.ts | Axios 实例 | 34–41 | 10 秒超时、withCredentials | 复用 |
| HTTP | 同上 | 请求/响应拦截器 | 124–181 | Bearer、X-Token、Tenant Header、401 刷新 | 复用 |
| HTTP 上下文 | frontend/src/app/setupHttpContext.ts | Context providers | 19–35 | Tenant 与登录跳转注入 | 复用 |
| 状态 | frontend/src/features/context/stores/tenantContext.ts | useTenantContextStore | 16–220 | Tenant→Store→Marketplace→Profile | 复用，不建第三套上下文 |
| Context API | frontend/src/features/context/api/contextApi.ts | 租户/店铺/Marketplace/Profile | 46–83 | 权威上下文选项 | 复用 |
| OpenAPI 类型 | frontend/src/shared/api/generated/schema.d.ts | Campaign path | 320–335 | 当前接口无查询参数 | 修改契约后重新生成 |
| UI 组件库 | frontend/package.json | 依赖 | — | 未发现第三方表格/日期 UI 库 | 使用项目内 Vue/CSS 组件 |

结论：

- 当前没有可直接满足目标页面的通用表格、日期选择器、分页或列设置组件；
- 应建立 features/advertising 内的局部组件；
- 不应引入大型 UI 库来完成单页复刻；
- 旧 CampaignsPage 未注册且状态模型落后，不应作为新页面基础。

### 5.2 后端

| 层级 | 实际文件 | 类/函数 | 行号 | 当前作用 | 本方案处理 |
|---|---|---|---:|---|---|
| 总路由 | backend/api/v1/urls.py | advertising/analytics include | 14–16 | API v1 注册 | 不新增平行根路由 |
| 广告路由 | backend/apps/advertising/urls.py | campaigns path | 9–14 | 已有 Campaign 实体列表 | 扩展此接口 |
| View | backend/apps/advertising/views.py | CampaignListView | 18–35 | 认证后调用 Selector | 增加参数 Serializer、分页返回 |
| Selector | backend/apps/advertising/selectors.py | campaign_rows | 6–33 | 读取 default Campaign | 改为远程只读查询编排 |
| Serializer | backend/apps/advertising/serializers.py | CampaignRowSerializer | 4–12 | 当前简单字段 | 扩展请求/响应 DTO |
| 本地 Model | backend/apps/advertising/models.py | Campaign | 26–80 | 标准化导入实体 | 不作为本页数据源 |
| 远程接口 | backend/apps/analytics/views.py | RemoteCampaignMetricListView | 85–111 | 远程指标诊断 | 保持兼容 |
| 远程 Selector | backend/apps/analytics/selectors.py | remote_campaign_metric_rows | 503–565 | Profile 权限、日期、指标公式 | 提取可复用能力 |
| 远程 Reader | backend/integrations/advertising_data/remote_databases.py | RemoteAdvertisingDataReader | 34–269 | 固定参数 SQL、两库拼接 | 扩展成分页查询 Repository |
| 指标计算 | backend/apps/analytics/calculations.py | CTR/CPC/CVR/ACoS/ROAS | 4–24 | 基于 Decimal 的确定性计算 | 复用 |
| Profile 权限 | backend/apps/permissions/services.py | require_profile_scope | 159–202 | Tenant、Store、Profile、权限校验 | 必须复用 |
| Context | backend/apps/stores/selectors.py | tenant/store/profile options | 12–81 | 计算用户可见上下文 | 复用 |
| 数据库设置 | backend/config/settings/base.py | DATABASES、映射配置 | 92–148 | 三 alias 与映射 | 复用 |
| 数据库环境 | backend/config/settings/environment.py | remote DB config | 97–125 | 只读会话初始化 | 保持 |
| Router | backend/config/db_routers.py | RemoteDatabaseRouter | 1–27 | 阻止远程迁移与跨库关系 | 保持 |
| 权限目录 | backend/apps/permissions/migrations/0003_seed_permissions.py | advertising.view | 4–20 | 当前广告查看权限 | 列表沿用；导出权限待评审 |
| OpenAPI | openapi/schema.yaml | Campaign path | 620–648 | 当前返回简单数组 | 扩展为分页对象 |
| 现有测试 | backend/tests/test_report_imports.py | Campaign API 断言 | 817–826 | 依赖当前数组响应 | 接口升级时同步修改 |

### 5.3 当前接口影响结论

建议扩展既有：

    GET /api/v1/advertising/tenants/{tenant_id}/profiles/{profile_id}/campaigns

而不是新建重复列表接口。

这将改变现有响应中 data 从数组变为分页对象，是一个明确的 V1 契约变更。当前确认的直接影响包括：

- openapi/schema.yaml；
- 自动生成的 schema.d.ts；
- test_report_imports.py 中现有断言；
- 未注册的旧 campaignApi.ts；
- 后续新的广告概览页 API 模块。

现有 /analytics/.../remote-campaigns 保持原用途和兼容性。

---

## 6. 目标页面功能盘点

### 6.1 筛选条件

目标 DOM 已确认：

- “进行中”筛选标签；
- “已启用”筛选标签；
- 每个标签的单独移除按钮；
- “删除所有”；
- 高级筛选菜单：状态、展示量、点击量、花费、购买量、CPC、ACoS、CTR、CVR。

目标演示页的实际行为：

- 筛选状态只存在于 JavaScript 内存；
- 不写 URL；
- 不关联 Store/Profile；
- 不发 API 请求；
- 状态筛选菜单有未接入提示；
- 数值筛选在浏览器中处理。

本系统方案：

- 基础筛选写入 URL Query；
- Tenant/Store/Marketplace/Profile 继续由现有 Context Store 管理；
- 前端请求只传业务筛选，不传远程 mer_id、mer_code；
- 数值高级筛选是否首期开放需产品确认。

### 6.2 工具栏

已确认存在：

- “广告活动”标题/下拉视觉；
- 创建广告活动按钮；
- 广告活动搜索框；
- 筛选图标；
- 日期范围选择器；
- 7/14/30 天快捷选项；
- 自定义日期范围；
- 导出按钮。

未发现：

- 真正刷新按钮；
- 列设置按钮；
- 列宽拖动；
- 自定义列持久化。

演示页创建按钮仅显示提示，不发写请求。搜索框没有接入 Campaign 搜索处理。导出按钮没有生成文件。

### 6.3 表格列

目标 DOM 共 19 列：

| 序号 | 列 |
|---:|---|
| 1 | 行选择框 |
| 2 | 启用开关 |
| 3 | 广告活动名称及辅助代码 |
| 4 | 投放类型 |
| 5 | 状态 |
| 6 | 竞价方案 |
| 7 | 开始日期 |
| 8 | 结束日期 |
| 9 | 预算金额 |
| 10 | 展示量 |
| 11 | 搜索结果首页位置占比 |
| 12 | 花费 |
| 13 | 点击量 |
| 14 | 点击率 |
| 15 | 总成本 |
| 16 | 购买量 |
| 17 | 单次点击成本 |
| 18 | ACoS |
| 19 | CVR |

截图右侧未完整显示的列为 ACoS、CVR。

### 6.4 表格交互结论

| 能力 | 目标 HTML 实际情况 | 本系统结论 |
|---|---|---|
| 行展开 | 名称前三角实际跳转 campaign-detail.html，不是内联展开 | 不把它误写成已确认的 Ad Group 展开 |
| 排序 | 主表未绑定排序事件 | 本期可作为系统增强实现服务端白名单排序 |
| 固定列 | 未发现 | 本期不实现 |
| 列宽调整 | 未发现 | 本期不实现 |
| 自定义列 | 未发现 | 本期不实现 |
| 横向滚动 | 表格最小宽度约 1894px，容器 overflow:auto | 本期复刻 |
| 开关 | 只修改内存数据 | 本期禁用，不能制造写入成功假象 |
| 名称辅助标识 | 显示广告代码 | 映射 SCM code 或分析表 campaign_code |
| 空值 | 使用长破折号 — | 本期沿用 |
| Hover | 浅灰背景 | 本期复刻 |

### 6.5 表格底部

目标 HTML：

- 默认每页 15 条；
- 客户端 slice 分页；
- 有上一页、下一页和页码；
- 没有每页数量选择器；
- 合计基于全部过滤结果，不是当前页；
- 合计字段包括展示量、花费、点击、CTR、总成本、购买量、CPC、ACoS、CVR；
- 搜索结果首页位置占比合计显示 —。

本系统必须改为服务端分页，合计仍表示“当前筛选范围全部数据”。

---

## 7. 功能边界矩阵

分类：

- A：本期真实实现
- B：本期仅复刻展示
- C：本期禁用或占位
- D：依赖 Amazon Ads API
- E：依赖卖家现有业务 API
- F：依赖授权、真实样例或产品确认
- G：明确不在本期范围

| 功能 | 页面存在 | 数据来源 | 当前项目已有 | 前端职责 | 后端职责 | Alias | 写入 | 分类/本期 | 风险或依赖 |
|---|---|---|---|---|---|---|---|---|---|
| Campaign 列表 | 是 | 分析表+SCM 元数据 | 部分 | 展示、状态 | 权限、Join、映射 | 两个 remote | 否 | A | 远程键语义 |
| 进行中筛选 | 是 | SCM 日期、状态 | 无完整口径 | URL 标签 | 规范化生命周期 | remote | 否 | A | “进行中”定义确认 |
| 已启用筛选 | 是 | SCM/分析状态 | 部分 | URL 标签 | 状态枚举映射 | remote | 否 | A | 状态冲突优先级 |
| 单独清除筛选 | 是 | URL | 无 | 删除参数、页码归 1 | 无 | 无 | 否 | A | 无 |
| 删除所有 | 是 | URL | 无 | 恢复默认筛选 | 无 | 无 | 否 | A | 默认筛选定义 |
| 关键词搜索 | 控件存在但未接入 | name/code | 无 | 300ms 防抖 | 参数化查询 | remote | 否 | A | 模糊搜索索引 |
| 日期范围 | 是 | creation_date | 部分 | 日期控件、URL | 边界校验 | analysis | 否 | A | 远程时区未确认 |
| 数值高级筛选 | 是 | 指标聚合 | 无 | 条件编辑 | HAVING 白名单 | analysis | 否 | F | 产品需确认首期范围 |
| 排序 | 主表未实现 | 聚合字段 | 无 | 表头交互 | 白名单排序 | analysis/SCM | 否 | A | 聚合排序成本 |
| 分页 | 客户端演示 | 聚合结果 | 无 | 页码 | 服务端分页/count | analysis | 否 | A | count 成本 |
| 合计 | 是 | 聚合指标 | 部分 | 合计行 | 全筛选范围汇总 | analysis | 否 | A | 不得按当前页合计 |
| 行展开 | 目标实际为跳转 | Ad Group 分析表 | 表存在，无页面接口 | 点击后延迟请求 | 安全查询子级 | analysis | 否 | F | Campaign 键和粒度需确认 |
| 导出 | 按钮存在、未实现 | 同列表筛选 | 无 | 处理中/失败 | 参数校验、流式 CSV | remote；default 审计 | 仅读审计 | A | 权限、容量、保留策略 |
| 创建 Campaign | 是、演示提示 | 官方写 API | 无 | 禁用展示 | 不提供写接口 | 无 | 否 | C+D+F | 当前 V1 禁止真实写入 |
| 启用 Campaign | 是、仅内存 | 官方写 API | 无 | 禁用开关 | 不提供写接口 | 无 | 否 | C+D+F | 不可更新远程表 |
| 暂停 Campaign | 同上 | 官方写 API | 无 | 禁用 | 不提供 | 无 | 否 | C+D+F | 同上 |
| 修改预算 | 未形成真实编辑 | 官方写 API | 无 | 只读文本 | 不提供 | 无 | 否 | C+D+F | 幂等和审计 |
| 修改竞价策略 | 未形成真实编辑 | 官方写 API | 无 | 只读文本 | 不提供 | 无 | 否 | C+D+F | 同上 |
| 行选择 | 复选框存在 | 页面状态 | 无 | 禁用展示 | 无 | 无 | 否 | C | 无可执行批量动作 |
| 批量操作 | 未发现真实实现 | 官方写 API | 无 | 不展示菜单 | 不提供 | 无 | 否 | G | 当前 V1 范围外 |
| 列设置 | 未发现 | 页面配置 | 无 | 不实现 | 无 | 无 | 否 | G | 非复刻必要项 |
| 列宽调整 | 未发现 | 页面状态 | 无 | 不实现 | 无 | 无 | 否 | G | 非复刻必要项 |

边界结论：本期的“只读”表示不改变广告业务状态。导出安全审计可以写入 default 的 AuditLog，但不得写远程库。

---

## 8. 总体架构

~~~mermaid
flowchart LR
    B["Browser"]
    V["Vue AdvertisingOverviewPage"]
    X["Existing Axios Client"]
    A["Existing JWT / Refresh Cookie"]
    D["DRF Existing Campaign Endpoint"]
    P["Tenant + Store + Profile Permission Scope"]
    S["Campaign Read Selector"]
    R["RemoteAdvertisingDataReader"]
    AA[("ads_analysis_remote")]
    SCM[("scm_remote")]
    SYS[("default")]

    B --> V --> X --> A --> D --> P --> S --> R
    P --> SYS
    R --> AA
    R --> SCM
~~~

基本约束：

- 浏览器只调用 DRF；
- 前端永不连接 MySQL；
- default 负责身份与范围；
- 两个 remote alias 仅用于参数化 SELECT；
- 页面不得从本地 Campaign 表回退生成“看似真实”的数据；
- 远程查询成功但无记录时显示“暂无数据”；
- 远程配置错误、超时或权限异常必须显示错误，不能伪装成空数据。

---

## 9. 路由与代码入口

### 9.1 页面路由

采用现有：

    /advertising/overview

页面内容实现于：

    frontend/src/features/advertising/pages/AdvertisingOverviewPage.vue

不改变 App.vue、AppLayout.vue、顶部栏、侧边栏、模块导航、通知、帮助中心、用户菜单、退出登录以及既有 /campaigns 分析页语义。

建议 URL：

    /advertising/overview
      ?lifecycle=ongoing
      &enabled=true
      &range=last30
      &search=
      &ordering=-spend
      &page=1
      &pageSize=15

手工日期时：

    ?startDate=2026-07-01&endDate=2026-07-30

Context 不重复写入 Query：

    Tenant → AmazonStore → Marketplace → AdvertisingProfile

它继续由现有 tenantContext 管理。API path 中的 tenant_id/profile_id 来自当前已选上下文，并由后端重新授权。

### 9.2 API 路由

扩展既有：

    GET /api/v1/advertising/tenants/{tenant_id}/profiles/{profile_id}/campaigns

条件性新增：

    GET /api/v1/advertising/tenants/{tenant_id}/profiles/{profile_id}/campaigns/{campaign_key}/children
    GET /api/v1/advertising/tenants/{tenant_id}/profiles/{profile_id}/campaigns/export

不新增第二个 Campaign 列表端点。

---

## 10. 前端方案

### 10.1 组件树

    AdvertisingOverviewPage
    └── CampaignListPanel
        ├── CampaignActiveFilters
        │   ├── CampaignFilterChip
        │   └── ClearCampaignFiltersButton
        ├── CampaignToolbar
        │   ├── DisabledCreateCampaignButton
        │   ├── CampaignSearchInput
        │   ├── CampaignAdvancedFilterButton
        │   ├── CampaignDateRangePicker
        │   └── CampaignExportButton
        ├── CampaignDataTable
        │   ├── CampaignTableHeader
        │   ├── CampaignTableSkeleton
        │   ├── CampaignTableRow
        │   ├── CampaignExpandedRow
        │   ├── CampaignSummaryRow
        │   ├── CampaignEmptyState
        │   └── CampaignErrorState
        └── CampaignPagination

建议文件位于：

    frontend/src/features/advertising/
      api/campaignApi.ts
      components/
      composables/useCampaignList.ts
      pages/AdvertisingOverviewPage.vue
      types/campaign.ts

按需求创建，不提前生成空壳。

### 10.2 状态归属

| 状态 | 存放位置 | 原因 |
|---|---|---|
| Tenant/Store/Marketplace/Profile | 现有 tenantContext Pinia | 已有权威上下文 |
| lifecycle、enabled、search、日期、排序、页码 | URL Query | 刷新恢复、前进后退、可分享 |
| 列表、合计 | 页面请求状态 | 服务端权威事实，不长期存 Pinia |
| Loading/Error/requestId | 页面 composable | 请求生命周期 |
| 展开行 key | 页面组件 | 临时 UI 状态 |
| 行选择 | 页面组件 | 本期禁用或只读 |
| 导出中 | 页面组件 | 当前请求状态 |
| 远程 Merchant 映射 | 不进前端 | 服务端秘密范围 |

不建议创建 Campaign Pinia Store。该页面没有需要跨页面长期保存的客户端业务事实。

### 10.3 请求控制

- 搜索输入 300ms 防抖，建议值；
- 筛选、排序、日期、pageSize 变化时将 page 重置为 1；
- 使用 Axios signal/AbortController 取消旧请求；
- 每次请求携带递增序号，只接收最后一次请求；
- 刷新时保留旧数据并显示轻量遮罩，首次进入使用 Skeleton；
- 401 交给现有拦截器刷新一次，失败后回登录页；
- 导出使用独立请求，不覆盖列表 Loading；
- API 的 requestId 显示在错误详情中，便于排障，不显示敏感内容。

### 10.4 格式化

- 金额使用 Intl.NumberFormat 和响应中的 currencyCode；
- 日期为 Profile 业务日期，不进行浏览器时区二次偏移；
- 整数使用千位分隔；
- 百分比显示两位小数，目标示例中的整数首页占比可按产品确认后确定；
- API Decimal 以字符串传输；
- null、无法计算、远程字段缺失统一显示 —；
- 页面确实无 Campaign 时显示“暂无数据”；
- 不同 Profile 的金额不合并。

### 10.5 响应式策略

- 桌面优先；
- 表格维持约 1894px 最小宽度并横向滚动；
- 不压缩隐藏指标列；
- 内容区小于 768px 时工具栏换行；
- 日期控件、搜索框保持可操作宽度；
- 不改变现有 56px 侧边栏；
- 不实现主表固定列、列拖拽和用户列配置。

### 10.6 写控件处理

本期：

- “创建广告活动”保留参考页面位置，但 disabled；
- 启用开关使用只读 disabled 状态；
- 预算和竞价方案仅展示文本；
- 行复选框 disabled；
- 不显示批量操作菜单；
- Tooltip 明确提示“当前版本仅支持查看”。

不能使用点击后 Toast“操作成功”的伪实现。

---

## 11. 后端方案

### 11.1 调用链

    DRF View
    → Query Serializer
    → require_profile_scope()
    → Campaign Selector
    → Remote Advertising Read Repository
    → ads_analysis_remote / scm_remote
    → Response Serializer

View 不拼 SQL，权限 Service 不承担业务聚合，远程 Repository 不接收未经验证的任意 SQL 字段或 alias。

### 11.2 建议职责

| 层 | 职责 |
|---|---|
| View | 认证、调用 Serializer/Selector、响应 |
| Query Serializer | 日期、分页、排序、筛选白名单 |
| Permission Service | TenantMembership、Store/Profile、功能权限 |
| Selector | 组织远程查询、合计、元数据、空值原因 |
| Remote Repository | 固定 SQL、参数绑定、只读 alias |
| Calculations | CTR/CPC/ACoS/CVR 等确定性公式 |
| Response Serializer | Decimal 字符串、枚举、分页和 meta |

### 11.3 Campaign 唯一键

当前远程表没有已确认的跨商户全局 Campaign 主键。

建议内部范围键：

    (mer_id, mer_code, campaign_id)

若 campaign_id 为空，则受控回退：

    (mer_id, mer_code, campaign_code)

API 不接受裸 campaign_id 直接越过 Scope。campaign_key 应是服务端生成的非敏感、不透明标识，展开时再次解码并附加 mer_id + mer_code 条件。

Campaign ID/code 稳定性仍需卖家数据负责人确认。

---

## 12. 数据源与数据库 alias

### 12.1 当前表结构证据

| Alias | 表 | 用途 | 已确认相关字段 |
|---|---|---|---|
| scm_remote | eb_ad_campaign | 当前 Campaign 元数据 | mer_id、mer_code、campaign_id、code、name、type、state、start_date、end_date、budget、bidding_strategy |
| ads_analysis_remote | bi_analyze_ad_campaign | Campaign 日期指标 | mer_id、mer_code、creation_date、Campaign 标识、预算、状态、imperssion、click、spend、orders、sales、top_of_search_is |
| ads_analysis_remote | bi_analyze_ad_group | Ad Group 指标 | Campaign、Group、日期及指标 |
| ads_analysis_remote | bi_analyze_ad_targeting | Targeting 指标 | Campaign、Group、Targeting、日期及指标 |
| ads_analysis_remote | bi_analyze_ad_search_term | Search Term 指标 | Campaign、Group、Query、日期及指标 |
| default | ads_campaign | 本地导入后的标准化 Campaign | 不作为本页面数据源 |

注意：远程分析表字段实际拼写是 imperssion。Repository 可将其映射成应用层 impressions，不得假设数据库已改名。

### 12.2 元数据规模

information_schema 的近似行数，截至 2026-08-03：

| 表 | 近似行数 |
|---|---:|
| scm_remote.eb_ad_campaign | 约 4.1 万 |
| scm_remote.eb_ad_group | 约 4.2 万 |
| scm_remote.eb_ad_targeting | 约 30.5 万 |
| ads_analysis_remote.bi_analyze_ad_campaign | 约 25.6 万 |
| ads_analysis_remote.bi_analyze_ad_group | 约 23.5 万 |
| ads_analysis_remote.bi_analyze_ad_targeting | 约 96.2 万 |
| ads_analysis_remote.bi_analyze_ad_search_term | 约 38.9 万 |

这些是数据库元数据估算，不是精确 COUNT(*)，不能据此承诺延迟或 QPS。

### 12.3 数据库 alias 选择流程

~~~mermaid
flowchart TD
    Q["Campaign API 请求"] --> U["从认证用户取得 TenantMembership"]
    U --> P["校验 Profile 属于可访问 Store"]
    P --> M["使用服务端 Profile 映射"]
    M --> C{"查询内容"}
    C -->|用户/租户/Profile/审计| D[("default")]
    C -->|Campaign 当前元数据| S[("scm_remote")]
    C -->|日期指标和聚合| A[("ads_analysis_remote")]
    S --> RO["固定参数 SELECT"]
    A --> RO
    RO --> X["禁止 migrate / DDL / UPDATE"]
~~~

### 12.4 数据源规则

- 页面数据不从本地 Campaign Model 回退；
- SCM 无匹配但分析表有数据时，可返回 Campaign，metadataMatched=false；
- SCM 名称、预算、状态缺失时显示 —，不得伪造；
- 分析表无指标但 SCM 有 Campaign 是否显示，当前无法完全确认。建议本期以分析表为主集合，因此所选日期无数据时不显示；
- 如果产品要求“所有 Campaign，包括零曝光活动”，需改为 SCM 主集合左连接分析结果，必须另行确认语义和成本。

---

## 13. 字段和指标映射

### 13.1 维度字段

| 页面字段 | 来源 | 处理 |
|---|---|---|
| 启用 | SCM state，分析状态回退 | enabled → true；其他 false |
| 广告活动名称 | SCM name，分析 campaign_name 回退 | 空值显示 — |
| 辅助标识 | SCM code，分析 campaign_code 回退 | 可用于搜索，不作为前端授权条件 |
| 投放类型 | SCM type / 分析 campaign_type | auto→自动投放，manual→手动投放 |
| 状态 | SCM state 优先 | 映射为统一状态枚举 |
| 竞价方案 | SCM bidding_strategy | 固定竞价、动态只降低、动态提高和降低 |
| 开始日期 | SCM start_date | Profile 业务日期 |
| 结束日期 | SCM end_date | null 显示“无结束日期” |
| 预算金额 | SCM budget 优先 | Profile currency，不跨 Profile 合计 |

### 13.2 指标映射

| 页面字段 | 中文定义 | 原始字段 | 来源 | 聚合方式 | 时间口径 | 空值规则 | 格式化 |
|---|---|---|---|---|---|---|---|
| 展示量 | 广告获得展示的次数 | imperssion | bi_analyze_ad_campaign | SUM | Profile 日期，含首尾 | 无数据为 —，有零值显示 0 | 整数千分位 |
| 点击量 | 广告点击次数 | click | 同上 | SUM | 同上 | 同上 | 整数千分位 |
| 点击率 | 点击/展示 | 计算 | 聚合结果 | SUM(click)/SUM(impressions)×100% | 同上 | 展示为 0 时 — | 2 位百分比 |
| 花费 | 广告支出 | spend | 同上 | SUM | 同上 | 无数据 — | currency，2 位展示 |
| 购买量 | 归因订单数 | orders | 同上 | SUM | 同上 | 无数据 — | 整数 |
| 单次点击成本 | 平均每次点击花费 | 计算 | 聚合结果 | SUM(spend)/SUM(click) | 同上 | 点击为 0 时 — | currency |
| 首页位置占比 | 搜索结果顶部展示占比 | top_of_search_is | 同上 | 待确认 | 同上 | 未确认口径前返回 null | 百分比 |
| 总成本 | 目标页中与花费相同 | spend | 同上 | SUM | 同上 | 无数据 — | currency |
| 预算金额 | 当前每日预算 | SCM budget | eb_ad_campaign | 不求和 | 当前元数据 | 缺失 — | “每日 + currency” |
| ACoS | 花费/广告销售额 | 计算 | spend、sales | SUM(spend)/SUM(sales)×100% | 归因口径待确认 | 销售额为 0 时 — | 2 位百分比 |
| CVR | 购买/点击 | 计算 | orders、click | SUM(orders)/SUM(click)×100% | 归因口径待确认 | 点击为 0 时 — | 2 位百分比 |

### 13.3 关键口径结论

- CTR、CPC、ACoS、CVR 必须用合计后的分子/分母重新计算，不能平均各日百分比；
- 目标 HTML 明确将“花费”和“总成本”渲染为同一个 cost 值。为复刻可暂时均映射 SUM(spend)，响应元数据注明二者同源；
- top_of_search_is 的单位是 0–1 还是 0–100、跨日如何汇总尚未确认。在确认前返回 null，前端显示 —；
- orders 的归因窗口未确认；远程表同时存在其他归因字段，不能擅自把 orders 定义成 1 日或 7 日；
- campaign_daily_budget 不应跨日期求和；建议 SCM 当前预算优先，缺失时取分析表最新快照，而不是 MAX；
- 所有计算使用 Decimal，API 以字符串传金额和小数；
- 显示层建议按币种最小单位四舍五入，计算层保留原始精度。具体舍入规则需产品/财务确认。

### 13.4 日期和时区

| 层 | 当前事实/方案 |
|---|---|
| 浏览器 | 只负责选择 Profile 业务日期，不用浏览器时区重解释 date-only |
| Django | USE_TZ=True，UTC 存储系统时间 |
| default MySQL | 系统时间按 UTC |
| Profile | 已有 timezone 和 currency |
| 远程 creation_date | 存储时区未确认 |
| 边界 | startDate、endDate 均包含 |
| 默认范围 | 页面显式使用 range=last30，以远程最新可用日期为终点 |
| API 未传日期 | 保持现有决策：最新可用数据日 |

在远程时区未确认前，不应把 creation_date 自动当 UTC 转换。

---

## 14. API 契约

### 14.1 Campaign 列表

    GET /api/v1/advertising/tenants/{tenant_id}/profiles/{profile_id}/campaigns

状态：需要扩展既有接口。

权限：

- IsAuthenticated；
- 有效 TenantMembership；
- Profile 属于当前 Tenant 下可访问 Store；
- Profile access level 至少 VIEW；
- advertising.view；
- 跨范围统一 404；
- 当前范围内缺功能权限返回 403。

参数：

| 参数 | 类型 | 默认值 | 校验 |
|---|---|---|---|
| lifecycle | enum | ongoing | ongoing/all/ended |
| enabled | bool | true | 严格布尔 |
| search | string | 空 | trim，最长 100 |
| range | enum | last30（页面显式传） | latest/last7/last14/last30 |
| startDate | date | 无 | 自定义范围时必填 |
| endDate | date | 无 | 自定义范围时必填 |
| ordering | string | -spend | 白名单，前缀 - 表示降序 |
| page | int | 1 | ≥1 |
| pageSize | int | 15 | 建议允许 15/30/50/100，最大 100 |
| includeSummary | bool | true | 严格布尔 |

建议最大日期范围：90 天。该值需在 EXPLAIN 和真实数据延迟测试后确认。

排序白名单：

    name
    targetingType
    status
    biddingStrategy
    startDate
    endDate
    dailyBudget
    impressions
    topOfSearchShare
    spend
    clicks
    ctr
    totalCost
    orders
    cpc
    acos
    cvr

topOfSearchShare 在口径未确认前不得开放排序。

### 14.2 成功响应示例

以下完全为虚构数据：

~~~json
{
  "code": "SUCCESS",
  "message": "操作成功",
  "requestId": "req_demo_001",
  "data": {
    "items": [
      {
        "campaignKey": "cmp_demo_10001",
        "name": "演示广告活动 A",
        "referenceCode": "DEMO-SP-001",
        "enabled": true,
        "targetingType": "AUTO",
        "status": "DELIVERING",
        "biddingStrategy": "FIXED_BIDS",
        "startDate": "2026-07-01",
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
        "metadataMatched": true,
        "partialFields": ["topOfSearchShare"]
      }
    ],
    "summary": {
      "impressions": 1234,
      "spend": {"amount": "42.31000", "currencyCode": "USD"},
      "clicks": 23,
      "ctr": "0.018638",
      "totalCost": {"amount": "42.31000", "currencyCode": "USD"},
      "orders": 2,
      "cpc": {"amount": "1.83957", "currencyCode": "USD"},
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
      "source": "REMOTE_MYSQL",
      "currencyCode": "USD",
      "timezone": "America/Los_Angeles",
      "startDate": "2026-07-01",
      "endDate": "2026-07-30",
      "dataThroughDate": "2026-07-30",
      "totalCostSemantics": "SPEND_ALIAS"
    }
  }
}
~~~

### 14.3 错误响应

沿用项目统一错误包络：

~~~json
{
  "code": "INVALID_DATE_RANGE",
  "message": "结束日期不能早于开始日期",
  "requestId": "req_demo_error_001",
  "details": {
    "endDate": ["必须大于或等于 startDate"]
  }
}
~~~

建议错误码：

| HTTP | Code | 场景 |
|---:|---|---|
| 400 | INVALID_QUERY_PARAMETER | 类型或枚举错误 |
| 400 | INVALID_DATE_RANGE | 日期非法 |
| 400 | PAGE_OUT_OF_RANGE | 页码越界 |
| 401 | AUTHENTICATION_REQUIRED | Access/Refresh 均失效 |
| 403 | PERMISSION_DENIED | 范围内缺权限 |
| 404 | RESOURCE_NOT_FOUND | 跨 Tenant/Store/Profile |
| 422 | EXPORT_TOO_LARGE | 超过同步导出上限 |
| 503 | REMOTE_DATA_UNAVAILABLE | 远程数据库不可用 |
| 503 | REMOTE_PROFILE_MAPPING_MISSING | Profile 未配置远程映射 |

### 14.4 合计接口决策

不单独新增合计接口。列表和合计在同一响应返回，原因：

- UI 首屏必须同时显示列表和合计；
- 二者必须共享完全相同的租户、日期和筛选口径；
- 避免两个请求产生数据时间差；
- 避免重复解析、授权和远程 Scope；
- 可在同一个过滤基集上计算分页结果与 Summary。

实现可使用共享 CTE 或两个参数完全相同的只读查询。不能为了“一次 SQL”引入难维护或明显更慢的窗口查询；最终以 EXPLAIN 为准。

### 14.5 筛选项接口决策

Phase 1 不单独新增筛选项接口：

- 状态、投放类型和竞价方案是受控枚举；
- 日期可用范围通过列表 meta 返回；
- Tenant/Store/Profile 已由 Context API 提供。

如果后续要展示远程动态 Portfolio、状态数量或产品维度，再新增专门筛选接口。

### 14.6 行展开接口

状态：待确认，禁止在 Campaign 键及粒度确认前实现。

    GET /api/v1/advertising/tenants/{tenant_id}/profiles/{profile_id}/campaigns/{campaign_key}/children
        ?level=adGroup
        &startDate=2026-07-01
        &endDate=2026-07-30

首层仅建议返回 Ad Group 聚合。Targeting 采用再次按需加载，避免一次展开扫描大表。

必须附加：

    mer_id + mer_code + campaign_id/code + date range

不得仅按前端提交的 campaign_id 查询。

### 14.7 导出接口

    GET /api/v1/advertising/tenants/{tenant_id}/profiles/{profile_id}/campaigns/export

状态：计划新增。

方案：

- 查询参数与列表一致，忽略分页；
- 服务端生成 UTF-8 BOM CSV；
- 建议同步硬上限 10,000 条；
- 超限返回 EXPORT_TOO_LARGE，不截断后伪装完整；
- 响应设置 Cache-Control: no-store；
- Content-Disposition 文件名仅使用安全日期/Profile 标识；
- 不在 MySQL 保存文件正文；
- 导出行为写 default 的 AuditLog；
- 不把远程商户映射、Token 或请求头写入文件和日志。

如真实 Profile 经常超过 10,000 条，再评审异步导出任务；本期不提前创建任务表和文件保留机制。

### 14.8 限流与缓存

- 列表沿用当前认证用户全局限流，现配置证据为 120 次/分钟；
- 建议导出单独限制为 5 次/小时/用户/Profile；
- 初期不启用跨请求结果缓存，先测真实数据更新频率；
- 若启用，缓存键必须包含 tenant_id、profile_id、服务端 merchant 映射版本、日期、全部筛选、排序、分页、数据水位和 schemaVersion；
- 建议 TTL 60 秒，仅为建议值；
- 跨 Tenant/Profile 复用缓存键属于严重越权风险。

---

## 15. 查询与聚合流程

### 15.1 页面加载流程

~~~mermaid
sequenceDiagram
    participant U as "User"
    participant P as "AdvertisingOverviewPage"
    participant C as "Tenant Context"
    participant A as "Campaign API"

    U->>P: 进入 /advertising/overview
    P->>C: 确认 Tenant/Store/Marketplace/Profile
    alt Context 不完整
        C-->>P: 显示既有上下文选择提示
    else Context 完整
        P->>P: 从 URL 恢复筛选
        P->>A: 请求列表、合计、meta
        A-->>P: 分页结果
        P-->>U: 渲染表格或“暂无数据”
    end
~~~

### 15.2 广告活动列表查询流程

~~~mermaid
flowchart TD
    A["收到 GET Campaigns"] --> B["Query Serializer 校验"]
    B --> C["require_profile_scope"]
    C --> D["服务器解析 mer_id + mer_code"]
    D --> E["确定 Profile 日期范围"]
    E --> F["ads_analysis_remote 聚合 Campaign 指标"]
    F --> G["scm_remote 批量补充当页元数据"]
    G --> H["后端计算 CTR/CPC/ACoS/CVR"]
    H --> I["构建 Summary + Pagination + Meta"]
    I --> J["统一响应"]
~~~

### 15.3 筛选、排序和分页流程

~~~mermaid
flowchart LR
    U["筛选变化"] --> Q["更新 URL Query"]
    Q --> R["page 重置为 1"]
    R --> C["取消上次请求"]
    C --> V["后端校验白名单"]
    V --> W["WHERE / HAVING"]
    W --> O["白名单 ORDER BY"]
    O --> P["LIMIT / OFFSET"]
    P --> S["全筛选范围 Summary"]
    S --> UI["列表 + 合计 + 分页"]
~~~

### 15.4 行展开流程

~~~mermaid
sequenceDiagram
    participant U as "User"
    participant T as "CampaignTable"
    participant A as "Children API"
    participant P as "Permission Scope"
    participant DB as "ads_analysis_remote"

    U->>T: 展开某 Campaign
    T->>A: campaignKey + 日期
    A->>P: 重新校验 Tenant/Profile
    P->>A: 返回服务端 merchant 范围
    A->>DB: 按商户、Campaign、日期查询 Ad Group
    DB-->>A: 聚合结果
    A-->>T: 子级数据或 partial reason
    T-->>U: 展开内容
~~~

### 15.5 导出流程

~~~mermaid
flowchart TD
    U["点击导出"] --> F["前端进入导出处理中"]
    F --> A["GET export + 当前筛选"]
    A --> P["认证、Profile 权限、导出限流"]
    P --> N["估算/检查导出条数"]
    N -->|超过上限| E["422 EXPORT_TOO_LARGE"]
    N -->|允许| Q["远程只读流式查询"]
    Q --> C["生成 UTF-8 BOM CSV"]
    C --> L["default 写安全审计"]
    L --> D["浏览器下载"]
    E --> UI["显示导出失败"]
~~~

---

## 16. 权限与租户隔离

### 16.1 登录用户到远程 Profile 的映射

~~~mermaid
flowchart TD
    L["W0765 登录"] --> A["Existing Auth API"]
    A --> I["default: User / ExternalIdentity"]
    I --> M["TenantMembership"]
    M --> S["accessible_stores"]
    S --> SM["StoreMarketplace"]
    SM --> P["accessible_profiles"]
    P --> X["AdvertisingProfile.external_profile_id"]
    X --> R["服务端 REMOTE_AD_PROFILE_MERCHANT_MAP"]
    R --> K["mer_id + mer_code"]
    K --> DB["远程只读查询"]
~~~

代码层已确认映射链路，W0765 的实际关联记录数量本次未从 default 运行库验证。

### 16.2 授权顺序

1. JWT/Refresh Cookie 认证；
2. tenant_id 对应有效 TenantMembership；
3. Profile 存在且属于当前 Tenant；
4. Profile 所在 Store 在用户可访问 Store 集合；
5. Profile access level 至少 VIEW；
6. 用户具备 advertising.view；
7. 服务端取得远程 mer_id + mer_code；
8. 所有 SQL 强制添加该范围；
9. Campaign 展开再次验证 Campaign 属于范围。

### 16.3 IDOR 防护

禁止：

    前端传 merchant_id=...
    前端传 mer_code=...
    只按 campaign_id 查询
    根据 UI 隐藏按钮代替权限

必须：

    认证身份 → Tenant → Store/Profile → 服务端 Merchant 映射 → 查询条件

即使用户修改 URL 中 tenant_id、profile_id 或 campaign_key：

- 完全越出范围返回 404；
- 范围内但缺权限返回 403；
- 不泄露目标对象是否真实存在。

### 16.4 导出权限

最低要求：

- advertising.view；
- Profile VIEW；
- 与列表完全相同的数据范围；
- 后端再次校验，不信任前端当前页；
- 审计用户、Tenant、Profile、筛选摘要、导出行数、结果状态；
- 日志不记录完整 Campaign 名称集合或远程商户映射。

是否新增 advertising.export 独立权限，需要安全和产品确认。当前权限目录中未找到该权限。

---

## 17. 导出方案

Phase 1 推荐同步流式 CSV：

- 不新增任务 Model、迁移和文件清理机制；
- 不持久化文件正文；
- 能覆盖“导出处理中”和“导出失败”；
- 设置硬性行数上限；
- 大数据量异步导出作为后续扩展。

建议列顺序与表格一致，但不导出：

- 行选择框；
- 开关控件；
- 内部 campaign_key；
- Tenant ID；
- mer_id、mer_code；
- Profile 内部主键。

导出金额同时包含数值和 currencyCode。日期列应注明 Profile timezone。大数据量异步导出不在没有保留、清理、下载鉴权决策前实现。

---

## 18. 未来写操作方案

当前主规格明确 V1 不调用真实 Amazon Ads API，也不自动修改广告。因此功能 Phase 2 属于未来范围，必须重新授权后开展。

~~~mermaid
flowchart LR
    B["Browser"]
    D["Django Write API"]
    P["权限 + Profile Scope"]
    I["Idempotency Key"]
    V["Action Preview / Drift Check"]
    A["Approval + Audit Transaction"]
    Q["Celery Task after commit"]
    API["Authorized Amazon Ads API"]
    R["ExecutionRecord"]
    RO[("remote analysis DB")]

    B --> D --> P --> I --> V --> A --> Q --> API --> R
    RO -. "仅作读侧核验，禁止 UPDATE" .-> V
~~~

进入写操作阶段必须满足：

- 官方 Amazon Ads 写接口及版本已确认；
- OAuth scope 和授权账号已确认；
- Sandbox 或测试 Profile 可用；
- 幂等键、重试策略和冲突策略已确认；
- Action Preview Schema 已确认；
- 操作前漂移检查已确认；
- AuditLog、ApprovalRecord、ExecutionRecord 同事务边界；
- 任务仅在事务提交后派发；
- 部分成功和失败补偿有明确状态机；
- 不把分析库写成“已生效”来模拟 Amazon 成功。

未来写接口只能是新增并显式授权的 POST/PATCH 端点，不能让当前 GET 接口隐式产生写入。

---

## 19. 性能与缓存

### 19.1 当前风险

当前远程 Reader 使用 DATE(creation_date) 参与过滤和分组。这可能使 creation_date 索引无法充分利用。

建议改为半开区间：

    creation_date >= :start_datetime
    AND creation_date < :end_next_day_datetime

前提是先确认远程 creation_date 的实际时区语义。

远程相关表目前主要是单列索引，未确认存在适合本查询的复合索引：

    (mer_id, mer_code, creation_date, campaign_id)

远程库只读，本项目不能自行增加索引。需要数据库所有者基于 EXPLAIN 决定。

### 19.2 查询策略

- 分析表先按 Profile 商户、日期聚合；
- 只对当前页 Campaign 批量查询 SCM 元数据；
- 禁止逐行查询 SCM，避免 N+1；
- Summary 在分析表聚合，不遍历前端页数据；
- 行展开点击后延迟加载；
- Targeting/Search Term 不随 Campaign 首屏加载；
- count 使用与列表一致的过滤基集；
- 搜索同时覆盖 name/code 时必须参数化并转义 LIKE 通配符；
- 默认 pageSize=15，最大建议 100；
- 默认范围由前端显式传 last30；
- 最大范围建议 90 天，需验证后落定。

### 19.3 数据延迟

当前无法确认分析数据的更新周期、最晚完整数据日、历史回补、同日重述以及 SCM 元数据与分析指标的同步延迟。

API 必须返回 dataThroughDate。页面日期终点超过该日期时可提示“数据更新至 YYYY-MM-DD”，不能暗示实时数据。

### 19.4 缓存

初期建议先不缓存，采集只读性能基线。若确认需要缓存：

- TTL 建议 60 秒；
- Key 必须完整包含租户、Profile、筛选、排序、页码和数据水位；
- 远程数据水位变化时失效；
- Profile 映射变化时失效；
- 只缓存序列化后的只读结果；
- 不缓存 403/404；
- 不将 Redis 作为唯一授权事实。

---

## 20. 安全约束

1. 前端不连接数据库；
2. 两个远程数据库保持只读；
3. 不在远程库运行 Django migrate；
4. 不通过直接 UPDATE 模拟 Amazon Ads 操作；
5. 写操作未来只能走合法授权的 Amazon Ads API；
6. 写操作必须具备权限、审计、幂等、状态机和失败处理；
7. 不记录 Token、Cookie、Refresh Token 或 Authorization Header；
8. 导出必须再次授权并记录审计；
9. 日志不得记录密码、完整隐私数据、远程连接信息；
10. 不因复刻页面绕过现有认证机制；
11. 所有排序字段和筛选表达式使用白名单；
12. 所有远程 SQL 必须参数化；
13. 不能允许用户控制数据库 alias；
14. 错误响应不能泄露远程表名、SQL、主机名或商户映射；
15. 当前 Reader 的数据库异常日志包含 merchant 标识，实施时应改为脱敏/hash 标识；
16. CSV 必须防公式注入：以 =、+、-、@ 开头的文本需要安全转义；
17. 下载响应使用 nosniff、no-store 和安全文件名。

---

## 21. 异常处理

| 状态 | 页面行为 |
|---|---|
| 首次加载 | 显示与表格行高一致的 Skeleton，不显示旧占位文案 |
| 刷新中 | 保留旧表格并显示非阻塞加载层 |
| 空数据 | 表体显示“暂无数据”，保留筛选和日期 |
| 请求失败 | 显示错误摘要、重试按钮、requestId |
| 权限不足 | 403 专用状态，不展示残留数据 |
| 登录过期 | 现有拦截器刷新一次；失败后进入登录 |
| 数据局部缺失 | 单字段 —，行附 partialFields 提示 |
| Profile 映射缺失 | 显示配置错误，不显示“暂无数据” |
| 远程数据库不可用 | 503 状态，不回退本地假数据 |
| 分页越界 | 后端返回 PAGE_OUT_OF_RANGE 和最后页；前端仅自动纠正一次 |
| 日期非法 | 日期控件内联错误，不发请求或显示 400 字段错误 |
| 导出处理中 | 禁用导出按钮并显示进度文字 |
| 导出失败 | 恢复按钮，显示错误和 requestId |
| 导出过大 | 提示缩短日期或筛选，不静默截断 |
| Context 不完整 | 使用现有上下文选择提示，不擅自选择其他 Profile |

---

## 22. 测试方案

### 22.1 前端测试

- 页面组件首次加载；
- URL Query 恢复；
- 单个筛选标签删除；
- 删除所有；
- 筛选变化页码归 1；
- 搜索 300ms 防抖；
- 旧请求取消和乱序响应丢弃；
- 排序白名单交互；
- 上一页、下一页、页码；
- Loading、刷新、Empty、403、401、503；
- 局部字段缺失显示 —；
- CTR/CPC/ACoS/CVR 格式化；
- 零分母显示规则；
- Profile currency 格式；
- 日期首尾边界；
- 导出中、失败、超限；
- 写按钮和开关 disabled；
- 顶部栏、侧边栏和原交互回归；
- 1659×747 视觉截图回归；
- 横向滚动后右侧 ACoS/CVR 可见。

### 22.2 后端测试

- Query Serializer 类型、长度和日期校验；
- ordering SQL 注入及白名单；
- pageSize 最大值；
- TenantMembership 缺失返回 404；
- Store/Profile 越权返回 404；
- 范围内缺 advertising.view 返回 403；
- Profile access level；
- Profile→mer_id+mer_code 服务端映射；
- 远程 alias 固定选择；
- 不允许请求参数选择 alias；
- SQL 仅包含参数化 SELECT；
- 远程 migrate 禁止；
- Campaign 聚合；
- Summary 不受分页影响；
- CTR/CPC 等零分母；
- SCM 缺失时 partial；
- 空结果；
- 页码越界；
- 行展开重新授权；
- 导出权限、CSV 注入、行数上限；
- 查询次数，确保 SCM 为一次批量查询；
- OpenAPI 快照和 TypeScript 生成差异。

### 22.3 只读约束测试

建议增加自动化断言：

- Reader 对远程 cursor 仅执行首关键字为 SELECT/CTE 的 SQL；
- RemoteDatabaseRouter.allow_migrate() 对两个 remote alias 永远 false；
- 测试数据库账号缺少 INSERT/UPDATE/DELETE/DDL 权限；
- Campaign GET 和 export 不调用本地 Campaign 写 Service；
- 失败时不调用任何 Amazon API Provider。

---

## 23. 验收标准

### 23.1 联调验收矩阵

| 场景 | 操作 | 预期请求 | 预期页面 | 权限要求 | 验收结果 |
|---|---|---|---|---|---|
| 默认进入 | 打开概览 | GET campaigns，默认筛选 | Skeleton→数据/暂无数据 | advertising.view | 待执行 |
| 搜索 | 输入名称或代码 | 防抖后 page=1 | 匹配结果和合计更新 | 同上 | 待执行 |
| 状态筛选 | 删除/添加标签 | lifecycle/enabled 更新 | 标签和列表一致 | 同上 | 待执行 |
| 日期筛选 | 选择合法范围 | start/end | 数据、合计、meta 更新 | 同上 | 待执行 |
| 清除筛选 | 删除所有 | 默认 Query | 恢复默认标签 | 同上 | 待执行 |
| 排序 | 点击可排序表头 | ordering | 服务端顺序更新 | 同上 | 待执行 |
| 翻页 | 下一页 | page+1 | 仅页数据变，合计不变 | 同上 | 待执行 |
| 展开 | 点击三角 | children GET | 延迟加载 Ad Group | 同上 | 阻塞确认 |
| 导出 | 点击导出 | export GET | 处理中→下载 | 查看/导出权限 | 待执行 |
| 无数据 | 使用无记录范围 | 200、items=[] | “暂无数据” | 同上 | 待执行 |
| 接口失败 | 模拟 503 | GET 失败 | 错误+重试+requestId | 同上 | 待执行 |
| 登录过期 | 令 Access 过期 | 自动 refresh 一次 | 成功恢复或去登录 | 有效 Refresh | 待执行 |
| 越权 | 修改 tenant/profile | GET | 404，无数据泄露 | 无 | 待执行 |
| 部分缺失 | SCM 无匹配 | 200 partial | 缺失列 — | 同上 | 待执行 |
| 分页越界 | 请求过大页码 | 400 | 自动纠正一次 | 同上 | 待执行 |

### 23.2 视觉验收

以截图视口 1659×747 为基准，在现有应用壳的内容区对比：

| 项目 | 验收要求 |
|---|---|
| 内容区外边距 | 目标值约 16px，偏差不超过 4px |
| 工具栏和筛选条 | 主要控件位置偏差不超过 4px |
| 表头高度 | 与目标 CSS 推导值偏差不超过 2px |
| 常规行高 | 约 50px，偏差不超过 2px |
| 目标列覆盖 | 19 列全部存在，可横向滚动访问 |
| 名称列 | 最小约 180px，允许随内容区增长 |
| 表格最小宽度 | 约 1894px，允许 5% 误差 |
| 字体 | 正文 12–13px；表头 12px、半粗 |
| 开关 | 约 34×18px，保持 disabled 语义 |
| 状态标签 | 绿色投放、黄色暂停、灰色归档、红色结束 |
| Hover | 浅灰行背景 |
| 合计行 | 灰底、顶部加粗分隔线 |
| 数字 | 使用 tabular numbers，右对齐 |
| 视觉回归 | 1659×747、1440×900 两个视口 |
| 状态覆盖 | Loading/Empty/Error/403/partial/export 全部有截图 |

不复制目标品牌图案、水印或私有资源。

---

## 24. 实施阶段

这里的 Campaign-P1/P2 是功能分期，不替代仓库 PLANS.md 的全局 Phase 1–7；实际编码只能落在当前已获授权的全局阶段。

### Campaign-P1：只读活动列表

纳入：

- 页面内容区复刻；
- URL 筛选标签；
- 搜索；
- 日期范围；
- 服务端分页；
- 白名单排序；
- 全筛选结果合计；
- 状态标签；
- 安全只读导出；
- Loading/Empty/Error/权限状态；
- Tenant/Store/Profile 隔离；
- OpenAPI 和 TS 类型同步；
- 视觉回归。

条件性纳入：

- Ad Group 行展开。必须先确认 Campaign 键、日期粒度和真实样例。

不纳入：

- 创建；
- 启停；
- 预算修改；
- 竞价策略修改；
- 批量操作；
- 自定义列。

### Campaign-P2：广告活动写操作

当前 V1 不授权实施。只有全部前提满足后才能单独立项：

- 官方写 API；
- 授权 scope；
- 测试环境；
- 幂等；
- 审计；
- 审批；
- 漂移检测；
- 重试与补偿；
- 账号隔离；
- 真实 API 成功证据。

---

## 25. 风险和待确认事项

| 事项 | 当前状态 | 本期影响 | 建议负责人 | 阻塞级别 | 确认时间 |
|---|---|---|---|---|---|
| 官方 Amazon Ads 写接口 | 仓库未实现，V1 禁止 | 不影响只读；阻塞 P2 | 架构/平台 | P2 阻塞 | P2 立项前 |
| 创建 Campaign | 仅目标页演示按钮 | 本期 disabled | 产品 | 非 P1 阻塞 | UI 评审前 |
| 启用开关真实写入 | 目标页仅改内存 | 本期必须 disabled | 产品/安全 | 非 P1 阻塞 | UI 评审前 |
| 预算修改 | 未实现 | 只读展示 | 产品/平台 | P2 阻塞 | P2 立项前 |
| 竞价策略修改 | 未实现 | 只读展示 | 产品/平台 | P2 阻塞 | P2 立项前 |
| 导出权限 | 仅有 advertising.view | 决定是否新增权限迁移 | 安全/产品 | 中 | 开发前 |
| 导出同步/异步 | 建议同步上限 10,000 | 影响接口和 UI | 后端/运维 | 中 | API 评审 |
| Campaign 数据延迟 | 未确认 | 需要 dataThroughDate | 数据负责人 | 高 | 开发前 |
| 首页位置占比 | 字段存在，单位/聚合未知 | 未确认前显示 — | 数据/卖家 | P1 字段阻塞 | 开发前 |
| 花费与总成本 | 目标页同源 | 暂均映射 spend | 产品 | 中 | UI 评审 |
| 购买归因窗口 | orders 语义未知 | Tooltip 不能声明 1d/7d | 数据/卖家 | 高 | 开发前 |
| Profile 币种/时区 | default Profile 有字段 | 远程数据语义仍需核验 | 数据负责人 | 高 | 开发前 |
| W0765 Store/Profile 映射 | 代码路径确认，运行记录未验证 | 阻塞最终联调验收 | 后端/运维 | 高 | 联调前 |
| Marketplace 隔离 | 模型层存在；远程表未见明确 marketplace key | 可能同商户多站点混合 | 架构/数据 | 高 | 查询实现前 |
| 历史数据回补 | 未确认 | 缓存失效和合计变化 | 数据负责人 | 中 | 性能评审 |
| 多租户审计 | 已有 Audit 模块 | 导出应记录 | 安全/后端 | 中 | API 评审 |
| Campaign 唯一键 | id/code 均存在，稳定性未知 | 影响分页、展开、去重 | 数据负责人 | 高 | 查询实现前 |
| SCM 与分析状态冲突 | 当前 Reader 以 SCM 补充 | 需明确优先级 | 产品/数据 | 中 | 开发前 |
| “所有 Campaign”含零指标活动 | 未确认 | 决定 SCM 主表或分析主表 | 产品 | 高 | 开发前 |
| 远程日期时区 | 未确认 | 影响首尾日期正确性 | DBA/数据 | 高 | SQL 实现前 |
| Ad Group 展开 | 表存在，目标页实际是详情跳转 | 是否首期实现未定 | 产品/架构 | 高 | P1 排期前 |
| 复合索引 | 未发现合适索引 | 可能影响搜索/聚合 | DBA | 中 | EXPLAIN 后 |
| 真实网络契约 | 目标 HTML 无网络代码 | 不能复制卖家 API | 产品/卖家 | 非阻塞 | 如有真实站点再补充 |

---

## 26. 任务拆解

| 编号 | 阶段 | 任务 | 涉及文件 | 前置依赖 | 产出 | 风险 | 复杂度 |
|---|---|---|---|---|---|---|---|
| CP1-01 | P1 | 确认 Campaign 唯一键和状态映射 | 决策日志、远程映射文档 | 数据负责人确认 | 已确认决策 | 高 | M |
| CP1-02 | P1 | 确认日期、归因、首页占比口径 | 决策日志、字段字典 | 真实脱敏样例 | 指标契约 | 高 | M |
| CP1-03 | P1 | 定义 Campaign OpenAPI | openapi/schema.yaml、serializers | CP1-01/02 | 请求/响应 Schema | 中 | M |
| CP1-04 | P1 | 扩展远程 Campaign Repository | remote_databases.py | SQL/索引评审 | 参数化分页查询 | 高 | XL |
| CP1-05 | P1 | 实现权限过滤 | permissions service、selector | Profile 映射 | 404/403 隔离 | 高 | M |
| CP1-06 | P1 | 实现列表 Selector | advertising selectors | CP1-04/05 | 列表 DTO | 高 | L |
| CP1-07 | P1 | 实现合计 | Selector/Repository | 指标口径 | Summary | 中 | L |
| CP1-08 | P1 | 扩展已有列表 View | views/urls/serializers | CP1-03/06 | 分页 GET | 中 | M |
| CP1-09 | P1 | 生成前端 API 类型 | OpenAPI、generated schema | CP1-03/08 | TS 类型 | 低 | S |
| CP1-10 | P1 | 广告概览页面结构 | AdvertisingOverviewPage.vue | 视觉评审 | 内容区框架 | 中 | M |
| CP1-11 | P1 | 筛选标签和 URL 状态 | advertising components/composable | Query 契约 | 可恢复筛选 | 中 | M |
| CP1-12 | P1 | 工具栏和搜索 | advertising components | API | 防抖搜索 | 低 | M |
| CP1-13 | P1 | 日期控件 | advertising components | 时区口径 | 快捷/自定义范围 | 高 | M |
| CP1-14 | P1 | 表格及 19 列 | CampaignDataTable | 字段契约 | 主表复刻 | 中 | L |
| CP1-15 | P1 | 合计行与分页 | 表格/分页组件 | API | 服务端分页 UI | 中 | M |
| CP1-16 | P1 | Loading/Empty/Error | 页面组件 | 错误码 | 全状态页面 | 中 | M |
| CP1-17 | P1 | 行展开 | children API、组件 | 唯一键/产品确认 | Ad Group 子级 | 高 | L |
| CP1-18 | P1 | 只读导出 | export View/API/client | 权限/上限确认 | 安全 CSV | 高 | L |
| CP1-19 | P1 | 前端组件测试 | *.spec.ts | 页面完成 | 自动化测试 | 中 | L |
| CP1-20 | P1 | 后端权限/查询测试 | backend tests | API 完成 | 隔离和聚合测试 | 高 | XL |
| CP1-21 | P1 | OpenAPI/契约回归 | schema、generated types | API 完成 | 无生成差异 | 中 | M |
| CP1-22 | P1 | 视觉回归 | 测试截图 | 页面完成 | 视口基线 | 中 | M |
| CP1-23 | P1 | 不变区域回归 | AppLayout 相关测试 | 页面完成 | 顶栏/侧栏不变证据 | 高 | M |
| CP1-24 | P1 | 性能基线与 EXPLAIN | 查询说明文档 | 只读 DBA 权限 | 查询计划和风险 | 高 | L |
| CP1-25 | P1 | 文档同步 | 决策日志、模块文档 | 全部完成 | 口径与运行说明 | 低 | M |
| CP2-01 | P2 | 官方写接口调研 | 独立 ADR | 新阶段授权 | API 可行性结论 | 高 | XL |
| CP2-02 | P2 | 写操作状态机和幂等 | actions/audit | CP2-01 | 正式写方案 | 高 | XL |
| CP2-03 | P2 | 创建/启停/预算/竞价 | 未定 | 全部写前提 | 真实 API 链路 | 极高 | XL |

---

## 27. 相关文件与接口

核心文件：

- frontend/src/app/router.ts:45
- frontend/src/shared/layouts/AppLayout.vue:40
- frontend/src/features/advertising/pages/AdvertisingOverviewPage.vue:1
- frontend/src/shared/api/httpClient.ts:34
- frontend/src/features/context/stores/tenantContext.ts:16
- backend/apps/advertising/urls.py:9
- backend/apps/advertising/views.py:18
- backend/apps/advertising/selectors.py:6
- backend/integrations/advertising_data/remote_databases.py:34
- backend/apps/permissions/services.py:159
- backend/config/settings/base.py:92
- backend/config/db_routers.py:1
- openapi/schema.yaml:620
- docs/15-decision-log.md

相关既有接口：

    POST /api/v1/auth/login
    POST /api/v1/auth/refresh
    GET  /api/v1/auth/me
    GET  /api/v1/context/tenants
    GET  /api/v1/context/tenants/{tenant_id}/stores
    GET  /api/v1/context/tenants/{tenant_id}/stores/{store_id}/marketplaces
    GET  /api/v1/context/tenants/{tenant_id}/stores/{store_id}/profiles
    GET  /api/v1/advertising/tenants/{tenant_id}/profiles/{profile_id}/campaigns
    GET  /api/v1/analytics/tenants/{tenant_id}/profiles/{profile_id}/remote-campaigns

本次只读分析及文档输出中：

- 未修改业务代码；
- 未执行测试、构建或类型检查；
- 未执行 migrate、DDL、Seed；
- 未启动 Celery；
- 未启动或修改 Docker 服务；
- 未进行任何远程写入；
- 隔离目录 amazon-ads-operations-0.1.1 未读取、扫描或修改。

---

## 28. 扩展点

后续可在不破坏当前边界的情况下扩展：

- Ad Group → Targeting 的分层延迟加载；
- Portfolio 筛选；
- 数据更新时间和回补状态；
- 用户级列偏好，但只能保存展示偏好；
- 异步大文件导出；
- Campaign 详情页；
- Sponsored Brands/Display 独立模型和页面；
- 经重新授权后的 Amazon Ads 官方写接口；
- Action Preview、审批、执行证据与漂移检测；
- 基于真实 EXPLAIN 的远程索引优化；
- 读模型同步到本地分析库，但不得用静态数据冒充同步完成。

---

## 结论摘要

1. 本期应复用 /advertising/overview，只替换内容区，现有顶部栏、侧边栏、通知、帮助和退出登录全部不动。
2. 广告活动业务数据只能来自 ads_analysis_remote 和 scm_remote。
3. default 仅用于认证、Tenant/Profile 权限和安全审计，不作为本页面 Campaign 数据源。
4. 页面复用既有 Campaign API 路由，不创建第二个重复列表接口。
5. 列表、筛选、搜索、日期、服务端分页、排序、合计和只读导出属于 Campaign-P1。
6. 无远程记录时必须显示“暂无数据”；数据库错误或映射缺失不能伪装为空数据。
7. 目标页面共有 19 列，截图外还包括 ACoS 和 CVR。
8. 目标 HTML 的分页、开关和筛选都是本地演示行为，没有真实网络请求。
9. 创建、启停、预算和竞价修改本期全部禁用，不提供虚假成功交互。
10. 未来写操作只能调用合法授权的 Amazon Ads API，绝不能直接更新远程数据库。
11. Campaign 查询必须从登录用户推导 Tenant→Store→Profile→服务端 Merchant 映射，不能相信前端 merchant_id。
12. 首页位置占比、订单归因窗口、远程时区和 Campaign 唯一键是编码前的主要阻塞项。
13. “花费”和“总成本”在目标页中同源，本期可均映射 spend，但应保留显式语义说明。
14. 行展开是否进入首期取决于 Campaign 键和 Ad Group 粒度确认；目标页实际是详情跳转而非内联展开。
15. 开始编码前必须完成真实脱敏样例、Profile 映射、Marketplace 隔离、导出权限和 SQL 查询计划评审。
