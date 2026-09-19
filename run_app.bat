@echo off
title TraceAI Enterprise Gateway & AI Web Platform
echo ======================================================================
echo           Starting TraceAI Multimodal Ingestion Gateway
echo ======================================================================

cd /d "%~dp0"

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in system PATH.
    echo Please install Python 3.10+ from python.org
    pause
    exit /b 1
)

if not exist ".venv" (
    echo [1/3] Creating Python virtual environment in .venv...
    python -m venv .venv
)

echo [2/3] Activating virtual environment...
call .venv\Scripts\activate.bat

echo [3/3] Checking requirements...
python -c "import fastapi, uvicorn" >nul 2>nul
if %errorlevel% neq 0 (
    echo Installing dependencies from requirements.txt...
    pip install -r requirements.txt
)

echo ----------------------------------------------------------------------
echo TraceAI Copilot is launching!
echo UI URL: http://127.0.0.1:8000
echo API Docs: http://127.0.0.1:8000/docs
echo ----------------------------------------------------------------------

start http://127.0.0.1:8000
python app.py

pause
