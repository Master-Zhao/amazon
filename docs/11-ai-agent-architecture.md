# 11 AI与多智能体架构

## 1. 五类能力边界

| 能力 | 负责 | 不负责 |
|---|---|---|
| 确定性算法 | CTR/CPC/CVR/ACOS/ROAS、金额、聚合、窗口比较 | 自由文本策略判断 |
| 规则引擎 | 阈值、零分母、预算耗尽、高花费无订单等可复现判断 | 权限和状态直接写入 |
| 大模型 | 解释、归纳、候选策略和自然语言生成 | 权限、金额、唯一真值和执行 |
| Agent | 在限定目的、数据、工具和Schema内完成一种分析 | 自行扩大范围或互相自由调用 |
| Orchestrator | 固定编排、输入裁剪、Schema校验、失败策略和汇总 | 绕过Service写正式业务数据 |

## 2. V1 Agent

### 数据分析智能体

- 输入：已冻结指标、趋势、数据质量摘要和分析范围。
- 输出：关键变化、分段结果、证据引用和数据限制。
- 工具：只读指标查询、确定性聚合。

### 异常诊断智能体

- 输入：AnomalyRecord、规则版本、相关趋势和对象状态。
- 输出：可能原因、支持/反对证据、需人工核实项。
- 不得改写规则命中事实。

### 预算分析智能体

- 输入：预算、花费、销售、时间进度和待确认利润数据。
- 输出：预算风险与候选调整范围。
- 所有金额和比率由确定性代码提供。

### 综合策略智能体

- 输入：前三类Agent已验证的结构化输出。
- 输出：候选Recommendation结构、优先级、风险和证据映射。
- 不直接访问更大数据范围，不直接提交审批。

### AnalysisOrchestrator

- 冻结AnalysisScopeSnapshot。
- 选择固定AgentVersion。
- 按预定义依赖顺序调用Agent。
- 验证每个输入/输出Schema。
- 定义失败、超时、重试和部分结果策略。
- 只在必需结果有效时创建Recommendation。

## 3. 通信规则

- Agent之间不自由聊天。
- Agent不直接相互调用。
- 所有通信经过Orchestrator的结构化对象。
- 每个AgentVersion具有输入Schema、输出Schema、允许工具、Prompt引用/哈希和超时策略。
- 未在允许工具列表中的能力不可调用。
- 模型输出中的对象ID必须在服务端重新验证属于ScopeSnapshot。

## 4. 数据范围与最小化

Agent输入只包含完成任务必需的数据：

- tenantId、storeId仅作为受控上下文，不作为模型授权依据。
- 使用内部匿名引用代替不必要的账号信息。
- 不发送密码、Token、密钥、完整用户身份或未批准的敏感字段。
- LLM允许接收的数据类别和保存期限均待确认。
- 跨币种数据不直接合并。

## 5. LLMProvider

统一接口应表达：

- provider和模型引用。
- 结构化输入。
- 期望输出Schema。
- 超时、重试和取消。
- 用量、延迟和稳定错误。
- 数据保留/隐私配置引用。

业务模块不得依赖具体供应商SDK。MockLLMProvider按固定输入返回确定性结果，并可模拟超时、无效JSON、Schema错误、限流和服务不可用。

## 6. Prompt和Agent版本

- Prompt必须版本化，AgentVersion引用不可变Prompt内容或哈希。
- 已用于正式Recommendation的版本不得修改。
- 版本变更需要评审、回归测试和决策记录。
- V1不允许Agent自行修改Prompt、工具、Schema、规则或代码。

## 7. 保存与展示

允许保存：

- AgentVersion。
- 结构化输入摘要或受控引用。
- 结构化输出。
- 确定性工具结果。
- 数据证据引用。
- 错误码、用量和时间。

禁止保存或展示：

- 模型隐藏思维过程。
- 密码、Token和密钥。
- 超出已确认范围的完整敏感上下文。

输入输出正文的保留时间为待确认。

## 8. 输出门槛

进入Recommendation前必须满足：

1. JSON/结构化格式有效。
2. 输出Schema通过。
3. 对象引用属于AnalysisScopeSnapshot。
4. 金额均为Decimal字符串并有currency。
5. 指标引用可回溯到事实和计算版本。
6. 动作类型属于V1允许集合。
7. 不含直接执行指令或绕过审批要求。
8. 必需Agent结果完整；部分结果策略待确认。

失败使用`AGENT_OUTPUT_INVALID`等稳定错误码，不能由人工页面直接“忽略校验后提交”。

## 9. 正式数据写入边界

- AgentRun/AgentStep由Orchestrator服务记录。
- Recommendation由Recommendation Service基于通过验证的结果创建。
- 人工Revision由Recommendation Service创建。
- Preview、审批和执行分别由对应Service创建。
- Agent没有写Campaign、预算、竞价、状态或执行结果的能力。

## 10. 测试

- Schema正确/错误。
- 超时、限流和Provider失败。
- Prompt/AgentVersion追溯。
- Scope越界对象ID。
- 金额/权限/状态幻觉不能生效。
- Mock结果可重复。
- 上游部分失败时Orchestrator行为。
- 不记录隐藏思维过程和敏感字段。
