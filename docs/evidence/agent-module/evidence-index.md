# 智能体模块比赛证据索引

## 1. 证据包状态

| 项目 | 当前事实 |
|---|---|
| 证据生成日期 | 2026-07-20 |
| 生成基线 | `0d8da52` |
| Python | 3.12.4 |
| 全量测试 | 565 passed，失败 0，跳过 0 |
| 固定评估 | 12/12 passed |
| 评估 Provider | fake |
| 真实模型 | `real_model_used=false`，真实请求数 0 |
| 生产写入违规 | 0 |
| 离线结论 | PASS |
| 真实模型结论 | FAIL / NOT EXECUTED |

本证据包使用 Stub、Fake Transport 和 HTTP Mock。真实模型请求数为 0。该证据包不代表真实模型回答质量已经通过。

所有命令均从仓库根目录执行。日志只包含合成数据、测试结果和非敏感 Git 元数据；敏感信息扫描未发现 API Key、Authorization Header 或 access token。

## 2. 证据目录

| 编号 | 证据 | 实际命令 | 证明内容 | 对应比赛章节 | 是否真实模型 | 敏感信息 | 文件 |
|---|---|---|---|---|---|---|---|
| E-01 | 全量 pytest | `.venv/Scripts/python.exe -m pytest -q` | 565 项测试全部通过，失败 0、跳过 0，耗时 49.11 秒 | 6.1、6.2 | 否 | 无 | `docs/evidence/agent-module/logs/pytest-full.txt` |
| E-02 | 全量 Fake 评估 | `.venv/Scripts/python.exe evaluation/run_evaluation.py` | provider=fake、12/12 通过、`real_model_used=false`、生产写入违规 0 | 5.2、6.1、6.2 | 否 | 无 | `docs/evidence/agent-module/logs/evaluation-all.txt` |
| E-03 | 高 ACoS 正常路径 | `.venv/Scripts/python.exe -m amazon_ads_agent examples/high-acos-keyword.json` | 建议值 1.08；`plan_version=1`；终态 waiting；必须人工确认；dry-run 且生产写入 false | 4.2、4.3、6.2 | 否，ReasonerStub | 无 | `docs/evidence/agent-module/logs/high-acos.txt` |
| E-04 | 首次错误后修订 | `.venv/Scripts/python.exe -m amazon_ads_agent examples/invalid-reasoner-output.json --reasoner-mode invalid_once` | 首次候选越界被拒绝；新 attempt 和 plan version；第二次成功；最终 waiting；生产写入 false | 4.3、5.2、6.2 | 否，ReasonerStub 故障注入 | 无 | `docs/evidence/agent-module/logs/invalid-once.txt` |
| E-05 | 连续错误后人工介入 | `.venv/Scripts/python.exe -m amazon_ads_agent examples/repeated-invalid-output.json --reasoner-mode always_invalid` | Reasoner 两次；同一错误连续两次；无第三次调用；无 Preflight；生成人工介入包；退出码 3；生产写入 false | 4.3、5.2、5.3、6.2 | 否，ReasonerStub 故障注入 | 无 | `docs/evidence/agent-module/logs/always-invalid.txt` |
| E-06 | Git 里程碑 | `git log --oneline --decorate -12` | 当前 HEAD、PoC 初始化、协议加固、Provider、Prompt、评估、HTTP Transport 和离线验收里程碑 | 5.1、6.1 | 否 | 无 | `docs/evidence/agent-module/logs/git-milestones.txt` |

## 3. 关键结果定位

### 3.1 全量测试

日志末尾应保留：

```text
565 passed in 49.11s
exit_code=0
```

### 3.2 固定评估

日志应保留：

```text
provider=fake real_model_used=false total=12 passed=12 failed=0 production_write_violations=0
exit_code=0
```

### 3.3 正常高 ACoS

应能同时定位：`suggested_value=1.08`、`plan_version=1`、`current_status=waiting_for_approval`、`human_approval_required=true`、`production_write_called=false` 和 `exit_code=0`。

