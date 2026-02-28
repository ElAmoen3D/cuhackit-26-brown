/**
 * server.js — SecureView Express proxy server
 *
 * Responsibilities:
 * 1. Proxy JSON data + health endpoints → Python face-recognition server (:5001)
 * 2. Proxy the MJPEG live video stream   → Python server (:5001/video_feed)
 * 3. Serve the built Vue frontend (dist/) in production
 * 4. Face Database CRUD  (GET/POST/DELETE /face_db)
 * 5. Copilot AI analysis (POST /copilot/analyze → Azure OpenAI)
 * 6. Snapshot endpoint   (GET /snapshot → single JPEG from MJPEG stream)
 *
 * Startup order:
 * 1. python multiple_tracking.py   (starts on :5001)
 * 2. node server.js                (starts on :8080)
 * 3. npm run dev  OR  open http://localhost:8080 for the built app
 *
 * Environment variables (copy .env.example → .env):
 *   AZURE_OPENAI_ENDPOINT    e.g. https://myresource.openai.azure.com
 *   AZURE_OPENAI_API_KEY     your Azure OpenAI / Copilot API key
 *   AZURE_OPENAI_DEPLOYMENT  model deployment name (default: gpt-4o)
 */

require('dotenv').config()

const express = require('express')
const http    = require('http')
const https   = require('https')
const path    = require('path')
const fs      = require('fs')
const multer  = require('multer')
const { URL } = require('url')
const app     = express()

const PYTHON_HOST = '127.0.0.1'
const PYTHON_PORT = 5001
const SERVER_PORT = 8080

// ── Face DB directory ─────────────────────────────────────────────────────────
const FACE_DB_DIR = path.join(__dirname, '..', 'face_db')
if (!fs.existsSync(FACE_DB_DIR)) fs.mkdirSync(FACE_DB_DIR, { recursive: true })

// ── Multer (face image uploads) ───────────────────────────────────────────────
const storage = multer.diskStorage({
  destination: FACE_DB_DIR,
  filename: (req, file, cb) => {
    const safe = path.basename(file.originalname).replace(/[^a-zA-Z0-9._\-\s]/g, '_')
    cb(null, safe)
  }
})
const upload = multer({
  storage,
  fileFilter: (req, file, cb) => {
    if (file.mimetype.startsWith('image/')) cb(null, true)
    else cb(new Error('Only image files are allowed'))
  },
  limits: { fileSize: 20 * 1024 * 1024 }
})

// ── CORS headers (allow Vite dev server on :5173) ─────────────────────────────
app.use((req, res, next) => {
  res.setHeader('Access-Control-Allow-Origin', '*')
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type')
  if (req.method === 'OPTIONS') return res.sendStatus(204)
  next()
})

// ── Serve built Vue app (production) ─────────────────────────────────────────
const DIST_DIR = path.join(__dirname, 'dist')
app.use(express.static(DIST_DIR))

// ── Body parser (JSON) for Copilot endpoint ───────────────────────────────────
app.use(express.json({ limit: '20mb' }))

// ── GET /face_db — list all enrolled faces with base64 thumbnails ─────────────
app.get('/face_db', (req, res) => {
  try {
    const IMAGE_EXTS = /\.(jpe?g|png|webp|bmp|gif)$/i
    const files = fs.readdirSync(FACE_DB_DIR).filter(f => IMAGE_EXTS.test(f))
    const entries = files.map(filename => {
      const filepath = path.join(FACE_DB_DIR, filename)
      const data     = fs.readFileSync(filepath)
      const ext      = path.extname(filename).toLowerCase().slice(1)
      const mime     = ext === 'png' ? 'image/png'
                     : ext === 'webp' ? 'image/webp'
                     : 'image/jpeg'
      return {
        filename,
        name:    path.basename(filename, path.extname(filename)),
        dataUrl: `data:${mime};base64,${data.toString('base64')}`,
      }
    })
    res.json(entries)
  } catch (err) {
    res.status(500).json({ error: err.message })
  }
})

// ── POST /face_db/upload — add new image(s) to the face database ──────────────
app.post('/face_db/upload', upload.array('images', 20), (req, res) => {
  const saved = (req.files ?? []).map(f => f.filename)
  res.json({ success: true, saved })
})

