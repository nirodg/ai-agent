@echo off
REM run.bat — Start the AI Sales Enrichment Agent (Windows)

cd /d "%~dp0"

REM Activate virtualenv if present and not already active
IF "%VIRTUAL_ENV%"=="" (
    IF EXIST ".venv\Scripts\activate.bat" (
        echo 🔧 Activating .venv...
        call .venv\Scripts\activate.bat
    ) ELSE (
        echo ⚠️  No .venv found. Run: python setup.py
        exit /b 1
    )
)

REM Check .env exists
IF NOT EXIST ".env" (
    echo ⚠️  .env not found. Run: python setup.py
    exit /b 1
)

echo 🚀 Starting AI Sales Enrichment Agent...
echo    URL: http://localhost:8501
echo    Press Ctrl+C to stop.
echo.

python -m streamlit run main.py ^
    --server.port 8501 ^
    --server.headless false ^
    --browser.gatherUsageStats false