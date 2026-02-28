<script setup lang="ts">
/// <reference types="vite/client" />
import { ref, computed, onMounted, onUnmounted } from 'vue'
import {
  Menu, X,
  LayoutDashboard, Monitor, ClipboardList, Settings,
  Eye, UserCheck, AlertTriangle, Clock,
  Activity, Wifi, WifiOff, UserPlus,
  Bell, Camera, Signal, Shield, BarChart2, Calendar, CloudUpload
} from 'lucide-vue-next'

// ── Types ─────────────────────────────────────────────────────────────────────
interface FaceCoords {
  x: number; y: number; w: number; h: number
  center_x: number; center_y: number
}
interface KnownFace  { name: string; coords: FaceCoords }
interface Alert      { type: 'KNOWN' | 'UNKNOWN'; name: string; time: string }
interface Counts     { known: number; unknown: number; total: number }
interface ApiPayload {
  known: KnownFace[]
  unknown: FaceCoords[]
  counts: Counts
  alerts: Alert[]
  timestamp: number
  _offline?: boolean
}

// ── Navigation state ──────────────────────────────────────────────────────────
const currentPage = ref<'dashboard' | 'logs'>('dashboard')
const activeTab   = ref<'live' | 'detected'>('live')
const sidebarOpen = ref(true)

// ── System state ──────────────────────────────────────────────────────────────
const systemOnline = ref(false)
const clock        = ref('--:--:--')
const currentDate  = ref('')
const lastUpdate   = ref('--:--:--')
const errorCount   = ref(0)

// ── API data ──────────────────────────────────────────────────────────────────
const counts       = ref<Counts>({ known: 0, unknown: 0, total: 0 })
const knownFaces   = ref<KnownFace[]>([])
const unknownFaces = ref<FaceCoords[]>([])
const apiAlerts    = ref<Alert[]>([])

// ── API Routing ───────────────────────────────────────────────────────────────
// Relies on vite.config.ts proxy in dev, and relative paths in prod.
const STREAM_URL = '/live'
const DATA_URL = '/data'

const streamError = ref(false)

// ── Computed: detected people for the Detected tab ───────────────────────────
const detectedPeople = computed(() => {
  const known = knownFaces.value
    .filter(p => p.name !== 'SCANNING...')
    .map((p, i) => ({
      id: `k-${i}-${p.name}`,
      name: p.name,
      type: 'known' as const,
      coords: p.coords,
    }))

  const scanning = knownFaces.value
    .filter(p => p.name === 'SCANNING...')
    .map((_, i) => ({
      id: `s-${i}`,
      name: 'Analyzing…',
      type: 'scanning' as const,
      coords: null as FaceCoords | null,
    }))

  const unknown = unknownFaces.value.map((u, i) => ({
    id: `u-${i}`,
    name: 'Unknown Person',
    type: 'unknown' as const,
    coords: u,
  }))

  return [...known, ...scanning, ...unknown]
})

// ── Computed: access log rows from alert history ──────────────────────────────
const accessLogs = computed(() =>
  [...apiAlerts.value]
    .reverse()
    .map((a, i) => ({
      id: i,
      name:   a.name === 'INTRUDER' ? 'Unknown Person' : a.name,
      status: a.type === 'KNOWN' ? 'Authorized' : 'Denied',
      time:   a.time,
    }))
)

// ── Data polling (250 ms) ─────────────────────────────────────────────────────
let pollTimer:  ReturnType<typeof setInterval> | null = null
let clockTimer: ReturnType<typeof setInterval> | null = null

async function pollData(): Promise<void> {
  try {
    const res = await fetch(DATA_URL, { cache: 'no-store' })
    if (!res.ok) throw new Error('Non-OK response')
    const d: ApiPayload = await res.json()

    errorCount.value  = 0
    systemOnline.value = !d._offline

    counts.value       = d.counts  ?? { known: 0, unknown: 0, total: 0 }
    knownFaces.value   = d.known   ?? []
    unknownFaces.value = d.unknown ?? []
    apiAlerts.value    = (d.alerts ?? []).slice(-200)

    if (d.timestamp) {
      lastUpdate.value = new Date(d.timestamp * 1000).toLocaleTimeString('en-US', { hour12: false })
    }
  } catch {
    errorCount.value++
    if (errorCount.value > 4) systemOnline.value = false
  }
}

// ── Sidebar toggle ───────────────────────────────────────────────────────────
function toggleSidebar(): void {
  sidebarOpen.value = !sidebarOpen.value
  localStorage.setItem('sidebarOpen', String(sidebarOpen.value))
}

