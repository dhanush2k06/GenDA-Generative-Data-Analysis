@echo off
echo ==========================================================
echo   Starting GenDA - Generative Data Analyst (v2.0 Local)
echo ==========================================================

echo [1/2] Launching Python Backend Service on 127.0.0.1:8000...
start "GenDA Backend" backend\.venv\Scripts\python.exe -m genda --port 8000 --token dev-token-local-genda-123

echo [2/2] Launching Frontend on 127.0.0.1:5173...
echo.
echo Browser UI:       http://127.0.0.1:5173/
echo Backend Swagger:  http://127.0.0.1:8000/docs
echo Security Token:   dev-token-local-genda-123
echo.

npm run dev
