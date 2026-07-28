# V1 页面与交互审计

审计日期：2026-07-28

审计对象：当前 `1f8a230` 仓库，以及 `localhost:8080` 的只读浏览器结果

## 浏览器结果

使用真实浏览器访问 `http://localhost:8080/`：

- 登录页可渲染，包含邮箱、密码和登录按钮；
- 未提交账号或密码；
- `/diagnostics/health` 的主内容区域为空；
- 浏览器未发现可复用的已登录会话；
- 未在 Stage 1 执行任何会改变数据的点击或表单提交。

注意：该 URL 的容器源码来自 `C:\QSZ\技术方案 - 副本`，因此浏览器结果不能
作为当前仓库的 UI 验收。

## 路由清单

| 路由 | 页面 | 审计状态 |
| --- | --- | --- |
| `/login` | 登录 | 可渲染；本仓库真实登录未验证 |
| `/` | 账号工作台 | 需认证；未验证 |
| `/seller-context` | 卖家空间 | 代码存在；级联交互未验证 |
| `/reports` | 报表中心 | 代码存在；异步轮询不完整 |
| `/advertising/campaigns` | Campaign | 代码存在；详情字段不足 |
| `/dashboard` | Campaign 指标 | 代码存在；未验证 |
| `/advertising/targeting` | Targeting 分析 | 原始 JSON 展示，交互不足 |
| `/advertising/search-terms` | Search Term 分析 | 原始 JSON 展示，交互不足 |
| `/optimization` | 优化工作流 | 代码存在；流程和弹窗不足 |
| `/actions` | 审批执行中心 | 代码存在；回填字段不足 |
| `/audit` | 审计日志 | 代码存在；上下文切换和字段不足 |
| `/knowledge` | 知识库 | 只读列表，未验证 |
| `/system/roles` | 角色权限 | 创建交互不完整 |
| `/diagnostics/health` | 运行诊断 | 当前真实页面主内容为空 |

## 逐页缺陷

### 登录

- 有必填输入和失败提示代码。
- 未验证错误凭据、refresh 恢复、退出及刷新后恢复。
- 没有可在仓库内硬编码的演示密码；Stage 3 必须通过安全命令设置。

### 卖家空间

- 四级选择控件存在。
- 代码可在选择上级后加载下级，但真实数据库迁移阻塞导致本仓库未验证。
- 需要验证刷新恢复、Tenant 切换清理下级状态、403/404 和无权限选项。

### 报表中心

- 文件、报表类型和 Profile 上下文代码存在。
- 创建后只立即查询一次 ImportTask，未持续轮询到终态。
- 缺少上传进度、明确文件级错误、完整行级错误、错误下载、时间范围和导入摘要。
- 通用错误文案吞掉了服务端可操作错误细节。

### Campaign 与 Dashboard

- Campaign 可选择列表项，但详情只有外部 ID、状态、预算。
- 缺少 Target ACOS、时间范围、主要指标、异常详情和刷新/重试。
- Dashboard 有 ECharts，但没有筛选、分页、明细表和除零原因展示。

### Targeting 与 Search Term

- 当前以 `<pre>` 直接展示 API 对象。
- 只在 `onMounted` 加载，不监听 Profile 切换。
- 缺少 loading、retry、分页、筛选、排序、指标格式化和详情。

### 优化工作流

- 四 Agent、Recommendation 选择和审批按钮存在。
- 创建 Preview 与提交审批被合并，缺少提交前的完整动作审阅。
- 无独立详情/弹窗，Tenant、Store、Marketplace、Profile、对象、证据、风险、
  时间范围、创建/提交/审批人员等字段不完整。
- 只实现 APPROVED、RETURNED 的页面入口，缺少 REJECTED、WITHDRAWN。
- RETURNED 流程未在界面清晰展示不可变旧版本与新版本关系。

### 人工执行

- SUCCEEDED、FAILED、SKIPPED 按钮和证据文件选择存在。
- 执行备注被固定为代码常量。
- 缺少实际执行值、执行时间、可编辑备注、附件摘要和批量部分成功反馈。
- 直接输出对象 JSON，信息结构和可读性不足。

### 角色与审计

- 角色创建 API 存在，但提交函数没有错误捕获和成功反馈。
- 角色页面只创建固定只读角色，不能完整展示/编辑权限组合。
- 审计页面不监听 Tenant 切换，缺少操作者、Tenant/Profile、变更前后值和结果。

## 全局交互缺口

- 多数业务页没有明确 Retry 按钮。
- 多数页面没有成功反馈或请求级错误详情。
- 权限控制主要依靠页面可见性，尚未用真实浏览器验证按钮状态与 API 403/404。
- 关键业务没有完整对话框/抽屉，无法满足审阅和确认所需字段。
- 当前单一 Playwright 文件不能证明两条完整路径和全部 50 项验收。

## 修复优先级

1. 先完成数据库迁移协调并让当前仓库可启动。
2. 恢复安全演示账号与四级上下文。
3. 打通真实上传、Celery、指标、Agent、Recommendation、审批、执行和审计。
4. 再补齐页面的 loading/empty/error/retry/success、字段和权限状态。
5. 最后用真实浏览器逐页交互，所有未实际验证项保持
   `IMPLEMENTED_NOT_FULLY_VERIFIED` 或 `NOT_IMPLEMENTED`。
