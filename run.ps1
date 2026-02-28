# CUHackit 2026 - Windows PowerShell Launch Script
# This script starts all required services

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ScriptDir = $ScriptDir.TrimEnd('\')

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "   CUHackit 2026 - System Launcher" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Check if Python is installed
try {
    $pythonVersion = python --version 2>&1
    Write-Host "[Setup] Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "Error: Python not found. Please install Python 3.8 or higher." -ForegroundColor Red
    Write-Host "Download from: https://www.python.org/downloads/" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Check if Node is installed
try {
    $nodeVersion = node --version 2>&1
    Write-Host "[Setup] Node.js found: $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "Error: Node.js not found. Please install Node.js 14 or higher." -ForegroundColor Red
    Write-Host "Download from: https://nodejs.org/" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Kill any leftover processes
Write-Host "`n[0/3] Cleaning up old processes..." -ForegroundColor Yellow
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Get-Process node -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1

# Check .env file
if (-not (Test-Path "$ScriptDir\.env")) {
    Write-Host "[Setup] Creating .env file from template..." -ForegroundColor Yellow
    if (Test-Path "$ScriptDir\.env.example") {
        Copy-Item "$ScriptDir\.env.example" "$ScriptDir\.env"
        Write-Host "`nWarning: Please edit .env and add your COPILOT_API_KEY" -ForegroundColor Yellow
        Write-Host "         Get it from: https://console.anthropic.com/`n" -ForegroundColor Yellow
        Read-Host "Press Enter after editing .env"
        exit 1
    }
}

# Install Python dependencies
Write-Host "[Setup] Checking Python dependencies..." -ForegroundColor Yellow
$pythonTest = python -c "import deepface, cv2, httpx" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[Setup] Installing Python packages..." -ForegroundColor Yellow
    python -m pip install -q deepface opencv-python httpx numpy flask flask-cors
}

# Install Node dependencies
if (-not (Test-Path "$ScriptDir\camera_backend\node_modules")) {
    Write-Host "[Setup] Installing Node packages..." -ForegroundColor Yellow
    Set-Location "$ScriptDir\camera_backend"
    npm install -q
}

if (-not (Test-Path "$ScriptDir\hackathon-frontend\node_modules")) {
    Write-Host "[Setup] Installing Frontend packages..." -ForegroundColor Yellow
    Set-Location "$ScriptDir\hackathon-frontend"
    npm install -q
}

Write-Host "`n[Setup] ✓ All dependencies ready`n" -ForegroundColor Green

# Start Python backend
Write-Host "[1/3] Starting Python Backend (port 5001)..." -ForegroundColor Cyan
$env:PYTHONIOENCODING = "utf-8"
Start-Process python -ArgumentList "$ScriptDir\video_processing\multiple_tracking.py" -WindowStyle Minimized -PassThru
Write-Host "      Waiting for TensorFlow to initialize (15s)..." -ForegroundColor Yellow
Start-Sleep -Seconds 15

# Start Node server
Write-Host "`n[2/3] Starting Express Server (port 8080)..." -ForegroundColor Cyan
Start-Process cmd -ArgumentList "/k", "cd /d $ScriptDir\camera_backend && node server.js" -WindowStyle Minimized
Start-Sleep -Seconds 3

# Start Vue dev server
Write-Host "`n[3/3] Starting Vue Frontend (port 5173)..." -ForegroundColor Cyan
Start-Process cmd -ArgumentList "/k", "cd /d $ScriptDir\hackathon-frontend && npm run dev" -WindowStyle Normal

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "   ✓ All services started!" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Green

Write-Host "Services Running:" -ForegroundColor Cyan
Write-Host "  • Python Backend: http://localhost:5001" -ForegroundColor White
Write-Host "  • Express Server: http://localhost:8080" -ForegroundColor White
Write-Host "  • Vue Frontend:   http://localhost:5173" -ForegroundColor Green
Write-Host "                    ↑ OPEN THIS IN YOUR BROWSER`n" -ForegroundColor Green

Write-Host "To stop all services, close all open windows." -ForegroundColor Yellow
