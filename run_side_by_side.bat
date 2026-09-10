@echo off
echo ===================================================
echo  Starting Marine Debris Detection System
echo  Backend:  http://127.0.0.1:8000
echo  Frontend: http://127.0.0.1:5173
echo ===================================================

cd /d "%~dp0"

echo [1/2] Starting FastAPI Backend (Port 8000)...
start "Marine Debris - Backend (FastAPI)" cmd /k "python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000"

timeout /t 2 /nobreak >nul

echo [2/2] Starting Vite Frontend (Port 5173)...
start "Marine Debris - Frontend (Vite)" cmd /k "cd frontend && npx vite --host 127.0.0.1 --port 5173"

timeout /t 2 /nobreak >nul

echo Opening browser at http://127.0.0.1:5173/ ...
start http://127.0.0.1:5173/

echo Services started side by side in dedicated terminal windows.
