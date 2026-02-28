# start.ps1 — SecureView full-stack launcher
# Run from the repo root: .\start.ps1

$ROOT     = $PSScriptRoot
$FRONTEND = Join-Path $ROOT "hackathon-frontend"
$BACKEND  = Join-Path $ROOT "video_processing\camera_backend"
$PYTHON   = Join-Path $ROOT "video_processing\multiple_tracking.py"
$CONDA_ENV = "cuhackit-2026"

Write-Host "`n=== SecureView Startup ===" -ForegroundColor Cyan

# ── 1. Build Vue frontend → video_processing/camera_backend/dist ──────────────
Write-Host "`n[1/4] Building frontend..." -ForegroundColor Yellow
Push-Location $FRONTEND
npm install --silent
npm run build
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Frontend build failed. Fix errors above and re-run." -ForegroundColor Red
    Pop-Location
    exit 1
}
Pop-Location
Write-Host "      Frontend built OK." -ForegroundColor Green

# ── 2. Install Node dependencies ──────────────────────────────────────────────
Write-Host "`n[2/4] Installing Node dependencies..." -ForegroundColor Yellow
Push-Location $BACKEND
npm install --silent
Pop-Location

# ── 3. Start Python face-recognition server (port 5001) ──────────────────────
Write-Host "`n[3/4] Starting Python backend (conda env: $CONDA_ENV)..." -ForegroundColor Yellow
$pythonExe = "C:\Users\rohit\miniconda3\envs\$CONDA_ENV\python.exe"
if (-not (Test-Path $pythonExe)) {
    Write-Host "ERROR: Python not found at $pythonExe" -ForegroundColor Red
    exit 1
}
$env:PYTHONIOENCODING = "utf-8"
$pyProc = Start-Process -FilePath $pythonExe -ArgumentList "`"$PYTHON`"" `
    -WorkingDirectory (Split-Path $PYTHON) `
    -PassThru -NoNewWindow `
    -Environment @{ PYTHONIOENCODING = "utf-8" }
Write-Host "      Python PID: $($pyProc.Id) — waiting for it to initialize..."
Start-Sleep -Seconds 12

# ── 4. Start Node proxy server (port 8080) ────────────────────────────────────
Write-Host "`n[4/4] Starting Node server (port 8080)..." -ForegroundColor Yellow
$nodeProc = Start-Process -FilePath "node" -ArgumentList "server.js" `
    -WorkingDirectory $BACKEND `
    -PassThru -NoNewWindow
Start-Sleep -Seconds 2

# ── 5. Start localhost.run SSH tunnel → public URL (no password page) ──────────
Write-Host "`n[TUNNEL] Starting localhost.run tunnel (no password page)..." -ForegroundColor Cyan
Write-Host "`n========================================" -ForegroundColor Green
Write-Host "  Your public URL will appear below." -ForegroundColor Green
Write-Host "  Look for: https://xxxx.lhrtunnel.link" -ForegroundColor Green
Write-Host "  If prompted 'Are you sure...', type: yes" -ForegroundColor Yellow
Write-Host "  Ctrl+C stops the tunnel (servers keep running)." -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Green

# Run tunnel in foreground — Ctrl+C only kills the tunnel, NOT the servers
ssh -R 80:localhost:8080 localhost.run
Write-Host "`nTunnel closed. Python and Node are still running." -ForegroundColor Yellow
Write-Host "Re-run: ssh -R 80:localhost:8080 localhost.run" -ForegroundColor Cyan
