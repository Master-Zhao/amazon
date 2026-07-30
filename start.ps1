param(
    [ValidateSet("all", "docker", "hybrid")]
    [string]$Mode = "all",
    [switch]$Stop,
    [switch]$Status,
    [switch]$Help
)

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot
$ComposeFile = Join-Path $ProjectRoot "compose.local.yml"
$ComposeProject = "amazon-ads-local"

function Show-Help {
    Write-Host @"
Amazon 广告智能优化系统 V1 - 启动脚本

用法:
  .\start.ps1              # 默认：全容器模式启动
  .\start.ps1 -Mode all    # 全容器模式（Docker 启动所有服务）
  .\start.ps1 -Mode docker # 同 all
  .\start.ps1 -Mode hybrid # 混合开发模式（Docker 仅 MySQL/Redis，本地运行 Django/Vue）
  .\start.ps1 -Stop        # 停止所有服务
  .\start.ps1 -Status      # 查看服务状态
  .\start.ps1 -Help        # 显示帮助

访问地址:
  前端页面:    http://localhost:8080
  后端 API:    http://localhost:8000
  API 文档:    http://localhost:8080/api/docs/
  前端开发:    http://localhost:5173 (hybrid 模式)
"@
}

function Stop-Services {
    Write-Host "[停止] 正在停止所有服务..." -ForegroundColor Yellow
    docker compose -p $ComposeProject -f $ComposeFile down
    Write-Host "[停止] 服务已停止" -ForegroundColor Green
}

function Show-Status {
    docker compose -p $ComposeProject -f $ComposeFile ps
}

function Ensure-EnvFile {
    $envFile = Join-Path $ProjectRoot ".env"
    $envExample = Join-Path $ProjectRoot ".env.example"
    if (-not (Test-Path $envFile)) {
        Write-Host "[初始化] 未找到 .env 文件，从 .env.example 复制并填入本地默认值..." -ForegroundColor Yellow
        Copy-Item $envExample $envFile
        $content = Get-Content $envFile -Raw
        $content = $content -replace 'DJANGO_SECRET_KEY=.*', 'DJANGO_SECRET_KEY=local-development-key-not-for-production'
        $content = $content -replace 'DB_PASSWORD=.*', 'DB_PASSWORD=local-database-password'
        $content = $content -replace 'MYSQL_ROOT_PASSWORD=.*', 'MYSQL_ROOT_PASSWORD=local-root-password'
        Set-Content $envFile $content
        Write-Host "[初始化] 已创建 .env（含本地开发默认密码）" -ForegroundColor Yellow
    }
}

function Wait-For-Healthy {
    param([string[]]$Services, [int]$TimeoutSeconds = 120)
    $start = Get-Date
    foreach ($svc in $Services) {
        Write-Host "[等待] $svc 健康检查中..." -ForegroundColor Cyan -NoNewline
        while ($true) {
            $output = docker compose -p $ComposeProject -f $ComposeFile ps $svc 2>$null
            $isHealthy = $output | Select-String -Pattern "healthy" -Quiet
            if ($isHealthy) {
                Write-Host " OK" -ForegroundColor Green
                break
            }
            if (((Get-Date) - $start).TotalSeconds -gt $TimeoutSeconds) {
                Write-Host " TIMEOUT" -ForegroundColor Red
                Write-Host "[错误] $svc 在 ${TimeoutSeconds}s 内未就绪，请检查日志: docker compose -f compose.local.yml logs $svc" -ForegroundColor Red
                exit 1
            }
            Start-Sleep -Seconds 2
        }
    }
}

