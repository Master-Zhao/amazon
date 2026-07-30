<#
.SYNOPSIS
    Amazon Ads 优化系统 - 本地无 Docker 一键环境配置脚本
.DESCRIPTION
    自动检测并安装 Python、Node.js、MySQL、Redis，
    创建 Python 虚拟环境，安装后端/前端依赖，
    初始化数据库，生成 .env 配置文件。
.EXAMPLE
    .\setup-local.ps1
    .\setup-local.ps1 -SkipMysql -SkipRedis   # 跳过 MySQL/Redis 安装提示
#>
param(
    [switch]$SkipMysql,
    [switch]$SkipRedis,
    [switch]$SkipNode,
    [switch]$SkipPython
)

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot

function Write-Step($msg) { Write-Host "`n=== $msg ===" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "  [OK] $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "  [WARN] $msg" -ForegroundColor Yellow }
function Write-Fail($msg) { Write-Host "  [FAIL] $msg" -ForegroundColor Red }

# ──────────────────────────────────────────────
# 1. 检测 Python
# ──────────────────────────────────────────────
Write-Step "检测 Python 环境"

$pythonCmd = $null
foreach ($cmd in @("python3.11", "python3.12", "python3.13", "python")) {
    try {
        $ver = & $cmd --version 2>&1
        if ($ver -match "Python (\d+\.\d+)") {
            $majorMinor = [version]$Matches[1]
            if ($majorMinor -ge [version]"3.11") {
                $pythonCmd = $cmd
                Write-Ok "找到 Python: $ver ($cmd)"
                break
            }
        }
    } catch {}
}

if (-not $pythonCmd -and -not $SkipPython) {
    Write-Warn "未找到 Python >= 3.11"
    Write-Host "  请安装 Python 3.11+: https://www.python.org/downloads/"
    Write-Host "  Windows 推荐用 winget: winget install Python.Python.3.11"
    $pythonCmd = Read-Host "  输入 Python 可执行文件路径 (或回车跳过)"
    if (-not $pythonCmd) { Write-Fail "无法继续，需要 Python >= 3.11"; exit 1 }
}

# ──────────────────────────────────────────────
# 2. 检测 Node.js + pnpm
# ──────────────────────────────────────────────
Write-Step "检测 Node.js 环境"

$nodeOk = $false
try {
    $nodeVer = & node --version 2>&1
    if ($nodeVer -match "v(\d+)\.") {
        $nodeMajor = [int]$Matches[1]
        if ($nodeMajor -ge 18) { $nodeOk = $true; Write-Ok "Node.js $nodeVer" }
        else { Write-Warn "Node.js 版本过低 ($nodeVer)，需要 >= 18" }
    }
} catch { Write-Warn "未找到 Node.js" }

if (-not $nodeOk -and -not $SkipNode) {
    Write-Host "  请安装 Node.js 18+: https://nodejs.org/ 或 winget install OpenJS.NodeJS.LTS"
    Read-Host "  安装后按回车继续"
}

$pnpmOk = $false
try {
    $pnpmVer = & pnpm --version 2>&1
    $pnpmOk = $true
    Write-Ok "pnpm $pnpmVer"
} catch {
    Write-Warn "未找到 pnpm，正在安装..."
    & npm install -g pnpm
    if ($?) { $pnpmOk = $true; Write-Ok "pnpm 安装成功" }
    else { Write-Fail "pnpm 安装失败，请手动: npm install -g pnpm" }
}

# ──────────────────────────────────────────────
# 3. 检测 MySQL
# ──────────────────────────────────────────────
Write-Step "检测 MySQL"

$mysqlOk = $false
try {
    $mysqlVer = & mysql --version 2>&1
    $mysqlOk = $true
    Write-Ok "MySQL: $mysqlVer"
} catch {}

if (-not $mysqlOk -and -not $SkipMysql) {
    Write-Warn "未找到 MySQL"
    Write-Host "  Windows 安装方式:"
    Write-Host "    1. MySQL Installer: https://dev.mysql.com/downloads/installer/"
    Write-Host "    2. winget:          winget install Oracle.MySQL"
    Write-Host "    3. Chocolatey:      choco install mysql"
    Read-Host "  安装后按回车继续"
}

# ──────────────────────────────────────────────
# 4. 检测 Redis
# ──────────────────────────────────────────────
Write-Step "检测 Redis"

$redisOk = $false
try {
    $redisVer = & redis-server --version 2>&1
    $redisOk = $true
    Write-Ok "Redis: $redisVer"
} catch {}

if (-not $redisOk -and -not $SkipRedis) {
    Write-Warn "未找到 Redis"
    Write-Host "  Windows 安装方式:"
    Write-Host "    1. Memurai (推荐):  https://www.memurai.com/get-memurai"
    Write-Host "    2. Chocolatey:      choco install redis-64"
    Write-Host "    3. WSL:             wsl 中 apt install redis-server"
    Write-Host "  也可以跳过 Redis，Celery 会使用 eager 模式（仅限开发）"
    $ans = Read-Host "  是否跳过 Redis? (Y/n)"
    if ($ans -ne "n" -and $ans -ne "N") {
        Write-Warn "将跳过 Redis，Celery 使用 eager 模式"
    } else {
        Read-Host "  安装 Redis 后按回车继续"
    }
}

# ──────────────────────────────────────────────
# 5. 创建 .env 文件
# ──────────────────────────────────────────────
Write-Step "生成 .env 配置文件"

$envFile = Join-Path $ProjectRoot ".env"
$envTemplate = Join-Path $ProjectRoot ".env.local-nodocker"

if (Test-Path $envFile) {
    Write-Warn ".env 已存在，跳过（如需重新生成请先删除 .env）"
} elseif (Test-Path $envTemplate) {
    Copy-Item $envTemplate $envFile
    Write-Ok "已从 .env.local-nodocker 复制生成 .env"
} else {
    Write-Warn "未找到 .env.local-nodocker 模板，请手动创建 .env"
}

# ──────────────────────────────────────────────
# 6. 后端: 创建虚拟环境 + 安装依赖
# ──────────────────────────────────────────────
Write-Step "配置后端 Python 环境"

$backendDir = Join-Path $ProjectRoot "backend"
$venvDir = Join-Path $backendDir ".venv"

if ($pythonCmd) {
    if (-not (Test-Path $venvDir)) {
        Write-Host "  创建虚拟环境..."
        & $pythonCmd -m venv $venvDir
        Write-Ok "虚拟环境已创建: $venvDir"
    } else {
        Write-Ok "虚拟环境已存在"
    }

    $pipCmd = Join-Path $venvDir "Scripts\pip.exe"
    if (-not (Test-Path $pipCmd)) {
        $pipCmd = Join-Path $venvDir "bin\pip"
    }

    Write-Host "  安装后端依赖 (这可能需要几分钟)..."
    $reqFile = Join-Path $backendDir "requirements-dev.txt"
    if (Test-Path $reqFile) {
        & $pipCmd install -r $reqFile
    } else {
        $reqFile = Join-Path $backendDir "requirements.txt"
        & $pipCmd install -r $reqFile
    }
    if ($?) { Write-Ok "后端依赖安装完成" }
    else { Write-Fail "后端依赖安装失败，请检查错误信息" }
}

# ──────────────────────────────────────────────
# 7. 前端: 安装依赖
# ──────────────────────────────────────────────
Write-Step "配置前端 Node.js 环境"

$frontendDir = Join-Path $ProjectRoot "frontend"

if ($pnpmOk) {
    Write-Host "  安装前端依赖 (这可能需要几分钟)..."
    & pnpm --dir $frontendDir install
    if ($?) { Write-Ok "前端依赖安装完成" }
    else { Write-Fail "前端依赖安装失败" }
}

# ──────────────────────────────────────────────
# 8. 初始化数据库
# ──────────────────────────────────────────────
Write-Step "初始化数据库"

if ($mysqlOk -and $pythonCmd) {
    $dbUser = if ($env:DB_USER) { $env:DB_USER } else { "amazon_ads" }
    $dbPass = if ($env:DB_PASSWORD) { $env:DB_PASSWORD } else { "local-database-password" }
    $dbName = if ($env:DB_NAME) { $env:DB_NAME } else { "amazon_ads" }

    Write-Host "  尝试创建数据库和用户..."
    $createSql = @"
CREATE DATABASE IF NOT EXISTS $dbName CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE USER IF NOT EXISTS '$dbUser'@'localhost' IDENTIFIED BY '$dbPass';
GRANT ALL PRIVILEGES ON ${dbName}.* TO '$dbUser'@'localhost';
FLUSH PRIVILEGES;
"@
    try {
        $createSql | & mysql -u root -p 2>&1
        Write-Ok "数据库初始化完成"
    } catch {
        Write-Warn "数据库初始化失败，请手动执行:"
        Write-Host $createSql
    }
}

# ──────────────────────────────────────────────
# 9. 运行数据库迁移
# ──────────────────────────────────────────────
Write-Step "运行数据库迁移"

if ($pythonCmd -and (Test-Path $venvDir)) {
    $djangoCmd = Join-Path $venvDir "Scripts\python.exe"
    if (-not (Test-Path $djangoCmd)) {
        $djangoCmd = Join-Path $venvDir "bin\python"
    }

    $env:DJANGO_SETTINGS_MODULE = "config.settings.local"
    & $djangoCmd (Join-Path $backendDir "manage.py") migrate --noinput
    if ($?) { Write-Ok "数据库迁移完成" }
    else { Write-Warn "迁移失败，可能数据库尚未就绪" }
}

# ──────────────────────────────────────────────
# 完成
# ──────────────────────────────────────────────
Write-Step "配置完成"

Write-Host @"
  后端启动:  .\start-local.ps1 -Backend
  前端启动:  .\start-local.ps1 -Frontend
  全部启动:  .\start-local.ps1
  访问地址:  http://localhost:5173 (前端)
             http://localhost:8000 (后端 API)
             http://localhost:8000/api/docs/ (API 文档)
"@ -ForegroundColor White