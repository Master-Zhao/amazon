# 亚马逊广告智能体比赛交接清单

## GitHub 工程材料

| 项目 | 交接内容 | 状态 |
|---|---|---|
| 仓库 | <https://github.com/Master-Zhao/amazon> | 已推送 |
| 默认分支 | `main` | 已核验 |
| 首页 README | `README.md`（`main` 根目录） | 已推送 |
| 完整 PoC 分支 | `agent-poc-import` | 已推送 |
| CI | `.github/workflows/ci.yml` | Run `29796371771` success |
| Release Notes | `docs/releases/v0.1.0-offline-poc.md` | 已留档 |
| Tag | `v0.1.0-offline-poc` | 发布交接时核验 |
| 当前工程 Commit | 以 Tag 指向的提交为准 | 发布交接时核验 |
| 全量测试 | 565 passed | 已复验 |
| Fake 评估 | 12/12 passed；`real_model_used=false`；写入违规 0 | 已复验 |

## 智能体比赛材料

- 第 04、05、06 章：`docs/reports/competition-sections-04-06-agent-module.md`；
- 六页 PPT 大纲：`docs/reports/agent-module-ppt-outline.md`；
- 三场景演示脚本：`docs/demo/agent-module-demo-runbook.md`；
- 证据索引：`docs/evidence/agent-module/evidence-index.md`；
- 文本日志：`docs/evidence/agent-module/logs/`，共 6 份；
- 截图：未伪造，当前 0 份；索引保留 6 份人工截取步骤。

## 可直接用于总项目章节

| 总项目章节 | 智能体材料 |
|---|---|
| 2.2 系统架构 | 智能体状态图和数据流 |
| 4.1 管理页 | AI 副驾驶结构化输出 |
| 4.2 数据分析 | 单对象指标与证据分析 |
| 4.3 AI 优化 | Candidate、Reasoner、Validator、人工确认 |
| 5 技术难点 | 关键架构决策与安全边界 |
| 6 测试效果 | pytest、Fake 评估和零写入违规 |
| 7 差异化亮点 | 受控 AI、有限修订、可审计、fail-closed |
| 8 赛题契合 | AI 原生、人机协同和安全工程化 |

## 仍需其他团队成员补充

- CodeArts 需求、代码生成、测试和 CI/CD 截图；
- 华为云资源架构、真实部署信息；
- 前端管理页、数据分析页面和完整系统演示；
- 用户反馈材料；
- 按证据索引中的命令人工截取 6 张终端截图。

## 禁止误用的结论

- 不得声称真实模型已经验证；
- 不得声称 Amazon Ads API 已接入；
- 不得声称预算优化或静默学习已经完成；
- 不得使用或创建 `poc-02-verified`；
- 不得把离线 PoC 结果描述为生产验收结果。
