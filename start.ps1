<#
.SYNOPSIS
    RouteWise start script (Windows / PowerShell).

.DESCRIPTION
    Brings up everything needed for local dev:
      1. Actian VectorAI DB (docker compose, detached).
      2. FastAPI backend on :8000   - if backend/ exists with main.py.
      3. Frontend dev server         - in routewise/.

    The frontend runs in the foreground; Ctrl+C tears it down. The VDB
    container keeps running (intentional — it's slow to warm). Stop it with:
      docker compose -f vectorai-db-beta\docker-compose.yml down
#>

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

function Section($msg) { Write-Host "`n=== $msg ===" -ForegroundColor Cyan }

Section "Starting Actian VectorAI DB"
docker compose -f "vectorai-db-beta\docker-compose.yml" up -d

$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

if (Test-Path "backend\main.py") {
    Section "Starting FastAPI backend on :8000"
    if (-not (Test-Path $venvPython)) {
        Write-Host "[start] .venv missing — run .\install.ps1 first" -ForegroundColor Red
        exit 1
    }
    Start-Process -FilePath $venvPython `
        -ArgumentList "-m","uvicorn","backend.main:app","--reload","--port","8000" `
        -WorkingDirectory $PSScriptRoot
} else {
    Write-Host "[start] backend/main.py not found yet — skipping API boot" -ForegroundColor Yellow
}

Section "Starting frontend (routewise/)"
Push-Location "routewise"
try {
    npm run dev
} finally {
    Pop-Location
}
