<script setup lang="ts">
/// <reference types="vite/client" />
import { ref, computed, onMounted, onUnmounted } from 'vue'
import {
  Menu, X,
  LayoutDashboard, Monitor, ClipboardList, Settings,
  Eye, UserCheck, AlertTriangle, Clock,
  Activity, Wifi, WifiOff, UserPlus
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
  clockTimer = setInterval(() => {
    clock.value = new Date().toLocaleTimeString('en-US', { hour12: false })
  }, 1000)
})

onUnmounted(() => {
  if (pollTimer)  clearInterval(pollTimer)
  if (clockTimer) clearInterval(clockTimer)
})
</script>

<template>
  <div class="dashboard-container">

    <aside class="sidebar" :class="{ 'sidebar-collapsed': !sidebarOpen }">
      <div class="logo">
        <h2>SecureView</h2>
        <span class="logo-tagline">SURVEILLANCE INTELLIGENCE</span>
      </div>

      <div class="sys-status-pill" :class="systemOnline ? 'online' : 'offline'">
        <component :is="systemOnline ? Wifi : WifiOff" :size="13" />
        <span>{{ systemOnline ? 'SYSTEM ONLINE' : 'OFFLINE' }}</span>
      </div>

      <nav>
        <ul>
          <li :class="{ active: currentPage === 'dashboard' }" @click="currentPage = 'dashboard'">
            <component :is="LayoutDashboard" :size="15" class="nav-icon" />
            <span>Dashboard</span>
          </li>
          <li @click="currentPage = 'dashboard'; activeTab = 'live'">
            <component :is="Monitor" :size="15" class="nav-icon" />
            <span>Live Feed</span>
          </li>
          <li :class="{ active: currentPage === 'logs' }" @click="currentPage = 'logs'">
            <component :is="ClipboardList" :size="15" class="nav-icon" />
            <span>Access Logs</span>
          </li>
          <li>
            <component :is="Settings" :size="15" class="nav-icon" />
            <span>Settings</span>
          </li>
        </ul>
      </nav>

      <div class="sidebar-stats">
        <div class="ss-row">
          <span class="ss-label">Detected</span>
          <span class="ss-val">{{ counts.total }}</span>
        </div>
        <div class="ss-row">
          <span class="ss-label">Known</span>
          <span class="ss-val green">{{ counts.known }}</span>
        </div>
        <div class="ss-row">
          <span class="ss-label">Unknown</span>
          <span class="ss-val red">{{ counts.unknown }}</span>
        </div>
        <div class="ss-row">
          <span class="ss-label">Updated</span>
          <span class="ss-val cyan">{{ lastUpdate }}</span>
        </div>
      </div>

      <button
        class="sidebar-toggle-btn"
        @click="toggleSidebar"
        :aria-label="sidebarOpen ? 'Close sidebar' : 'Open sidebar'"
      >
        <X    v-if="sidebarOpen" :size="18" />
        <Menu v-else             :size="18" />
      </button>
    </aside>

    <main class="main-content">
      <header class="top-bar">
        <h1>
          {{ currentPage === 'dashboard' ? 'Dashboard Overview' : 'Recent Access Logs' }}
        </h1>
        <div class="top-bar-right">
          <div class="clock">{{ clock }}</div>
          <div class="online-badge" :class="systemOnline ? 'on' : 'off'">
            <component :is="systemOnline ? Wifi : WifiOff" :size="13" />
            <span>{{ systemOnline ? 'ONLINE' : 'OFFLINE' }}</span>
          </div>
        </div>
      </header>

      <div class="stats-bar">
        <div class="stat-tile">
          <component :is="Eye" :size="20" class="st-icon" />
          <div class="st-body">
            <span class="st-label">DETECTED</span>
            <span class="st-value">{{ counts.total }}</span>
          </div>
        </div>
        <div class="stat-tile">
          <component :is="UserCheck" :size="20" class="st-icon green" />
          <div class="st-body">
            <span class="st-label">IDENTIFIED</span>
            <span class="st-value green">{{ counts.known }}</span>
          </div>
        </div>
        <div class="stat-tile">
          <component :is="AlertTriangle" :size="20" class="st-icon red" />
          <div class="st-body">
            <span class="st-label">UNKNOWN</span>
            <span class="st-value red">{{ counts.unknown }}</span>
          </div>
        </div>
        <div class="stat-tile">
          <component :is="Clock" :size="20" class="st-icon cyan" />
          <div class="st-body">
            <span class="st-label">LAST UPDATE</span>
            <span class="st-value cyan small">{{ lastUpdate }}</span>
          </div>
        </div>
      </div>

      <template v-if="currentPage === 'dashboard'">
        <div class="main-tabs">
          <button :class="['main-tab-btn', { active: activeTab === 'live' }]" @click="activeTab = 'live'">
            <component :is="Monitor" :size="14" />
            Live Feed
          </button>
          <button :class="['main-tab-btn', { active: activeTab === 'detected' }]" @click="activeTab = 'detected'">
            <component :is="Activity" :size="14" />
            Detected People
            <span v-if="detectedPeople.length > 0" class="tab-badge">
              {{ detectedPeople.length }}
            </span>
          </button>
        </div>

        <div class="dashboard-grid">
          <div v-if="activeTab === 'live'" class="card camera-card full-width">
            <div class="card-header">
              <span class="live-indicator">● LIVE</span>
              <span class="cam-id">CAM-01 // MAIN ENTRANCE</span>
              <span class="last-ts">Updated {{ lastUpdate }}</span>
            </div>

            <div class="video-wrapper">
              <div class="corner tl" /><div class="corner tr" />
              <div class="corner bl" /><div class="corner br" />

              <img
                v-if="!streamError"
                :src="STREAM_URL"
                class="video-stream"
                alt="Live surveillance feed"
                @error="streamError = true"
              />

              <div v-else class="offline-overlay">
                <svg xmlns="http://www.w3.org/2000/svg" width="52" height="52" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M23 7l-7 5 7 5V7z"/>
                  <rect x="1" y="5" width="15" height="14" rx="2" ry="2"/>
                  <line x1="1" y1="1" x2="23" y2="23"/>
                </svg>
                <p class="offline-title">STREAM OFFLINE</p>
                <p class="offline-sub">Start <code>multiple_tracking.py</code> then retry</p>
                <button class="retry-btn" @click="streamError = false">
                  ↺ &nbsp;Retry Connection
                </button>
              </div>

              <div class="scanlines" />
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

      <button
        v-if="!sidebarOpen"
        class="sidebar-uncollapse-btn"
        @click="toggleSidebar"
        aria-label="Open sidebar"
      >
        <Menu :size="22" />
      </button>
    </main>
  </div>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;600;700&display=swap');

