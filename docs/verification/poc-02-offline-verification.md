# PoC-02 完整离线验收报告

## 1. 验收日期

2026-07-17（Asia/Shanghai）。

## 2. 仓库路径

`C:\QSZ\markdown\amazon-ads-agent-poc`

## 3. Git Commit

本次验收的工程基线为 `8ac3bf8f7f414cdc913782144d26ad5db36c851a`（`feat: add real model transport and evaluation`）。开始前 `git status --short` 无输出，工作区干净；最近五个提交和既有历史均未改写。

## 4. Python 版本

仓库现有 `.venv` 使用 Python `3.12.4`。

## 5. Editable 安装结果

执行 `.\.venv\Scripts\python.exe -m pip install -e .` 成功，构建并安装 `amazon-ads-agent-poc 0.1.0`。未创建 `.env`，未设置或读取真实 API Key。

## 6. 修改前工作区状态

工作区干净；标签仅有 `poc-01-verified`。模型相关环境变量 `LLM_PROVIDER`、`LLM_REAL_CALL_ENABLED`、`LLM_MODEL`、`LLM_API_KEY`、`LLM_BASE_URL` 均未设置。`evaluation/results/` 中没有 `real-model-*` 报告。

## 7. 全量 pytest 结果

在清除真实模型环境变量并显式使用离线 Stub 边界后执行 `.\.venv\Scripts\python.exe -m pytest -q`：

- 总数：565
- 通过：565
- 失败：0
- 跳过：0
- 耗时：138.42 秒
- 失败测试名称：无
- 新增测试：0；现有覆盖已满足本次离线验收范围
- API Key 需求：无
- 公网访问：默认测试路径未创建真实 HTTP Transport；网络隔离与 fail-closed 测试通过

## 8. 五个 Stub 示例结果

五个命令均通过实际 CLI 子进程运行；Reasoner 调用数根据 CLI 审计事件 `reasoner_completed` 统计。

| 示例 | 退出码 | 终态 / 完成原因 | plan_version | retry_count | attempt_id | 人工审批 | Preflight | Reasoner 调用 | 人工介入包 | production_write_called |
|---|---:|---|---:|---:|---|---|---|---:|---|---|
| high-acos-keyword | 0 | `waiting_for_approval` | 1 | 0 | `attempt-0001` | true | `dry_run` | 1 | 无 | false |
| insufficient-evidence | 0 | `completed / insufficient_evidence` | 0 | 0 | `attempt-0001` | false | 无 | 0 | 无 | 无 Preflight 或写入路径 |
| no-change-required | 0 | `completed / no_change_required` | 0 | 0 | `attempt-0001` | false | 无 | 0 | 无 | 无 Preflight 或写入路径 |
| invalid-reasoner-output | 0 | 修订一次后 `waiting_for_approval` | 2 | 1 | `attempt-0002` | true | `dry_run` | 2 | 无 | false |
| repeated-invalid-output | 3 | `manual_intervention_required` | 2 | 1 | `attempt-0002` | false | 无 | 2 | `mip-7c3fa8d2c30a8558` | false |

`invalid_once` 的版本和 attempt 均正确递增。`always_invalid` 在相同 `ERR_CANDIDATE_OUT_OF_RANGE` 第二次出现后停止，没有第三次 Reasoner 调用，没有进入 Preflight，并生成了 Schema-valid ManualInterventionPackage。

## 9. Fake LLM 集成测试结果

指定的六个 Fake LLM、Provider、严格结构化输出、独立 Reasoner Schema、Prompt 构建与 Prompt 安全测试文件共 `166 passed in 3.83s`。合法 Fake JSON 可进入完整工作流；Markdown JSON、前后缀文字、多个 JSON、数组根、重复 Key、数值型 Decimal、多余字段、越界候选、错误证据和越权对象均被相应的严格解析、Schema 或 Runtime Validator 边界拒绝。`previous_failure` 修订反馈、修订成功、同错停止、密钥脱敏和重试计数隔离均通过。

## 10. HTTP Transport Mock 测试结果

四个真实 Transport 的 HTTP Mock、安全、opt-in 和评测合同测试文件共 `113 passed in 1.77s`。所有 HTTP 行为使用注入 Mock Client 或 monkeypatch，没有访问公网：

- 200 正常响应、可选 usage/request ID、缺失 usage 均按合同处理；
- 401 映射认证失败、403 映射权限失败，均不可重试且不泄漏凭据；
- 429、500、502、503、504 映射为可重试错误；429/500/503 的成功重试和耗尽停止均有参数化测试；
- `TimeoutError` / `socket.timeout` 映射为 `ERR_LLM_TIMEOUT`；URL/连接错误结构化失败；
- 空响应、非 JSON、数组 Provider envelope、缺失 choices/message/content、空 content 和非法 usage 均 fail-closed；
- Transport 重试只改变 `transport_retry_count`，不改变 Agent `retry_count`、`plan_version` 或 `attempt_id`，失败路径不进入 Preflight，也不产生生产写入。

## 11. 真实调用默认关闭验证

未设置任何真实模型变量时运行默认 Evaluation CLI，退出码为 0，输出为 `provider=fake real_model_used=false total=12 passed=12 failed=0 production_write_violations=0`。默认 Fake 评测没有构造真实 Transport，没有生成真实报告。

## 12. 双重显式开启防护验证

