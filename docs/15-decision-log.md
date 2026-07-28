# 15 决策日志

## 1. 使用规则

- 状态值：`待确认`、`已确认`、`已否决`、`已取代`。
- 未确认前不得实现“禁止实施”列中的内容。
- 推荐方案仅供人工决策，不代表已选定。
- 已确认时补充确认人、日期、依据和受影响文档。
- 2026-07-28 起，根目录 `codex_master_goal_amazon_ads_v1.md` 是唯一主规格。下方“主规格同步确认”中同 ID 的新状态优先于旧“待确认”行；保留旧行用于追溯原问题，不表示继续阻塞。

## 2. 已确认决策

| ID | 决策 |
|---|---|
| D-001 | User为全局账号，不含tenant_id；通过TenantMembership关联Tenant |
| D-002 | 个人卖家也创建Tenant，Team可选 |
| D-003 | 功能权限采用RBAC |
| D-004 | Store数据权限为UserStoreAccess与TeamStoreAccess并集，无显式拒绝 |
| D-005 | V1模块化单体、前后端分离、REST/JSON、`/api/v1` |
| D-006 | V1不连接真实Amazon Advertising API，不允许AI自动投放 |
| D-007 | V1单级审批，按V1a—V1d交付 |
| D-008 | 核心状态只通过Service转换；历史证据只追加 |

## 2.1 主规格同步确认（2026-07-28）

确认依据：项目发起人指定 `codex_master_goal_amazon_ads_v1.md` 为当前唯一主需求并要求执行 Phase 0。确认人：项目发起人。记录人：Phase 0 总体实现代理。

| ID | 状态 | 主规格确认结果 | 仍需验证但不改变范围的事项 |
|---|---|---|---|
| D-101 | 已确认 | Tenant → AmazonStore → StoreMarketplace → Marketplace；一个 StoreMarketplace 可有多个 AdvertisingProfile，Profile 只属于一个 StoreMarketplace | 用真实账号/报表核对外部语义 |
| D-102 | 已确认 | V1 同时完整支持 Campaign、Targeting、Search Term 三类报表，不再只选一种 | 三类均需真实脱敏样例最终验证 |
| D-103 | 已确认 | V1 完整实现 Sponsored Products；Brands/Display 仅保留扩展边界 | 真实报表字段验证 |
| D-104 | 已确认 | Campaign、Targeting、Search Term 分别使用独立 Daily Metric 事实表 | 自然键和索引需样例验证 |
| D-105 | 已确认 | Upload/Task/Batch 只追加；新 Batch 可修正当前权威事实；权威记录必须追溯来源 Batch | 字段级重述与归因边界需样例验证 |
| D-106 | 已确认 | 原始报表和证据文件默认保留 365 天；到期可归档/删除正文，保留元数据、Batch 和审计 | 环境覆盖和归档介质待实现期细化 |
| D-109 | 已确认 | ProductListing 在 `(store_marketplace_id, seller_sku)` 唯一 | 真实报表 SKU 空值/规范化规则待验证 |
| D-111 | 已确认 | 动作范围为 Campaign 预算/启停、Keyword 竞价/启停、Product Target 竞价/启停、新增普通 Keyword、新增 Negative Keyword | 上下限、证据和漂移细节待实施期确认 |
| D-115 | 已确认 | LLM 仅接收当前 Tenant、已授权 Profile、本次分析必要的最少结构化数据，不发送凭据或其他 Tenant 数据 | 真实 Provider 不属于当前接入范围 |
| D-117 | 已确认 | JWT 双 Token；Access 短期且前端内存优先，Refresh 使用 HttpOnly Cookie | CSRF、SameSite、轮换、吊销细节在 Phase 1/2 固化 |
| D-118 | 已确认 | Python 3.13、Django 5.2 LTS、DRF 3.16.x、Celery 5.6.x、Node 24 LTS、Vite 8.x、MySQL 8.4 LTS、Redis 7.x | Phase 1 必须做实际兼容验证，不得擅自降级 |
| D-119 | 已确认 | 所有金额以 Decimal 字符串和 currency 传输，不存在默认业务币种 | 无 |
| D-121 | 已确认 | 文件级致命错误整份失败；合法行入库、错误行记录；两者并存为 PARTIAL_SUCCEEDED | 具体错误分类需随三类 Schema 固化 |
| D-124 | 已确认 | PERSONAL Tenant Owner 可自我确认；TEAM/COMPANY 提交人不得审批自己的方案 | 代理审批不属于 V1 |
| D-125 | 已确认 | Action 创建/执行前必须校验 beforeValue 仍有效；关键值漂移不能沿用旧批准内容 | 非关键字段容忍列表待实现期确认 |
| D-127 | 已确认 | 原始报表/证据正文默认 365 天；审计长期保留并支持归档 | 法规和生产归档参数待部署期确认 |
| D-128 | 已确认 | `amazon-ads-operations-0.1.1` 持续隔离，未经另行授权不得读取、修改、移动、删除或复用 | 无 |