:root {
  --bg:            #080b10;
  --bg-mid:        #0d1117;
  --bg-light:      #161b22;
  --bg-lighter:    #21262d;
  --indigo:        #6366f1;
  --indigo-bright: #818cf8;
  --indigo-dark:   #4f46e5;
  --neon-red:      #ff3131;
  --red-glow:      rgba(255, 49, 49, 0.35);
  --cyan:          #00d9ff;
  --green:         #22c55e;
  --amber:         #f59e0b;
  --text:          #e1e8ed;
  --text-dim:      #8b95a5;
  --text-muted:    #4b5563;
  --border:        #2d333b;
  --mono:          'IBM Plex Mono', 'JetBrains Mono', monospace;
}

.dashboard-container {
  display: flex;
  height: 100vh;
  overflow: hidden;
  font-family: var(--mono);
  color: var(--text);
  background:
    radial-gradient(ellipse at 20% 50%, rgba(99,102,241,0.07) 0%, transparent 55%),
    radial-gradient(ellipse at 80% 20%, rgba(0,217,255,0.04) 0%, transparent 50%),
    linear-gradient(160deg, var(--bg) 0%, var(--bg-mid) 60%, var(--bg) 100%);
  position: relative;
}

.dashboard-container::before {
  content: '';
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 0;
  background-image:
    linear-gradient(0deg, transparent 24%, rgba(99,102,241,0.045) 25%, rgba(99,102,241,0.045) 26%, transparent 27%,
                    transparent 74%, rgba(99,102,241,0.045) 75%, rgba(99,102,241,0.045) 76%, transparent 77%),
    linear-gradient(90deg, transparent 24%, rgba(99,102,241,0.045) 25%, rgba(99,102,241,0.045) 26%, transparent 27%,
                    transparent 74%, rgba(99,102,241,0.045) 75%, rgba(99,102,241,0.045) 76%, transparent 77%);
  background-size: 50px 50px;
  animation: grid-drift 25s linear infinite;
}
@keyframes grid-drift { to { background-position: 50px 50px; } }

