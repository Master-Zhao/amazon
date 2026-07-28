# Phase 1 异步任务设计

## 运行结构

Celery 与 Django 通过 `config/celery.py` 集成，Broker 为 Redis DB 0，短期结果后端为 Redis DB 1。Compose 分别运行 `celery-worker` 与 `celery-beat`。

预留队列：

- `default`
- `imports`
- `analysis`
- `maintenance`

Phase 1 只注册 `apps.core.tasks.smoke_task`，路由到 `default`。它仅返回 `status`、`request_id` 和 `task_id`，不写业务表，也不代表报表、分析或 AI 能力。

## 可靠性基线

- 全局硬超时默认 30 秒、软超时默认 20 秒，可通过环境变量调整。
- smoke task 使用 10 秒软超时、15 秒硬超时。
- 仅对 `ConnectionError` 自动重试，指数退避，最多 2 次；没有无限重试。
- `task_acks_late=True`、`task_reject_on_worker_lost=True`。
- 结果默认 3600 秒过期。
- 日志包含 requestId 和 Celery taskId。
- 三套 Compose 的 Worker healthcheck 先验证 PID1 存活，再通过定向 `celery inspect ping` 验证 Broker 连通和 Worker 响应；30 秒间隔、10 秒超时、5 次重试、30 秒启动宽限，输出被抑制以避免探针日志噪声。
- Beat healthcheck 验证 PID1 存活且 `/proc/1/cmdline` 确实为 Celery beat 调度进程；不依赖永远存在的静态文件。30 秒间隔、5 秒超时、3 次重试、20 秒启动宽限。

## 已验证路径

执行：

```powershell
docker compose -f compose.local.yml exec backend python manage.py celery_smoke --timeout 30
```

实际由 Django 管理命令发布任务，Redis Broker 传递，Worker 执行，Redis result backend 返回结果。最终收口验证 taskId 为 `6dd14fe1-8108-4383-b141-ee1817a68d21`，命令成功退出；`docker compose ps` 同时确认 Worker 与 Beat 均为 healthy。

## 后续约束

Phase 2—7 的异步入口仍必须是 `Celery Task → Service`。Task 不得直接修改核心状态；事务提交后再派发。Beat 当前没有业务周期任务，不能被解释为导入、分析或清理调度已完成。