## 2.2 Phase 1 实施决策（2026-07-28）

确认依据：项目发起人明确授权执行 Phase 1。下列决策只固化基础工程实现，不扩大业务范围。

| ID | 状态 | Phase 1 决策 | 说明 |
|---|---|---|---|
| D-129 | 已确认 | local/prod 使用 MySQL；test 采用 SQLite 单元测试 + MySQL 8.4 容器集成测试 | MySQL 测试数据库位于隔离 Compose tmpfs |
| D-130 | 已确认 | 环境由 `DJANGO_SETTINGS_MODULE` 显式选择 `local/test/prod` | 不使用主机名等模糊自动推断 |
| D-131 | 已确认 | 数据库迁移使用独立 `migrate` Compose 服务和发布步骤 | backend、worker、beat 均不自动迁移 |
| D-132 | 已确认 | requestId 缺失/非法时由 Django 生成，合法客户端值经 Nginx 透传 | 同时写入响应头、响应体和日志 |
| D-133 | 已确认 | JSON camel/snake 转换由 DRF 公共 Parser/Renderer 递归完成 | Serializer 不逐字段手工转换 |
| D-134 | 已确认 | Phase 1 Celery 仅实现无业务语义的 smoke task | Redis 作为 Broker/短期结果，不是正式事实存储 |
| D-135 | 已确认 | 前端认证、Tenant 与 refresh 能力仅保留空扩展点 | 不生成 Token、Tenant 或假登录接口 |
| D-136 | 已确认 | 本机默认 Python 3.12 不改变项目目标；uv 与容器实际使用 Python 3.13.3 | 兼容测试已覆盖 Django、Celery、MySQL 与前端运行结构 |
| D-137 | 已确认 | 生产后端镜像以 uid 10001 运行，Django 使用 Gunicorn；前端由 Nginx 提供构建产物 | TLS 终止、监控、备份和高可用仍待生产环境设计 |
| D-138 | 已确认 | Django 框架内置 `django_*`、`auth_*` 表豁免项目业务表前缀规则；项目自定义表仍必须使用已批准的模块前缀 | 项目发起人于 2026-07-28 确认；不改写已执行的 Django 基础迁移 |
| D-139 | 已确认 | ECharts 不在 Phase 1 安装；首次实现真实 Dashboard 或趋势图页面时再引入 | 避免添加当前未使用依赖，不改变主规格最终技术栈 |
| D-140 | 已确认 | 自动化浏览器 E2E 不作为 Phase 1 的 20 项阻塞条件；后续业务联调和 Phase 7 再实现 | 现有真实浏览器验收有效，但不得描述为已完成可重复自动化 E2E |

## 2.3 Phase 2A 认证决策（2026-07-28）

确认依据：项目发起人明确授权“Phase 2A：账号认证与 JWT 双 Token”，并禁止进入 Phase 2B。