// ── Lifecycle ─────────────────────────────────────────────────────────────────
onMounted(() => {
  const saved = localStorage.getItem('sidebarOpen')
  if (saved !== null) sidebarOpen.value = saved === 'true'

  pollData()
  pollTimer  = setInterval(pollData, 250)
  const tick = () => {
    const now = new Date()
    clock.value = now.toLocaleTimeString('en-US', { hour12: false })
    currentDate.value = now.toLocaleDateString('en-CA')
  }
  tick()
  clockTimer = setInterval(tick, 1000)
})

onUnmounted(() => {
  if (pollTimer)  clearInterval(pollTimer)
  if (clockTimer) clearInterval(clockTimer)
})
</script>

<template>
  <div class="app-shell">

    <!-- ── NARROW ICON SIDEBAR ──────────────────────────────────── -->
    <nav class="icon-sidebar">
      <div class="sidebar-brand">
        <div class="brand-mark">S</div>
      </div>

      <ul class="nav-icons">
        <li :class="{ active: currentPage === 'dashboard' }" @click="currentPage = 'dashboard'; activeTab = 'live'" title="Dashboard">
          <component :is="LayoutDashboard" :size="20" />
        </li>
        <li @click="currentPage = 'dashboard'; activeTab = 'live'" title="Live Feed">
          <component :is="Camera" :size="20" />
        </li>
        <li @click="currentPage = 'dashboard'; activeTab = 'detected'" title="Detections">
          <component :is="Eye" :size="20" />
        </li>
        <li :class="{ active: currentPage === 'logs' }" @click="currentPage = 'logs'" title="Access Logs">
          <component :is="ClipboardList" :size="20" />
        </li>
        <li title="Signals">
          <component :is="Signal" :size="20" />
        </li>
        <li title="Activity">
          <component :is="BarChart2" :size="20" />
        </li>
        <li title="Monitor">
          <component :is="Monitor" :size="20" />
        </li>
        <li title="Shield">
          <component :is="Shield" :size="20" />
        </li>
      </ul>

      <ul class="nav-icons nav-icons-bottom">
        <li title="Settings">
          <component :is="Settings" :size="20" />
        </li>
      </ul>
    </nav>

    <!-- ── MAIN AREA ─────────────────────────────────────────────── -->
    <main class="main-area">
      <!-- Page header -->
      <header class="page-header">
        <div class="ph-left">
          <h1>{{ currentPage === 'dashboard' ? 'Dashboard' : 'Access Logs' }}</h1>
          <p class="ph-sub">Welcome back, <strong>SecureView</strong></p>
        </div>
        <div class="ph-right">
          <button class="hdr-icon-btn" title="Notifications">
            <component :is="Bell" :size="18" />
          </button>
          <button class="hdr-icon-btn" title="Users">
            <component :is="UserPlus" :size="18" />
          </button>
        </div>
      </header>

      <div class="page-body">
        <!-- ── 4 STAT CARDS ─────────────────────────────────────── -->
        <div class="metrics-row">
          <!-- Clock / date -->
          <div class="metric-card clock-card">
            <div class="mc-clock">{{ clock }}</div>
            <div class="mc-date">
              <component :is="Calendar" :size="11" />
              {{ currentDate }}
            </div>
          </div>
          <!-- Last update -->
          <div class="metric-card">
            <div class="mc-label">Last Update</div>
            <div class="mc-dual">
              <div class="mc-dual-val">{{ lastUpdate }}</div>
            </div>
            <div class="mc-sublabel">System &nbsp;&nbsp; Process</div>
          </div>
          <!-- Status -->
          <div class="metric-card">
            <div class="mc-label">Status</div>
            <div class="mc-status-body">
              <component :is="CloudUpload" :size="32" :class="['mc-status-icon', systemOnline ? 'green' : 'red']" />
              <div :class="['mc-status-text', systemOnline ? 'green' : 'red']">{{ systemOnline ? 'Online' : 'Offline' }}</div>
              <div class="mc-status-ver">v1.0-alpha</div>
            </div>
          </div>
          <!-- Detection summary (weather-style card) -->
          <div class="metric-card detect-summary-card">
            <div class="ds-top">
              <component :is="Eye" :size="22" class="ds-icon" />
              <div class="ds-big">{{ counts.total }}</div>
            </div>
            <div class="ds-rows">
              <div class="ds-row"><span>Identified</span><span class="green">{{ counts.known }}</span></div>
              <div class="ds-row"><span>Unknown</span><span class="red">{{ counts.unknown }}</span></div>
            </div>
          </div>
        </div>

      <template v-if="currentPage === 'dashboard'">
        <!-- Tab strip -->
        <div class="tab-strip">
          <button :class="['tab-pill', { active: activeTab === 'live' }]" @click="activeTab = 'live'">
            <component :is="Monitor" :size="13" /> Live Feed
          </button>
          <button :class="['tab-pill', { active: activeTab === 'detected' }]" @click="activeTab = 'detected'">
            <component :is="Activity" :size="13" /> Detected People
            <span v-if="detectedPeople.length > 0" class="tab-badge">{{ detectedPeople.length }}</span>
          </button>
        </div>

        <!-- ── CAMERA GRID ──────────────────────────────────────── -->
        <div v-if="activeTab === 'live'" class="camera-grid">
          <!-- Live camera -->
          <div class="cam-card">
            <div class="cam-header">
              <span class="cam-name">Main Entrance</span>
              <span :class="['cam-dot', systemOnline ? 'online' : 'offline']"></span>
            </div>
            <div class="cam-body">
              <img v-if="!streamError" :src="STREAM_URL" class="cam-stream" alt="Live feed" @error="streamError = true" />
              <div v-else class="cam-offline-overlay">
                <svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
                <p>STREAM OFFLINE</p>
                <button @click="streamError = false">↺ Retry</button>
              </div>
              <div class="cam-scanlines" />
              <div class="cam-corners"><span class="cc tl"/><span class="cc tr"/><span class="cc bl"/><span class="cc br"/></div>
            </div>
            <div class="cam-footer">
              <span class="cam-ts">Updated {{ lastUpdate }}</span>
              <button class="cam-ctrl-btn">⏸</button>
              <button class="cam-ctrl-btn">↺</button>
            </div>
          </div>

          <!-- CAM-02 placeholder -->
          <div class="cam-card">
            <div class="cam-header">
              <span class="cam-name">Entrance CAM-02</span>
              <span class="cam-dot offline"></span>
            </div>
            <div class="cam-body cam-placeholder">
              <component :is="Camera" :size="32" class="cam-ph-icon" />
              <span class="cam-ph-label">NOT CONNECTED</span>
            </div>
            <div class="cam-footer">
              <span class="cam-ts">—</span>
              <button class="cam-ctrl-btn">⏸</button>
              <button class="cam-ctrl-btn">↺</button>
            </div>
          </div>

          <!-- CAM-03 placeholder -->
          <div class="cam-card">
            <div class="cam-header">
              <span class="cam-name">Exit CAM-03</span>
              <span class="cam-dot offline"></span>
            </div>
            <div class="cam-body cam-placeholder">
              <component :is="Camera" :size="32" class="cam-ph-icon" />
              <span class="cam-ph-label">NOT CONNECTED</span>
            </div>
            <div class="cam-footer">
              <span class="cam-ts">—</span>
              <button class="cam-ctrl-btn">⏸</button>
              <button class="cam-ctrl-btn">↺</button>
            </div>
          </div>
        </div>

        <!-- ── SYSTEM METRICS ROW (below cameras) ────────────── -->
        <div v-if="activeTab === 'live'" class="sysmetrics-row">
          <div class="sysm-card">
            <div class="sysm-label">Detected</div>
            <div class="sysm-big">{{ counts.total }}</div>
            <div class="sysm-track"><div class="sysm-fill" :style="{width: Math.min(counts.total * 25, 100) + '%'}"></div></div>
          </div>
          <div class="sysm-card">
            <div class="sysm-label">Identified</div>
            <div class="sysm-big green">{{ counts.known }}</div>
            <div class="sysm-track"><div class="sysm-fill green" :style="{width: counts.total > 0 ? (counts.known / counts.total * 100) + '%' : '0%'}"></div></div>
          </div>
          <div class="sysm-card">
            <div class="sysm-label">Unknown / Alerts</div>
            <div class="sysm-big red">{{ counts.unknown }}</div>
            <div class="sysm-track sysm-alert"><div class="sysm-fill red" :style="{width: counts.total > 0 ? (counts.unknown / counts.total * 100) + '%' : '0%'}"></div></div>
          </div>
        </div>

        <div v-if="activeTab === 'detected'" class="card detected-card full-width">
            <div class="card-header">
              <h3>Detected People</h3>
              <span class="detection-count">
                {{ detectedPeople.length }}
                {{ detectedPeople.length === 1 ? 'person' : 'people' }} in frame
              </span>
            </div>

            <div class="detected-container">
              <div v-if="detectedPeople.length === 0" class="empty-state">
                <component :is="Eye" :size="44" />
                <p>No faces detected in camera feed</p>
                <p class="empty-sub">Faces will appear here as they are detected</p>
              </div>

              <div
                v-for="person in detectedPeople"
                :key="person.id"
                :class="['detected-item', person.type]"
              >
                <div :class="['person-avatar', person.type]">
                  <span>{{ person.type === 'unknown' ? '?' : person.type === 'scanning' ? '…' : person.name.charAt(0) }}</span>
                </div>

                <div class="person-info">
                  <span class="person-name">{{ person.name }}</span>

                  <span :class="['match-badge', person.type]">
                    <span v-if="person.type === 'known'">✓ &nbsp;VERIFIED</span>
                    <span v-else-if="person.type === 'scanning'">⟳ &nbsp;SCANNING</span>
                    <span v-else>✗ &nbsp;UNRECOGNIZED</span>
                  </span>

                  <span v-if="person.coords" class="coords">
                    pos ({{ person.coords.center_x }}, {{ person.coords.center_y }})
                    &nbsp;·&nbsp;
                    {{ person.coords.w }}×{{ person.coords.h }}px
                  </span>
                </div>

                <button v-if="person.type === 'unknown'" class="add-person-btn">
                  <component :is="UserPlus" :size="14" />
                  Enroll
                </button>
              </div>
            </div>
          </div>
      </template>

      <template v-if="currentPage === 'logs'">
        <div class="logs-view">
          <div class="card logs-card">
            <div class="card-header">
              <h3>All Access Logs</h3>
              <span class="log-count">{{ accessLogs.length }} event{{ accessLogs.length !== 1 ? 's' : '' }}</span>
            </div>

            <div class="table-container" v-if="accessLogs.length > 0">
              <table>
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Name</th>
                    <th>Status</th>
                    <th>Time</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(log, i) in accessLogs" :key="log.id">
                    <td class="row-num">{{ i + 1 }}</td>
                    <td>{{ log.name }}</td>
                    <td>
                      <span :class="['status-badge', log.status.toLowerCase()]">
                        {{ log.status }}
                      </span>
                    </td>
                    <td class="time-cell">{{ log.time }}</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div v-else class="empty-state logs-empty">
              <component :is="ClipboardList" :size="44" />
              <p>No access events recorded yet</p>
              <p class="empty-sub">Events appear here as the recognition system detects faces</p>
            </div>
          </div>
        </div>
      </template>

      </div><!-- /page-body -->
    </main>
  </div>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

