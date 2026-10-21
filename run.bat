@echo off
setlocal
cd /d "%~dp0"

echo ==========================================================
echo   Starting GenDA - Generative Data Analyst (v2.0 Local)
echo ==========================================================

:: Free port 8000 if occupied by a previous backend process
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000 " ^| findstr "LISTENING" 2^>nul') do (
    echo Freeing port 8000 (PID %%a)...
    taskkill /F /PID %%a >nul 2>&1
)

if not exist "backend\.venv\Scripts\python.exe" (
    echo [ERROR] Python virtual environment not found at backend\.venv\Scripts\python.exe
    echo Please set up the backend virtual environment first:
    echo   cd backend ^&^& python -m venv .venv ^&^& .venv\Scripts\pip install -e .
    pause
    exit /b 1
)

echo [1/2] Launching Python Backend Service on 127.0.0.1:8000...
start "GenDA Backend" backend\.venv\Scripts\python.exe -m genda --port 8000 --token dev-token-local-genda-123

echo Waiting for backend service to initialize...
timeout /t 2 /nobreak >nul

echo [2/2] Launching Frontend on 127.0.0.1:5173...
echo.
echo Browser UI:       http://127.0.0.1:5173/
echo Backend Swagger:  http://127.0.0.1:8000/docs
echo Security Token:   dev-token-local-genda-123
echo.

call npm run dev