| ID | 状态 | Phase 2A 决策 | 说明 |
|---|---|---|---|
| D-141 | 已确认 | 使用 `djangorestframework-simplejwt 5.5.x` 负责 JWT 签名和校验 | 该版本支持 Python 3.13、Django 5.2；不自行实现密码学 |
| D-142 | 已确认 | Refresh Token 原文只存在于 HttpOnly Cookie；项目以 SHA-256 摘要记录活动刷新会话 | 自有表 `sys_refresh_token` 满足项目表名前缀并支持轮换、撤销、重放拒绝 |
| D-143 | 已确认 | 邮箱执行 `strip + casefold`，并以现有唯一约束加 `Lower(email)` 唯一约束保证大小写唯一 | 新增 `accounts.0002_authentication`，不修改 `0001_initial` |
| D-144 | 已确认 | local/test Cookie 为 HttpOnly、Secure=false、SameSite=Lax；prod 强制 HttpOnly=true、Secure=true，SameSite 可配置 | `SameSite=None` 额外要求 Secure |
| D-145 | 已确认 | 前端 Access Token 只存内存；并发 401 合并为一次 Refresh；登录/刷新/退出不参与自动刷新 | Refresh 失败清空认证状态并跳转登录，不引入 Tenant 上下文 |
| D-146 | 已确认 | `audit_auth_event` 只追加认证事件，记录邮箱哈希和 requestId，不记录凭据或 Token | 完整 AuditLog 业务模块不属于 Phase 2A |

Phase 2A 验证状态：API 认证链路、SQLite/MySQL 后端测试、前端单元测试与生产构建通过。自动浏览器验收为 `NOT VERIFIED`，原因是 Codex 浏览器控制工具初始化和连接失败；未继续尝试工具修复。Phase 2B 未获授权。

## 2.4 M1 Tenant、Store、Profile 与权限决策（2026-07-28）

确认依据：项目发起人授权按 `CODEX_FULL_V1_EXECUTION_GOAL.md` 从 M0 连续执行到 M6，该授权取代 Phase 2B 未授权的历史边界。

| ID | 状态 | M1 决策 | 说明 |
|---|---|---|---|
| D-147 | 已确认 | Tenant、Team、Store、Marketplace、StoreMarketplace、AdvertisingProfile 使用 UUID 主键，Amazon 外部 ID 单独使用字符串字段 | API 始终输出字符串 ID |
| D-148 | 已确认 | Membership 使用 OWNER/ADMIN/MEMBER；Owner/Admin 对当前 Tenant 全 Store/Profile 具有 MANAGE | 个人 Tenant 不强制 Team |
| D-149 | 已确认 | Store 与 Profile 分别使用 User/Team 白名单，Profile 等级按 VIEW→OPERATE→APPROVE→EXECUTE→MANAGE 取最高 | 无显式 DENY |
| D-150 | 已确认 | 功能权限码由迁移维护固定目录；Tenant 自定义角色只能组合目录内权限 | 系统角色不可通过业务 API 删除 |
| D-151 | 已确认 | 完全越出 Tenant/Store/Profile 范围返回 404；当前 Tenant 内缺功能或动作等级返回 403 | API 绕过前端同样执行 |
| D-152 | 已确认（兼容覆盖 D-147 的物理主键部分） | 现有 MySQL 已由 bigint 主键历史迁移创建且保存跨模块关联数据；本次 RC1 协调保留该物理主键谱系，不做破坏性 UUID 重写 | 当前任务明确规定冲突时数据安全优先；API ID 仍统一输出字符串，Amazon 外部 ID 仍使用独立字符串字段；详见 `MIGRATION_RECONCILIATION.md` |

## 3. 强制待确认事项

说明：D-101、D-102、D-103、D-104、D-105、D-106、D-109、D-111、D-115、D-117、D-118、D-119 已由 2.1 节确认。其原始行保留为历史背景，执行状态以 2.1 节为准。D-120 仍是三类报表最终验收阻塞。