/* ── CSS VARIABLES ────────────────────────────────────────────────────────── */
.app-shell {
  --bg:          #0b0b0e;
  --sidebar-bg:  #0d0d10;
  --surface:     #131317;
  --surface-2:   #1b1b20;
  --surface-3:   #232328;
  --border:      #2a2a32;
  --border-soft: #1f1f26;
  --accent:      #dc2626;
  --accent-dim:  rgba(220,38,38,0.15);
  --accent-line: rgba(220,38,38,0.4);
  --green:       #22c55e;
  --amber:       #f59e0b;
  --blue:        #3b82f6;
  --text:        #eeeef2;
  --text-dim:    #8888a0;
  --text-muted:  #45455a;
  --mono:        'JetBrains Mono', monospace;
  --sans:        'Inter', system-ui, sans-serif;
  --sidebar-w:   64px;
}

* { box-sizing: border-box; margin: 0; padding: 0; }

/* ── SHELL ────────────────────────────────────────────────────────────────── */
.app-shell {
  display: flex;
  height: 100vh;
  overflow: hidden;
  font-family: var(--sans);
  font-size: 14px;
  color: var(--text);
  background: var(--bg);
}

/* ── ICON SIDEBAR ─────────────────────────────────────────────────────────── */
.icon-sidebar {
  width: var(--sidebar-w);
  min-width: var(--sidebar-w);
  background: var(--sidebar-bg);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  align-items: center;
  z-index: 20;
  padding-bottom: 12px;
}

