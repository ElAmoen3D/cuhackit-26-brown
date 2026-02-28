#!/bin/bash

# CUHackit 2026 - Unified Launch Script for macOS & Linux
# This script starts all required services

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   CUHackit 2026 - System Launcher${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down services...${NC}"
    kill %1 2>/dev/null || true
    kill %2 2>/dev/null || true
    kill %3 2>/dev/null || true
    wait 2>/dev/null || true
    echo -e "${GREEN}All services stopped.${NC}"
}

trap cleanup EXIT INT TERM

# Check if Python is installed
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo -e "${RED}Error: Python3 not found. Please install Python 3.8 or higher.${NC}"
    exit 1
fi

# Determine Python command
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
else
    PYTHON_CMD="python"
fi

# Check if Node is installed
if ! command -v node &> /dev/null; then
    echo -e "${RED}Error: Node.js not found. Please install Node.js 14 or higher.${NC}"
    exit 1
fi

# Check if conda is available and activate environment if it exists
if command -v conda &> /dev/null; then
    # Try to activate cuhackit environment if it exists
    if conda env list | grep -q cuhackit; then
        echo -e "${YELLOW}[Setup] Activating conda environment: cuhackit${NC}"
        source "$(conda info --base)/etc/profile.d/conda.sh"
        conda activate cuhackit
    elif conda env list | grep -q base; then
        echo -e "${YELLOW}[Setup] Using base conda environment${NC}"
        source "$(conda info --base)/etc/profile.d/conda.sh"
        conda activate base
    fi
fi

# Kill any leftover processes
echo -e "${YELLOW}[0/3] Cleaning up old processes...${NC}"
pkill -f "python.*multiple_tracking" 2>/dev/null || true
pkill -f "node.*server.js" 2>/dev/null || true
lsof -ti:5001,8080,5173 | xargs kill -9 2>/dev/null || true
sleep 1

# Check .env file
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    echo -e "${YELLOW}[Setup] Creating .env file from template...${NC}"
    if [ -f "$SCRIPT_DIR/.env.example" ]; then
        cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
        echo -e "${YELLOW}        Please edit .env and add your COPILOT_API_KEY${NC}"
        echo -e "${YELLOW}        Then run this script again.${NC}"
        exit 1
    fi
fi

# Install Python dependencies if needed
echo -e "${YELLOW}[Setup] Checking Python dependencies...${NC}"
$PYTHON_CMD -c "import deepface, cv2, httpx" 2>/dev/null || {
    echo -e "${YELLOW}[Setup] Installing Python packages...${NC}"
    $PYTHON_CMD -m pip install -q deepface opencv-python httpx numpy flask flask-cors
}

# Install Node dependencies
echo -e "${YELLOW}[Setup] Checking Node dependencies...${NC}"
if [ ! -d "$SCRIPT_DIR/camera_backend/node_modules" ]; then
    echo -e "${YELLOW}[Setup] Installing Node packages...${NC}"
    cd "$SCRIPT_DIR/camera_backend"
    npm install -q
fi

if [ ! -d "$SCRIPT_DIR/hackathon-frontend/node_modules" ]; then
    echo -e "${YELLOW}[Setup] Installing Frontend packages...${NC}"
    cd "$SCRIPT_DIR/hackathon-frontend"
    npm install -q
fi

echo ""
echo -e "${GREEN}✓ All dependencies ready${NC}"
echo ""

# Start Python backend
echo -e "${BLUE}[1/3] Starting Python Backend (port 5001)...${NC}"
export PYTHONIOENCODING=utf-8
cd "$SCRIPT_DIR/video_processing"
$PYTHON_CMD multiple_tracking.py &
PYTHON_PID=$!
echo -e "${GREEN}     PID: $PYTHON_PID${NC}"
echo -e "${YELLOW}     Waiting for TensorFlow to initialize (15s)...${NC}"
sleep 15

# Check if Python is still running
if ! kill -0 $PYTHON_PID 2>/dev/null; then
    echo -e "${RED}Error: Python backend failed to start${NC}"
    exit 1
fi

# Start Node server
echo ""
echo -e "${BLUE}[2/3] Starting Express Server (port 8080)...${NC}"
cd "$SCRIPT_DIR/camera_backend"
node server.js &
NODE_PID=$!
echo -e "${GREEN}     PID: $NODE_PID${NC}"
sleep 2

# Check if Node is still running
if ! kill -0 $NODE_PID 2>/dev/null; then
    echo -e "${RED}Error: Express server failed to start${NC}"
    kill $PYTHON_PID 2>/dev/null || true
    exit 1
fi

# Start Vue dev server
echo ""
echo -e "${BLUE}[3/3] Starting Vue Frontend (port 5173)...${NC}"
cd "$SCRIPT_DIR/hackathon-frontend"
npm run dev &
VUE_PID=$!
echo -e "${GREEN}     PID: $VUE_PID${NC}"
sleep 3

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   ✓ All services started successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}Services Running:${NC}"
echo -e "  • Python Backend: ${GREEN}http://localhost:5001${NC}"
echo -e "  • Express Server: ${GREEN}http://localhost:8080${NC}"
echo -e "  • Vue Frontend:   ${GREEN}http://localhost:5173${NC} ← Open this"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"
echo ""

# Wait for all processes
wait $PYTHON_PID $NODE_PID $VUE_PID 2>/dev/null || true
