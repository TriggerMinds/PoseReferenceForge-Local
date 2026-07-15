@echo off
cd /d "%~dp0"
echo Starting PoseReferenceForge Local...
".venv\Scripts\python.exe" -m app.main
if %errorlevel% neq 0 (
    echo.
    echo Application exited with error code %errorlevel%.
    echo Check logs for details.
    pause
)