// ── DELETE /face_db/:filename — remove a person from the database ─────────────
app.delete('/face_db/:filename', (req, res) => {
  const filename = path.basename(req.params.filename) // strip any path traversal
  const filepath = path.join(FACE_DB_DIR, filename)
  if (!filepath.startsWith(FACE_DB_DIR + path.sep) &&
      filepath !== FACE_DB_DIR + path.sep + filename) {
    // extra guard, redundant with basename but belt-and-suspenders
  }
  try {
    if (fs.existsSync(filepath)) {
      fs.unlinkSync(filepath)
      res.json({ success: true })
    } else {
      res.status(404).json({ error: 'File not found' })
    }
  } catch (err) {
    res.status(500).json({ error: err.message })
  }
})

// ── GET /snapshot — single JPEG frame grabbed from the MJPEG stream ───────────
function getSnapshot() {
  return new Promise(resolve => {
    const req = http.get(
      `http://${PYTHON_HOST}:${PYTHON_PORT}/video_feed`,
      pRes => {
        let buf = Buffer.alloc(0)
        const timer = setTimeout(() => { req.destroy(); resolve(null) }, 6000)
        pRes.on('data', chunk => {
          buf = Buffer.concat([buf, chunk])
          const s = buf.indexOf(Buffer.from([0xff, 0xd8]))
          const e = buf.indexOf(Buffer.from([0xff, 0xd9]))
          if (s !== -1 && e !== -1 && e > s) {
            clearTimeout(timer)
            req.destroy()
            resolve(buf.slice(s, e + 2).toString('base64'))
          }
        })
      }
    )
    req.on('error', () => resolve(null))
  })
}

app.get('/snapshot', async (req, res) => {
  const b64 = await getSnapshot()
  if (!b64) return res.status(503).send('Stream offline')
  const buf = Buffer.from(b64, 'base64')
  res.setHeader('Content-Type', 'image/jpeg')
  res.setHeader('Content-Length', buf.length)
  res.send(buf)
})

// ── POST /copilot/analyze — analyze footage via Azure OpenAI (gpt-4o vision) ──
app.post('/copilot/analyze', async (req, res) => {
  const { subject, coords } = req.body ?? {}

  const apiKey    = process.env.AZURE_OPENAI_API_KEY
  const endpoint  = (process.env.AZURE_OPENAI_ENDPOINT ?? '').replace(/\/$/, '')
  const deployment = process.env.AZURE_OPENAI_DEPLOYMENT || 'gpt-4o'

  if (!apiKey || !endpoint) {
    return res.status(503).json({
      error: 'Copilot API not configured. Set AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT in your .env file.'
    })
  }

  // Grab a live snapshot for visual context
  const snapshotB64 = await getSnapshot()

  const positionNote = coords
    ? ` The person is located at pixel position (${coords.center_x}, ${coords.center_y}) with a bounding box of ${coords.w}×${coords.h}px.`
    : ''

  const isUnknown  = !subject || subject === 'Unknown Person'
  const subjectDesc = isUnknown ? 'an unrecognized individual' : `the identified individual "${subject}"`

  const systemPrompt =
    'You are a security intelligence analyst reviewing live surveillance footage. ' +
    'Analyze the provided camera frame and describe the person\'s behavior, body language, ' +
    'apparent activity, clothing, and any notable or potentially suspicious characteristics. ' +
    'Be concise, professional, and factual. Structure your response as a brief security report.'

  const userText =
    `Analyze this security camera frame. ${isUnknown ? 'An UNRECOGNIZED person' : `Person identified as "${subject}"`} ` +
    `has been flagged by the detection system.${positionNote} ` +
    `Provide a behavioral analysis and summarize what this person appears to be doing.`

  const contentParts = snapshotB64
    ? [
        { type: 'text', text: userText },
        { type: 'image_url', image_url: { url: `data:image/jpeg;base64,${snapshotB64}`, detail: 'high' } }
      ]
    : userText  // fallback: text-only if stream is offline

  const body = JSON.stringify({
    messages: [
      { role: 'system', content: systemPrompt },
      { role: 'user',   content: contentParts }
    ],
    max_tokens:  600,
    temperature: 0.3,
  })

  const apiUrl = new URL(
    `${endpoint}/openai/deployments/${deployment}/chat/completions?api-version=2024-02-01`
  )

  const options = {
    hostname: apiUrl.hostname,
    path:     apiUrl.pathname + apiUrl.search,
    method:   'POST',
    headers: {
      'Content-Type':   'application/json',
      'api-key':        apiKey,
      'Content-Length': Buffer.byteLength(body),
    },
  }

  const proto = apiUrl.protocol === 'https:' ? https : http
  const azureReq = proto.request(options, azureRes => {
    let raw = ''
    azureRes.on('data', c => raw += c)
    azureRes.on('end', () => {
      try {
        const parsed = JSON.parse(raw)
        if (parsed.error) return res.status(500).json({ error: parsed.error.message })
        const analysis = parsed.choices?.[0]?.message?.content?.trim() ?? 'No analysis returned.'
        res.json({ analysis })
      } catch {
        res.status(500).json({ error: 'Failed to parse Copilot response.' })
      }
    })
  })
  azureReq.on('error', e => res.status(500).json({ error: e.message }))
  azureReq.write(body)
  azureReq.end()
})

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
    copilot_enabled: false,
    suspicious_activities: 0,
    _offline:   true,
  })
})