.sidebar-brand {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 18px 0 14px;
  border-bottom: 1px solid var(--border-soft);
  margin-bottom: 8px;
}
.brand-mark {
  width: 32px; height: 32px;
  background: var(--accent);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1rem;
  font-weight: 800;
  color: #fff;
  letter-spacing: -0.02em;
}

.nav-icons {
  list-style: none;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  width: 100%;
  padding: 4px 0;
}
.nav-icons-bottom {
  margin-top: auto;
  padding-top: 8px;
  border-top: 1px solid var(--border-soft);
}

.nav-icons li {
  width: 42px; height: 42px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  cursor: pointer;
  color: var(--text-muted);
  position: relative;
  transition: all 0.18s ease;
  border-left: 3px solid transparent;
}
.nav-icons li:hover  { color: var(--text-dim); background: var(--surface-2); }
.nav-icons li.active {
  color: var(--text);
  background: var(--accent-dim);
  border-left-color: var(--accent);
}

/* ── MAIN AREA ────────────────────────────────────────────────────────────── */
.main-area {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--bg);
}

/* ── PAGE HEADER ──────────────────────────────────────────────────────────── */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 32px;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.ph-left h1 {
  font-size: 1.45rem;
  font-weight: 700;
  color: var(--text);
  letter-spacing: -0.02em;
  line-height: 1.1;
}
.ph-sub {
  font-size: 0.78rem;
  color: var(--text-dim);
  margin-top: 3px;
}
.ph-sub strong { color: var(--text); font-weight: 600; }
.ph-right { display: flex; align-items: center; gap: 8px; }
.hdr-icon-btn {
  width: 34px; height: 34px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 7px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-dim);
  cursor: pointer;
  transition: all 0.17s ease;
}
.hdr-icon-btn:hover { color: var(--text); background: var(--surface-3); }

