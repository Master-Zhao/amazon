# V1 性能测试计划

性能目标是待验证目标，不是能力声明。M6 提供可重复脚本、数据规模和停止条件；当前未在主规格参考环境完成 300 虚拟用户、200 RPS、10 分钟正式压测。

## 前置条件

- 使用隔离 test 环境、虚构 fixtures 和独立 Tenant/Profile。
- 固定提交、镜像、CPU、内存、MySQL/Redis 配置并记录。
- 从零迁移并导入 5 份各 100,000 行的虚构 CSV；不得使用真实广告数据。
- 先验证权限、幂等和审计正确性，再增加压力。

## 分层场景

| 场景 | 负载 | 验证 |
|---|---:|---|
| live/ready 基线 | 10 RPS，30 秒 | 网络、代理、健康端点 |
| 只读业务 API | 逐步 20/50/100/200 RPS | p50/p95、错误率、查询数、租户隔离 |
| 报表导入 | 5 × 100,000 行并发 | 内存、批次唯一、部分失败、重述 |
| Mock 分析 | 20 个并发任务 | 队列隔离、超时、重复 Recommendation |
| 审批/执行 | 重放与并发请求 | 单审批/单执行记录、状态不回退 |
| 实例对比 | 1 与 2 个 API 实例 | 吞吐、连接池、锁等待 |

## 命令

无第三方依赖的只读烟雾脚本：

```powershell
python tests/performance/load_smoke.py --base-url http://localhost:8081 --path /health/live --duration 30 --rps 10
```

受保护接口通过进程环境或调用方安全注入短期 Access Token；脚本不会打印 Token：

```powershell
python tests/performance/load_smoke.py --base-url http://localhost:8081 --path /api/v1/audit/ --duration 60 --rps 20 --access-token $env:LOAD_ACCESS_TOKEN --tenant-id $env:LOAD_TENANT_ID
```

## 采集与停止条件

记录提交、时间、环境、命令、原始 JSON、容器资源、MySQL 慢查询/锁等待、Celery 队列长度和错误日志。出现跨租户数据、重复不可变记录、状态回退、秘密泄露、持续 5xx 或资源失控时立即停止。不得通过放宽认证、权限、审批或隔离规则获得更高数字。

## 当前结论

脚本语法和 `--help` 在 M6 验证；正式容量测试为 `NOT VERIFIED`。因此不声明 200 RPS、300 用户、延迟或容量上限。
