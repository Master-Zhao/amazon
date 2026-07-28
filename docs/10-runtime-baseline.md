# 10 运行环境基线

## 1. 状态

Python、Django、Django REST Framework、Celery、Node、Vue、Vite、TypeScript、MySQL和Redis的具体版本均为**待确认**。本文不自行冻结版本，也不产生依赖文件。

## 2. 固定技术方向

| 领域 | 固定技术 |
|---|---|
| 后端语言/框架 | Python、Django、Django REST Framework |
| 异步任务 | Celery |
| 前端 | Vue 3、TypeScript、Vite |
| 路由/状态/HTTP/UI/图表 | Vue Router、Pinia、Axios、Element Plus、ECharts |
| 数据库 | MySQL 8 |
| 缓存/消息/短锁 | Redis |
| 边缘与部署 | Nginx、Docker Compose |
| 契约 | OpenAPI |

## 3. 版本选择方案

### 方案A：各组件最新稳定版

- 优点：获得最新功能和安全修复。
- 影响：组件之间兼容性验证量大，文档和第三方包可能尚未跟进。

### 方案B：有维护周期的稳定组合

- 优点：维护期和兼容性更可预测。
- 影响：可能不是最新功能，需要关注支持结束日期。

### 方案C：组织现有标准基线

- 优点：部署、监控和人员经验统一。
- 影响：如果版本较旧，可能引入安全和升级成本。

### 推荐

优先选“有维护周期的稳定组合”，但必须在人工确认组织约束并完成兼容验证后冻结；当前不得填写具体版本。

## 4. 必须形成的兼容矩阵

| 组件 | 待确认版本 | 必须验证 |
|---|---|---|
| Python | 待确认 | Django、DRF、Celery、MySQL驱动支持 |
| Django | 待确认 | Python支持范围、LTS/维护期、自定义User |
| DRF | 待确认 | Django支持范围、OpenAPI工具链 |
| Celery | 待确认 | Python、Redis broker/result兼容 |
| MySQL | 8.x具体版本待确认 | 字符集、时区、CHECK、JSON、索引长度 |
| Redis | 待确认 | Celery兼容、持久化策略、内存策略 |
| Node | 待确认 | Vite、Vue、TypeScript和包管理器支持 |
| Vue | 3.x具体版本待确认 | Router、Pinia、Element Plus、ECharts |
| TypeScript | 待确认 | Vue/Vite插件与生成类型 |
| Nginx | 待确认 | 上传限制、代理超时、TLS |

## 5. 数据库基线

需要人工冻结：

- MySQL 8具体小版本。
- 字符集和排序规则；推荐支持完整Unicode，但不在本轮指定具体collation。
- 服务端、连接和会话时区策略。
- 严格SQL模式。
- Decimal精度规范。
- JSON使用边界。
- 连接数和超时初始值。

## 6. Redis边界

Redis只用于：

- Celery broker及短期任务结果。
- 短期缓存。
- 有过期时间的短锁。
- 可丢失、可从MySQL恢复的进度信息。

Redis不得保存审批、执行、审计或正式状态的唯一副本。缓存Key必须包含环境和Tenant作用域，防止碰撞。

## 7. 本地、测试和生产一致性

- 各环境使用同一主版本组合。
- 配置通过环境变量或安全配置注入，仓库只保留无秘密示例。
- 测试环境使用MockLLMProvider和Mock Amazon适配器。
- 时区、字符集、数据库严格模式在测试中与生产一致。
- 新环境通过自动化命令完成依赖安装、数据库迁移、静态构建和健康检查；具体命令在工程初始化后定义。

## 8. 冻结前验证门槛

1. 官方支持矩阵核对。
2. 最小后端启动和数据库连接实验。
3. Celery与Redis消息/重试实验。
4. 前端类型检查和生产构建实验。
5. OpenAPI生成与前端类型消费实验。
6. MySQL Decimal、UTC/业务日期和JSON行为实验。
7. 文件上传大小、代理超时和流式下载实验。
8. 依赖漏洞和许可证检查。

在上述验证和人工批准完成前，不得初始化依赖锁文件或宣称版本已冻结。