.sidebar {
  width: 260px;
  min-width: 260px;
  background: linear-gradient(180deg, var(--bg-light) 0%, var(--bg-mid) 100%);
  border-right: 2px solid var(--indigo);
  box-shadow: inset -6px 0 24px rgba(99,102,241,0.06), -4px 0 16px rgba(0,0,0,0.5);
  display: flex;
  flex-direction: column;
  position: relative;
  z-index: 10;
  overflow: hidden;
  transition: width 0.32s cubic-bezier(0.4, 0, 0.2, 1),
              min-width 0.32s cubic-bezier(0.4, 0, 0.2, 1),
              opacity 0.25s ease;
}
.sidebar.sidebar-collapsed {
  width: 0;
  min-width: 0;
  opacity: 0;
  pointer-events: none;
}

.sidebar::after {
  content: '';
  position: absolute;
  top: 0; right: 0;
  width: 2px; height: 100%;
  background: linear-gradient(180deg, var(--indigo) 0%, var(--neon-red) 50%, transparent 100%);
  opacity: 0.25;
  animation: shimmer-v 4s ease-in-out infinite;
}
@keyframes shimmer-v { 0%,100%{opacity:0.15} 50%{opacity:0.5} }

.logo {
  padding: 28px 22px 20px;
  border-bottom: 1px solid var(--border);
  background: linear-gradient(135deg, rgba(99,102,241,0.12) 0%, transparent 100%);
  flex-shrink: 0;
}
.logo h2 {
  font-size: 1.35rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--indigo-bright);
  text-shadow: 0 0 22px rgba(99,102,241,0.55);
  animation: logo-pulse 2.5s ease-in-out infinite;
}
@keyframes logo-pulse {
  0%,100% { text-shadow: 0 0 22px rgba(99,102,241,0.55); }
  50%      { text-shadow: 0 0 36px rgba(99,102,241,0.85); }
}
.logo-tagline {
  display: block;
  font-size: 0.6rem;
  letter-spacing: 0.18em;
  color: var(--text-muted);
  margin-top: 4px;
  text-transform: uppercase;
}

.sys-status-pill {
  display: flex;
  align-items: center;
  gap: 7px;
  margin: 14px 16px 4px;
  padding: 7px 12px;
  border-radius: 20px;
  font-size: 0.65rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  border: 1px solid;
  flex-shrink: 0;
  transition: all 0.4s ease;
}
.sys-status-pill.online  { color: var(--green); border-color: rgba(34,197,94,0.4); background: rgba(34,197,94,0.08); }
.sys-status-pill.offline { color: var(--neon-red); border-color: rgba(255,49,49,0.4); background: rgba(255,49,49,0.08); animation: pill-blink 1.5s ease-in-out infinite; }
@keyframes pill-blink { 0%,100%{opacity:1} 50%{opacity:0.6} }

nav { flex-shrink: 0; padding: 8px 0; }
nav ul { list-style: none; }
nav li {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 13px 22px;
  cursor: pointer;
  color: var(--text-dim);
  font-size: 0.82rem;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  border-left: 3px solid transparent;
  transition: all 0.25s ease;
  position: relative;
  overflow: hidden;
}
nav li::before {
  content: '';
  position: absolute;
  top: 0; left: -100%;
  width: 100%; height: 100%;
  background: linear-gradient(90deg, transparent 0%, rgba(99,102,241,0.18) 50%, transparent 100%);
  transition: left 0.5s ease;
}
nav li:hover::before  { left: 100%; }
nav li:hover          { color: var(--indigo-bright); border-left-color: rgba(99,102,241,0.5); background: rgba(99,102,241,0.07); }
nav li.active         { color: var(--indigo-bright); border-left-color: var(--neon-red); background: linear-gradient(90deg, rgba(99,102,241,0.15) 0%, transparent 100%); }
.nav-icon { flex-shrink: 0; opacity: 0.85; }

