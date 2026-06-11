@echo off
cd /d "%~dp0ai-engine"

if exist "%~dp0.venv\Scripts\activate.bat" (
    call "%~dp0.venv\Scripts\activate.bat"
) else if exist "%~dp0ai-engine\.venv\Scripts\activate.bat" (
    call "%~dp0ai-engine\.venv\Scripts\activate.bat"
)

echo.
echo [AI Engine] Starting FastAPI server at http://127.0.0.1:8000
echo [AI Engine] Press Ctrl+C to stop
echo.

python src/server.py

pause