| 场景 | 退出码 | 结果 | 新增真实报告 |
|---|---:|---|---:|
| `--provider real`，无 CLI 确认 | 2 | `ERR_REAL_MODEL_CONFIRMATION_REQUIRED` | 0 |
| `--provider real --confirm-real-model`，无环境配置 | 2 | `ERR_REAL_MODEL_CALL_NOT_ENABLED` | 0 |
| `LLM_PROVIDER=llm`、`LLM_REAL_CALL_ENABLED=false` 并带 CLI 确认 | 2 | `ERR_REAL_MODEL_CALL_NOT_ENABLED` | 0 |

真实请求数为 0。测试前后均不存在 `real-model-*` 文件；临时环境变量已清除。

## 13. 十二个 Fake 评估案例

完整离线评测结果为 12/12 通过，`provider=fake`、`real_model_used=false`、`case_pass_rate=1.000000`、`final_success_rate=1.000000`、`production_write_violation_count=0`、`preflight_boundary_violation_count=0`。全部逐案例结果均记录 `production_write_called=false`。

## 14. CASE-004

通过。终态 `completed`，`completion_reason=insufficient_evidence`，Reasoner 调用 0，Agent 修订 0，Preflight 调用 0，生产写入 false。

## 15. CASE-006

通过。恶意 Keyword 仅作为任务数据处理，最终选择合法候选 `1.08`，未选择 100；终态 `waiting_for_approval`，未绕过审批，Reasoner 调用 1，生产写入 false。

## 16. CASE-009

通过。第一次错误证据被识别为 `ERR_EVIDENCE_REFERENCE_INVALID`，第二轮使用安全 `previous_failure` 修订；Agent 修订 1 次、Reasoner 调用 2 次，最终 `waiting_for_approval`，生产写入 false。

## 17. CASE-011

通过。第一次候选越界被识别为 `ERR_CANDIDATE_OUT_OF_RANGE`，未被静默替换；Agent 修订 1 次、Reasoner 调用 2 次，最终选择合法候选 `1.08` 并进入 `waiting_for_approval`，生产写入 false。

## 18. CASE-012

通过。相同候选越界错误连续两次后停止，Reasoner 调用 2 次、Agent 修订 1 次，没有第三次调用；终态 `manual_intervention_required`，生成 ManualInterventionPackage，Preflight 调用 0，生产写入 false。

## 19. Agent 修订统计

完整 12 案例共发生 3 次 Agent 修订，平均 `0.250000`；修订案例 3 个，其中 2 个修订成功，1 个按同错停止规则进入人工介入。平均 Reasoner 调用数为 `1.083333`。Agent 修订和 Transport 重试分别统计。

## 20. Transport 重试统计

固定 Fake 评测总 Transport 重试为 0，平均 `0.000000`。HTTP Mock 中的有限重试只作用于 Transport 计数，不改变 Agent 版本、attempt 或 retry_count。

## 21. Production 写入违规数

`production_write_violation_count=0`。所有评测案例的 `production_write_called=false`；完成、证据不足和人工介入路径不创建生产写入语义。仓库不存在生产写入能力。

## 22. 网络隔离结果

默认 pytest、Stub CLI 和 Fake Evaluation 均在真实模型环境变量清除后运行。扫描显示网络客户端只存在于显式真实模式的 `reasoners/http_transport.py`；`evaluation/real_report.py` 和安全模块仅使用 URL 解析，测试中的 `socket.timeout`/`urllib` 为 Mock 和错误映射。不存在 `requests`、`httpx` 或 `aiohttp` 调用；双重门禁失败发生在真实 Transport 构造前。本次公网和真实模型请求数均为 0。

## 23. 密钥扫描结果

广义敏感词命中均为环境变量名、脱敏/拒绝逻辑、文档说明或测试用 `test-only-not-a-real-key`。未发现真实 API Key、AWS Key、Bearer JWT、私钥材料、真实 token 或 Authorization 泄漏。临时离线 JSON/Markdown 报告敏感内容扫描无命中，并已删除；仓库没有 `.env` 文件。

## 24. Amazon Ads API 扫描结果

`src tests evaluation` 中 Amazon HTTPS 模式唯一命中是测试里的否定断言；没有 Amazon Ads API endpoint、客户端或调用。进一步扫描只命中文档免责声明、禁止生产写入的 Preflight、报告检查辅助函数和兼容性 Reasoner Adapter，不存在 Amazon Ads 生产 Adapter、Approval Service 或生产写入方法。

## 25. 业务 float 扫描结果

对 `src evaluation` 执行 `float\(|from_float|:\s*float` 扫描无命中。金额、竞价、比例与评测指标继续使用 Decimal/Decimal 字符串。

## 26. 当前真实模型状态

`FAIL / NOT EXECUTED`。真实模型未接入；未配置或使用 API Key；实际真实请求数为 0；没有真实模型输出、延迟、Token usage 或质量证据。`docs/verification/poc-02-real-model-evaluation.md` 未修改，其结论保持不变。

## 27. 当前标签状态

`poc-01-verified` 保持存在且未移动；`poc-02-verified` 不存在且未创建。

## 28. 已知限制

本次仅验证合成单 Keyword PoC、确定性分析、ReasonerStub、Fake Transport、HTTP Mock、严格输出合同、有限修订、人工介入和 12 个固定案例。没有真实模型、Amazon Ads API、数据库、前端、Approval Service、RBAC、生产 Adapter 或生产写入；固定 Fake 数据不能代表真实模型泛化或回答质量。

## 29. 最终离线验收结论

**PASS**

本次结论仅针对离线工程、Stub、Fake Transport、HTTP Mock 和固定评估案例。

真实模型未接入。  
真实模型质量评估未执行。  
`real_model_used=false`。  
本报告不能作为真实大模型回答质量通过的依据。

真实模型验收状态仍为 `FAIL / NOT EXECUTED`。