// ── GET /suspicious-activities  — suspicious activities log ──────────────────
app.get('/suspicious-activities', (req, res) => {
  proxyJSON('/suspicious-activities', res, {
    activities: [],
    total_count: 0,
    timestamp: Date.now() / 1000,
    _offline: true,
  })
})

// ── GET /activity-summary/:faceId  — activity summary for specific face ──────
app.get('/activity-summary/:faceId', (req, res) => {
  const faceId = req.params.faceId
  proxyJSON(`/activity-summary/${faceId}`, res, {
    face_id: faceId,
    total_detections: 0,
    suspicious_count: 0,
    avg_suspicion: 0.0,
    max_suspicion: 0.0,
    risk_trend: 'UNKNOWN',
    _offline: true,
  })
})

// ── GET /live  — MJPEG video stream ──────────────────────────────────────────
app.get('/live', (req, res) => {
  const RECONNECT_DELAY_MS = 1000
  const MAX_RECONNECTS     = 10
  let reconnects = 0
  let destroyed  = false

  // Clean up everything if the browser disconnects
  req.on('close', () => {
    destroyed = true
  })

  function connectToPython () {
    if (destroyed) return

    const pythonReq = http.get(
      `http://${PYTHON_HOST}:${PYTHON_PORT}/video_feed`,
      (pRes) => {
        // First successful connection — forward headers once
        if (!res.headersSent) {
          res.writeHead(pRes.statusCode, {
            ...pRes.headers,
            'Access-Control-Allow-Origin': '*',
          })
        }
        reconnects = 0  // reset counter on successful connection

        pRes.on('data', (chunk) => {
          if (!destroyed) {
            try { res.write(chunk) } catch (_) { destroyed = true }
          }
        })

        pRes.on('end', () => {
          if (!destroyed) tryReconnect()
        })

        pRes.on('error', () => {
          if (!destroyed) tryReconnect()
        })
      }
    )

    pythonReq.on('error', () => {
      if (!res.headersSent && !res.writableEnded) {
        res.status(503).send('Stream offline — make sure multiple_tracking.py is running on port 5001')
        destroyed = true
      } else {
        tryReconnect()
      }
    })

    req.on('close', () => pythonReq.destroy())
  }

  function tryReconnect () {
    if (destroyed || reconnects >= MAX_RECONNECTS) {
      if (!res.writableEnded) res.end()
      return
    }
    reconnects++
    setTimeout(connectToPython, RECONNECT_DELAY_MS)
  }

  connectToPython()
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
  console.log('╔═══════════════════════════════════════════════════════════════╗')
  console.log('║           SecureView — Surveillance Dashboard                 ║')
  console.log('╠═══════════════════════════════════════════════════════════════╣')
  console.log(`║  Express server  → http://localhost:${SERVER_PORT}                 ║`)
  console.log(`║  Python backend  → http://localhost:${PYTHON_PORT} (required)      ║`)
  console.log('╠═══════════════════════════════════════════════════════════════╣')
  console.log('║  GET  /                Vue app (dist/ after npm run build)    ║')
  console.log('║  GET  /live            MJPEG stream                           ║')
  console.log('║  GET  /snapshot        Single JPEG frame                      ║')
  console.log('║  GET  /data            Face recognition JSON                  ║')
  console.log('║  GET  /health          System health                          ║')
  console.log('║  GET  /face_db         List enrolled faces                    ║')
  console.log('║  POST /face_db/upload  Add images to face database            ║')
  console.log('║  DEL  /face_db/:f      Remove face from database              ║')
  console.log('║  POST /copilot/analyze AI behavioral analysis                 ║')
  console.log('╠═══════════════════════════════════════════════════════════════╣')
  console.log('║  Dev mode: npm run dev  (Vite on :5173, proxies to here)      ║')
  console.log('╚═══════════════════════════════════════════════════════════════╝')
  console.log('')
  console.log('  ⚠  Start multiple_tracking.py first!')
  if (!process.env.AZURE_OPENAI_API_KEY) {
    console.log('  ⚠  AZURE_OPENAI_API_KEY not set — Copilot analysis disabled')
  }
  console.log('')
})