# 09 前端架构

## 1. 逻辑目录

本目录仅为规划，本次未创建frontend目录。

```text
frontend/src/
  api/
  assets/
  components/
    common/
    business/
  layouts/
  router/
  stores/
  types/
  utils/
  views/
    dashboard/
    data/
    analytics/
    ai/
    actions/
    knowledge/
    system/
```

## 2. 调用链

`Vue页面 → 业务API模块 → Axios统一HTTP客户端 → Django REST API`

页面不直接创建独立Axios实例，不手工拼接认证头和错误逻辑。

## 3. 页面与一级菜单

| 一级菜单 | 页面 |
|---|---|
| 工作台 | 指标摘要、待处理任务、风险和快捷入口 |
| 数据中心 | 报表上传、导入任务、错误、Store/Profile |
| 广告分析 | Campaign列表、趋势、异常详情 |
| 智能优化 | 分析任务、Agent结果、Recommendation及Revision对比 |
| 审批执行 | Action Preview、待审批、人工执行、效果评估 |
| 知识中心 | 用户偏好、团队策略、知识规则 |
| 系统管理 | Tenant成员、Team、Role、Store授权、审计 |

菜单按后端返回的Permission进行过滤，但后端仍做最终授权。

## 4. 登录与Tenant选择

- 登录页使用全局邮箱和密码。
- 认证方式待Cookie Session/双Token决策。
- 登录后无Membership显示不可进入提示。
- 一个有效Tenant自动进入。
- 多个Tenant进入选择页；切换后清理Store选择、业务缓存和进行中页面状态。
- 当前Tenant必须在主布局中持续可见。

## 5. 当前Store上下文

- Store选择器只展示后端授权集合。
- 需要Store的页面在未选择时显示明确引导。
- V1分析任务只能选择一个Store。
- Store切换清理依赖Store的Pinia状态和查询缓存。
- URL中的storeId不是权限证据；403/404按后端结果处理。

## 6. Vue Router与守卫

路由元数据可包含：

- 是否需认证。
- 是否需Tenant。
- 是否需Store。
- 所需Permission。
- 菜单归属和页面标题。

守卫负责用户体验跳转，不取代API授权。必须提供403、404和系统错误页。

## 7. Pinia职责

适合保存：

- 当前User摘要。
- Tenant列表和当前Tenant。
- 当前权限编码集合。
- 可访问Store列表和当前Store。
- 全局通知、页面偏好和异步任务轻量索引。

不适合保存为唯一来源：

- 审批结论、执行结果、正式状态、指标事实。
- 大型报表数据或完整Agent输入输出。

## 8. Axios统一客户端

- 统一baseURL、超时、requestId和认证处理。
- 请求字段遵守camelCase。
- 解析统一成功/错误结构。
- 401：防止并发刷新风暴；无法恢复时清理会话并跳转登录。
- 403：显示缺少权限，不自动重试。
- 404：显示资源不存在或不可访问，不推断越权对象存在。
- 409：显示版本冲突并允许用户刷新对比。
- 422：将字段错误映射到表单。
- 5xx/网络错误：提供安全重试和requestId。

认证决策前不得实现Token持久化假设。

## 9. 页面状态标准

每个数据页必须区分：

- 初始加载。
- 刷新中但保留旧数据。
- 空数据。
- 部分失败：例如部分导入、部分Agent结果或部分执行。
- 完全失败。
- 无权限。
- 数据过期/版本冲突。

不能用单一“失败”提示掩盖部分成功。

## 10. 异步任务体验

- 202后保存taskId和taskUrl。
- 按pollAfterSeconds轮询并退避。
- 展示状态、阶段、进度、成功/错误计数和最近更新时间。
- 页面刷新后可通过业务任务ID恢复。
- 只有后端声明可取消时显示取消按钮。
- 不以Celery内部ID作为用户可见主标识。

## 11. AI建议展示

- 结构化展示建议类型、目标对象、当前值、建议值、理由、证据、风险和置信说明。
- 明确区分确定性指标、规则结果和LLM结论。
- 不展示隐藏思维过程。
- AI原始Revision只读。
- 人工修订创建新Revision，并提供字段级/结构化前后对比。
- 输出Schema错误的结果进入错误视图，不出现“提交审批”操作。

## 12. Action Preview与执行

- Preview逐项展示目标、动作类型、before、after、currency、风险和来源Revision。
- 提交前进行摘要确认；高风险动作二次确认。
- 提交后显示不可变version和hash摘要。
- 审批页明确显示所审批版本，避免查看当前草稿却审批旧版本。
- 执行页逐项回填实际值、结果、时间和证据附件。
- 预览值、实际值和后续评估值不能互相覆盖。

## 13. 金额与指标

- 所有金额同时展示currency。
- 不直接合并不同currency。
- 百分比表示方式待确认；组件必须由API Schema提供的单位格式化。
- 零分母结果显示为明确的不可计算/空值，不伪造为0%。

## 14. 可访问性与安全

- 所有关键动作支持键盘操作、明确标签和焦点反馈。
- 二次确认不能只依赖颜色。
- 不在localStorage存放密码或未确认可存放的Refresh Token。
- 不在前端日志打印Token、完整报表行或LLM敏感输入。