/* ── PAGE BODY (scrollable) ───────────────────────────────────────────────── */
.page-body {
  flex: 1;
  overflow-y: auto;
  padding: 24px 28px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* ── METRICS ROW ──────────────────────────────────────────────────────────── */
.metrics-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  flex-shrink: 0;
}
.metric-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 20px 22px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-height: 110px;
}
.mc-label {
  font-size: 0.62rem;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--text-muted);
  font-family: var(--mono);
}
.mc-sublabel {
  font-size: 0.62rem;
  color: var(--text-muted);
  font-family: var(--mono);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-top: auto;
}

/* Clock card */
.clock-card { justify-content: center; }
.mc-clock {
  font-size: 2.4rem;
  font-weight: 700;
  color: var(--text);
  font-family: var(--mono);
  line-height: 1;
}
.mc-date {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 0.72rem;
  color: var(--text-dim);
  font-family: var(--mono);
}

/* Uptime / dual val */
.mc-dual {
  display: flex;
  align-items: baseline;
  gap: 6px;
  flex: 1;
}
.mc-dual-val {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text);
  font-family: var(--mono);
}

/* Status card */
.mc-status-body {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
  flex: 1;
  justify-content: center;
}
.mc-status-icon.green { color: var(--green); }
.mc-status-icon.red   { color: var(--accent); }
.mc-status-text {
  font-size: 1.05rem;
  font-weight: 700;
}
.mc-status-text.green { color: var(--green); }
.mc-status-text.red   { color: var(--accent); }
.mc-status-ver {
  font-size: 0.65rem;
  font-family: var(--mono);
  color: var(--text-muted);
}

