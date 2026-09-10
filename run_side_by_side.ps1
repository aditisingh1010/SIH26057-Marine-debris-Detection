Write-Host "===================================================" -ForegroundColor Cyan
Write-Host " Starting Marine Debris Detection Workstation" -ForegroundColor Cyan
Write-Host " Backend:  http://127.0.0.1:8000" -ForegroundColor Green
Write-Host " Frontend: http://127.0.0.1:5173" -ForegroundColor Green
Write-Host "===================================================" -ForegroundColor Cyan

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $Root) { $Root = Get-Location }

# Start Backend
Start-Process -FilePath "powershell.exe" -ArgumentList "-NoExit", "-Command", "cd '$Root'; python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000" -WindowStyle Normal

Start-Sleep -Seconds 2

# Start Frontend
Start-Process -FilePath "powershell.exe" -ArgumentList "-NoExit", "-Command", "cd '$Root\frontend'; npx vite --host 127.0.0.1 --port 5173" -WindowStyle Normal

Start-Sleep -Seconds 2

# Open browser
Start-Process "http://127.0.0.1:5173/"

Write-Host "Both services launched side by side." -ForegroundColor Cyan