.sidebar-stats {
  margin: auto 0 0;
  padding: 16px 22px;
  border-top: 1px solid var(--border);
  background: rgba(99,102,241,0.04);
  flex-shrink: 0;
}
.ss-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 5px 0;
  font-size: 0.7rem;
}
.ss-label { color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.08em; }
.ss-val   { font-weight: 700; color: var(--text); }
.ss-val.green { color: var(--green); }
.ss-val.red   { color: var(--neon-red); }
.ss-val.cyan  { color: var(--cyan); font-size: 0.65rem; }

.sidebar-toggle-btn {
  position: relative;
  margin: 0;
  padding: 14px;
  background: linear-gradient(135deg, rgba(99,102,241,0.15) 0%, rgba(99,102,241,0.05) 100%);
  border: 1px solid rgba(99,102,241,0.3);
  border-top: 1px solid var(--border);
  color: var(--indigo-bright);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-family: var(--mono);
  font-size: 0.7rem;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  transition: all 0.25s ease;
  flex-shrink: 0;
}
.sidebar-toggle-btn:hover {
  background: rgba(99,102,241,0.22);
  color: var(--text);
}

.sidebar-uncollapse-btn {
  position: fixed;
  bottom: 28px; left: 24px;
  background: linear-gradient(135deg, rgba(99,102,241,0.2) 0%, rgba(99,102,241,0.08) 100%);
  border: 1px solid rgba(99,102,241,0.45);
  color: var(--indigo-bright);
  cursor: pointer;
  padding: 12px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px; height: 48px;
  z-index: 99;
  transition: all 0.3s ease;
  box-shadow: 0 0 20px rgba(99,102,241,0.2);
}
.sidebar-uncollapse-btn:hover {
  background: rgba(99,102,241,0.3);
  transform: scale(1.1);
  box-shadow: 0 0 32px rgba(99,102,241,0.4);
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative;
  z-index: 5;
  min-width: 0;
}

.top-bar {
  padding: 20px 36px;
  background: linear-gradient(90deg, var(--bg-light) 0%, var(--bg-lighter) 100%);
  border-bottom: 1px solid var(--indigo);
  box-shadow: 0 4px 24px rgba(0,0,0,0.5), 0 0 1px var(--indigo);
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
  position: relative;
  overflow: hidden;
}
.top-bar::before {
  content: '';
  position: absolute;
  top: 0; left: -100%;
  width: 200%; height: 100%;
  background: linear-gradient(90deg, transparent 0%, rgba(99,102,241,0.07) 50%, transparent 100%);
  animation: header-sweep 7s ease-in-out infinite;
}
@keyframes header-sweep { 0%,100%{left:-100%} 50%{left:100%} }
.top-bar h1 {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--indigo-bright);
  letter-spacing: 0.06em;
  text-transform: uppercase;
  text-shadow: 0 0 16px rgba(99,102,241,0.4);
  position: relative; z-index: 2;
}
.top-bar-right {
  display: flex;
  align-items: center;
  gap: 18px;
  position: relative; z-index: 2;
}
.clock {
  font-size: 1rem;
  font-weight: 700;
  color: var(--indigo-bright);
  letter-spacing: 0.12em;
}
.online-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 12px;
  border-radius: 20px;
  font-size: 0.65rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  border: 1px solid;
}
.online-badge.on  { color: var(--green); border-color: rgba(34,197,94,0.4); background: rgba(34,197,94,0.1); }
.online-badge.off { color: var(--neon-red); border-color: rgba(255,49,49,0.4); background: rgba(255,49,49,0.1); }