/* Detection summary card (styled like weather card in image) */
.detect-summary-card {
  background: linear-gradient(135deg, #1a2a4a 0%, #1e3460 100%);
  border-color: #2a3f6a;
}
.ds-top {
  display: flex;
  align-items: center;
  gap: 10px;
}
.ds-icon { color: #60a5fa; }
.ds-big {
  font-size: 2.4rem;
  font-weight: 700;
  color: #fff;
  font-family: var(--mono);
  line-height: 1;
}
.ds-rows {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-top: auto;
}
.ds-row {
  display: flex;
  justify-content: space-between;
  font-size: 0.72rem;
  color: rgba(200,220,255,0.7);
}
.ds-row .green { color: #4ade80; font-weight: 600; }
.ds-row .red   { color: #f87171; font-weight: 600; }

/* ── TAB STRIP ────────────────────────────────────────────────────────────── */
.tab-strip {
  display: flex;
  gap: 0;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.tab-pill {
  display: flex;
  align-items: center;
  gap: 7px;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  padding: 12px 4px;
  margin-right: 24px;
  margin-bottom: -1px;
  color: var(--text-dim);
  font-family: var(--sans);
  font-size: 0.82rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.18s ease;
}
.tab-pill:hover  { color: var(--text); }
.tab-pill.active { color: var(--text); border-bottom-color: var(--accent); font-weight: 600; }
.tab-badge {
  background: var(--accent);
  color: #fff;
  font-size: 0.58rem;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 10px;
}

/* ── CAMERA GRID ──────────────────────────────────────────────────────────── */
.camera-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  flex-shrink: 0;
}
.cam-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.cam-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  border-bottom: 1px solid var(--border-soft);
}
.cam-name {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--text);
  letter-spacing: 0.02em;
}
.cam-dot {
  width: 8px; height: 8px;
  border-radius: 50%;
}
.cam-dot.online  { background: var(--green); box-shadow: 0 0 6px rgba(34,197,94,0.7); }
.cam-dot.offline { background: var(--text-muted); }

.cam-body {
  position: relative;
  aspect-ratio: 4/3;
  background: #000;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}
.cam-stream {
  width: 100%; height: 100%;
  object-fit: contain;
  position: absolute;
  inset: 0;
  display: block;
}
.cam-scanlines {
  position: absolute; inset: 0;
  background-image: repeating-linear-gradient(
    0deg, rgba(0,0,0,0.07) 0px, rgba(0,0,0,0.07) 1px, transparent 1px, transparent 3px
  );
  pointer-events: none;
  z-index: 3;
}
.cam-corners { position: absolute; inset: 0; pointer-events: none; z-index: 4; }
.cc {
  position: absolute;
  width: 14px; height: 14px;
  border-style: solid;
  border-color: rgba(220,38,38,0.5);
}
.cc.tl { top: 10px;    left: 10px;    border-width: 2px 0 0 2px; }
.cc.tr { top: 10px;    right: 10px;   border-width: 2px 2px 0 0; }
.cc.bl { bottom: 10px; left: 10px;    border-width: 0 0 2px 2px; }
.cc.br { bottom: 10px; right: 10px;   border-width: 0 2px 2px 0; }

.cam-placeholder {
  flex-direction: column;
  gap: 10px;
  background: var(--surface-2);
}
.cam-ph-icon  { color: var(--text-muted); opacity: 0.3; }
.cam-ph-label {
  font-size: 0.6rem;
  letter-spacing: 0.12em;
  color: var(--text-muted);
  text-transform: uppercase;
  font-family: var(--mono);
}

.cam-offline-overlay {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  position: absolute; inset: 0;
  background: rgba(11,11,14,0.92);
  color: var(--text-muted);
  z-index: 5;
  justify-content: center;
  text-align: center;
}
.cam-offline-overlay svg { color: var(--accent); opacity: 0.5; }
.cam-offline-overlay p  { font-size: 0.7rem; font-weight: 700; color: var(--accent); letter-spacing: 0.1em; text-transform: uppercase; font-family: var(--mono); }
.cam-offline-overlay button {
  background: var(--surface-3);
  border: 1px solid var(--border);
  color: var(--text);
  padding: 6px 16px;
  border-radius: 5px;
  font-size: 0.75rem;
  cursor: pointer;
  font-family: var(--sans);
}

.cam-footer {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  gap: 8px;
  border-top: 1px solid var(--border-soft);
}
.cam-ts {
  font-size: 0.62rem;
  color: var(--text-muted);
  font-family: var(--mono);
  flex: 1;
}
.cam-ctrl-btn {
  width: 26px; height: 26px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 5px;
  color: var(--text-dim);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  transition: all 0.15s ease;
}
.cam-ctrl-btn:hover { color: var(--text); background: var(--surface-3); }

/* ── SYSTEM METRICS ROW ───────────────────────────────────────────────────── */
.sysmetrics-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  flex-shrink: 0;
}
.sysm-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 18px 20px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.sysm-label {
  font-size: 0.6rem;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--text-muted);
  font-family: var(--mono);
}
.sysm-big {
  font-size: 2rem;
  font-weight: 700;
  color: var(--text);
  font-family: var(--mono);
  line-height: 1;
}
.sysm-big.green { color: var(--green); }
.sysm-big.red   { color: var(--accent); }
.sysm-track {
  height: 6px;
  background: var(--surface-3);
  border-radius: 3px;
  overflow: hidden;
  margin-top: 6px;
}
.sysm-alert {
  background: rgba(220,38,38,0.12);
}
.sysm-fill {
  height: 100%;
  background: var(--accent);
  border-radius: 3px;
  transition: width 0.4s ease;
}
.sysm-fill.green { background: var(--green); }
.sysm-fill.red   { background: var(--accent); }

/* ── FAKE TOP-BAR STUBS (removed, keep for compat) ─────────────────────── */
.top-bar {
  display: none;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
}
.top-bar h1 {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--text);
  letter-spacing: -0.01em;
}
.top-bar-right { display: flex; align-items: center; gap: 16px; }
.clock {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--text-dim);
  font-family: var(--mono);
  letter-spacing: 0.08em;
}
.online-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 11px;
  border-radius: 5px;
  font-size: 0.65rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  font-family: var(--mono);
  border: 1px solid;
}
.online-badge.on  { color: var(--green); border-color: rgba(34,197,94,0.3); background: rgba(34,197,94,0.07); }
.online-badge.off { color: var(--accent); border-color: var(--accent-line); background: var(--accent-dim); }

/* ── STATS BAR ─────────────────────────────────────────────────────────────── */
.stats-bar {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1px;
  background: var(--border-soft);
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.stat-tile {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px 24px;
  background: var(--surface);
  transition: background 0.15s ease;
}
.stat-tile:hover { background: var(--surface-2); }
.st-icon        { opacity: 0.6; color: var(--text-dim); flex-shrink: 0; }
.st-icon.green  { color: var(--green); opacity: 0.9; }
.st-icon.red    { color: var(--accent); opacity: 0.9; }
.st-icon.cyan   { color: var(--blue); opacity: 0.9; }
.st-body        { display: flex; flex-direction: column; gap: 3px; }
.st-label       { font-size: 0.6rem; letter-spacing: 0.15em; color: var(--text-muted); text-transform: uppercase; font-family: var(--mono); }
.st-value       { font-size: 1.7rem; font-weight: 700; line-height: 1; color: var(--text); }
.st-value.green { color: var(--green); }
.st-value.red   { color: var(--accent); }
.st-value.cyan  { color: var(--blue); }
.st-value.small { font-size: 0.95rem; font-family: var(--mono); }

/* ── TABS ─────────────────────────────────────────────────────────────────── */
.main-tabs {
  display: flex;
  gap: 0;
  padding: 0 32px;
  border-bottom: 1px solid var(--border);
  background: var(--surface);
  flex-shrink: 0;
}
.main-tab-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  padding: 14px 4px;
  margin-right: 24px;
  margin-bottom: -1px;
  color: var(--text-dim);
  font-family: var(--sans);
  font-size: 0.82rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.18s ease;
}
.main-tab-btn:hover  { color: var(--text); }
.main-tab-btn.active { color: var(--text); border-bottom-color: var(--accent); font-weight: 600; }
.tab-badge {
  background: var(--accent);
  color: white;
  font-size: 0.6rem;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 10px;
}

