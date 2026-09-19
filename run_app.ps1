# TraceAI Enterprise Platform Launcher for PowerShell
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "          Starting TraceAI Multimodal Ingestion Gateway               " -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $scriptDir

if (-not (Test-Path ".venv")) {
    Write-Host "[1/3] Initializing virtual environment in .venv..." -ForegroundColor Yellow
    python -m venv .venv
}

Write-Host "[2/3] Activating virtual environment..." -ForegroundColor Yellow
$activateScript = Join-Path $scriptDir ".venv\Scripts\Activate.ps1"
if (Test-Path $activateScript) {
    & $activateScript
}

Write-Host "[3/3] Checking dependencies..." -ForegroundColor Yellow
python -c "import fastapi, uvicorn" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing dependencies from requirements.txt..." -ForegroundColor Yellow
    pip install -r requirements.txt
}

Write-Host "----------------------------------------------------------------------" -ForegroundColor Green
Write-Host "TraceAI Copilot is launching!" -ForegroundColor Green
Write-Host "Web UI:   http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "API Docs: http://127.0.0.1:8000/docs" -ForegroundColor Green
Write-Host "----------------------------------------------------------------------" -ForegroundColor Green

Start-Process "http://127.0.0.1:8000"
python app.py
