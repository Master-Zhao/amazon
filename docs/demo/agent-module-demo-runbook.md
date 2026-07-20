# 亚马逊广告智能体模块现场演示脚本

## 1. 演示目标

| 项目 | 说明 |
|---|---|
| 建议总时长 | 5 分钟 10 秒，允许范围 4～6 分钟 |
| 演示场景 | 正常高 ACoS、首次错误后修订、连续失败后人工介入 |
| 运行方式 | 本地离线 CLI |
| Reasoner | ReasonerStub |
| 不依赖 | 真实模型、API Key、公网、Amazon Ads API、前端页面 |
| 安全终点 | `waiting_for_approval` 或 `manual_intervention_required` |
| 生产写入 | 始终为 0 |

演示核心结论：AI 只在确定性候选中选择；Schema、Runtime Validator、有限修订和人工确认共同控制安全边界。

## 2. 时间安排

| 环节 | 目标时间 |
|---|---:|
| 开场和边界说明 | 30 秒 |
| 场景一：正常高 ACoS 优化 | 90 秒 |
| 场景二：首次错误后自动修订 | 90 秒 |
| 场景三：连续失败后安全停止 | 90 秒 |
| 总结 | 40 秒 |
| 合计 | 5 分 10 秒 |

## 3. 演示前检查

所有路径均相对于仓库根目录。进入实际克隆目录后执行：

```powershell
git status
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pytest -q
```

演示前必须确认：

- Python 为 3.11 或更高；当前核验版本为 3.12.4。
- 全量测试结果为 565 passed。
- 未设置或展示真实 API Key。
- `poc-02-verified` 不存在。
- 演示命令使用 Stub，不会访问公网。
- `docs/evidence/agent-module/logs/` 下六份日志可读取。

正式演示时无需现场等待完整 pytest，可直接展示 `pytest-full.txt` 或人工补充的测试截图：

```powershell
Get-Content docs/evidence/agent-module/logs/pytest-full.txt | Select-Object -Last 10
```

## 4. 开场讲解（约 30 秒）

### 讲解词

> 这一模块验证的不是让大模型自由修改广告，而是把广告优化拆成确定性计算、候选生成、受控推理、运行期校验和人工确认。当前演示全部使用合成 Keyword 数据和离线 ReasonerStub，不需要公网或密钥，也没有接入 Amazon Ads API。合法建议只会停在等待人工确认，生产写入始终为零。

### 屏幕展示

```powershell
Get-Content docs/evidence/agent-module/logs/evaluation-all.txt
```

重点指向：`provider=fake`、`passed=12`、`failed=0`、`real_model_used=false` 和 `production_write_violations=0`。

## 5. 场景一：正常高 ACoS 优化（约 90 秒）

### 5.1 命令

```powershell
.\.venv\Scripts\python.exe -m amazon_ads_agent examples/high-acos-keyword.json
```

### 5.2 讲解顺序

1. 输入是一个合成 Keyword 快照，包含对象 ID、对象版本、当前竞价 `1.20`、曝光、点击、订单、消耗和销售额。
2. Metrics Engine 使用 Decimal 重算 CTR、CPC、CVR、ACoS 和 ROAS，不信任自由文本中的计算结论。
3. Evidence Engine 根据分析天数、点击、订单、销售额和目标 ACoS 判断数据是否充分。
4. ACoS 高于目标后，Candidate Engine 先生成 `1.02`、`1.08`、`1.14` 三个合法候选。
5. ReasonerStub 只能从候选集合选择，本场景选择中间值 `1.08`，无权创造新竞价。
6. 结构化结果经过 Schema 和 Runtime Validator，校验对象、当前值、版本、证据、候选、变化比例和计划摘要。
7. 合法方案只执行本地 `dry_run` Preflight。
8. 最终状态是 `waiting_for_approval`，不是已经批准或执行。
9. `human_approval_required=true`，`production_write_called=false`。

### 5.3 需要观察的输出

```text
candidate_values = [1.02, 1.08, 1.14]
suggested_value = 1.08
plan_version = 1
current_status = waiting_for_approval
human_approval_required = true
execution_preflight.mode = dry_run
execution_preflight.production_write_called = false
```

### 5.4 正常预期

- 命令退出码为 0。
- Reasoner 调用一次。
- Runtime Validator 和 Preflight 通过。
- 自动修改停止在人工确认前。

### 5.5 异常备用说明

如果现场终端输出过长或命令环境异常，展示已生成的真实日志：

```powershell
Get-Content docs/evidence/agent-module/logs/high-acos.txt |
  Select-String 'suggested_value|current_status|human_approval_required|production_write_called|plan_version|exit_code'
```

对应证据：`docs/evidence/agent-module/logs/high-acos.txt`；如已人工补图，可展示 `docs/evidence/agent-module/screenshots/03-high-acos-waiting-for-approval.png`。

## 6. 场景二：首次错误后自动修订（约 90 秒）

### 6.1 命令

单行方式最稳定：

```powershell
.\.venv\Scripts\python.exe -m amazon_ads_agent examples/invalid-reasoner-output.json --reasoner-mode invalid_once
```

### 6.2 讲解顺序

1. Stub 第一次故障注入返回候选集合外的 `0.80`。
2. 系统不会裁剪、替换或静默修复这个值，Runtime Validator 返回 `ERR_CANDIDATE_OUT_OF_RANGE`。
3. Failure Analyzer 生成稳定错误指纹，并把安全字段投影为 `previous_failure`。
4. Workflow 创建新的尝试；`attempt_id` 更新为 `attempt-0002`，`plan_version` 从 1 增加到 2。
5. 第二轮 Reasoner 根据失败反馈重新选择合法候选。
6. 第二个方案通过 Runtime Validator 和 dry-run Preflight。
7. 最终仍停在 `waiting_for_approval`，生产写入为 false。

