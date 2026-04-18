<#
.SYNOPSIS
    RouteWise install script (Windows / PowerShell).

.DESCRIPTION
    Idempotent first-time setup:
      1. Verifies python / docker / node are on PATH.
      2. Creates .venv and installs Python deps (requirements.txt + Actian wheel).
      3. Ensures the MiniLM embedding model is present under models/.
      4. Pulls the Actian VectorAI DB Docker image.
      5. Installs frontend npm deps in routewise/.

    Re-run any time; each step short-circuits if already done.
#>

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

function Section($msg) { Write-Host "`n=== $msg ===" -ForegroundColor Cyan }
function Need($cmd, $hint) {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
        Write-Host "[install] missing dependency: $cmd" -ForegroundColor Red
        Write-Host "          $hint" -ForegroundColor Yellow
        exit 1
    }
}

Section "Checking prerequisites"
Need "python" "Install Python 3.11+ from https://www.python.org/downloads/"
Need "docker" "Install Docker Desktop from https://www.docker.com/products/docker-desktop/"
Need "node"   "Install Node.js 20+ from https://nodejs.org/"
Need "npm"    "Comes with Node.js"

Section "Python venv (.venv)"
if (-not (Test-Path ".venv")) {
    python -m venv .venv
    Write-Host "[install] created .venv"
} else {
    Write-Host "[install] .venv already exists"
}

$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

& $venvPython -m pip install --upgrade pip wheel
& $venvPython -m pip install -r requirements.txt

Section "Actian VectorAI DB python client"
$wheel = Get-ChildItem "vectorai-db-beta\actian_vectorai-*.whl" | Select-Object -First 1
if ($wheel) {
    & $venvPython -m pip install --upgrade $wheel.FullName
} else {
    Write-Host "[install] no actian_vectorai wheel found in vectorai-db-beta/, skipping" -ForegroundColor Yellow
}

Section "Embedding model (all-MiniLM-L6-v2)"
& $venvPython "scripts\download_model.py"

Section "Pulling Actian VectorAI DB Docker image"
docker pull williamimoh/actian-vectorai-db:latest

Section "Frontend (routewise/)"
Push-Location "routewise"
try {
    npm install
} finally {
    Pop-Location
}

Section "Done"
Write-Host "Run .\start.ps1 to bring everything up." -ForegroundColor Green
