# 亚马逊关键词竞价优化智能体 PoC 实现任务 V0.1

## 1. 文档基本信息

| 项目 | 内容 |
|---|---|
| 文档版本 | V0.1 |
| 适用仓库 | `amazon-ads-agent-poc` |
| 主规范 | `docs/spec/amazon-ads-agent-loop-engineering-spec-v0.2.md` |
| 场景 | 单 Keyword 高 ACoS 竞价优化 |
| 数据 | 仅合成数据 |
| Reasoner | `ReasonerStub` |
| 环境 | 本地 PoC，不可用于生产 |

## 2. 本次目标

实现一个可运行、可测试、可审计的最小闭环，验证确定性业务计算、受限 Reasoner、运行期反馈、有限修订和人工审批前停止能够协同工作。

## 3. 目标简要概括

> 使用合成亚马逊关键词广告数据，跑通“确定性分析—候选生成—Reasoner 选择—校验反馈—有限自动修订—dry-run 预检—等待人工确认”的最小智能体闭环。

## 4. 背景与依据

本任务以 V0.2 为唯一主工程规范，重点落地 FR-003～FR-013 的计划生成阶段，以及 NFR-003、NFR-004、NFR-007～NFR-010、NFR-013 的确定性和安全边界。这是 PoC，不是生产系统；PoC 的任何简化不得成为生产默认行为。

## 5. 本次范围

- 单个 Keyword 的高 ACoS 竞价降低。
- 输入和输出 Draft 2020-12 JSON Schema 校验。
- Decimal 指标、证据判定、候选集合和变更比例。
- 只从候选集合选择值的 Reasoner Stub。
- 运行期校验、失败分析、最多三次自动修订和同错两次停止。
- 仅 dry-run 的预检、内存审计和 CLI。
- 数据不足、无需修改、正常变更、一次修订成功和连续失败五条路径。

## 6. 非本次范围

不接入真实 Amazon Ads API、大模型、数据库、前端、RBAC 或正式 Approval Service；不实现 Campaign 预算、暂停、删除、归档、生产写入、自动回滚、自动重放、多智能体、长期记忆或向量库。

## 7. 前置条件

Python 3.11+；可解析 YAML 与 Draft 2020-12 Schema；配置文件、四个 Schema 和输入快照必须存在。缺失配置一律 fail-closed。

## 8. 业务场景

合成 Keyword 当前竞价为 `1.20`，spend 为 `315.00`，sales 为 `900.00`，ACoS 为 `0.350000`，目标为 `0.250000`。数据达到最小天数、点击和订单阈值后，Candidate Engine 生成 `1.02`、`1.08`、`1.14`，Reasoner Stub 在其中选择 `1.08`。

## 9. 输入和输出

输入为 `task-input.schema.json` 管理的合成快照。业务 Decimal 均为字符串。正常变更输出必须为 `waiting_for_approval`、`human_approval_required=true`、`production_write_called=false`。数据不足或无规则触发时输出 `completed` 且 `changes=[]`。连续非法输出形成 PoC 人工介入终态，不代表批准或执行。

## 10. 模块拆分

配置与 Schema 加载器负责 fail-closed 读取；指标模块重算五项指标；证据模块决定是否继续；候选引擎生成唯一合法集合；Reasoner Stub 只选择与解释；后处理器冻结变更和摘要；Validator 检查 Schema、引用、边界与状态；Failure Analyzer 决定修订或人工介入；Preflight 仅构造 dry-run 摘要；Audit 追加事件；Workflow 编排状态。

## 11. 工作流

`load → schema validation → metrics → evidence → candidates → reasoner → post-process → runtime validation → optional revision → dry-run preflight → waiting_for_approval`。无变更分支在证据阶段结束，不进入预检。运行期不得调用 pytest 或其他开发测试套件。

## 12. 自动修订机制

初始 `plan_version=1`。可修正失败生成结构化 FailureAnalysis；每次修订更新 `attempt_id` 并将 `plan_version` 加一。最多自动修订三次，最多四个方案版本；相同错误指纹连续出现两次立即停止。成功后不得继续修改。

## 13. 安全边界

仓库没有生产 Adapter，没有 API URL，不访问网络，不读取凭据，不声称真实写入成功。Reasoner 不能创造候选。预检固定 `production_write_called=false`，任何设置为 true 的请求都会抛出安全异常。输出停在等待人工审批；本次不会实现正式审批服务。

## 14. 文件交付清单

交付主规范副本、AGENTS.md、本任务文档、问题记录、版本化 YAML、四个 Schema、五个合成样例、Python `src` 包、pytest 测试与 README。

## 15. 测试要求

覆盖 Schema 正反例、Decimal 与五项指标、证据分支、候选边界、Reasoner 三种模式、Validator 错误码、五条工作流、审计覆盖和静态安全扫描。测试数据必须合成且可重复。

## 16. 验收标准

正常路径建议值属于候选集合并停在审批前；一次非法输出能创建新 attempt 和版本后成功；连续相同错误两次停止；无变更路径无需审批；所有路径生产写入调用为零；全部 pytest 通过。

## 17. Definition of Done

文件齐全、Schema 可自校验、配置可解析、包可安装、CLI 五个示例可运行、完整测试通过、安全扫描无生产能力、规范副本哈希与源文件一致、Git 状态清晰。

## 18. 与主规范的追踪关系

| 主规范 | PoC 证据 |
|---|---|
| FR-003、NFR-008 | 输入 Schema 与运行期对象校验 |
| FR-004、NFR-007 | Decimal 指标与取整测试 |
| FR-005、FR-008 | 数据不足/无需修改工作流 |
| FR-006、NFR-003 | 确定性候选集合 |
| FR-007、NFR-009 | 受限 Reasoner 与确定性后处理 |
| FR-009 | change_id、版本与 plan_digest |
| FR-010、NFR-010 | fail-closed Runtime Validator |
| FR-011、NFR-013 | 与测试隔离的 dry-run 预检 |
| FR-012 | 三次上限、同错两次、attempt/version 更新 |
| FR-013、NFR-004 | 等待人工审批且零生产写入 |

关联编号完整集合：FR-003、FR-004、FR-005、FR-006、FR-007、FR-008、FR-009、FR-010、FR-011、FR-012、FR-013、NFR-003、NFR-004、NFR-007、NFR-008、NFR-009、NFR-010、NFR-013。

## 19. 已知限制

仅验证单 Keyword 和降价候选；置信度采用显式版本化的 PoC 固定配置，不代表生产评分；Reasoner 是 Stub；所有数据为合成数据；不持久化审计；不实现正式审批服务。所有 PoC 数值均显式版本化，PoC 的简化不得成为生产默认行为。

## 20. 待确认事项

生产策略、平台步长、币种精度、置信度公式、真实 Adapter Contract、审批身份和持久化方式均待未来版本确认。本 PoC 不推断这些生产值。
