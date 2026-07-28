# 备份与恢复

本手册适用于 V1 单机 Compose 部署。备份对象包括 MySQL、上传文件卷、受控环境配置和实际部署的镜像/提交标识；Redis 不作为业务事实备份源。

## 备份

在受控主机设置本地环境变量，不把密码写入命令历史或仓库：

```powershell
$env:MYSQL_PWD = Read-Host "输入数据库密码"
docker compose --env-file .env.prod -f compose.prod.yml exec -T mysql mysqldump --single-transaction --routines --triggers --databases amazon_ads > amazon_ads_YYYYMMDD.sql
Remove-Item Env:MYSQL_PWD
docker compose --env-file .env.prod -f compose.prod.yml cp backend:/app/media ./media-backup-YYYYMMDD
git rev-parse HEAD
docker compose --env-file .env.prod -f compose.prod.yml images
```

实际数据库名和上传挂载路径以受控 `.env.prod` 与 Compose 为准。备份文件必须加密、限制访问并执行保留策略；不得提交 Git。

## 恢复演练

恢复必须先在隔离环境验证：

1. 记录待恢复提交、镜像标签、迁移版本和备份哈希。
2. 启动空的 MySQL/Redis，不连接生产流量。
3. 导入 SQL，再恢复上传文件。
4. 使用对应提交运行 `python manage.py migrate --check`。
5. 检查 `/health/live`、`/health/ready`，再执行登录、上下文、导入、分析、审批和审计烟雾测试。
6. 抽样核对租户数量、关键只追加表数量和文件哈希。

示例导入命令：

```powershell
Get-Content amazon_ads_YYYYMMDD.sql | docker compose --env-file .env.restore -f compose.prod.yml exec -T mysql mysql
docker compose --env-file .env.restore -f compose.prod.yml --profile tools run --rm migrate python manage.py migrate --check
```

## 恢复点与回滚边界

- 数据迁移默认前向修复；未经验证不得反向执行可能丢数据的迁移。
- `ReportUpload`、`ImportTask`、`ImportBatch`、Recommendation revision、Preview version、审批、执行和审计记录保持只追加语义。
- 应用回滚不能替代数据库恢复；镜像、数据库和上传文件必须来自兼容恢复点。
- M6 当前只交付手册，未在本执行环境完成真实备份恢复演练，状态为 `NOT VERIFIED`。
