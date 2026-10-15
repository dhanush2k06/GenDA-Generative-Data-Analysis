Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Starting GenDA — Generative Data Analyst (v2.0 Local)" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# --- Kill any stale process holding port 8000 ---
$stale = netstat -ano | Select-String ":8000 " | ForEach-Object {
    ($_ -split '\s+')[-1]
} | Select-Object -Unique
foreach ($pid in $stale) {
    if ($pid -match '^\d+$' -and $pid -ne '0') {
        Write-Host "  Freeing port 8000 (PID $pid)..." -ForegroundColor DarkYellow
        taskkill /PID $pid /F 2>$null | Out-Null
    }
}
Start-Sleep -Milliseconds 500

# 1. Start Python Backend
Write-Host "`n[1/2] Launching Backend Service on 127.0.0.1:8000..." -ForegroundColor Green
$backendProcess = Start-Process `
    -FilePath "backend\.venv\Scripts\python.exe" `
    -ArgumentList "-m genda --port 8000 --token dev-token-local-genda-123" `
    -PassThru -NoNewWindow -WorkingDirectory $PSScriptRoot
Start-Sleep -Seconds 2

# 2. Start Frontend Dev Server
Write-Host "[2/2] Launching Frontend (Vite) on 127.0.0.1:5173..." -ForegroundColor Green
Write-Host "`nOpen your browser at: http://127.0.0.1:5173/" -ForegroundColor Yellow
Write-Host "Backend API docs at:  http://127.0.0.1:8000/docs" -ForegroundColor Yellow
Write-Host "Security Token:       dev-token-local-genda-123`n" -ForegroundColor Yellow

try {
    npm run dev
} finally {
    Write-Host "`nStopping backend (PID $($backendProcess.Id))..." -ForegroundColor DarkYellow
    Stop-Process -Id $backendProcess.Id -Force -ErrorAction SilentlyContinue
}
