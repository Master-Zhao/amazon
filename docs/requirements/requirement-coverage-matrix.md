# V1 需求覆盖矩阵

状态只使用 `IMPLEMENTED_AND_TESTED`、`IMPLEMENTED_NOT_FULLY_VERIFIED`、`RESERVED_BY_CONFIRMED_SCOPE`、`BLOCKED_BY_REAL_SAMPLE`、`NOT_IMPLEMENTED`。本矩阵随 M0—M6 更新；“测试”列只记录实际证据。

| ID | 需求 | 来源 | 模块 | 实现/迁移/API/页面 | 测试与文档 | 状态 | 验证证据与风险 |
|---|---|---|---|---|---|---|---|
| AUTH-001 | 自定义全局 User 与邮箱登录 | 主规格 6、7 | accounts | `accounts.User`、0001/0002、`/auth/login`、登录页 | `test_authentication.py`、认证设计 | IMPLEMENTED_AND_TESTED | SQLite 51 项、前端 28 项基线包含认证 |
| AUTH-002 | JWT Access Token 仅存前端内存 | 主规格 6 | accounts/auth | Bearer API、Pinia auth store | 后端/前端认证测试 | IMPLEMENTED_AND_TESTED | 无 localStorage/sessionStorage 持久化 |
| AUTH-003 | HttpOnly Refresh Cookie | 主规格 6 | accounts | login/refresh Cookie | Cookie 属性测试 | IMPLEMENTED_AND_TESTED | 生产域名/TLS 未现场验证 |
| AUTH-004 | Refresh 轮换、吊销与重放拒绝 | 主规格 6 | accounts | `sys_refresh_token`、refresh/logout | 轮换/撤销/并发事务测试 | IMPLEMENTED_AND_TESTED | MySQL 证据来自 Phase 2A |
| AUTH-005 | `/auth/me` 与用户禁用 | 主规格 6 | accounts | `/auth/me` | disabled/expired/forged tests | IMPLEMENTED_AND_TESTED | Token 只证明账号身份 |
| AUTH-006 | 登录成功/失败只追加审计且不泄露凭据 | 主规格 6、17 | accounts | `audit_auth_event` | 审计与日志测试 | IMPLEMENTED_AND_TESTED | 完整业务 AuditLog 在 M4 |
| AUTH-007 | 页面刷新恢复与并发 401 单次刷新 | 主规格 6 | frontend auth | auth store、Axios interceptor | store/http client tests | IMPLEMENTED_AND_TESTED | 浏览器 E2E 在 M5 |
| ORG-001 | User 多 Tenant 与 Tenant 类型 | 主规格 7 | tenants | models/migration/context API | `test_tenant_permissions.py`、data-model | IMPLEMENTED_AND_TESTED | 多 Tenant/类型测试 |
| ORG-002 | TenantMembership、可选 Team、TeamMember | 主规格 7 | tenants | models/services、0001 | personal/team tests | IMPLEMENTED_AND_TESTED | PERSONAL 无虚拟 Team |
| STORE-001 | Tenant→Store→StoreMarketplace→Marketplace→Profile | 主规格 7 | stores | models/0001/context API | context tests、data-model | IMPLEMENTED_AND_TESTED | D-101 已确认；真实账号未验证 |
| STORE-002 | 前端四级上下文与单选自动选择 | 主规格 7 | tenant-context | context store/page | 3 store tests | IMPLEMENTED_AND_TESTED | 多选不自动选择 |
| PERM-001 | 系统/自定义 Role、Permission、UserRole | 主规格 8 | permissions | models/0001/0002/API | role tests、permission-model | IMPLEMENTED_AND_TESTED | 固定权限目录 |
| PERM-002 | Store/Profile User 与 Team 授权并集、最高等级 | 主规格 8 | permissions | models/services/grant API | union/highest tests | IMPLEMENTED_AND_TESTED | 无显式 DENY |
| PERM-003 | Owner/Admin 全范围、无显式 DENY | 主规格 8 | permissions | authorization service | owner tests | IMPLEMENTED_AND_TESTED | MANAGE |
| PERM-004 | 认证∩Membership∩功能∩Store∩Profile | 主规格 8 | permissions | authorize service | 404/403 tests | IMPLEMENTED_AND_TESTED | 跨范围 404、范围内缺动作 403 |
| ADS-001 | Sponsored Products 广告层级 | 主规格 9 | advertising | models/migrations/API | report tests | IMPLEMENTED_AND_TESTED | Brands/Display 仅扩展枚举 |
| ADS-002 | Keyword/ProductTarget/SearchTerm 与匹配类型 | 主规格 9 | advertising | models/import/selectors | targeting/search fixtures | IMPLEMENTED_AND_TESTED | 真实自然键待样例 |
| ADS-003 | Campaign/AdGroup 级 Negative Keyword | 主规格 9 | advertising | NegativeKeyword model | 后续动作测试 | IMPLEMENTED_NOT_FULLY_VERIFIED | M4 新增动作验证 |
| PROD-001 | Product/CatalogItem/Listing 关系与唯一键 | 主规格 9 | products | models/0001 | 迁移约束 | IMPLEMENTED_NOT_FULLY_VERIFIED | D-109；真实 SKU 待样例 |
| REPORT-001 | Campaign CSV/Excel 上传异步导入 | 主规格 10 | reports | upload/task/parser | CSV/XLSX tests | BLOCKED_BY_REAL_SAMPLE | fixture 通过，真实导出待验证 |
| REPORT-002 | Targeting CSV/Excel 上传异步导入 | 主规格 10 | reports | upload/task/parser | targeting fixture | BLOCKED_BY_REAL_SAMPLE | fixture 通过，真实导出待验证 |
| REPORT-003 | Search Term CSV/Excel 上传异步导入 | 主规格 10 | reports | upload/task/parser | search fixture | BLOCKED_BY_REAL_SAMPLE | fixture 通过，真实导出待验证 |
| REPORT-004 | FileStorage 与 FileUploadReportSource | 主规格 10 | integrations | LocalFileStorage/source capability | source tests | IMPLEMENTED_AND_TESTED | 第三方/Amazon API Source 仅预留 |
| REPORT-005 | Upload/Task/Batch 只追加、重处理新建 | 主规格 10 | reports | models/service | duplicate/reprocess test | IMPLEMENTED_AND_TESTED | 新 Batch 血缘 |
| REPORT-006 | 文件级/行级错误与部分成功 | 主规格 10 | reports | parser/service/errors | partial/profile mismatch | IMPLEMENTED_AND_TESTED | 文件级更多格式待真实样例 |
| REPORT-007 | 流式保存、分块解析、批量写入 | 主规格 10、18 | reports | chunked storage/read-only parser | fixture tests | IMPLEMENTED_NOT_FULLY_VERIFIED | 大规模批量性能 M6 |
| METRIC-001 | 三类 Daily Metric 独立事实 | 主规格 11 | analytics | models/0001/selectors | analytics tests | IMPLEMENTED_AND_TESTED | Dashboard 仅 Campaign |
| METRIC-002 | CTR/CPC/CVR/ACOS/ROAS 与 null 原因 | 主规格 11 | analytics | calculations/service/API | formula tests | IMPLEMENTED_AND_TESTED | Decimal/null reason |
| METRIC-003 | Campaign/Targeting 历史快照 | 主规格 11 | analytics | fact models/import | snapshot tests | IMPLEMENTED_AND_TESTED | 不读当前值覆盖历史 |
| METRIC-004 | Target ACOS 继承 | 主规格 11 | analytics | target_acos_for | inheritance tests | IMPLEMENTED_AND_TESTED | Campaign→Profile→Tenant |
| ANOM-001 | 版本化异常规则、风险、数据不足 | 主规格 11 | analytics | rule version/evaluator | anomaly tests | IMPLEMENTED_AND_TESTED | CRITICAL 仅预留 |
| AGENT-001 | 四 Agent、Orchestrator、统一 Schema | 主规格 12 | agents | task/run/schema/API | `test_optimization_workflow.py` | IMPLEMENTED_AND_TESTED | 四 Run 与非法 Schema 已验证 |
| AGENT-002 | LLMProvider 与 MockLLMProvider | 主规格 12 | integrations.llm | Provider 端口/Mock/保留边界 | provider workflow test | IMPLEMENTED_AND_TESTED | 真实 Provider 仅预留且不可用 |
| AGENT-003 | 最小授权输入与后端确定性校验 | 主规格 12 | agents/recommendations | ScopeSnapshot/Service | Profile/before/金额校验 | IMPLEMENTED_NOT_FULLY_VERIFIED | M6 补全动作分支安全矩阵 |
| REC-001 | 11 类 Recommendation 动作 | 主规格 13 | recommendations | model/revision/validator/API | Mock 预算动作测试 | IMPLEMENTED_NOT_FULLY_VERIFIED | 11 类已列入白名单，全部分支待 M5 |
| ACTION-001 | Preview 不可变版本与漂移校验 | 主规格 13 | actions | version/hash/freeze/locks | 冻结更新拒绝测试 | IMPLEMENTED_AND_TESTED | beforeValue 在建议落库前校验 |
| ACTION-002 | PERSONAL 自确认及 TEAM/COMPANY 职责分离 | 主规格 13 | actions | approval service | 两类审批测试 | IMPLEMENTED_AND_TESTED | COMPANY 与 TEAM 共用守卫 |
| ACTION-003 | 只追加 ApprovalRecord 与退回新版本 | 主规格 13 | actions | approval/version models | 状态测试 | IMPLEMENTED_NOT_FULLY_VERIFIED | M5 补退回 UI 与并发测试 |
| ACTION-004 | 人工执行清单、部分回填与证据 | 主规格 13 | actions | task/item/record API | 回填幂等测试 | IMPLEMENTED_NOT_FULLY_VERIFIED | 附件证据上传 UI 待 M5 |
| ACTION-005 | 效果评估基础任务与结果 | 主规格 13 | actions | EffectEvaluation/task | 模型随迁移验证 | IMPLEMENTED_NOT_FULLY_VERIFIED | 当前只建立 baseline |
| KNOW-001 | 轻量只读知识中心 | 主规格 14 | knowledge | seed/API/UI | build/typecheck | IMPLEMENTED_NOT_FULLY_VERIFIED | M5 补页面状态测试 |
| UI-001 | 七个一级菜单与真实业务页面 | 主规格 15 | frontend | M1—M5 | unit/E2E | NOT_IMPLEMENTED | 按里程碑逐步完成 |
| UI-002 | loading/normal/empty/partial/failure/forbidden | 主规格 15 | frontend | M5 | component tests | NOT_IMPLEMENTED | M5 |
| API-001 | 统一信封、camelCase、字符串 ID、Decimal+currency | 主规格 16 | core | Phase 1+各模块 | core/OpenAPI tests | IMPLEMENTED_NOT_FULLY_VERIFIED | 基础已验证，业务模型持续检查 |
| AUDIT-001 | 关键业务 AuditLog 只追加和查询 | 主规格 17 | audit | model/service/API/UI | 实例/批量删除拒绝测试 | IMPLEMENTED_AND_TESTED | M5 扩大事件覆盖 |
| PERF-001 | 队列隔离、超时、有限重试 | 主规格 18 | config | M2/M4/M6 | M6 | NOT_IMPLEMENTED | M6 |
| PERF-002 | 幂等、锁、唯一约束与防重复状态转换 | 主规格 18 | all services | M1—M6 | 并发测试 | NOT_IMPLEMENTED | M6 收口 |
| PERF-003 | 分页、索引、Selector 与 N+1 防护 | 主规格 18 | API/selectors | M1—M6 | 查询数测试 | NOT_IMPLEMENTED | M6 收口 |
| PERF-004 | 限流、背压、缓存隔离、可观测性 | 主规格 18 | core/config | M6 | M6 | NOT_IMPLEMENTED | M6 |
| PERF-005 | 可重复 Locust 压测 | 主规格 18 | tests/performance | M6 | 实测报告 | NOT_IMPLEMENTED | 不虚构 200 RPS 目标 |
| DEPLOY-001 | local/test/prod Compose 与健康检查 | 主规格 19 | infra | Phase 1/M6 | Compose evidence | IMPLEMENTED_NOT_FULLY_VERIFIED | M6 最终从零复验 |
| TEST-001 | 后端/前端/OpenAPI/Compose/E2E 验收 | 主规格 20 | tests | M0—M6 | 各里程碑报告 | IMPLEMENTED_NOT_FULLY_VERIFIED | E2E/业务测试待后续 |
| DOC-001 | 架构/API/部署/测试/演示文档 | 主规格 21 | docs | M0—M6 | 文档清单 | IMPLEMENTED_NOT_FULLY_VERIFIED | M6 最终收口 |
| RESERVED-001 | 第三方报表来源 Adapter | 主规格 4、10 | integrations | M2 | contract tests | RESERVED_BY_CONFIRMED_SCOPE | 不真实接入 |
| RESERVED-002 | Amazon Ads API 报表来源 Adapter | 主规格 4、10 | integrations | M2 | contract tests | RESERVED_BY_CONFIRMED_SCOPE | 不真实调用 |
| RESERVED-003 | Sponsored Brands/Display 扩展边界 | 主规格 4、9 | advertising | M2 | enum tests | RESERVED_BY_CONFIRMED_SCOPE | 不完整实现 |
| RESERVED-004 | CRITICAL 风险枚举 | 主规格 4、11 | analytics | M3 | enum tests | RESERVED_BY_CONFIRMED_SCOPE | 不产生 CRITICAL 规则 |
| RESERVED-005 | 跨 Marketplace/币种汇总 | 主规格 4、11 | analytics | 无 | 隔离测试 | RESERVED_BY_CONFIRMED_SCOPE | V1 禁止 |
| RESERVED-006 | 真实 LLM Provider | 主规格 4、12 | integrations.llm | M4 接口 | contract tests | RESERVED_BY_CONFIRMED_SCOPE | 演示只用 Mock |
| RESERVED-007 | 库存/采购/物流/财务 | 主规格 4、9 | 无 | 无 | 范围文档 | RESERVED_BY_CONFIRMED_SCOPE | 不属于 V1 |
