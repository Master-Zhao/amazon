# 迁移历史与数据库结构协调

日期：2026-07-28

## 最终策略

本次协调以现有 MySQL 数据安全为第一优先级，恢复数据库创建时实际执行的
历史迁移快照，并让当前仓库沿用这条已运行谱系。

没有执行：

- `migrate --fake` 或 `migrate --fake-initial`
- 修改或删除 `django_migrations` 记录
- `DROP TABLE`、`TRUNCATE TABLE`
- 删除或重建现有 MySQL 数据卷
- `docker compose down -v`
- reset、revert 或覆盖既有标签

## 为什么没有把现有 bigint 主键强制改成 UUID

RC1 后来生成的迁移文件把多项既有 bigint 主键、外键和字段定义改写成了
另一套 UUID 初始结构，但数据库已使用早期历史迁移保存了真实关联数据。

直接套用后来文件会同时影响 tenants、stores、permissions、products、reports、
advertising、analytics、agents、recommendations、actions、audit 共 11 个应用，
并不能通过一个字段补丁安全解决。

本次任务明确规定冲突时按“数据安全 → 已确认业务规则 → 迁移兼容”处理。
因此保留数据库实际使用的内部主键结构，API 继续把所有对象 ID 输出为字符串。
这一选择避免了破坏已有外键、审批记录、执行记录、报表血缘和审计记录。

## 恢复的历史快照

关键恢复项包括：

```text
actions.0001_initial
actions.0002_initial
advertising.0001_initial
advertising.0002_initial
advertising.0003_initial
advertising.0004_campaign_target_acos
agents.0001_initial
analytics.0001_initial
analytics.0002_searchtermdailymetric_searchtermmetricrevision_and_more
analytics.0003_campaigndailymetric_snapshot_hour_local_and_more
analytics.0004_persist_metric_calculation_reasons
audit.0001_initial
permissions.0001_initial
products.0001_initial
recommendations.0001_initial
reports.0001_initial
stores.0001_initial
tenants.0001_initial
```

这些文件与当前数据卷的 `django_migrations` 记录和实际表结构一致。
今后不得修改这些已执行迁移，只能增加新的向前迁移。

## 新增迁移

### `permissions.0002_permission_description`

在不修改已执行 `permissions.0001_initial` 的前提下，为 `sys_permission` 新增：

```text
description varchar(255) NOT NULL DEFAULT ''
```

### `permissions.0003_seed_permissions`

幂等补齐当前运行链路使用的权限编码，并给已有记录补充名称和说明。
使用 `update_or_create(code=...)`，不会重复创建相同编码。

### Knowledge

现有数据库此前没有应用知识库迁移。恢复迁移图后正常应用：

```text
knowledge.0001_initial
knowledge.0002_seed_knowledge
```

## 原“8 个未应用迁移”的处理

| 原 RC1 项目 | 处理结果 |
| --- | --- |
| actions 新索引/幂等迁移 | 实际历史 `actions.0002_initial` 已包含运行模型所需版本、幂等和执行结构 |
| advertising target ACOS | 恢复为数据库实际已执行的 `0004_campaign_target_acos` |
| advertising Search Term 改名 | 保留真实历史字段和运行解析契约，避免覆盖已有数据 |
| agents 索引迁移 | 实际历史 `agents.0001_initial` 已包含运行所需索引 |
| knowledge 两步 | 正常向前应用 |
| permissions seed | 改为 description 后的 `0003_seed_permissions` |
| recommendations 索引 | 实际历史 `recommendations.0001_initial` 已包含运行索引 |

没有把名称冲突的后来文件继续伪装成数据库已执行迁移。

## 备份

写入现有数据库前已创建仓库外备份：

```text
C:\Users\admin\AppData\Local\Temp\codex-amazon-ads-v1-stage2-20260728-2325\
amazon_ads_before_reconciliation_no_drop.sql
```

验证：

```text
SHA-256: DB88B84918945FADA06B1FB390751FE37A4DFEE81EBDBE55D48946162C807A2F
mysqldump completion marker: present
DROP TABLE statements: absent
```

备份未加入 Git。

## 隔离升级验证

在无主机端口、MySQL `tmpfs` 的隔离容器中恢复备份副本，再执行迁移。

结果：

```text
knowledge.0001_initial                     OK
knowledge.0002_seed_knowledge              OK
permissions.0002_permission_description    OK
permissions.0003_seed_permissions          OK
second migrate                             No migrations to apply
```

关键数据行在升级前后保持：

```text
sys_user                              3
ads_campaign                          2
analytics_campaign_daily_metric       2
```

升级后：

```text
sys_permission.description column     1
knowledge_category rows               6
knowledge_article rows                6
```

## 空数据库从零验证

在同一隔离 MySQL 中创建全新空数据库并执行完整迁移。

结果：

```text
42 migrations applied
makemigrations --check --dry-run: No changes detected
sys_permission rows: 15
knowledge_category rows: 6
sys_permission.description column: present
```

## 现有数据库升级结果

隔离验证通过后，才对现有数据卷执行相同迁移。

结果：

```text
first migrate: 4 migrations OK
second migrate: No migrations to apply
sys_user: 3
ads_campaign: 2
analytics_campaign_daily_metric: 2
sys_permission: 16
knowledge_category: 6
knowledge_article: 6
sys_permission.description: present
```

## 重复验证命令

```powershell
python backend/manage.py check
python backend/manage.py makemigrations --check --dry-run
python backend/manage.py migrate --check
python backend/manage.py showmigrations --plan
python -m pytest backend/tests/test_migration_reconciliation.py
```

运行本机命令时必须通过未跟踪环境变量提供数据库密码，不得提交真实 `.env`。
