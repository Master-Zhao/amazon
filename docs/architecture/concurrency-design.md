# Phase 1 并发设计基线

Phase 1 建立进程和任务边界，不声明任何并发量、QPS、延迟或容量目标已经达成。

## 当前并发结构

- local：Django runserver，仅开发用途。
- test：Gunicorn 2 workers，用于结构验证。
- prod：Gunicorn 3 workers，60 秒请求超时。
- local Celery Worker：prefork concurrency 2。
- prod Celery Worker：prefork concurrency 4。
- Beat 单独部署，避免与多个 Worker 混合。

这些数值是可运行默认值，不是压测结论；生产应基于 CPU、内存、任务时长和压测调优。

## 已有保护

- requestId 使用 `contextvars` 隔离并发请求日志上下文。
- Celery 有有限重试、硬/软超时和任务丢失重投基础。
- Redis 只承担可恢复的临时协调职责。
- 迁移是显式单独步骤，避免多个应用容器竞争执行迁移。

## 后续阶段必须补充

- 数据写入幂等键、唯一约束和并发冲突测试。
- 导入、分析、审批与执行的状态机锁和事务边界。
- `select_for_update`、乐观版本或短锁的具体选择。
- Beat 单实例保障及任务重复派发保护。
- 容量、压力、超时、连接池与故障恢复测试。

在这些测试完成前，不得宣称系统满足主规格中的任何性能目标。
