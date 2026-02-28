# 🚀 CUHackit 2026 - System Launch Guide

This guide shows how to run the complete system on Windows, macOS, and Linux.

## **Prerequisites (All Platforms)**

Before running any launch script, ensure you have:

1. **Python 3.8+**
   - [Download Python](https://www.python.org/downloads/)
   - Verify: `python --version`

2. **Node.js 14+**
   - [Download Node.js](https://nodejs.org/)
   - Verify: `node --version`

3. **Git** (for cloning the repository)
   - [Download Git](https://git-scm.com/)

4. **Conda** (Optional but recommended)
   - [Download Miniconda](https://docs.conda.io/en/latest/miniconda.html)

## **Setup .env File (One-time)**

```bash
cd /path/to/cuhackit-26-brown

# Copy template
cp .env.example .env

# Edit .env with your editor
nano .env  # or use your preferred editor

# Add your Copilot API key:
# COPILOT_API_KEY=sk-ant-xxxxx
# Get one from: https://console.anthropic.com/
```

---

## **Windows**

### **Option 1: Batch Script (Recommended)**

Double-click `run.bat` from the project folder.

The script will:
- ✓ Auto-detect Python and Node.js
- ✓ Install missing dependencies
- ✓ Start all 3 services in separate windows
- ✓ Open browser automatically

**To stop:** Close all open command windows

### **Option 2: PowerShell Script**

```powershell
# Run as Administrator (Right-click PowerShell → Run as Administrator)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\run.ps1
```

### **Option 3: Manual (Command Prompt)**

**Terminal 1:**
```batch
cd video_processing
conda activate base
pip install deepface opencv-python httpx numpy flask flask-cors
python multiple_tracking.py
```

**Terminal 2:**
```batch
cd camera_backend
npm install
node server.js
```

**Terminal 3:**
```batch
cd hackathon-frontend
npm install
npm run dev
```

Then open: **http://localhost:5173**

---

## **macOS**

### **Option 1: Shell Script (Recommended)**

```bash
# Make script executable (one-time)
chmod +x ./run.sh

# Run the script
./run.sh
```

The script will:
- ✓ Auto-detect Python and Node.js
- ✓ Check conda environment
- ✓ Install missing dependencies
- ✓ Start all 3 services in background
- ✓ Show service URLs

**To stop:** Press `Ctrl+C`

### **Option 2: Manual (Terminal)**

**Terminal 1:**
```bash
cd video_processing
conda activate base
pip install deepface opencv-python httpx numpy flask flask-cors
python3 multiple_tracking.py
```

**Terminal 2:**
```bash
cd camera_backend
npm install
node server.js
```

**Terminal 3:**
```bash
cd hackathon-frontend
npm install
npm run dev
```

Then open: **http://localhost:5173**

---

## **Linux**

### **Option 1: Shell Script (Recommended)**

```bash
# Make script executable (one-time)
chmod +x ./run.sh

# Run the script
./run.sh
```

The script will:
- ✓ Auto-detect Python and Node.js
- ✓ Install missing system dependencies
- ✓ Start all 3 services
- ✓ Show service URLs

**To stop:** Press `Ctrl+C`

### **Option 2: Using conda**

```bash
# Create conda environment
conda create -n cuhackit python=3.9
conda activate cuhackit
pip install deepface opencv-python httpx numpy flask flask-cors node
```

Then run `./run.sh`

### **Option 3: Manual (Terminal)**

**Terminal 1:**
```bash
cd video_processing
python3 -m venv venv
source venv/bin/activate
pip install deepface opencv-python httpx numpy flask flask-cors
python3 multiple_tracking.py
```

**Terminal 2:**
```bash
cd camera_backend
npm install
node server.js
```

**Terminal 3:**
```bash
cd hackathon-frontend
npm install
npm run dev
```

Then open: **http://localhost:5173**

---

## **What Happens When You Run**

All scripts perform the same operations:

1. **Check Dependencies** - Verifies Python and Node.js are installed
2. **Cleanup** - Kills any old processes running on ports 5001, 8080, 5173
3. **Install Packages** - Installs Python and npm dependencies if missing
4. **Start Python Backend** - Face detection server on `http://localhost:5001`
5. **Start Express Server** - API proxy on `http://localhost:8080`
6. **Start Vue Frontend** - Web dashboard on `http://localhost:5173`

---

## **Expected Output**

You should see something like:

```
========================================
   CUHackit 2026 - System Launcher
========================================

[0/3] Cleaning up old processes...
[Setup] Checking dependencies...
[Setup] ✓ All dependencies ready

[1/3] Starting Python Backend (port 5001)...
      Waiting for TensorFlow to initialize (15s)...

[2/3] Starting Express Server (port 8080)...

[3/3] Starting Vue Frontend (port 5173)...

========================================
   ✓ All services started!
========================================

Services Running:
  • Python Backend: http://localhost:5001
  • Express Server: http://localhost:8080
  • Vue Frontend:   http://localhost:5173 ← OPEN THIS
```

---

## **Access the Dashboard**

Open your browser and navigate to:

```
http://localhost:5173
```

You should see:
- ✅ Live video feed from your camera
- ✅ Real-time face detection
- ✅ Face recognition results
- ✅ AI threat analysis
- ✅ System monitoring dashboard

---

## **Troubleshooting**

| Problem | Solution |
|---------|----------|
| **"Python not found"** | Install Python 3.8+ from python.org |
| **"Node not found"** | Install Node.js 14+ from nodejs.org |
| **"Port already in use"** | Kill processes: `lsof -ti:5001,8080,5173 \| xargs kill -9` |
| **"Module not found"** | Run pip install manually in each directory |
| **Blank dashboard** | Wait 20 seconds for TensorFlow to load |
| **Copilot unavailable** | Check COPILOT_API_KEY in .env file |
| **Camera not working** | Check camera permissions in System Preferences (macOS) |

---

## **Service Ports**

| Service | Port | Purpose |
|---------|------|---------|
| Python Backend | 5001 | Face detection, DeepFace API |
| Express Server | 8080 | REST API proxy |
| Vue Frontend | 5173 | Web dashboard |

---

## **Stopping Services**

### **macOS/Linux:**
- Press `Ctrl+C` in the terminal running `run.sh`

### **Windows (Batch):**
- Close all minimized command windows

### **Windows (PowerShell):**
- Close all command windows

### **Manual Stop:**
```bash
# macOS/Linux
pkill -f "python.*multiple_tracking"
pkill -f "node.*server.js"
pkill -f "npm run dev"

# Windows (PowerShell as Admin)
Stop-Process -Name python -Force
Stop-Process -Name node -Force
```

---

## **Performance Notes**

- **First startup:** 30-45 seconds (TensorFlow initialization)
- **Subsequent startups:** 10-15 seconds
- **CPU Usage:** ~30-40% (Python) + ~5% (Node) + ~10% (Vue)
- **Memory Usage:** ~2-3 GB (TensorFlow model loading)

---

## **Need Help?**

- Check the logs in each terminal window
- Ensure all services show "running" status
- Verify ports 5001, 8080, 5173 are available
- Make sure your .env file has COPILOT_API_KEY set

---

**Happy hacking! 🚀**
