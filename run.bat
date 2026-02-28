@echo off
title SecureView Launcher

echo.
echo === SecureView Startup ===
echo.

:: Kill any leftover processes from a previous run
echo [0/3] Cleaning up old processes...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq *multiple_tracking*" >nul 2>&1
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8080 " ^| findstr LISTENING') do taskkill /F /PID %%p >nul 2>&1
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":5001 " ^| findstr LISTENING') do taskkill /F /PID %%p >nul 2>&1
timeout /t 1 /nobreak >nul

:: Start Python backend
echo [1/3] Starting Python face recognition (port 5001)...
set PYTHONIOENCODING=utf-8
start "Python Backend" /MIN "C:\Users\rohit\miniconda3\envs\cuhackit-2026\python.exe" "%~dp0video_processing\multiple_tracking.py"

:: Wait for Python + TensorFlow to fully load
echo      Waiting for TensorFlow to initialize (12s)...
timeout /t 12 /nobreak >nul

:: Start Node proxy server
echo [2/3] Starting Node server (port 8080)...
start "Node Server" /MIN cmd /c "cd /d %~dp0video_processing\camera_backend && node server.js"
timeout /t 2 /nobreak >nul

:: Start localtunnel and show URL
echo [3/3] Starting tunnel...
echo.
echo ========================================
echo   Your public URL will appear below.
echo   Look for: https://xxxx.loca.lt
echo   Password: visit https://api.ipify.org
echo             and enter that IP on the page
echo   Ctrl+C to stop the tunnel.
echo   (Python + Node keep running after)
echo ========================================
echo.
npx localtunnel --port 8080

echo.
echo Tunnel closed. Python and Node are still running in the background.
echo To stop them, close their minimized windows or restart this script.
pause
