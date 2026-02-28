# Tiger-Security — Local Setup Guide

A real-time face recognition and activity monitoring system with a Vue.js dashboard.

## Architecture

| Service | Runtime | Port | Description |
|---|---|---|---|
| Python face engine | Python 3.10+ | 5001 | OpenCV + DeepFace detection/tracking |
| Express proxy server | Node.js 20+ | 8080 | REST API, Gemini AI, face DB CRUD |
| Vue frontend | Vite (dev) | 5173 | Dashboard UI |

---

## Prerequisites

- **Node.js** v20.19+ or v22.12+
- **Python** 3.10+
- A webcam connected to your machine

---

## 1. Clone & Environment Setup

```bash
git clone <repo-url>
cd cuhack-26
```

Copy the example env file and fill in your credentials:

```bash
cp .env.example .env   # or just edit .env directly
```

Required `.env` values:

```env
GEMINI_API_KEY=<your Google AI Studio key>
GEMINI_MODEL=gemini-2.0-flash
PYTHON_PORT=5001
EXPRESS_PORT=8080
CAMERA_INDEX=0
```

> Get a free Gemini API key at https://aistudio.google.com/app/apikey

---

## 2. Install Python Dependencies

From the `video_processing/` directory:

```bash
cd video_processing
pip install opencv-python deepface numpy
```

---

## 3. Start the Python Face Engine

```bash
# from video_processing/
python multiple_tracking.py
```

Leave this terminal running. It will:
- Open your webcam (`CAMERA_INDEX=0` by default)
- Start an HTTP server on **port 5001** (`/video_feed`, `/data`, `/health`)

---

## 4. Start the Express Backend + Vue Frontend

Open a **second terminal** from the `hackathon-frontend/` directory:

```bash
cd hackathon-frontend
npm install
npm run dev
```

This single command (via `concurrently`) will:
- Install and start the Express backend (`video_processing/camera_backend/server.js`) on **port 8080**
- Start the Vite dev server on **port 5173**

---

## 5. Open the App

Navigate to:

```
http://localhost:5173
```

The Express server (port 8080) proxies all `/data`, `/video_feed`, `/face_db`, and `/gemini` requests to the Python engine.

---

## Face Database

Place face images in `video_processing/face_db/` before starting the Python engine.
Name each file after the person it contains — e.g. `alice.jpg`, `bob.png`.
The dashboard also supports uploading faces at runtime via the UI.

---

## Startup Order Summary

```
Terminal 1 │ cd video_processing && python multiple_tracking.py
Terminal 2 │ cd hackathon-frontend && npm install && npm run dev
Browser    │ http://localhost:5173
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `No module named 'deepface'` | `pip install deepface` |
| Webcam not found | Change `CAMERA_INDEX` in `.env` (try `1` or `2`) |
| Port 5001 already in use | Kill the existing process or change `PYTHON_PORT` in `.env` |
| Port 8080 already in use | Change `EXPRESS_PORT` in `.env` and update `video_processing/camera_backend/server.js` accordingly |
| Gemini analysis not working | Check `GEMINI_API_KEY` is set correctly in `.env` |
