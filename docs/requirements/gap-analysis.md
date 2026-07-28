# Phase 0 完整差距清单

## 1. 判定口径

- **已存在**：仓库中已有可核验交付物；若为文档，仅表示文档存在，不代表业务能力存在。
- **部分存在**：已有设计或局部说明，但未实现、未测试，或与主规格有冲突。
- **缺失**：仓库中没有对应代码、配置、测试或文档交付。
- **需要真实 Amazon 报表样例才能最终验证**：可先以 fixtures 开发，但最终 Schema、粒度或性能不能仅凭当前文档确认。

## 2. 治理、仓库和文档

| 能力/交付 | 状态 | 证据与差距 |
|---|---|---|
| 主规格 | 已存在 | 根目录 `codex_master_goal_amazon_ads_v1.md`，1,174 行；文件名与请求中的 `CODEX_MASTER_GOAL.md` 大小写/名称不同 |
| 根 README | 部分存在 | 有项目定位和旧文档导航，但仍写版本/认证/首报表待确认，且没有启动命令 |
| 长期工程规则 | 已存在 | Phase 0 已更新 `AGENTS.md` |
| Phase 1—7 计划 | 已存在 | Phase 0 已创建 `PLANS.md` |
| 需求范围文档 | 已存在 | Phase 0 已创建 confirmed/out-of-scope |
| 团队协作文档 | 已存在 | Phase 0 已创建 ownership/handoffs/sequence |
| 总体架构/领域/权限/状态/API/测试设计 | 部分存在 | 00—15 文档和 8 个 Mermaid 文件存在；多处仍基于旧“一报表/一种广告类型/Store 授权”规格 |
| 主规格要求的 architecture 子目录文档集 | 缺失 | 现有平铺文档可复用内容，但要求的 11 份路径尚未建立 |
| api/error-codes 文档 | 部分存在 | `docs/07-api-conventions.md` 含部分错误码，目标路径和完整枚举缺失 |
| deployment 文档集 | 缺失 | 无本地、Docker、生产、备份恢复、故障排查文档 |
| testing 文档集 | 部分存在 | 有测试策略和验收标准；无验收清单、性能计划/结果目标路径 |
| presentation 文档集 | 缺失 | 无讲稿、演示脚本、常见问题、当前状态、一页摘要 |
| AI 开发记录 | 缺失 | 无 prompts、implementation logs、test results、ADR、change summaries 目录与记录 |

## 3. 工程与运行环境

| 能力/交付 | 状态 | 证据与差距 |
|---|---|---|
| Git 仓库 | 缺失 | `git rev-parse` 和 `git status` 均报告不是 Git 仓库 |
| Django 工程 | 缺失 | 无 backend、manage.py、settings、URL 或应用 |
| Vue 工程 | 缺失 | 无 frontend、package.json 或源码 |
| Python 依赖/锁 | 缺失 | 无 pyproject.toml、uv.lock；机器默认 Python 3.12.4，与目标 3.13 不符 |
| 前端依赖/锁 | 缺失 | 无 package.json、pnpm-lock.yaml；机器 Node 24.10.0、pnpm 11.9.0 可用 |
| MySQL/Redis/Nginx 配置 | 缺失 | 无配置或 Compose；本机命令未发现 mysql、redis-server、nginx |
| Dockerfile/Compose | 缺失 | `docker compose config --quiet` 报无配置文件 |
| local/test/prod 环境 | 缺失 | 无环境分层和 `.env.example` |
| 启动能力 | 缺失 | 无可启动应用、服务定义或 README 命令 |
| CI/CD | 缺失 | 无 `.github` 或其他流水线 |

## 4. 基础平台、认证和权限

