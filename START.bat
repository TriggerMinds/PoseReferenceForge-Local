@echo off
cd /d "%~dp0"
set LOGFILE=logs\startup_error.log
if not exist logs mkdir logs
set PY=.venv\Scripts\python.exe
if not exist "%PY%" goto missing
echo Starting PoseReferenceForge Local...
echo [%date% %time%] Starting... >> "%LOGFILE%"
"%PY%" -m app.main 2>> "%LOGFILE%"
set EC=%errorlevel%
if not %EC%==0 goto fail
exit /b 0
:missing
echo ERROR: Virtual environment not found.
echo Expected: %CD%\.venv\Scripts\python.exe
echo Run scripts\setup_windows.ps1
echo [%date% %time%] FAILED: .venv not found >> "%LOGFILE%"
pause
exit /b 1
:fail
echo Application failed with code %EC%.
echo See "%CD%\%LOGFILE%"
pause
exit /b %EC%
