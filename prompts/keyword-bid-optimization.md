# Keyword Bid Optimization Task

这是单 Keyword 竞价优化的只读推理任务，不是生产执行任务。

## Task Context

结构化输入的 `task_context` 包含 `task_id`、`run_id`、`attempt_id`、`plan_version`、`data_snapshot_id`、`optimization_goal` 和 `requested_risk_profile`。

## Advertising Object

`entity_metrics` 包含 `object_type`、`object_id`、`keyword`、`current_bid` 和 `object_version`。这些字段不可修改。

## Raw Metrics

原始指标仅来自输入：`impressions`、`clicks`、`orders`、`spend`、`sales`、`currency`。

## Calculated Metrics

派生指标仅来自确定性计算：`ctr`、`cpc`、`cvr`、`acos`、`roas`；目标值为 `task_context.target_acos`。

## Legal Candidates

输入以 JSON 形式提供合法候选，例如：

    {"candidate_values":["1.02","1.08","1.14"]}

selected_value 必须与 candidate_values 中某一字符串完全一致。不得自行计算、重新取整、改变精度、增加单位或生成新值。

## Constraints

只读 `constraints` 包含 `max_decrease_ratio`、`max_increase_ratio`、`min_bid`、`max_bid`、`bid_step`、`requested_risk_profile`、`human_approval_required` 和规则版本。

## Required Output

仅返回符合 `schemas/reasoner-output.schema.json` 的纯 JSON object。不要输出 Markdown、代码块或 JSON 前后的任何文字。该建议仍需系统校验、preflight 和人工审批。
