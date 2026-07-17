# PoC-01 运行验收报告

## 1. 验收日期

2026-07-17（Asia/Shanghai）。

## 2. 仓库提交

- 修改前基线：`0a99fbbe2f5501f588f125724f57f2e647046481`，`feat: initialize amazon ads agent poc`。
- 验收实现：本报告所在提交，提交主题为 `fix: harden poc-01 verification and manual intervention protocol`。

## 3. 操作系统

运行时报告为 Microsoft Windows `10.0.26200`，X64。CIM 查询受当前权限限制，采用 .NET `RuntimeInformation` 获取。

## 4. Python 版本

Python `3.12.4`，使用仓库内 `.venv`。

## 5. 安装结果

修改前和修改后均实际运行仓库内虚拟环境的 editable 安装。`pip install -e . --no-deps --no-build-isolation` 成功构建并安装 `amazon-ads-agent-poc 0.1.0`，未下载业务依赖或访问外部服务。

## 6. 修改前测试结果

`70 passed in 3.13s`。无失败、跳过或弱化测试。

## 7. 修改后测试结果

`103 passed in 9.70s`。所有原测试和新增测试通过。

## 8. 新增测试数量

新增 33 项，位于：

- `tests/test_acceptance_independent.py`
- `tests/test_manual_intervention_protocol.py`

独立测试覆盖候选越界、虚构对象、当前值/版本不一致、无效证据、六项关键配置缺失、production 开关攻击、六类旧摘要复用、冻结后停止、同错停止、最大修订和 ManualInterventionPackage 正反例。

## 9. 五个示例运行结果

修改前实际结果：

| 示例 | 状态 | 退出码 | plan_version | retry_count | attempt_id | 审计数 | production_write_called |
|---|---|---:|---:|---:|---|---:|---|
| high-acos | waiting_for_approval | 0 | 1 | 0 | attempt-0001 | 9 | false |
| insufficient-evidence | completed | 0 | 0 | 0 | attempt-0001 | 5 | false |
| no-change-required | completed | 0 | 0 | 0 | attempt-0001 | 5 | false |
| invalid-once | waiting_for_approval | 0 | 2 | 1 | attempt-0002 | 13 | false |
| always-invalid | manual_intervention_required | 3 | 2 | 1 | attempt-0002 | 13 | false |

修改后实际结果保持上述业务状态、版本、退出码和审计数量。额外确认 always-invalid 的 `manual_intervention_package_id=mip-7c3fa8d2c30a8558`、`execution_preflight=null`、`stop_reason=same_error_repeated`、`production_write_called=false`。

## 10. manual_intervention 协议验证

V0.2.1 将 AgentOutput 与 ManualInterventionPackage 分离。AgentOutput 表示终态并引用包；包保存停止原因、最后错误、指纹、两次失败历史、13 个关联审计事件及恢复限制。人工介入时 `human_approval_required=false`、`changes=[]`、`execution_preflight=null`。合法包通过 Schema；缺 ID、生产写入为 true、原 run 非终态、历史字段不完整、未知字段和无时区时间均被拒绝。

## 11. 自动修订验证

invalid-once 从 `attempt-0001/plan_version=1` 修订为 `attempt-0002/plan_version=2` 后成功。always-invalid 在相同错误指纹连续出现两次后停止，Reasoner 共调用两次，不发生第三次同类修订。不同错误指纹路径最多修订 3 次、最多生成 4 个版本，随后生成 `maximum_revisions_reached` 人工介入包。

## 12. 摘要校验验证

Runtime Validator 现在独立重算 V0.2.1 计划摘要。分别修改 `suggested_value`、`candidate_values`、`reason`、`evidence`、`expected_current_value`、`expected_object_version` 并复用旧摘要，均返回 `ERR_PLAN_DIGEST_MISMATCH`，不会进入 preflight 或等待审批。

## 13. 配置缺失验证

分别删除 `max_decrease_ratio`、`bid_step`、`min_bid`、`max_bid`、`max_automatic_revisions`、`stop_on_same_error_consecutive_count`，均在 Reasoner 调用前返回 `ERR_RULE_CONFIG_MISSING`。没有默认值推断、候选计划或 preflight。

## 14. production 开关攻击验证

将临时配置 `production_write_enabled` 设为 true 时返回 `ERR_PRODUCTION_WRITE_FORBIDDEN`。正式配置未修改；没有 production 调用，所有可观察结果保持 `production_write_called=false`。

## 15. 网络和密钥扫描结果

`requests`、`httpx`、`urllib`、`aiohttp`、`boto` 客户端命中为 0；Amazon 生产 URL 命中为 0；真实令牌、AWS key 形态、Bearer JWT 和私钥材料命中为 0。审计模块中的凭据字段名是拒绝列表，不是凭据。测试中的 `production_write_called=true` 和 `production_write_enabled=true` 仅为反向攻击输入，不存在于合法生产代码路径。

## 16. Decimal 检查结果

`src` 中不存在 `float(`、`from_float` 或 `: float` 业务路径。扫描在测试中命中的 `float(` 仅是断言源码不含该调用的字符串。金额、竞价和比例继续使用 Decimal 字符串与 `decimal.Decimal`。

## 17. 主规范 V0.2 哈希检查

修改前 SHA-256：`E35211513D5A455CF6EE9220D6B3E3A01C684ECE35E3E8474652D4A842CFDFBC`。修改后复核值相同；`git diff` 对该文件无变化。

## 18. V0.2.1 变更说明

新增 `docs/spec/amazon-ads-agent-loop-engineering-spec-v0.2.1.md`，仅澄清人工介入终态、独立包引用和 PoC 摘要重算守卫。原 V0.2 保持不变；未增加真实模型、API、审批、数据库或生产执行能力。

## 19. 已知限制

本项目仍仅支持合成单 Keyword 高 ACoS PoC；Reasoner 是测试 Stub；审计和人工介入包仅在内存中返回；没有正式人工恢复、审批、RBAC、数据库、前端、Amazon Ads API 或 production Adapter。这些是既定 PoC 范围，不影响本次验收结论。

## 20. 最终结论

PASS
