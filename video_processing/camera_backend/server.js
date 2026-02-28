/**
 * server.js — SecureView Express proxy server
 *
 * Responsibilities:
 * 1. Proxy JSON data + health endpoints → Python face-recognition server (:5001)
 * 2. Proxy the MJPEG live video stream   → Python server (:5001/video_feed)
 * 3. Serve the built Vue frontend (dist/) in production
 * 4. Face Database CRUD  (GET/POST/DELETE /face_db)
 * 5. Gemini AI analysis (POST /gemini/analyze → Google Gemini API)
 * 6. Snapshot endpoint   (GET /snapshot → single JPEG from MJPEG stream)
 *
 * Startup order:
 * 1. python multiple_tracking.py   (starts on :5001)
 * 2. node server.js                (starts on :8080)
 * 3. npm run dev  OR  open http://localhost:8080 for the built app
 *
 * Environment variables (copy .env.example → .env):
 *   GEMINI_API_KEY       your Google AI Studio / Gemini API key
 *   GEMINI_MODEL         model name (default: gemini-2.0-flash)
 */

// Load .env from the workspace root (two levels up from video_processing/camera_backend/)
require('dotenv').config({ path: require('path').join(__dirname, '../../.env') })

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

// ── Body parser (JSON) for Gemini endpoint ───────────────────────────────────
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

// ── Gemini rate-limit state ───────────────────────────────────────────────────
// Free-tier limits for gemini-2.5-flash: 5 RPM, 250 000 TPM, 20 RPD
const GEMINI_LIMITS = { rpm: 5, tpm: 250_000, rpd: 20 }

// Minimum gap between any two live API calls (ms).
// 60 000 ms / 5 RPM = 12 000 ms; add 1 s buffer → 13 s.
const GEMINI_MIN_INTERVAL_MS = 13_000
let   geminiLastCallTs = 0   // timestamp of the most recent live call

// Per-subject result cache (avoids burning a request for the same person twice).
// TTL: 5 minutes.  Key: subject name (lowercased).
const GEMINI_CACHE_TTL_MS = 5 * 60_000
const geminiCache = new Map() // key → { analysis, ts }

function getCachedAnalysis (subject) {
  const key   = (subject || 'unknown').toLowerCase()
  const entry = geminiCache.get(key)
  if (!entry) return null
  if (Date.now() - entry.ts > GEMINI_CACHE_TTL_MS) { geminiCache.delete(key); return null }
  return entry.analysis
}

function setCachedAnalysis (subject, analysis) {
  const key = (subject || 'unknown').toLowerCase()
  geminiCache.set(key, { analysis, ts: Date.now() })
}

// Seconds until the next live call is allowed (0 = ready now)
function geminiCooldownSec () {
  const elapsed = Date.now() - geminiLastCallTs
  return elapsed >= GEMINI_MIN_INTERVAL_MS ? 0 : Math.ceil((GEMINI_MIN_INTERVAL_MS - elapsed) / 1000)
}

// Sliding-window buckets (timestamps in ms / token counts)
const geminiRate = {
  minuteRequests: [],   // timestamps of requests in the last 60 s
  minuteTokens:   [],   // { ts, tokens } pairs in the last 60 s
  dayRequests:    [],   // timestamps of requests today (midnight-reset)
}

function pruneGeminiRate () {
  const now     = Date.now()
  const oneMin  = now - 60_000
  const midnightToday = new Date(now)
  midnightToday.setHours(0, 0, 0, 0)

  geminiRate.minuteRequests = geminiRate.minuteRequests.filter(t  => t  > oneMin)
  geminiRate.minuteTokens   = geminiRate.minuteTokens  .filter(e  => e.ts > oneMin)
  geminiRate.dayRequests    = geminiRate.dayRequests   .filter(t  => t  >= midnightToday.getTime())
}

function geminiRateStatus () {
  pruneGeminiRate()
  const usedRpm  = geminiRate.minuteRequests.length
  const usedTpm  = geminiRate.minuteTokens.reduce((s, e) => s + e.tokens, 0)
  const usedRpd  = geminiRate.dayRequests.length

  // Seconds until the oldest minute-window request expires
  const nextRpmReset = geminiRate.minuteRequests.length
    ? Math.ceil((geminiRate.minuteRequests[0] + 60_000 - Date.now()) / 1000)
    : 0

  return {
    rpm:  { used: usedRpm,  limit: GEMINI_LIMITS.rpm,  remaining: Math.max(0, GEMINI_LIMITS.rpm  - usedRpm)  },
    tpm:  { used: usedTpm,  limit: GEMINI_LIMITS.tpm,  remaining: Math.max(0, GEMINI_LIMITS.tpm  - usedTpm)  },
    rpd:  { used: usedRpd,  limit: GEMINI_LIMITS.rpd,  remaining: Math.max(0, GEMINI_LIMITS.rpd  - usedRpd)  },
    nextRpmResetSec: nextRpmReset,
    cooldownSec: geminiCooldownSec(),
  }
}

