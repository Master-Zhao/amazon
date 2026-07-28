# Phase 0 仓库审计与命令记录

审计日期：2026-07-28  
工作目录：`C:\QSZ\技术方案`  
范围：排除 `amazon-ads-operations-0.1.1` 隔离目录

## 1. 审计结论

- 根目录不是 Git 仓库。
- 除隔离目录外，审计前只有根 README、AGENTS、主规格、00—15 设计文档和 8 个 Mermaid 图。
- 没有后端、前端、依赖清单、锁文件、迁移、测试、Dockerfile、Compose、环境示例或 CI。
- 系统不可启动，业务演示不能开始。
- 本阶段未安装依赖、未创建业务代码、迁移、接口或页面。

## 2. 实际执行的命令与结果

### 2.1 根目录和 Git

```powershell
Get-ChildItem -Force | Select-Object Mode,Length,LastWriteTime,Name
git status --short --branch
```

结果：

- 根目录含 `amazon-ads-operations-0.1.1`、`docs`、`AGENTS.md`、`codex_master_goal_amazon_ads_v1.md`、`README.md`。
- Git 命令失败：`fatal: not a git repository (or any of the parent directories): .git`。

### 2.2 文件清单

```powershell
rg --files -g '!amazon-ads-operations-0.1.1/**'
```

结果：审计前列出 27 个非隔离文件，全部为 Markdown；没有源码、配置、迁移或测试文件。

### 2.3 主规格和现有文档读取

实际使用 `Get-Content -Encoding UTF8` 完整读取：

- `codex_master_goal_amazon_ads_v1.md`，1,174 行，分三段读取。
- `AGENTS.md`、`README.md`。
- `docs/00-project-overview.md` 至 `docs/15-decision-log.md`。
- `docs/diagrams` 下全部 8 个 Markdown/Mermaid 文件。

用于读取的命令形式：

```powershell
Get-Content -LiteralPath <file> -Encoding UTF8
```

主规格标题枚举命令：

```powershell
$lines=Get-Content -LiteralPath '.\codex_master_goal_amazon_ads_v1.md' -Encoding UTF8
$lines | Select-String -Pattern '^#{1,4} '
```

结果：确认 23 个主章节及 Phase 0 指令，完整行数 1,174。

### 2.4 工程路径探测

```powershell
@('backend','frontend','tests','pyproject.toml','uv.lock','requirements.txt','package.json','pnpm-lock.yaml','Dockerfile','docker-compose.yml','docker-compose.yaml','compose.yml','compose.yaml','.env','.env.example','Makefile','manage.py','pytest.ini','tox.ini','.github') |
  ForEach-Object { '{0}={1}' -f $_,(Test-Path -LiteralPath $_) }
```

结果：所有路径均为 `False`。

### 2.5 本机工具版本

```powershell
python --version
node --version
pnpm --version
docker --version
docker compose version
git --version
```

结果：

```text
Python 3.12.4
v24.10.0
11.9.0
Docker version 29.5.2, build 79eb04c
Docker Compose version v5.1.4
git version 2.51.0.windows.1
```

说明：当前默认 Python 低于主规格 3.13；Node 为 24 LTS 主版本。工具版本不代表项目依赖已安装或兼容。

### 2.6 依赖命令探测

```powershell
$tools=@('uv','mysql','redis-server','nginx')
foreach($name in $tools){
  $cmd=Get-Command $name -ErrorAction SilentlyContinue
  if($null -eq $cmd){ Write-Output ($name+': NOT_FOUND') }
  else{ Write-Output ($name+': '+$cmd.Source) }
}
python -m django --version
python -m celery --version
```

结果：

- `uv` 存在于 `C:\Users\admin\.local\bin\uv.exe`。
- 全局 Python 可导入 Django，版本 `5.2.15`，但仓库没有 Django 项目。
- Celery 探测失败：`C:\ProgramData\anaconda3\python.exe: No module named celery`。
- 未发现 `mysql`、`redis-server`、`nginx` 本机命令。

### 2.7 Git 根检查和 Compose 配置检查

```powershell
git rev-parse --show-toplevel
docker compose config --quiet
```

结果：

- Git：`fatal: not a git repository (or any of the parent directories): .git`。
- Compose：`no configuration file provided: not found`。

### 2.8 受保护的项目检查

执行了以下存在性守卫：

```powershell
if(Test-Path -LiteralPath '.\backend'){
  Write-Output 'backend found: test command must be read from its manifest'
}else{
  Write-Output 'SKIPPED backend tests: backend/ does not exist'
}
if(Test-Path -LiteralPath '.\package.json'){
  Write-Output 'root package.json found'
}elseif(Test-Path -LiteralPath '.\frontend\package.json'){
  Write-Output 'frontend/package.json found'
}else{
  Write-Output 'SKIPPED frontend typecheck/build: no package.json exists outside isolated directory'
}
if((Test-Path -LiteralPath '.\compose.yaml') -or
   (Test-Path -LiteralPath '.\compose.yml') -or
   (Test-Path -LiteralPath '.\docker-compose.yaml') -or
   (Test-Path -LiteralPath '.\docker-compose.yml')){
  Write-Output 'Compose file found'
}else{
  Write-Output 'SKIPPED Compose service startup: no Compose file exists'
}
if(Test-Path -LiteralPath '.\manage.py'){
  Write-Output 'manage.py found'
}elseif(Test-Path -LiteralPath '.\backend\manage.py'){
  Write-Output 'backend/manage.py found'
}else{
  Write-Output 'SKIPPED Django startup/check: no manage.py exists'
}
```

实际输出：

```text
SKIPPED backend tests: backend/ does not exist
SKIPPED frontend typecheck/build: no package.json exists outside isolated directory
SKIPPED Compose service startup: no Compose file exists
SKIPPED Django startup/check: no manage.py exists
```

没有运行 pytest、前端 typecheck/build 或 Django check，因为没有对应工程/清单；没有扫描隔离目录。

### 2.9 Phase 0 文档结构复核

实际执行了 `Test-Path`、`Select-String`、README 相对链接解析、`rg --files` 和关键决策 `rg -n` 的组合检查。

结果：

```text
PASS: all required Phase 0 files exist
Phase headings=7
Required phase field headings=70
README 中 24 个相对链接目标均存在
PASS: no non-Markdown implementation files created
D-101/102/103/104/117/118/124/128 均检出“已确认”
PASS: no selected typo/false-claim patterns found
```

## 3. 检查计数

| 检查类别 | 通过 | 失败 | 跳过 |
|---|---:|---:|---:|
| 主规格和文档可读 | 27 个审计前非隔离文件可读 | 0 | 0 |
| Git 状态 | 0 | 2 个 Git 命令 | 0 |
| 工具探测 | Python/Node/pnpm/Docker/Compose/Git/uv/Django 可调用 | Celery、mysql、redis-server、nginx 不可用 | 0 |
| 后端测试/启动 | 0 | 0 | 2 |
| 前端 typecheck/build | 0 | 0 | 2 |
| Compose | Docker/Compose CLI 可用 | config 失败（无配置） | service startup 跳过 |

这里的“通过”仅表示命令或文档检查结果，不表示任何业务测试通过。

## 4. 未执行

- 未执行依赖安装。
- 未执行数据库连接、迁移或 seed。
- 未执行后端测试、OpenAPI 校验、前端测试/typecheck/build。
- 未启动 API、Worker、Beat、MySQL、Redis、Nginx 或前端。
- 未执行浏览器 E2E。
- 未执行真实 Amazon 报表验证。
- 未执行任何并发、QPS、延迟或性能测试。