### 3.4 一次修订成功

应能同时定位：`ERR_CANDIDATE_OUT_OF_RANGE`、`plan_revised`、`attempt-0002`、`plan_version=2`、`current_status=waiting_for_approval`、`production_write_called=false` 和 `exit_code=0`。

### 3.5 连续失败安全停止

应能同时定位：两次 `reasoner_completed`、两次 `runtime_validation_failed`、`same_error_consecutive_count=2`、`stop_reason=same_error_repeated`、`current_status=manual_intervention_required`、`execution_preflight=null`、人工介入包、`production_write_called=false` 和 `exit_code=3`。

退出码 3 是本场景的预期协议结果，表示工作流安全转入人工介入，不表示测试执行异常。

## 4. 截图状态

当前 Codex 环境不能可靠截取终端窗口。未生成或伪造 PNG；完整原始日志已经保存。

| 编号 | 建议文件名 | 当前状态 | 截图时必须保留的字段 |
|---|---|---|---|
| S-01 | `01-pytest-565-passed.png` | 待人工截取 | 565 passed、耗时、exit_code=0 |
| S-02 | `02-evaluation-12-of-12.png` | 待人工截取 | provider=fake、total=12、passed=12、failed=0、real_model_used=false、写入违规 0 |
| S-03 | `03-high-acos-waiting-for-approval.png` | 待人工截取 | suggested_value=1.08、waiting_for_approval、人工确认 true、写入 false |
| S-04 | `04-invalid-once-revision.png` | 待人工截取 | 首次错误、plan_revised、attempt-0002、plan_version=2、最终 waiting |
| S-05 | `05-manual-intervention.png` | 待人工截取 | 两次失败、同错计数 2、人工介入、preflight=null、写入 false、exit_code=3 |
| S-06 | `06-git-milestones.png` | 待人工截取 | 当前 HEAD、关键提交和 `poc-01-verified` 标签 |

目标目录为 `docs/evidence/agent-module/screenshots/`。人工截图时使用 Windows Terminal 或 PowerShell，只截取终端内容，禁止包含桌面、用户名目录、API Key、Authorization 或其他隐私信息。

## 5. 人工截图命令

从仓库根目录依次执行。每条命令显示完成后使用 `Win+Shift+S` 仅框选终端结果，并按第 4 节文件名保存。

### S-01 全量测试结果

```powershell
Get-Content docs/evidence/agent-module/logs/pytest-full.txt | Select-Object -Last 10
```

### S-02 固定评估结果

```powershell
Get-Content docs/evidence/agent-module/logs/evaluation-all.txt
```

### S-03 高 ACoS 正常路径

```powershell
Get-Content docs/evidence/agent-module/logs/high-acos.txt |
  Select-String 'suggested_value|current_status|human_approval_required|production_write_called|plan_version|exit_code'
```

### S-04 一次修订成功

```powershell
Get-Content docs/evidence/agent-module/logs/invalid-once.txt |
  Select-String 'runtime_validation_failed|plan_revised|attempt-0002|plan_version|waiting_for_approval|production_write_called|exit_code'
```

### S-05 连续失败人工介入

```powershell
Get-Content docs/evidence/agent-module/logs/always-invalid.txt |
  Select-String 'reasoner_completed|runtime_validation_failed|same_error|manual_intervention_required|execution_preflight|production_write_called|exit_code'
```

### S-06 Git 里程碑

```powershell
Get-Content docs/evidence/agent-module/logs/git-milestones.txt
```

## 6. 核验说明

- 日志均由当前仓库命令实际生成，不是手工填写的测试结论。
- 截图数量：0；待人工截图数量：6。
- 未运行真实模型，未读取或配置 API Key。
- 未调用 Amazon Ads API，未创建生产 Adapter，未发生广告生产写入。
- `poc-02-verified` 未创建。
