# Quick Start - Pick Your OS

## **🪟 Windows Users**

### **Easiest Way:** Double-click `run.bat`
- Everything auto-starts
- Opens all required windows
- Just wait and open browser to http://localhost:5173

### **Or use PowerShell:**
```powershell
.\run.ps1
```

---

## **🍎 macOS Users**

### **Easiest Way:** Run in terminal
```bash
./run.sh
```
- Auto-detects conda environment
- Installs dependencies automatically
- Shows all service URLs
- Press Ctrl+C to stop

---

## **🐧 Linux Users**

### **Easiest Way:** Run in terminal
```bash
./run.sh
```
- Works with conda, venv, or system Python
- Auto-installs missing packages
- Shows all service URLs
- Press Ctrl+C to stop

---

## **Setup (All Platforms - One Time)**

```bash
# 1. Copy .env template
cp .env.example .env

# 2. Edit .env and add your Copilot API key
nano .env

# 3. Save and run the appropriate script
```

---

## **That's it!** 🎉

All three services start automatically:
- Python Backend (port 5001)
- Express Server (port 8080)
- Vue Frontend (port 5173) ← **Open this in your browser**

### **Services will be running at:**
```
🎥 http://localhost:5173  ← CLICK HERE
```

---

## **Troubleshooting**

| OS | If script won't run | Solution |
|----|-------------------|----------|
| macOS/Linux | Permission denied | `chmod +x run.sh` |
| Windows | Can't find python | Install from python.org |
| All | Port already in use | Close other applications using those ports |
| All | Slow first start | Wait 20s for TensorFlow to load |

---

**Need full setup guide?** See `LAUNCH_GUIDE.md`
