# Framework 后续验证 Backlog

| 项目 | 分类 | 负责模块 | 依赖 | 验收条件 |
|---|---|---|---|---|
| 生产限流/缓存/监控 | A | core/config/integrations.monitoring | Redis HA、监控平台、SLO | 多实例限流、Tenant cache 隔离、指标/告警和故障注入通过 |
| 300 用户/200 RPS/10 分钟 | A | testing/deployment | 生产等价 MySQL/Redis/Worker | 零跨租户、错误率/延迟/资源报告，结果不虚构 |
| 5×100,000 行并发导入 | A | reports/storage | 脱敏大文件、对象存储 | 内存峰值、队列背压、批量写入与失败恢复报告 |
| TLS 与 Cookie 域名 | A | deployment/accounts | 正式域名和证书 | HTTPS、Secure/SameSite、刷新/退出浏览器验收 |
| 真实备份恢复 | A | deployment | 备份目标、KMS、恢复环境 | 完整恢复演练、RPO/RTO 实测和校验 |
| 11 类 Action 浏览器 E2E | C | recommendations/actions/frontend | 可演示的每类对象 fixture | 每类 Preview/审批/回填/审计均通过 |
| 完整效果归因 | C | actions/analytics | 归因窗口、基线策略决策 | 窗口、对照、迟到重述和结果解释验收 |
| 真实 Amazon 报表兼容 | C/阻塞 | reports | 三类脱敏真实导出 | CSV/XLSX 字段、编码、粒度、自然键全部验证 |

分类 A 表示框架已提供配置/接口但需生产等价验证；C 表示后续产品迭代。任何项
完成前不得把 Framework RC 描述为生产认证。
