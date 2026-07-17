# Deterministic Reasoner Evaluation

本目录提供 PoC-02 第三小时的固定、可重复、可机器判定的离线评测。它复用正式 Workflow、Reasoner Output Schema、Runtime Validator、Failure Analyzer 和 ManualInterventionPackage，不另建业务规则实现。

## 目录

- `cases/`：12 个固定场景输入，只含合成数据。
- `expected/`：与 case 一一对应的机器可判定预期。
- `fixtures/`：合法与非法的预定义 Fake Transport 响应；均为 test-only。
- `results/`：运行报告目录，只提交 `.gitkeep`。
- `case_loader.py`：严格字段、Schema、配对和路径校验。
- `evaluator.py`：执行正式 Workflow 并生成稳定检查项。
- `metrics.py`：仅用 `Decimal` 计算比例和平均值。
- `report.py`：生成不含 Prompt、凭据或原始响应的 JSON/Markdown 报告。

## 运行

```powershell
python evaluation/run_evaluation.py
python evaluation/run_evaluation.py --case CASE-006
python evaluation/run_evaluation.py --case CASE-011
python evaluation/run_evaluation.py --case CASE-012
python evaluation/run_evaluation.py `
  --output evaluation/results/custom.json `
  --markdown-output evaluation/results/custom.md
```

默认输出为 `evaluation/results/latest.json` 和 `latest.md`。成功退出码为 0；参数或案例错误为 2；存在评测失败为 3；不可恢复内部错误为 4。输出路径必须位于 `evaluation/results/`，不能覆盖案例、预期或 Fixture。

## 指标解释

汇总包括案例通过率、首次 JSON/Schema/业务校验通过率、最终成功率、修订成功率、候选越界/虚构对象/错误证据/审批绕过计数、人工介入数、平均 Agent 修订、平均 Reasoner 调用、独立 Transport 重试、生产写入违规和 Preflight 边界违规。比例及平均值始终是六位小数的 Decimal 字符串；空集合安全返回 `0.000000`。

Agent 修订是 Runtime Validator 拒绝方案后由 Workflow 发起的新方案尝试；Transport 重试是同一 Reasoner 调用内的传输尝试。两者绝不混用。

## Fake 与真实模型边界

所有案例固定 `provider=fake|stub`、`real_model_used=false`，响应仅来自 `ReasonerStub`、`FakeTransport` 或仓库内预定义 Fixture。评测不读取 `LLM_API_KEY`，不访问网络，不包含真实 HTTP Transport、Amazon Ads API、Approval Service 或生产写入。

报告不记录完整 Prompt、Authorization Header、API Key 或模型原始响应。Fixture 中的攻击内容只用于测试，不能作为指令执行，也不能被描述为真实模型结果。

## 新增案例

1. 在 `cases/` 增加唯一 `CASE-xxx` 与稳定 snake_case 名称。
2. 只使用合成 TaskInput；Decimal 使用字符串，时间必须带时区。
3. 在 `expected/` 增加且只增加一个同 ID 的机器可判定预期。
4. 如需新响应，在允许的 Fixture 中加入 test-only 预定义数据。
5. 为案例加载、检查器、指标和 CLI 行为补充测试。
6. 运行全部评测和完整 pytest。

本阶段禁止设置真实模型凭据或把 Fixture 替换为网络调用。新增案例不能修改 Candidate Engine、放宽 Runtime Validator，也不能增加生产执行语义。

