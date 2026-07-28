# Adapter 开发

稳定边界：

| 能力 | Protocol | 当前实现 | 保留实现 |
|---|---|---|---|
| 报表 | `ReportSource` | `FileUploadReportSource` | `ThirdPartyProviderReportSource`, `AmazonAdsApiReportSource` |
| 文件 | `FileStorage` | `LocalFileStorage` | `ObjectStorageFileStorage` |
| LLM | `LLMProvider` | `MockLLMProvider` | `ExternalLLMProvider` |
| 执行 | `AmazonAdsExecutionAdapter` | `ManualExecutionAdapter` | `ReservedAmazonAdsExecutionAdapter` |
| 监控 | `MonitoringSink` | `LoggingMonitoringSink` | 生产 exporter 待接入 |

实现必须使用已定义 request/result dataclass 和专用错误类型；外部调用设置
timeout、有限重试且只重试瞬时错误。调用方生成并持久化幂等键，Adapter 不得跨
Tenant/Profile 合并或缓存凭据；日志不得包含 token、cookie 或正文。

对象存储 key 必须以 tenant namespace 开始；Report/Execution Adapter 校验目标
Profile 属于授权 Tenant。示例/单测应以 fake transport 或 Mock 返回固定结果，
禁止连真实 Amazon、第三方或 LLM。生产实现还需凭据轮换、指标、告警、限流和
故障注入验收。