.stats-bar {
  display: flex;
  gap: 1px;
  background: var(--border);
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.stat-tile {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 22px;
  background: var(--bg-mid);
  transition: background 0.2s ease;
  cursor: default;
}
.stat-tile:hover { background: #0f1520; }
.st-icon       { opacity: 0.8; color: var(--indigo-bright); flex-shrink: 0; }
.st-icon.green { color: var(--green); }
.st-icon.red   { color: var(--neon-red); }
.st-icon.cyan  { color: var(--cyan); }
.st-body       { display: flex; flex-direction: column; gap: 2px; }
.st-label      { font-size: 0.58rem; letter-spacing: 0.2em; color: var(--text-muted); text-transform: uppercase; }
.st-value      { font-size: 1.6rem; font-weight: 700; line-height: 1; color: var(--text); }
.st-value.green { color: var(--green); }
.st-value.red   { color: var(--neon-red); }
.st-value.cyan  { color: var(--cyan); }
.st-value.small { font-size: 0.9rem; }

.main-tabs {
  display: flex;
  gap: 4px;
  padding: 0 36px;
  border-bottom: 2px solid var(--border);
  background: var(--bg-light);
  flex-shrink: 0;
}
.main-tab-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  background: none;
  border: none;
  border-bottom: 3px solid transparent;
  padding: 16px 4px;
  margin-bottom: -2px;
  color: var(--text-dim);
  font-family: var(--mono);
  font-size: 0.82rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  cursor: pointer;
  transition: all 0.25s ease;
  position: relative;
}
.main-tab-btn:hover  { color: var(--indigo-bright); }
.main-tab-btn.active { color: var(--indigo-bright); border-bottom-color: var(--indigo); }
.tab-badge {
  background: var(--neon-red);
  color: white;
  font-size: 0.6rem;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 10px;
  animation: badge-pulse 1.5s ease-in-out infinite;
}
@keyframes badge-pulse { 0%,100%{opacity:1} 50%{opacity:0.65} }

.dashboard-grid {
  flex: 1;
  padding: 28px 36px;
  overflow-y: auto;
  display: flex;
  gap: 28px;
}

.card {
  background: linear-gradient(135deg, var(--bg-light) 0%, var(--bg-lighter) 100%);
  border: 1px solid var(--border);
  border-radius: 8px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.45), 0 0 24px rgba(99,102,241,0.1);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  animation: card-in 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
  opacity: 0;
  position: relative;
}
@keyframes card-in {
  from { opacity:0; transform: translateY(16px) scale(0.97); }
  to   { opacity:1; transform: translateY(0) scale(1); }
}
.card.full-width { width: 100%; flex: 1; }
.card::before {
  content: '';
  position: absolute; inset: 0;
  background: linear-gradient(135deg, rgba(99,102,241,0.08) 0%, transparent 50%);
  border-radius: 8px;
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.3s ease;
}
.card:hover::before { opacity: 1; }