// Rough token estimator (avoids an extra API call)
// ~4 chars per token for English text; images cost ~258 tokens each on Gemini
function estimateTokens (text, hasImage) {
  return Math.ceil(text.length / 4) + (hasImage ? 258 : 0)
}

// ── GET /gemini/rate-status — expose quota info to the frontend ───────────────
app.get('/gemini/rate-status', (req, res) => {
  res.json(geminiRateStatus())
})

// ── POST /gemini/analyze — analyze footage via Google Gemini Vision ──────────
app.post('/gemini/analyze', async (req, res) => {
  // Wrap everything so unhandled errors return JSON, not Express's HTML 500 page
  try {
  const { subject, coords } = req.body ?? {}

  const apiKey   = process.env.GEMINI_API_KEY
  const model    = process.env.GEMINI_MODEL || 'gemini-2.5-flash'

  if (!apiKey) {
    return res.status(503).json({
      error: 'Gemini API not configured. Set GEMINI_API_KEY in your .env file.'
    })
  }

  // ── Rate-limit check ────────────────────────────────────────────────────────
  const status = geminiRateStatus()

  // 1. Check subject cache — return instantly if we have a fresh result
  const cached = getCachedAnalysis(subject)
  if (cached) {
    return res.json({ analysis: cached, fromCache: true, rateLimit: status })
  }

  // 2. Enforce minimum inter-request gap (prevents bursting all 5 RPM slots)
  if (status.cooldownSec > 0) {
    return res.status(429).json({
      error: `Please wait ${status.cooldownSec}s before the next analysis (min interval: ${GEMINI_MIN_INTERVAL_MS / 1000}s).`,
      rateLimit: status,
    })
  }

  // 3. Hard quota checks
  if (status.rpd.remaining <= 0) {
    return res.status(429).json({
      error: `Daily request limit reached (${GEMINI_LIMITS.rpd} RPD). Resets at midnight.`,
      rateLimit: status,
    })
  }
  if (status.rpm.remaining <= 0) {
    return res.status(429).json({
      error: `Rate limit: too many requests. Try again in ${status.nextRpmResetSec}s (limit: ${GEMINI_LIMITS.rpm} RPM).`,
      rateLimit: status,
    })
  }

  // Grab a live snapshot for visual context
  const snapshotB64 = await getSnapshot()

  const positionNote = coords
    ? ` The person is located at pixel position (${coords.center_x}, ${coords.center_y}) with a bounding box of ${coords.w}×${coords.h}px.`
    : ''

  const isUnknown   = !subject || subject === 'Unknown Person'
  const systemText  =
    'You are a security intelligence analyst reviewing live surveillance footage. ' +
    'Analyze the provided camera frame and describe the person\'s behavior, body language, ' +
    'apparent activity, clothing, and any notable or potentially suspicious characteristics. ' +
    'Be concise, professional, and factual. Structure your response as a brief security report.'

  const userText =
    systemText + '\n\n' +
    `Analyze this security camera frame. ${isUnknown ? 'An UNRECOGNIZED person' : `Person identified as "${subject}"`} ` +
    `has been flagged by the detection system.${positionNote} ` +
    `Provide a behavioral analysis and summarize what this person appears to be doing.`

  // Estimate token usage; reject if it would blow the per-minute TPM budget
  const estimatedTokens = estimateTokens(userText, !!snapshotB64) + 600 // +600 for max output
  if (status.tpm.remaining < estimatedTokens) {
    return res.status(429).json({
      error: `Token budget exhausted for this minute (~${estimatedTokens} tokens needed, ${status.tpm.remaining} remaining). Wait ${status.nextRpmResetSec}s.`,
      rateLimit: status,
    })
  }

  // ── Record this request against all three windows ───────────────────────────
  const now = Date.now()
  geminiLastCallTs = now   // start the per-request cooldown
  geminiRate.minuteRequests.push(now)
  geminiRate.dayRequests.push(now)
  geminiRate.minuteTokens.push({ ts: now, tokens: estimatedTokens })

  const parts = [{ text: userText }]
  if (snapshotB64) {
    parts.push({ inline_data: { mime_type: 'image/jpeg', data: snapshotB64 } })
  }

  const body = JSON.stringify({
    contents: [{ parts }],
    generationConfig: { maxOutputTokens: 600, temperature: 0.3 },
  })

  const apiUrl = new URL(
    `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${apiKey}`
  )

  const options = {
    hostname: apiUrl.hostname,
    path:     apiUrl.pathname + apiUrl.search,
    method:   'POST',
    headers: {
      'Content-Type':   'application/json',
      'Content-Length': Buffer.byteLength(body),
    },
  }

  const geminiReq = https.request(options, geminiRes => {
    let raw = ''
    geminiRes.on('data', c => raw += c)
    geminiRes.on('end', () => {
      try {
        const parsed = JSON.parse(raw)
        // If Gemini itself returned a 429 / quota error, surface it clearly
        if (parsed.error) {
          const msg = parsed.error.message || 'Gemini API error'
          const statusCode = parsed.error.code === 429 ? 429 : 500
          return res.status(statusCode).json({ error: msg, rateLimit: geminiRateStatus() })
        }
        const analysis = parsed.candidates?.[0]?.content?.parts?.[0]?.text?.trim() ?? 'No analysis returned.'
        // Refine token count with actuals if the API returned them
        const actualTokens =
          (parsed.usageMetadata?.promptTokenCount ?? 0) +
          (parsed.usageMetadata?.candidatesTokenCount ?? 0)
        if (actualTokens > 0) {
          // Replace the estimate with the real count so future checks are accurate
          const entry = geminiRate.minuteTokens.find(e => e.ts === now)
          if (entry) entry.tokens = actualTokens
        }
        // Cache result so the same person can be re-analyzed for free for 5 min
        setCachedAnalysis(subject, analysis)
        res.json({ analysis, fromCache: false, rateLimit: geminiRateStatus() })
      } catch {
        res.status(500).json({ error: 'Failed to parse Gemini response.' })
      }
    })
  })
  geminiReq.on('error', e => res.status(500).json({ error: e.message }))
  geminiReq.write(body)
  geminiReq.end()
  } catch (err) {
    if (!res.headersSent) res.status(500).json({ error: err.message || 'Gemini route error' })
  }
})