| ID/问题 | 为什么确认 | 选项及影响 | 推荐方案 | 推荐理由 | 未确认前禁止实施 |
|---|---|---|---|---|---|
| D-101 Store/Marketplace/Profile基数 | 决定全库归属外键和唯一键 | Store跨站点：需关系表；Store=站点实例：简单但同卖家多个Store；Profile一对一/多对一影响广告范围 | 用真实账号结构和报表样例评审后选择 | 文本无法唯一推出真实基数 | `ads_store`最终字段/约束、下游Model和迁移 |
| D-102 V1首种报表 | 决定字段、粒度、指标和异常 | Campaign：总览简单；Targeting：适合投放对象；Search Term：优化价值高但复杂；Advertised Product：商品视角 | 在四选一中基于脱敏样例和业务优先级确认一种 | 无样例无法验证自然键和归因 | ReportSchema、解析器、事实表和验收数据 |
| D-103 V1首种广告类型 | 不同类型的Ad/Target/商品关系不同 | Sponsored Products：闭环较小；Brands/Display：结构和创意更复杂 | 首版只选择一种，优先级由业务确认 | 避免多类型抽象扩大V1 | 广告Model最终结构、动作类型 |
| D-104 DailyMetric事实模型 | 决定粒度完整性、查询和去重 | 统一表：接口一致但稀疏；多表：强约束但重复；混合：主题事实+统一查询 | 混合模型，V1只实现首种报表权威事实 | 平衡完整性和扩展性 | 事实Model、唯一键、聚合API |
| D-105 迟到/重述规则 | Amazon数据可能后续变化 | 忽略：旧数据错误；覆盖：历史弱；版本追加+权威更新：复杂但可追溯 | 原始批次追加，权威事实按确认规则更新并记来源 | 同时保留最新值与血缘 | 跨批次upsert和去重逻辑 |
| D-106 原始行保留期 | 影响复现、合规和成本 | 短期：成本低；长期：可追溯；按环境/类型分级：治理复杂 | 按数据类别定义保留期，至少覆盖导入争议窗口 | 不宜用单一永久/立即删除 | 生命周期任务、删除/归档配置 |
| D-107 文件最大尺寸 | 影响Nginx、DRF、存储和任务超时 | 小限制：稳定但用户需拆分；大限制：体验好但资源风险 | 根据真实样例P95/P99并留余量 | 无样例指定数值属于猜测 | 上传限制、代理超时、验收大文件 |
| D-108 编码和工作表规则 | 决定解析确定性 | 仅UTF-8/首表：简单；自动探测/指定表：兼容但复杂；模板化：稳定 | 首种报表明确允许编码和工作表选择 | 自动猜测可能导错数据 | 解析器和上传表单最终规则 |
| D-109 SKU唯一范围 | 决定ProductListing唯一键 | Tenant级：严格；Store级：常见且安全；Store+Marketplace：最明确 | 倾向Store+Marketplace，需样例确认 | 避免跨店同SKU冲突 | Listing唯一约束和导入去重 |
| D-110 一个ASIN能否对应多个Product | 决定Product与CatalogItem基数 | 禁止：聚合简单；允许：适配套装/内部分类但需治理 | 允许关系模型表达多对一可能性，业务规则确认后约束 | 不把Amazon目录和内部产品混为一体 | Product-Catalog最终基数约束 |
| D-111 Preview动作类型 | 决定动作Schema、校验和执行回填 | 预算、竞价、启停、关键词/Target各有不同风险 | V1只选少量高价值且可人工验证的动作 | 先验证审批执行闭环 | ActionPreviewItem Schema、页面和验收 |
| D-112 高风险执行截图 | 决定证据可信度和附件量 | 不强制：成本低；全部强制：负担高；按风险强制：需分级 | 按风险等级强制 | 平衡可审计与操作成本 | 证据必填守卫和确认流程 |
| D-113 观察窗口 | 决定何时评估 | 固定天数；按动作类型；人工选择 | 按动作类型提供受控默认并记录快照 | 不同动作见效时间不同 | dueAt计算和评估调度 |
| D-114 基线窗口 | 决定before指标 | 紧邻前窗；同比；对照组 | V1采用固定紧邻前窗，后续扩展 | 最简单可复现，但需业务确认长度 | 效果公式和Snapshot Schema |
| D-115 LLM允许接收的数据 | 涉及商业敏感和合规 | 完整数据：效果高风险高；脱敏聚合：风险低；私有模型：成本高 | 最小化、脱敏、结构化白名单 | 遵循最小数据原则 | 真实Provider输入构造 |
| D-116 LLM输入输出保留期 | 影响审计、隐私和成本 | 不留正文；短期；长期；按字段分级 | 保存结构化结论和引用，敏感正文短期或不留 | 满足追溯且降低泄露面 | 清理任务、Provider日志配置 |
| D-117 认证方式 | 决定CSRF、刷新、退出和存储 | HttpOnly Cookie Session：Web简单安全；Access+Refresh：多客户端灵活但复杂 | 若仅同域Web，倾向Cookie；确认多客户端需求后决定 | 避免无需求引入Token复杂性 | 认证接口、中间件和前端持久化 |
| D-118 具体技术版本 | 决定兼容、锁文件和镜像 | 最新稳定；维护期稳定组合；组织基线 | 兼容矩阵实验后人工冻结稳定组合 | 当前明确禁止自行决定 | 初始化、安装依赖、锁文件和镜像 |
| D-119 金额示例币种 | 防止示例被误作默认业务币种 | 固定示例币种；多币种示例 | 示例可任选但显著标记，实际字段强制currency | 文档示例不应创建隐含默认 | 任何无currency的金额接口/字段 |
| D-120 首份真实脱敏报表样例 | 没有样例无法验证Schema和粒度 | 业务提供完整脱敏文件；只提供列清单；构造样例 | 提供至少一份完整、保留格式的脱敏文件 | 列清单不足以暴露编码、标题行和粒度问题 | 报表解析、事实Model和V1a验收 |