.card-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 18px 22px;
  border-bottom: 1px solid var(--border);
  background: linear-gradient(90deg, rgba(99,102,241,0.08) 0%, transparent 100%);
  flex-shrink: 0;
}
.card-header h3 {
  font-size: 1rem;
  font-weight: 700;
  color: var(--indigo-bright);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin: 0;
  text-shadow: 0 0 10px rgba(99,102,241,0.3);
}
.detection-count,
.log-count,
.last-ts {
  margin-left: auto;
  font-size: 0.68rem;
  color: var(--text-muted);
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
.cam-id {
  font-size: 0.7rem;
  font-weight: 700;
  color: var(--indigo-bright);
  letter-spacing: 0.06em;
  text-transform: uppercase;
  opacity: 0.8;
}

.live-indicator {
  color: var(--neon-red);
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  filter: drop-shadow(0 0 8px rgba(255,49,49,0.7));
  animation: live-blink 1.1s ease-in-out infinite;
}
@keyframes live-blink { 0%,100%{opacity:1} 50%{opacity:0.45} }

.video-wrapper {
  position: relative;
  flex: 1;
  min-height: 420px;
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
  width: 20px; height: 20px;
  border-color: var(--indigo-bright);
  border-style: solid;
  opacity: 0.65;
  z-index: 5;
}
.tl { top: 10px;    left: 10px;    border-width: 2px 0 0 2px; }
.tr { top: 10px;    right: 10px;   border-width: 2px 2px 0 0; }
.bl { bottom: 10px; left: 10px;    border-width: 0 0 2px 2px; }
.br { bottom: 10px; right: 10px;   border-width: 0 2px 2px 0; }

.scanlines {
  position: absolute; inset: 0;
  background-image: repeating-linear-gradient(
    0deg,
    rgba(99,102,241,0.03) 0px, rgba(99,102,241,0.03) 1px,
    transparent 1px, transparent 2px
  );
  pointer-events: none;
  z-index: 4;
  animation: scanline-drift 10s linear infinite;
}
@keyframes scanline-drift { to { background-position: 0 10px; } }

.offline-overlay {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 14px;
  position: absolute; inset: 0;
  background: rgba(8,11,16,0.92);
  color: var(--text-dim);
  z-index: 6;
  text-align: center;
}
.offline-overlay svg { color: var(--neon-red); opacity: 0.7; }
.offline-title {
  font-size: 1rem;
  font-weight: 700;
  color: var(--neon-red);
  letter-spacing: 0.15em;
  text-transform: uppercase;
}
.offline-sub {
  font-size: 0.75rem;
  color: var(--text-muted);
}
.offline-sub code {
  color: var(--indigo-bright);
  background: rgba(99,102,241,0.12);
  padding: 2px 6px;
  border-radius: 3px;
}
.retry-btn {
  margin-top: 6px;
  background: linear-gradient(135deg, var(--indigo) 0%, var(--indigo-dark) 100%);
  color: white;
  border: 1px solid var(--indigo-bright);
  padding: 9px 22px;
  border-radius: 5px;
  font-family: var(--mono);
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  cursor: pointer;
  transition: all 0.25s ease;
}
.retry-btn:hover {
  background: linear-gradient(135deg, var(--indigo-bright) 0%, var(--indigo) 100%);
  box-shadow: 0 0 20px rgba(99,102,241,0.5);
  transform: translateY(-2px);
}

.detected-container {
  padding: 20px;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
  overflow-y: auto;
  flex: 1;
}

.detected-item {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: linear-gradient(135deg, var(--bg-mid) 0%, var(--bg-light) 100%);
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
  position: relative;
  overflow: hidden;
  animation: item-in 0.4s ease-out forwards;
  opacity: 0;
  transform: translateY(12px);
}
@keyframes item-in { to { opacity:1; transform: translateY(0); } }
.detected-item:nth-child(1) { animation-delay: 0.05s; }
.detected-item:nth-child(2) { animation-delay: 0.10s; }
.detected-item:nth-child(3) { animation-delay: 0.15s; }
.detected-item:nth-child(n+4) { animation-delay: 0.20s; }

.detected-item::before {
  content: '';
  position: absolute; top: 0; left: 0; right: 0; height: 2px;
  opacity: 0; transition: opacity 0.3s ease;
}
.detected-item:hover::before { opacity: 1; }
.detected-item.known::before    { background: var(--green); }
.detected-item.scanning::before { background: var(--amber); }
.detected-item.unknown::before  { background: var(--neon-red); }

.detected-item:hover {
  border-color: rgba(99,102,241,0.5);
  transform: translateY(-3px);
  box-shadow: 0 8px 24px rgba(99,102,241,0.2);
}

.person-avatar {
  width: 46px; height: 46px;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 1.1rem; font-weight: 700;
  flex-shrink: 0;
  border: 2px solid;
}
.person-avatar.known    { background: rgba(34,197,94,0.15);  border-color: var(--green);    color: var(--green); }
.person-avatar.scanning { background: rgba(245,158,11,0.15); border-color: var(--amber);    color: var(--amber); }
.person-avatar.unknown  { background: rgba(255,49,49,0.15);  border-color: var(--neon-red); color: var(--neon-red); animation: avatar-pulse 1.5s ease-in-out infinite; }
@keyframes avatar-pulse { 0%,100%{box-shadow:0 0 0 0 rgba(255,49,49,0.3)} 50%{box-shadow:0 0 0 6px rgba(255,49,49,0)} }

.person-info {
  display: flex; flex-direction: column; gap: 5px; flex: 1; min-width: 0;
}
.person-name {
  font-size: 0.9rem; font-weight: 700;
  color: var(--indigo-bright);
  text-transform: uppercase; letter-spacing: 0.05em;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.match-badge {
  display: inline-flex; align-items: center;
  font-size: 0.62rem; font-weight: 700;
  padding: 3px 8px; border-radius: 3px; border: 1px solid;
  text-transform: uppercase; letter-spacing: 0.06em;
  width: fit-content;
}
.match-badge.known    { background: rgba(34,197,94,0.15);  color: var(--green);    border-color: var(--green); }
.match-badge.scanning { background: rgba(245,158,11,0.15); color: var(--amber);    border-color: var(--amber); }
.match-badge.unknown  { background: rgba(255,49,49,0.15);  color: var(--neon-red); border-color: var(--neon-red); }
.coords {
  font-size: 0.6rem; color: var(--text-muted);
  letter-spacing: 0.04em; font-family: var(--mono);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}

.add-person-btn {
  display: flex; align-items: center; gap: 6px;
  background: linear-gradient(135deg, var(--indigo) 0%, var(--indigo-dark) 100%);
  color: white;
  border: 1px solid var(--indigo-bright);
  padding: 7px 12px; border-radius: 4px;
  font-family: var(--mono); font-size: 0.72rem; font-weight: 700;
  letter-spacing: 0.06em; text-transform: uppercase;
  cursor: pointer; flex-shrink: 0;
  transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.add-person-btn:hover {
  background: linear-gradient(135deg, var(--indigo-bright) 0%, var(--indigo) 100%);
  box-shadow: 0 0 18px rgba(99,102,241,0.5);
  transform: translateY(-2px);
}

.empty-state {
  grid-column: 1 / -1;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 12px; padding: 60px 20px;
  color: var(--text-muted); text-align: center;
  font-size: 0.9rem; letter-spacing: 0.04em;
}
.empty-state svg { opacity: 0.35; }
.empty-sub { font-size: 0.72rem; color: var(--text-muted); opacity: 0.7; }

.logs-view {
  padding: 28px 36px;
  overflow-y: auto;
  flex: 1;
  animation: page-in 0.4s ease-out forwards;
  opacity: 0;
}
@keyframes page-in { to { opacity:1; } }

.logs-card { width: 100%; animation-delay: 0.1s; }
.logs-empty { padding: 80px 20px; }

.table-container {
  overflow-x: auto;
  border-top: 1px solid var(--border);
}
table { width: 100%; border-collapse: collapse; }
th {
  background: linear-gradient(90deg, rgba(99,102,241,0.14) 0%, rgba(0,217,255,0.05) 100%);
  padding: 14px 20px;
  font-size: 0.72rem; font-weight: 700;
  color: var(--indigo-bright);
  text-transform: uppercase; letter-spacing: 0.1em;
  border-bottom: 2px solid var(--indigo);
  border-right: 1px solid var(--border);
  white-space: nowrap;
  position: sticky; top: 0; z-index: 2;
}
th:last-child { border-right: none; }
td {
  padding: 13px 20px;
  border-bottom: 1px solid var(--border);
  font-size: 0.85rem; color: var(--text);
  transition: color 0.2s ease;
}
tr { transition: background 0.2s ease; }
tr:hover { background: rgba(99,102,241,0.07); }
tr:hover td { color: var(--indigo-bright); }
.row-num { color: var(--text-muted); font-size: 0.75rem; width: 48px; }
.time-cell { color: var(--text-muted); font-size: 0.8rem; white-space: nowrap; }

.status-badge {
  display: inline-block;
  padding: 4px 10px; border-radius: 4px;
  font-size: 0.7rem; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.08em;
  border: 1px solid;
}
.status-badge.authorized {
  background: rgba(34,197,94,0.15); color: var(--green); border-color: var(--green);
  box-shadow: 0 0 10px rgba(34,197,94,0.2);
}
.status-badge.pending {
  background: rgba(245,158,11,0.15); color: var(--amber); border-color: var(--amber);
}
.status-badge.denied {
  background: rgba(255,49,49,0.15); color: var(--neon-red); border-color: var(--neon-red);
  box-shadow: 0 0 10px rgba(255,49,49,0.25);
  animation: denied-pulse 1.5s ease-in-out infinite;
}
@keyframes denied-pulse { 0%,100%{box-shadow: 0 0 10px rgba(255,49,49,0.25)} 50%{box-shadow: 0 0 18px rgba(255,49,49,0.45)} }

::-webkit-scrollbar       { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--bg-mid); }
::-webkit-scrollbar-thumb { background: var(--indigo); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--indigo-bright); }

@media (max-width: 900px) {
  .sidebar { width: 220px; min-width: 220px; }
  .dashboard-grid, .logs-view { padding: 18px 20px; }
  .top-bar { padding: 16px 20px; }
  .top-bar h1 { font-size: 1.1rem; }
  .stat-tile { padding: 12px 14px; }
  .st-value  { font-size: 1.3rem; }
  .stats-bar { overflow-x: auto; }
  .main-tabs { padding: 0 20px; }
}

@media (max-width: 600px) {
  .sidebar.sidebar-collapsed { display: none; }
  .stats-bar { display: grid; grid-template-columns: 1fr 1fr; }
  .top-bar-right .clock { display: none; }
}
</style>