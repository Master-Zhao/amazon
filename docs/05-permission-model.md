# 05 权限与数据隔离模型

## 1. 授权公式

一次受保护操作必须同时满足：

`有效TenantMembership ∩ 功能权限 ∩ Store授权 ∩ 对象Tenant归属 ∩ 对象Store归属 ∩ 状态守卫`

任一条件不满足即拒绝。前端菜单、路由和按钮不参与最终授权裁决。

## 2. 功能权限：RBAC

关系固定为：

`User → TenantMembership → UserRole → Role → RolePermission → Permission`

- User是全局账号。
- Role绑定在当前TenantMembership上下文，不是User的全局永久属性。
- Permission使用稳定编码；编码移除需要兼容期。
- V1可使用系统预置角色，租户自定义角色的开放时间待确认。

### 推荐预置角色

| 角色 | 典型用途 |
|---|---|
| `TENANT_ADMIN` | Tenant成员、角色、Store和授权管理 |
| `AD_OPERATOR` | 导入、分析、修订建议、创建预览 |
| `DATA_ANALYST` | 查看数据、创建分析、查看建议 |
| `APPROVER` | 审批授权Store的Preview |
| `EXECUTOR` | 查看并回填人工执行任务 |
| `VIEWER` | 授权Store内只读查看 |

角色只是权限集合，不应在业务代码中用角色名替代Permission判断。

## 3. 稳定权限编码

| 权限编码 | 用途 |
|---|---|
| `tenants.switch` | 切换当前Tenant |
| `dashboard.view` | 查看工作台 |
| `reports.upload` | 上传报表 |
| `reports.view` | 查看上传、任务和错误 |
| `reports.cancel` | 取消未完成导入 |
| `campaigns.view` | 查看Campaign及指标 |
| `analysis.create` | 创建分析任务 |
| `analysis.view` | 查看分析及Agent运行 |
| `analysis.cancel` | 取消分析 |
| `recommendations.view` | 查看建议 |
| `recommendations.review` | 接受、修订或拒绝建议 |
| `recommendations.submit` | 将建议提交生成Action Preview |
| `recommendations.withdraw` | 撤回允许撤回的建议 |
| `actions.view` | 查看Action Preview |
| `actions.create` | 创建或修订Preview草稿 |
| `actions.submit` | 提交Preview审批 |
| `actions.withdraw` | 撤回允许撤回的Preview |
| `approvals.view` | 查看待审批项 |
| `approvals.decide` | 批准、拒绝或退回 |
| `executions.view` | 查看人工执行任务 |
| `executions.execute` | 开始执行并逐项回填 |
| `executions.confirm` | 确认执行结果 |
| `executions.cancel` | 取消尚未开始的执行 |
| `evaluations.view` | 查看效果评估 |
| `evaluations.run` | 发起/重试效果评估 |
| `knowledge.view` | 查看偏好和知识 |
| `knowledge.manage` | 人工确认偏好、策略和规则 |
| `audit.view` | 查看授权范围内审计 |
| `admin.members.manage` | 管理Membership和Team |
| `admin.roles.manage` | 管理角色授权 |
| `admin.stores.manage` | 管理Store/Profile及Store授权 |

## 4. Store数据权限

最终Store集合固定为：

`有效UserStoreAccess ∪ 用户有效TeamMember对应的有效TeamStoreAccess`

V1没有显式拒绝权限，因此不存在“拒绝优先级”。没有Team的个人卖家只依赖UserStoreAccess。

计算要求：

- Access、Membership、Team、Store必须属于同一Tenant。
- 过期、停用或尚未生效的授权不计入。
- 当前Tenant切换后必须重新计算，不复用其他Tenant缓存。
- 缓存只是加速；权威授权来自MySQL。

## 5. 请求上下文

后端从已认证User和受信任的当前Tenant选择建立RequestContext，至少包含：

- userId。
- tenantId和tenantMembershipId。
- permissionCodes。
- allowedStoreIds。
- requestId。

客户端提交的tenantId或storeId不能单独作为授权证据。对象通过ID加载后还要检查其tenant_id和store_id。

## 6. 403与404

- 用户有权知道资源存在但缺少动作权限时，返回403。
- 对跨Tenant、跨Store或可能泄露资源存在性的对象查询，统一按404处理。
- 对列表查询直接过滤到授权范围，不返回“被过滤对象数量”。
- 审计中记录真实拒绝原因，但对客户端使用稳定且不过度暴露的消息。

## 7. 异步任务和Agent

- 创建任务时检查权限和Store范围。
- Celery执行时重新加载Membership、对象归属和任务快照。
- Agent只能接收AnalysisScopeSnapshot内的数据。
- Agent工具调用必须再次带tenant/store过滤，不能信任模型生成的对象ID。
- 用户在任务运行期间失去权限时，是否允许任务完成但禁止查看，需在安全评审中确认；推荐执行前重新校验并取消未开始步骤。

## 8. 管理与审计

以下操作必须写AuditLog：

- 登录、Tenant切换失败和敏感认证事件。
- Membership、Role、Permission和StoreAccess变更。
- 文件上传、取消、导入重试。
- 建议修订、提交、撤回。
- Preview提交、审批决定。
- 执行回填、确认和失败。
- 知识确认、策略发布。

## 9. 权限测试矩阵

至少覆盖：

- 同一User在不同Tenant拥有不同Role。
- 无Team个人卖家通过直接授权工作。
- 团队授权撤销后访问立即失效或按已确认缓存期限失效。
- 有功能权限但无Store权限。
- 有Store权限但无功能权限。
- 跨Tenant对象ID猜测。
- 跨Store列表、详情、导出、异步任务和附件下载。
- 前端显示错误时后端仍能独立拒绝越权请求。