必须强调：

> 系统不会静默修改模型输出，而是通过可审计的新一轮尝试完成修订。

### 6.3 需要观察的输出

```text
runtime_validation_failed [ERR_CANDIDATE_OUT_OF_RANGE]
failure_analyzed
plan_revised
attempt_id = attempt-0002
plan_version = 2
current_status = waiting_for_approval
production_write_called = false
```

### 6.4 正常预期

- 命令退出码为 0。
- Reasoner 调用两次，Agent 修订一次。
- 第一次失败方案不进入 Preflight。
- 第二次合法方案进入 dry-run 后等待人工确认。

### 6.5 异常备用说明

```powershell
Get-Content docs/evidence/agent-module/logs/invalid-once.txt |
  Select-String 'runtime_validation_failed|plan_revised|attempt-0002|plan_version|waiting_for_approval|production_write_called|exit_code'
```

对应证据：`docs/evidence/agent-module/logs/invalid-once.txt`；如已人工补图，可展示 `docs/evidence/agent-module/screenshots/04-invalid-once-revision.png`。

## 7. 场景三：连续失败后安全停止（约 90 秒）

### 7.1 命令

```powershell
.\.venv\Scripts\python.exe -m amazon_ads_agent examples/repeated-invalid-output.json --reasoner-mode always_invalid
```

### 7.2 讲解顺序

1. Stub 连续返回相同的候选外值。
2. 两次 Runtime Validator 错误具有相同 `error_fingerprint`。
3. 第二次失败后 `same_error_consecutive_count=2`，系统不执行第三次无限重试。
4. Workflow 生成独立、Schema 合法的 ManualInterventionPackage。
5. 终态为 `manual_intervention_required`，这不是人工审批。
6. 失败方案的 `execution_preflight=null`，不会进入 `waiting_for_approval`。
7. 原运行被标记为终态；未来恢复必须创建新 run，不能复用失败方案或旧审批。
8. `production_write_called=false`。

### 7.3 需要观察的输出

```text
两次 reasoner_completed
两次 runtime_validation_failed
same_error_consecutive_count = 2
stop_reason = same_error_repeated
current_status = manual_intervention_required
execution_preflight = null
manual_intervention_package != null
production_write_called = false
```

### 7.4 正常预期

- 命令退出码为 3。
- 退出码 3 表示预期的人工介入协议终态，不是脚本崩溃。
- Reasoner 调用两次、Agent 修订一次、第三次调用为 0。
- Preflight 和生产写入均为 0。

### 7.5 异常备用说明

```powershell
Get-Content docs/evidence/agent-module/logs/always-invalid.txt |
  Select-String 'reasoner_completed|runtime_validation_failed|same_error|manual_intervention_required|execution_preflight|production_write_called|exit_code'
```

对应证据：`docs/evidence/agent-module/logs/always-invalid.txt`；如已人工补图，可展示 `docs/evidence/agent-module/screenshots/05-manual-intervention.png`。

## 8. 演示总结（约 40 秒）

### 讲解词

> 三条路径说明，AI 的权限被限定在候选选择和解释，关键指标、候选边界和最终合法性由确定性模块掌握。系统允许有限、可审计的自动修订；同一错误重复时会安全停止并转人工。所有合法变更都必须等待人工确认，所有失败方案都不能进入 Preflight。当前展示的是离线工程闭环，真实模型质量尚未验证，Amazon Ads API 和生产写入尚未接入。

### 结论字段

```text
565 passed
12/12 fixed evaluation cases passed
0 real model requests
0 production write violations
```

## 9. 现场备用方案

### 9.1 命令运行失败

按场景使用 `docs/evidence/agent-module/logs/` 中对应日志。当前未生成或伪造截图；如团队已按证据索引补充截图，可优先展示 PNG，随后打开原始日志核验。

### 9.2 输出过长

使用各场景提供的 `Select-String` 命令，只显示状态、版本、错误、人工确认和生产写入字段。不要删改原始日志。

### 9.3 PowerShell 换行问题

- 推荐现场使用单行命令。
- 必须换行时，PowerShell 反引号必须位于行尾，后面不能有空格。
- 不要把 Bash 的反斜杠续行符复制到 PowerShell。

### 9.4 退出码 3

always-invalid 场景退出码 3 是预期协议：系统识别无法自动修正的重复错误并转人工。讲解时同步展示 `manual_intervention_required` 和 `exit_code=3`。

### 9.5 终端与录制

- 演示前执行 `Clear-Host`，关闭无关窗口和通知。
- 将终端宽度调到足以完整显示 JSON 字段，字号建议 18～22。
- 录制分辨率建议 1920×1080，帧率 30 fps。
- 每个场景运行前先说目标，运行后停留 3～5 秒指向关键字段。
- 不展示环境变量列表、`.env`、API Key、Authorization 或用户目录隐私信息。
- 建议提前录制一份完整备份视频，并保留未经剪切的日志证据。

## 10. 演示完成检查

- [ ] 总时长在 4～6 分钟。
- [ ] 三个场景均已演示或用真实日志替代。
- [ ] 正常路径明确停在 `waiting_for_approval`。
- [ ] 修订路径展示新的 attempt 和 plan version。
- [ ] 连续失败路径解释退出码 3 和人工介入包。
- [ ] 明确 `production_write_called=false`。
- [ ] 未声称真实模型质量通过。
- [ ] 未声称已接入 Amazon Ads API、前端或生产执行。
