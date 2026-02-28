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

:: Start localtunnel and retry until we get the secureview-app subdomain
echo [3/3] Starting tunnel (will retry until secureview-app subdomain is available)...
echo.
echo ========================================
echo   Target URL: https://secureview-app.loca.lt
echo   Password: visit https://api.ipify.org
echo             and enter that IP on the page
echo   Ctrl+C to stop the tunnel.
echo   (Python + Node keep running after)
echo ========================================
echo.
:tunnel_retry
set TUNNEL_OUT=%TEMP%\lt_out_%RANDOM%.txt
start /B cmd /c "npx localtunnel --port 8080 --subdomain secureview-app > %TUNNEL_OUT% 2>&1"
timeout /t 7 /nobreak >nul
findstr /i "secureview-app" %TUNNEL_OUT% >nul 2>&1
if %errorlevel%==0 (
    echo Got secureview-app — tunnel is live!
    type %TUNNEL_OUT%
    echo.
    echo Tunnel is running. Press Ctrl+C to stop.
    :keep_alive
    timeout /t 30 /nobreak >nul
    goto keep_alive
) else (
    echo Wrong subdomain assigned — killing tunnel and retrying in 3s...
    powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'node.exe' -and $_.CommandLine -like '*localtunnel*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
    del /f /q %TUNNEL_OUT% >nul 2>&1
    timeout /t 3 /nobreak >nul
    goto tunnel_retry
)

echo.
echo Tunnel closed. Python and Node are still running in the background.
echo To stop them, close their minimized windows or restart this script.
pause