/* ── DASHBOARD GRID ────────────────────────────────────────────────────────── */
.dashboard-grid {
  flex: 1;
  padding: 24px 32px;
  overflow-y: auto;
  display: flex;
  gap: 24px;
}

/* ── CARDS ──────────────────────────────────────────────────────────────────── */
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.card.full-width { width: 100%; flex: 1; }

.card-header {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 20px;
  border-bottom: 1px solid var(--border-soft);
  background: var(--surface-2);
  flex-shrink: 0;
}
.card-header h3 {
  font-size: 0.88rem;
  font-weight: 600;
  color: var(--text);
  margin: 0;
}
.detection-count,
.log-count,
.last-ts {
  margin-left: auto;
  font-size: 0.68rem;
  color: var(--text-muted);
  letter-spacing: 0.06em;
  text-transform: uppercase;
  font-family: var(--mono);
}
.cam-id {
  font-size: 0.7rem;
  font-weight: 600;
  color: var(--text-dim);
  letter-spacing: 0.06em;
  text-transform: uppercase;
  font-family: var(--mono);
}

.live-indicator {
  color: var(--accent);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  font-family: var(--mono);
  animation: live-blink 1.2s ease-in-out infinite;
}
@keyframes live-blink { 0%,100%{opacity:1} 50%{opacity:0.4} }

/* ── VIDEO ──────────────────────────────────────────────────────────────────── */
.video-wrapper {
  position: relative;
  flex: 1;
  min-height: 400px;
  background: #000;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}
.video-stream {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
  position: absolute;
  inset: 0;
}

.corner {
  position: absolute;
  width: 16px; height: 16px;
  border-color: rgba(220,38,38,0.5);
  border-style: solid;
  z-index: 5;
}
.tl { top: 12px;    left: 12px;    border-width: 2px 0 0 2px; }
.tr { top: 12px;    right: 12px;   border-width: 2px 2px 0 0; }
.bl { bottom: 12px; left: 12px;    border-width: 0 0 2px 2px; }
.br { bottom: 12px; right: 12px;   border-width: 0 2px 2px 0; }

.scanlines {
  position: absolute; inset: 0;
  background-image: repeating-linear-gradient(
    0deg, rgba(0,0,0,0.06) 0px, rgba(0,0,0,0.06) 1px, transparent 1px, transparent 3px
  );
  pointer-events: none;
  z-index: 4;
}

.offline-overlay {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 14px;
  position: absolute; inset: 0;
  background: rgba(11,11,13,0.95);
  color: var(--text-dim);
  z-index: 6;
  text-align: center;
}
.offline-overlay svg { color: var(--accent); opacity: 0.6; }
.offline-title {
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--accent);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  font-family: var(--mono);
}
.offline-sub { font-size: 0.75rem; color: var(--text-muted); }
.offline-sub code {
  color: var(--text-dim);
  background: var(--surface-2);
  padding: 2px 6px;
  border-radius: 3px;
  font-family: var(--mono);
}
.retry-btn {
  margin-top: 6px;
  background: var(--surface-2);
  color: var(--text);
  border: 1px solid var(--border);
  padding: 9px 22px;
  border-radius: 6px;
  font-family: var(--sans);
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.18s ease;
}
.retry-btn:hover { background: var(--surface-3); border-color: var(--accent); color: var(--accent); }

/* ── DETECTED PEOPLE ────────────────────────────────────────────────────────── */
.detected-container {
  padding: 20px;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 14px;
  overflow-y: auto;
  flex: 1;
}

.detected-item {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 16px;
  border: 1px solid var(--border-soft);
  border-radius: 7px;
  background: var(--surface-2);
  transition: border-color 0.18s ease, background 0.18s ease;
}
.detected-item:hover { border-color: var(--border); background: var(--surface-3); }
.detected-item.unknown { border-left: 3px solid var(--accent); }
.detected-item.known   { border-left: 3px solid var(--green); }
.detected-item.scanning { border-left: 3px solid var(--amber); }

