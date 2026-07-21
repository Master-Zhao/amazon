---
name: Bug report
about: Report a reproducible defect
title: "[Bug] "
labels: bug
assignees: ""
---

## 问题描述

请清晰描述问题及其影响。

## 复现步骤

1.
2.
3.

## 使用的命令

```text

```

## 预期状态


## 实际状态


## 环境

- Python 版本：
- 操作系统：
- Git Commit：
- 是否使用真实模型（是/否）：
- 是否涉及生产写入（是/否）：

## 验证结果

- `python -m pytest -q`：
- Fake 评估：
- 日志已脱敏，未包含 Key、Token、Authorization 或完整模型响应（是/否）：

## 补充信息

请仅附脱敏日志；不要提交 `.env`、凭据或真实业务数据。
