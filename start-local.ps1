<#
.SYNOPSIS
    Amazon Ads 优化系统 - 本地无 Docker 启动脚本
.DESCRIPTION
    启动后端 Django、前端 Vite dev server，可选启动 Celery worker/beat 和 Redis。
.EXAMPLE
    .\start-local.ps1                  # 启动全部
    .\start-local.ps1 -BackendOnly     # 仅启动后端
    .\start-local.ps1 -FrontendOnly    # 仅启动前端
    .\start-local.ps1 -NoCelery        # 启动前后端但不启动 Celery
#>
param(
    [switch]$BackendOnly,
    [switch]$FrontendOnly,
    [switch]$NoCelery,
    [switch]$NoRedis,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot
$backendDir = Join-Path $ProjectRoot "backend"
$frontendDir = Join-Path $ProjectRoot "frontend"
$venvDir = Join-Path $backendDir ".venv"
$frontendUrl = "http://localhost:5173/advertising/overview"

# 加载 .env
$envFile = Join-Path $ProjectRoot ".env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match "^\s*([^#][^=]+)=(.*)$") {
            $key = $Matches[1].Trim()
            $val = $Matches[2].Trim()
            if (-not [System.Environment]::GetEnvironmentVariable($key)) {
                [System.Environment]::SetEnvironmentVariable($key, $val, "Process")
            }
        }
    }
}

# 确保使用 local settings
$env:DJANGO_SETTINGS_MODULE = "config.settings.local"

# 查找虚拟环境中的 Python
$pythonCmd = $null
$venvPython = Join-Path $venvDir "Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    $venvPython = Join-Path $venvDir "bin\python"
}
if (Test-Path $venvPython) {
    $pythonCmd = $venvPython
} else {
    $pythonCmd = "python"
}

$jobs = @()

# ── Redis ──
if (-not $NoRedis -and -not $BackendOnly -and -not $FrontendOnly) {
    Write-Host "启动 Redis..." -ForegroundColor Cyan
    try {
        $redisProc = Get-Process redis-server -ErrorAction SilentlyContinue
        if ($redisProc) {
            Write-Host "  Redis 已在运行 (PID: $($redisProc.Id))" -ForegroundColor Green
        } else {
            $redisJob = Start-Job -ScriptBlock { redis-server }
            $jobs += $redisJob
            Write-Host "  Redis 已启动 (Job: $($redisJob.Id))" -ForegroundColor Green
        }
    } catch {
        Write-Host "  Redis 启动失败，Celery 将无法连接" -ForegroundColor Yellow
    }
}

# ── 后端 Django ──
if (-not $FrontendOnly) {
    Write-Host "启动后端 Django..." -ForegroundColor Cyan
    $managePy = Join-Path $backendDir "manage.py"

    # 先运行迁移检查
    & $pythonCmd $managePy migrate --check 2>$null
    if (-not $?) {
        Write-Host "  运行数据库迁移..." -ForegroundColor Yellow
        & $pythonCmd $managePy migrate --noinput
    }

    $backendJob = Start-Job -ScriptBlock {
        param($py, $manage)
        & $py $manage runserver 0.0.0.0:8000
    } -ArgumentList $pythonCmd, $managePy
    $jobs += $backendJob
    Write-Host "  后端已启动: http://localhost:8000" -ForegroundColor Green
    Write-Host "  API 文档:    http://localhost:8000/api/docs/" -ForegroundColor Green
}

# ── Celery ──
if (-not $FrontendOnly -and -not $NoCelery -and -not $BackendOnly) {
    Write-Host "启动 Celery worker + beat..." -ForegroundColor Cyan

    $celeryCmd = Join-Path $venvDir "Scripts\celery.exe"
    if (-not (Test-Path $celeryCmd)) {
        $celeryCmd = Join-Path $venvDir "bin\celery"
    }

    $celeryWorkerJob = Start-Job -ScriptBlock {
        param($celery, $backend)
        Set-Location $backend
        $env:DJANGO_SETTINGS_MODULE = "config.settings.local"
        & $celery -A config worker --loglevel=INFO --queues=default,imports,analysis,maintenance --concurrency=2
    } -ArgumentList $celeryCmd, $backendDir
    $jobs += $celeryWorkerJob

    $celeryBeatJob = Start-Job -ScriptBlock {
        param($celery, $backend)
        Set-Location $backend
        $env:DJANGO_SETTINGS_MODULE = "config.settings.local"
        & $celery -A config beat --loglevel=INFO
    } -ArgumentList $celeryCmd, $backendDir
    $jobs += $celeryBeatJob

    Write-Host "  Celery worker + beat 已启动" -ForegroundColor Green
}

# ── 前端 Vite ──
if (-not $BackendOnly) {
    Write-Host "启动前端 Vite dev server..." -ForegroundColor Cyan
    $frontendJob = Start-Job -ScriptBlock {
        param($dir)
        Set-Location $dir
        pnpm dev --host 0.0.0.0
    } -ArgumentList $frontendDir
    $jobs += $frontendJob
    Write-Host "  广告总览已启动: $frontendUrl" -ForegroundColor Green

    if (-not $NoBrowser) {
        Start-Sleep -Seconds 2
        try {
            Start-Process -FilePath $frontendUrl
        } catch {
            Write-Host "  无法自动打开浏览器，请手动访问: $frontendUrl" -ForegroundColor Yellow
        }
    }
}

# ── 等待 ──
Write-Host "`n全部服务已启动。按 Ctrl+C 停止所有服务。" -ForegroundColor White
Write-Host "  广告总览: $frontendUrl" -ForegroundColor White
Write-Host "  账号工作台: http://localhost:5173/" -ForegroundColor White
Write-Host "  后端:  http://localhost:8000" -ForegroundColor White
Write-Host "  API文档: http://localhost:8000/api/docs/" -ForegroundColor White

try {
    Wait-Job -Job $jobs
} catch {
    # Ctrl+C
} finally {
    Write-Host "`n停止所有服务..." -ForegroundColor Yellow
    $jobs | Remove-Job -Force -ErrorAction SilentlyContinue
}
