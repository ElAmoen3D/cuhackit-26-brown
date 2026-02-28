@echo off
REM CUHackit 2026 - Windows Launch Script
REM This script starts all required services

setlocal enabledelayedexpansion
title CUHackit 2026 - System Launcher

echo.
echo ========================================
echo    CUHackit 2026 - System Launcher
echo ========================================
echo.

REM Get script directory
set SCRIPT_DIR=%~dp0

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python not found. Please install Python 3.8 or higher.
    pause
    exit /b 1
)

REM Check if Node is installed
node --version >nul 2>&1
if errorlevel 1 (
    echo Error: Node.js not found. Please install Node.js 14 or higher.
    pause
    exit /b 1
)

REM Kill any leftover processes
echo [0/3] Cleaning up old processes...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq *multiple_tracking*" >nul 2>&1
taskkill /F /IM node.exe >nul 2>&1
for /f "tokens=5" %%p in ('netstat -ano 2^>nul ^| findstr ":8080 " ^| findstr LISTENING') do taskkill /F /PID %%p >nul 2>&1
for /f "tokens=5" %%p in ('netstat -ano 2^>nul ^| findstr ":5001 " ^| findstr LISTENING') do taskkill /F /PID %%p >nul 2>&1
for /f "tokens=5" %%p in ('netstat -ano 2^>nul ^| findstr ":5173 " ^| findstr LISTENING') do taskkill /F /PID %%p >nul 2>&1
timeout /t 1 /nobreak >nul

REM Check .env file
if not exist "%SCRIPT_DIR%.env" (
    echo [Setup] Creating .env file from template...
    if exist "%SCRIPT_DIR%.env.example" (
        copy "%SCRIPT_DIR%.env.example" "%SCRIPT_DIR%.env" >nul
        echo.
        echo Warning: Please edit .env and add your COPILOT_API_KEY
        echo          Get it from: https://console.anthropic.com/
        echo.
        pause
        exit /b 1
    )
)

REM Install Python dependencies if needed
echo [Setup] Checking Python dependencies...
python -c "import deepface, cv2, httpx" >nul 2>&1
if errorlevel 1 (
    echo [Setup] Installing Python packages...
    python -m pip install -q deepface opencv-python httpx numpy flask flask-cors
)

REM Install Node dependencies
if not exist "%SCRIPT_DIR%camera_backend\node_modules" (
    echo [Setup] Installing Node packages...
    cd /d "%SCRIPT_DIR%camera_backend"
    call npm install -q
)

if not exist "%SCRIPT_DIR%hackathon-frontend\node_modules" (
    echo [Setup] Installing Frontend packages...
    cd /d "%SCRIPT_DIR%hackathon-frontend"
    call npm install -q
)

echo.
echo [Setup] ✓ All dependencies ready
echo.

REM Start Python backend
echo [1/3] Starting Python Backend (port 5001)...
set PYTHONIOENCODING=utf-8
start "Python Backend" /MIN python "%SCRIPT_DIR%video_processing\multiple_tracking.py"
echo      Waiting for TensorFlow to initialize (15s)...
timeout /t 15 /nobreak >nul

REM Start Node server
echo.
echo [2/3] Starting Express Server (port 8080)...
start "Express Server" /MIN cmd /k "cd /d "%SCRIPT_DIR%camera_backend" && node server.js"
timeout /t 3 /nobreak >nul

REM Start Vue dev server
echo.
echo [3/3] Starting Vue Frontend (port 5173)...
start "Vue Frontend" cmd /k "cd /d "%SCRIPT_DIR%hackathon-frontend" && npm run dev"
timeout /t 3 /nobreak >nul

echo.
echo ========================================
echo    ✓ All services started!
echo ========================================
echo.
echo Services Running:
echo  • Python Backend: http://localhost:5001
echo  • Express Server: http://localhost:8080
echo  • Vue Frontend:   http://localhost:5173 [OPEN THIS]
echo.
echo To stop all services, close all open windows.
echo.
pause