.person-avatar {
  width: 42px; height: 42px;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 1rem; font-weight: 700;
  flex-shrink: 0;
  border: 1.5px solid;
}
.person-avatar.known    { background: rgba(34,197,94,0.12);  border-color: rgba(34,197,94,0.4);   color: var(--green); }
.person-avatar.scanning { background: rgba(245,158,11,0.12); border-color: rgba(245,158,11,0.4);  color: var(--amber); }
.person-avatar.unknown  { background: rgba(220,38,38,0.12);  border-color: rgba(220,38,38,0.4);   color: var(--accent); }

.person-info { display: flex; flex-direction: column; gap: 4px; flex: 1; min-width: 0; }
.person-name {
  font-size: 0.875rem; font-weight: 600;
  color: var(--text);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.match-badge {
  display: inline-flex; align-items: center;
  font-size: 0.6rem; font-weight: 700;
  padding: 2px 8px; border-radius: 3px; border: 1px solid;
  text-transform: uppercase; letter-spacing: 0.06em;
  font-family: var(--mono);
  width: fit-content;
}
.match-badge.known    { background: rgba(34,197,94,0.1);  color: var(--green);  border-color: rgba(34,197,94,0.3); }
.match-badge.scanning { background: rgba(245,158,11,0.1); color: var(--amber);  border-color: rgba(245,158,11,0.3); }
.match-badge.unknown  { background: rgba(220,38,38,0.1);  color: var(--accent); border-color: rgba(220,38,38,0.3); }
.coords {
  font-size: 0.6rem; color: var(--text-muted);
  font-family: var(--mono);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}

.add-person-btn {
  display: flex; align-items: center; gap: 6px;
  background: var(--surface-3);
  color: var(--text-dim);
  border: 1px solid var(--border);
  padding: 6px 12px; border-radius: 5px;
  font-family: var(--sans); font-size: 0.75rem; font-weight: 600;
  cursor: pointer; flex-shrink: 0;
  transition: all 0.18s ease;
}
.add-person-btn:hover { color: var(--text); border-color: var(--accent); }

.empty-state {
  grid-column: 1 / -1;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 12px; padding: 60px 20px;
  color: var(--text-muted); text-align: center;
  font-size: 0.875rem;
}
.empty-state svg { opacity: 0.25; }
.empty-sub { font-size: 0.72rem; color: var(--text-muted); opacity: 0.7; }

/* ── LOGS ─────────────────────────────────────────────────────────────────── */
.logs-view {
  padding: 24px 32px;
  overflow-y: auto;
  flex: 1;
}
.logs-card { width: 100%; }
.logs-empty { padding: 80px 20px; }

.table-container { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; }
th {
  background: var(--surface-2);
  padding: 12px 18px;
  font-size: 0.68rem;
  font-weight: 600;
  color: var(--text-dim);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  font-family: var(--mono);
  border-bottom: 1px solid var(--border);
  text-align: left;
  white-space: nowrap;
  position: sticky; top: 0; z-index: 2;
}
td {
  padding: 12px 18px;
  border-bottom: 1px solid var(--border-soft);
  font-size: 0.85rem;
  color: var(--text);
}
tr:hover td { background: var(--surface-2); }
.row-num   { color: var(--text-muted); font-size: 0.72rem; font-family: var(--mono); width: 48px; }
.time-cell { color: var(--text-muted); font-size: 0.78rem; font-family: var(--mono); white-space: nowrap; }

.status-badge {
  display: inline-block;
  padding: 3px 9px; border-radius: 4px;
  font-size: 0.68rem; font-weight: 600;
  text-transform: uppercase; letter-spacing: 0.07em;
  font-family: var(--mono);
  border: 1px solid;
}
.status-badge.authorized { background: rgba(34,197,94,0.1);  color: var(--green);  border-color: rgba(34,197,94,0.3); }
.status-badge.pending    { background: rgba(245,158,11,0.1); color: var(--amber);  border-color: rgba(245,158,11,0.3); }
.status-badge.denied     { background: rgba(220,38,38,0.1);  color: var(--accent); border-color: rgba(220,38,38,0.3); }

/* ── SCROLLBARS ─────────────────────────────────────────────────────────────── */
::-webkit-scrollbar       { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: var(--surface); }
::-webkit-scrollbar-thumb { background: var(--surface-3); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #3a3a42; }

/* ── RESPONSIVE ─────────────────────────────────────────────────────────────── */
@media (max-width: 1100px) {
  .metrics-row  { grid-template-columns: repeat(2, 1fr); }
  .camera-grid  { grid-template-columns: repeat(2, 1fr); }
  .sysmetrics-row { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 700px) {
  .icon-sidebar { width: 48px; min-width: 48px; }
  .metrics-row  { grid-template-columns: 1fr; }
  .camera-grid  { grid-template-columns: 1fr; }
  .sysmetrics-row { grid-template-columns: 1fr; }
  .page-header  { padding: 14px 16px; }
  .page-body    { padding: 14px 12px; }
}
</style>