## 4. 衍生待确认事项

说明：D-121、D-124、D-125、D-127、D-128 已由 2.1 节确认；未确认的取消、Agent 部分失败、任务级部分执行等细节继续保持待确认。

| ID/问题 | 为什么确认 | 选项及影响 | 推荐方案 | 推荐理由 | 未确认前禁止实施 |
|---|---|---|---|---|---|
| D-121 PARTIAL_SUCCEEDED阈值 | 决定部分错误是否接受 | 任一成功即部分；错误率阈值；关键字段错误即失败 | 区分文件级致命错误与行级可隔离错误 | 可解释且适合异步导入 | 导入终态判定 |
| D-122 IMPORTING能否取消 | 数据库写入中取消可能破坏一致性 | 禁止；批次边界取消；立即中断 | 只在安全批次边界取消 | 保证事实与计数一致 | 取消按钮和Task实现 |
| D-123 Agent部分失败策略 | 决定是否产生建议 | 任一失败全失败；必需/可选Agent；降级建议 | 为每个Agent声明必需性，综合策略必需输入缺失则失败 | 避免不完整建议伪装成功 | Orchestrator完成条件 |
| D-124 是否禁止自批 | 涉及职责分离 | 允许；全部禁止；仅高风险禁止 | 至少高风险动作禁止提交人自批 | 提高关键动作可信度 | Approval守卫 |
| D-125 APPROVED到READY漂移规则 | 批准后对象可能已变化 | 任意变化过期；容忍非关键变化；重新取值人工确认 | before关键值变化则失效并重建Version | 确保批准内容与执行一致 | 执行前校验 |
| D-126 执行部分成功表示 | 多Item可能结果不同 | 任务增加部分终态；仍WAITING_CONFIRMATION并逐项展示；失败整个任务 | 先逐项记录，任务确认规则结合允许动作确定 | 不擅自新增/改名现有状态 | 任务汇总逻辑 |
| D-127 Audit/File保留期 | 影响法规、成本和删除权 | 永久；固定年限；分级 | 按法规与业务类别分级 | 审计和附件价值不同 | 归档和物理清理 |
| D-128 现有隔离目录归属 | 防止误覆盖 | 属于其他项目；本项目遗留；占位 | 人工明确并继续保持隔离，除非另行授权 | 当前规则禁止读取复用 | 对该目录的任何读取/修改/移动/删除 |

## 5. 优先确认顺序

1. D-101 Store/Marketplace/Profile基数。
2. D-102、D-103、D-120首种报表、广告类型和脱敏样例。
3. D-104、D-105事实模型和重述规则。
4. D-109、D-110商品身份约束。
5. D-117、D-118认证和运行环境基线。
