/**
 * server.js — SecureView Express proxy server
 *
 * Responsibilities:
 * 1. Proxy JSON data + health endpoints → Python face-recognition server (:5001)
 * 2. Proxy the MJPEG live video stream   → Python server (:5001/video_feed)
 * 3. Serve the built Vue frontend (dist/) in production
 *
 * Startup order:
 * 1. python multiple_tracking.py   (starts on :5001)
 * 2. node server.js                (starts on :8080)
 * 3. npm run dev  OR  open http://localhost:8080 for the built app
 */

const express = require('express')
const http    = require('http')
const path    = require('path')
const app     = express()

const PYTHON_HOST = '127.0.0.1'
const PYTHON_PORT = 5001
const SERVER_PORT = 8080

// ── CORS headers (allow Vite dev server on :5173) ─────────────────────────────
app.use((req, res, next) => {
  res.setHeader('Access-Control-Allow-Origin', '*')
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS')
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type')
  if (req.method === 'OPTIONS') return res.sendStatus(204)
  next()
})

// ── Serve built Vue app (production) ─────────────────────────────────────────
const DIST_DIR = path.join(__dirname, 'dist')
app.use(express.static(DIST_DIR))

// ── Internal helper: proxy a JSON request to Python ──────────────────────────
function proxyJSON(pythonPath, res, offlineFallback) {
  const req = http.get(
    `http://${PYTHON_HOST}:${PYTHON_PORT}${pythonPath}`,
    (pRes) => {
      let raw = ''
      pRes.on('data', (chunk) => (raw += chunk))
      pRes.on('end', () => {
        res.setHeader('Cache-Control', 'no-cache, no-store, must-revalidate')
        res.setHeader('Content-Type', 'application/json')
        res.send(raw)
      })
    }
  )

  req.on('error', () => {
    res.status(503).json(offlineFallback)
  })

  req.setTimeout(2000, () => {
    req.destroy()
    res.status(503).json(offlineFallback)
  })
}

// ── GET /data  — face recognition results (JSON) ─────────────────────────────
app.get('/data', (req, res) => {
  proxyJSON('/data', res, {
    known:    [],
    unknown:  [],
    counts:   { known: 0, unknown: 0, total: 0 },
    alerts:   [],
    timestamp: Date.now() / 1000,
    _offline: true,
  })
})

// ── GET /health  — system health check ───────────────────────────────────────
app.get('/health', (req, res) => {
  proxyJSON('/health', res, {
    status:     'offline',
    identities: 0,
    _offline:   true,
  })
})

// ── GET /live  — MJPEG video stream ──────────────────────────────────────────
app.get('/live', (req, res) => {
  const pythonReq = http.get(
    `http://${PYTHON_HOST}:${PYTHON_PORT}/video_feed`,
    (pRes) => {
      res.writeHead(pRes.statusCode, {
        ...pRes.headers,
        'Access-Control-Allow-Origin': '*',
      })
      pRes.pipe(res)
    }
  )

  pythonReq.on('error', () => {
    res.status(503).send(
      'Stream offline — make sure multiple_tracking.py is running on port 5001'
    )
  })

  req.on('close', () => pythonReq.destroy())
})

// ── SPA fallback — serve index.html for all other routes ─────────────────────
// (Vue Router handles client-side navigation)
app.get(/.*/, (req, res) => {
  const indexPath = path.join(DIST_DIR, 'index.html')
  res.sendFile(indexPath, (err) => {
    if (err) {
      res.status(404).send(
        `SecureView: Vue build not found.\n\n` +
        `Run "npm run build" to generate the dist/ folder, ` +
        `or use "npm run dev" to start the Vite dev server (port 5173).\n\n` +
        `API endpoints are still available:\n` +
        `  GET http://localhost:${SERVER_PORT}/data\n` +
        `  GET http://localhost:${SERVER_PORT}/live\n` +
        `  GET http://localhost:${SERVER_PORT}/health`
      )
    }
  })
})

// ── Start ─────────────────────────────────────────────────────────────────────
app.listen(SERVER_PORT, () => {
  console.log('')
  console.log('╔══════════════════════════════════════════════════════════╗')
  console.log('║          SecureView — Surveillance Dashboard             ║')
  console.log('╠══════════════════════════════════════════════════════════╣')
  console.log(`║  Express server  → http://localhost:${SERVER_PORT}              ║`)
  console.log(`║  Python backend  → http://localhost:${PYTHON_PORT} (required)   ║`)
  console.log('╠══════════════════════════════════════════════════════════╣')
  console.log('║  GET /          Vue app (from dist/ after npm run build) ║')
  console.log('║  GET /live      Annotated MJPEG stream                   ║')
  console.log('║  GET /data      JSON face + coordinate payload           ║')
  console.log('║  GET /health    System health check                      ║')
  console.log('╠══════════════════════════════════════════════════════════╣')
  console.log('║  Dev mode:  npm run dev  (Vite on :5173, proxies to here)║')
  console.log('╚══════════════════════════════════════════════════════════╝')
  console.log('')
  console.log('  ⚠  Start multiple_tracking.py first!')
  console.log('')
})