function Start-AllDocker {
    Ensure-EnvFile
    Write-Host "[启动] 全容器模式 - 启动所有服务..." -ForegroundColor Cyan

    Write-Host "[1/4] 启动 MySQL 和 Redis..." -ForegroundColor Cyan
    docker compose -p $ComposeProject -f $ComposeFile up -d mysql redis
    Wait-For-Healthy -Services @("mysql", "redis")

    Write-Host "[2/4] 执行数据库迁移..." -ForegroundColor Cyan
    docker compose -p $ComposeProject -f $ComposeFile --profile tools run --rm migrate

    Write-Host "[3/4] 启动后端、Celery、前端和 Nginx..." -ForegroundColor Cyan
    docker compose -p $ComposeProject -f $ComposeFile up -d backend celery-worker celery-beat frontend nginx
    Wait-For-Healthy -Services @("backend", "frontend", "nginx") -TimeoutSeconds 180

    Write-Host "[4/4] 验证健康检查..." -ForegroundColor Cyan
    $live = try { Invoke-RestMethod -Uri "http://localhost:8080/health/live" -TimeoutSec 5 } catch { $null }
    $ready = try { Invoke-RestMethod -Uri "http://localhost:8080/health/ready" -TimeoutSec 5 } catch { $null }

    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  Amazon 广告智能优化系统 V1 已启动" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  前端页面:  http://localhost:8080" -ForegroundColor White
    Write-Host "  API 文档:  http://localhost:8080/api/docs/" -ForegroundColor White
    Write-Host "  健康检查:  live=$($live.code)  ready=$($ready.code)" -ForegroundColor White
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "停止服务: .\start.ps1 -Stop" -ForegroundColor DarkGray
    Write-Host "查看状态: .\start.ps1 -Status" -ForegroundColor DarkGray
}

function Start-Hybrid {
    Ensure-EnvFile
    Write-Host "[启动] 混合开发模式 - Docker 仅运行 MySQL/Redis，本地运行 Django/Vue" -ForegroundColor Cyan

    Write-Host "[1/3] 启动 MySQL 和 Redis 容器..." -ForegroundColor Cyan
    docker compose -p $ComposeProject -f $ComposeFile up -d mysql redis
    Wait-For-Healthy -Services @("mysql", "redis")

    Write-Host "[2/3] 设置环境变量并执行迁移..." -ForegroundColor Cyan
    $env:DJANGO_SETTINGS_MODULE = "config.settings.local"
    $env:DB_HOST = "127.0.0.1"
    $env:DB_PORT = "3306"
    $env:REDIS_URL = "redis://127.0.0.1:6379/0"
    $env:CELERY_BROKER_URL = "redis://127.0.0.1:6379/0"
    $env:CELERY_RESULT_BACKEND = "redis://127.0.0.1:6379/1"
    $env:VITE_DEV_PROXY_TARGET = "http://127.0.0.1:8000"

    uv sync --project backend --frozen
    uv run --project backend python backend/manage.py migrate

    Write-Host "[3/3] 启动后端和前端开发服务器..." -ForegroundColor Cyan
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  混合开发模式已准备就绪" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  后端:  http://localhost:8000" -ForegroundColor White
    Write-Host "  前端:  http://localhost:5173" -ForegroundColor White
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""

    Write-Host "[后端] 启动 Django 开发服务器..." -ForegroundColor Cyan
    Start-Process -FilePath "uv" -ArgumentList "run", "--project", "backend", "python", "backend/manage.py", "runserver", "127.0.0.1:8000" -WorkingDirectory $ProjectRoot -PassThru | ForEach-Object {
        Write-Host "  Django PID: $($_.Id)" -ForegroundColor DarkGray
    }

    Start-Sleep -Seconds 3

    Write-Host "[前端] 启动 Vue 开发服务器..." -ForegroundColor Cyan
    Start-Process -FilePath "pnpm" -ArgumentList "--dir", "frontend", "dev" -WorkingDirectory $ProjectRoot -PassThru | ForEach-Object {
        Write-Host "  Vue PID: $($_.Id)" -ForegroundColor DarkGray
    }

    Write-Host ""
    Write-Host "后端和前端已在后台启动，关闭此窗口不会停止服务" -ForegroundColor Yellow
    Write-Host "停止服务: .\start.ps1 -Stop (停止 MySQL/Redis 容器)" -ForegroundColor DarkGray
    Write-Host "查看状态: .\start.ps1 -Status" -ForegroundColor DarkGray
}

if ($Help) { Show-Help; exit 0 }
if ($Stop) { Stop-Services; exit 0 }
if ($Status) { Show-Status; exit 0 }

switch ($Mode) {
    "all"     { Start-AllDocker }
    "docker"  { Start-AllDocker }
    "hybrid"  { Start-Hybrid }
}