// ── Internal helper: proxy a JSON request to Python ──────────────────────────
function proxyJSON(pythonPath, res, offlineFallback) {
  const req = http.get(
    `http://${PYTHON_HOST}:${PYTHON_PORT}${pythonPath}`,
    (pRes) => {
      let raw = ''
      pRes.on('data', (chunk) => (raw += chunk))
      pRes.on('end', () => {
        // If Python returned a non-2xx status or an empty/non-JSON body,
        // fall back to the offline payload so the frontend always gets valid JSON.
        const status = pRes.statusCode || 500
        if (status < 200 || status >= 300) {
          return res.status(503).json(offlineFallback)
        }
        const trimmed = raw.trim()
        if (!trimmed || trimmed[0] === '<') {
          // Empty body or an accidental HTML response — use offline fallback
          return res.status(503).json(offlineFallback)
        }
        res.setHeader('Cache-Control', 'no-cache, no-store, must-revalidate')
        res.setHeader('Content-Type', 'application/json')
        res.send(trimmed)
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
    gemini_enabled: false,
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

// ── Global JSON error handler (must be after all routes) ────────────────────
// Ensures that any Express or middleware error returns JSON, never HTML.
app.use((err, req, res, _next) => {
  console.error('[Express Error]', err)
  if (!res.headersSent) {
    res.status(err.status || err.statusCode || 500).json({
      error: err.message || 'Internal server error'
    })
  }
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
  console.log('║  POST /gemini/analyze  AI behavioral analysis                 ║')
  console.log('╠═══════════════════════════════════════════════════════════════╣')
  console.log('║  Dev mode: npm run dev  (Vite on :5173, proxies to here)      ║')
  console.log('╚═══════════════════════════════════════════════════════════════╝')
  console.log('')
  console.log('  ⚠  Start multiple_tracking.py first!')
  if (!process.env.GEMINI_API_KEY) {
    console.log('  ⚠  GEMINI_API_KEY not set — Gemini analysis disabled')
  }
  console.log('')
})