| 能力/交付 | 状态 | 证据与差距 |
|---|---|---|
| 统一响应、异常、requestId、camelCase | 部分存在 | 有设计文档，无代码/OpenAPI/测试 |
| live/ready | 部分存在 | 主规格与部署图有要求，无端点 |
| 自定义 User | 部分存在 | 逻辑设计存在，无 Model/首迁移 |
| Tenant/Membership/Team | 部分存在 | 设计存在，无实现 |
| JWT 双 Token | 部分存在 | 主规格已确认，旧文档仍写待确认，无实现 |
| RBAC | 部分存在 | 权限码和模型设计存在，无实现 |
| StoreMarketplace/Profile 模型 | 部分存在 | 主规格已确认层级；旧文档/图仍使用旧 Store—Marketplace 关系，无实现 |
| Store/Profile 授权等级 | 部分存在 | 主规格定义 Profile 等级；旧权限文档只有 Store 授权，无实现 |
| 跨 Tenant/Store/Profile 403/404 | 部分存在 | 设计和测试矩阵存在，无自动化证据 |
| 认证/上下文前端 | 缺失 | 无页面、Pinia、Axios 或路由 |

## 5. 广告、产品和报表

| 能力/交付 | 状态 | 证据与差距 |
|---|---|---|
| Sponsored Products 模型 | 部分存在 | 候选逻辑表存在，旧文档仍称广告类型待确认，无实现 |
| Product/ASIN/SKU/Listing | 部分存在 | 候选关系存在，旧唯一范围描述与主规格未完全同步，无实现 |
| FileStorage | 部分存在 | Adapter 与元数据原则有设计，无实现 |
| ReportSource | 部分存在 | 主规格定义三种 Source，无接口或实现 |
| Campaign Report | 需要真实 Amazon 报表样例才能最终验证 | 无样例、Schema、解析器、fixture 或测试 |
| Targeting Report | 需要真实 Amazon 报表样例才能最终验证 | 无样例、Schema、解析器、fixture 或测试 |
| Search Term Report | 需要真实 Amazon 报表样例才能最终验证 | 无样例、Schema、解析器、fixture 或测试 |
| CSV/Excel 上传 | 缺失 | 无 API、存储、大小/编码/工作表实现 |
| Celery 异步导入 | 缺失 | 无 Celery 项目、Task、队列 |
| 文件级/行级错误与部分成功 | 部分存在 | 设计和状态名存在，无实现 |
| 重复、重处理、批次只追加 | 部分存在 | 设计原则存在，无约束/Service/测试 |
| 大文件流式/分块/批量 | 需要真实 Amazon 报表样例才能最终验证 | 无实现；文件规模和行特征未知 |
| 字段映射与自然键 | 需要真实 Amazon 报表样例才能最终验证 | 候选模型存在，真实列名/粒度未知 |
| 迟到/重述 | 需要真实 Amazon 报表样例才能最终验证 | 主规格确认血缘原则，边界数据与确定算法尚未验证 |
| 六份报表 fixtures | 缺失 | `tests/fixtures/reports` 不存在 |
| 报表前端 | 缺失 | 无上传、任务、错误、原文件页面 |

## 6. 指标、异常与分析页面

| 能力/交付 | 状态 | 证据与差距 |
|---|---|---|
| 三类 Daily Metric 分表 | 部分存在 | 主规格确认；旧数据库设计仍是统一 `analytics_daily_metric_fact`，无实现 |
| CTR/CPC/CVR/ACOS/ROAS | 部分存在 | 公式和测试策略存在，无代码/测试 |
| 零分母原因 | 部分存在 | 主规格定义原因，无实现 |
| 预算/状态/竞价日快照 | 部分存在 | 主规格定义，无事实表 |
| 权威粒度查询 | 部分存在 | 主规格定义，无 Selector |
| 币种/Marketplace 隔离 | 部分存在 | 设计存在，无代码/测试 |
| 目标 ACOS 继承 | 部分存在 | 规则存在，无配置/Service |
| 异常规则和 INSUFFICIENT_DATA | 部分存在 | 设计存在，无规则引擎 |
| Dashboard/Campaign/Targeting/Search Term API | 缺失 | 无 API |
| 对应前端页面 | 缺失 | 无前端 |

## 7. AI、动作、执行、知识和审计

| 能力/交付 | 状态 | 证据与差距 |
|---|---|---|
| LLMProvider/MockLLMProvider | 部分存在 | 架构设计存在，无接口/实现 |
| 四类 Agent/Orchestrator | 部分存在 | 职责和 Mermaid 存在，无代码 |
| 统一 JSON Schema | 部分存在 | 外层字段已定义，无 Schema 文件/校验 |
| Agent 范围/隐私边界 | 部分存在 | 规则存在，无防越权测试 |
| Recommendation/Revision | 部分存在 | 候选模型/状态存在，无实现 |
| 八类动作 | 部分存在 | 主规格已列举，旧决策仍称待确认，无 Schema/Service |
| Action Preview/Version | 部分存在 | 设计与状态机存在，无实现 |
| 单级审批及自批规则 | 部分存在 | 主规格明确 PERSONAL 与 TEAM/COMPANY 规则，旧文档待确认，无实现 |
| 人工执行与部分成功 | 部分存在 | 流程设计存在，无实现 |
| 基础效果评估 | 部分存在 | 候选状态/模型存在，窗口和公式未冻结，无实现 |
| 轻量知识中心 | 部分存在 | 主规格明确只读内容，旧文档偏好/策略范围不同，无实现 |
| 只追加 AuditLog | 部分存在 | 设计存在，无数据库保护/API/测试 |
| AI/建议/审批/执行前端 | 缺失 | 无前端 |

## 8. 测试、性能与交付

| 能力/交付 | 状态 | 证据与差距 |
|---|---|---|
| 后端单元/集成测试 | 缺失 | 无测试目录或测试配置 |
| 前端组件测试/typecheck/build | 缺失 | 无前端工程 |
| OpenAPI 校验/TS 类型 | 缺失 | 无 Schema 或生成流程 |
| 浏览器 E2E | 缺失 | 无应用或脚本 |
| Compose 启动测试 | 缺失 | 无 Compose 文件 |
| README 从零复现 | 缺失 | 无运行工程或命令 |
| 并发安全测试 | 缺失 | 无代码/脚本 |
| Locust/性能报告 | 缺失 | 无脚本或实测；不得声称达到目标 |
| 300 用户/200 RPS 等目标 | 缺失 | 仅为主规格目标，尚无测试结果 |
| 17 步演示链路 | 缺失 | 当前连登录都不可执行 |

## 9. 关键契约冲突

| 冲突 | 主规格 | 旧文档 | 保守处理 |
|---|---|---|---|
| 报表范围 | Campaign/Targeting/Search Term 三类全做 | 01/13/15 写首种报表或一种报表 | 不删三类需求；同步决策和阶段计划，真实样例仅影响最终验证 |
| 广告类型 | Sponsored Products | 01/03/15 写待确认 | 以主规格为准，不实现 Brands/Display |
| 技术版本 | 固定 Python 3.13 等 | 10/15 写全部待确认 | 固定目标版本，Phase 1 做兼容验证，不擅自降级 |
| 认证 | JWT 双 Token | 02/07/09/15 写 Session/Token 待确认 | 采用主规格；Phase 1/2 补安全细节 |
| Store/Profile 基数 | StoreMarketplace + Profile | 03/04/图仍是旧关系 | 不复用旧候选约束；先同步逻辑设计再建 Model |
| Profile 权限 | 五级 Profile 授权 | 05 只有 Store 授权 | Phase 2 同时设计 Store 与 Profile，不把 Store 权限替代 Profile |
| Daily Metric | 三张独立事实表 | 04 是统一事实表候选 | Phase 4 分表，统一只读接口可由 Selector 提供 |
| V1 范围 | 高并发框架和参考压测目标 | 00/01 写非商业级高并发 | 保留目标但不承诺已达；Phase 6 实测 |
| 知识中心 | 只读轻量文章必须真实可用 | 03/09 偏好/团队策略为主 | 先完成轻量文章；偏好/策略仅按主规格基础闭环实施 |

## 10. 实施阻塞

- Phase 1 可在明确授权后开始，但必须先完成运行时兼容验证和旧决策同步。
- Phase 2 建 Model 前必须把 StoreMarketplace/Profile 与 Profile 授权写入一致的数据/权限设计。
- Phase 3 可用虚构 fixtures 建框架，但三类真实报表验收在获得脱敏样例前保持阻塞。
- Phase 4 事实自然键与重述边界必须以报表粒度证据验证。
- Phase 5 效果窗口、证据强制和部分执行汇总状态仍需实施期确认。
- Phase 6 所有性能数字必须来自真实命令、环境和报告。
