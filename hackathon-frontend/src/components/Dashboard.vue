<script setup lang="ts">
/// <reference types="vite/client" />
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useAuth0 } from '@auth0/auth0-vue';
import {
  Menu, X, Trash2, Bot, Database, ImagePlus,
  LayoutDashboard, Monitor, ClipboardList, Settings,
  Eye, UserCheck, AlertTriangle, Clock,
  Activity, Wifi, WifiOff, UserPlus, Users,
  Bell, Camera, Signal, Shield, BarChart2, Calendar, CloudUpload, Zap,
  Pause, Play, RefreshCw, ChevronRight, Radio, Cpu, Lock
} from 'lucide-vue-next'
import ActivityAnalyzer from './ActivityAnalyzer.vue'

const { loginWithRedirect, logout, isAuthenticated, user, isLoading } = useAuth0();
const logoutRedirectUri = import.meta.env.VITE_AUTH0_REDIRECT_URI;

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
const currentPage = ref<'dashboard' | 'logs' | 'activity' | 'signal' | 'monitor' | 'shield'>('dashboard')
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
const STREAM_URL = '/live'
const DATA_URL   = '/data'
const streamError    = ref(false)
const streamPaused   = ref(false)
const streamRefreshKey = ref(Date.now())

function retryStream(): void {
  streamError.value    = false
  streamPaused.value   = false
  streamRefreshKey.value = Date.now()
}
function toggleStreamPause(): void {
  streamPaused.value = !streamPaused.value
}

// ── Notifications panel ───────────────────────────────────────────────────────
const showNotificationsPanel = ref(false)

const recentAlerts = computed(() =>
  [...apiAlerts.value].reverse().slice(0, 30)
)
const unreadAlertCount = computed(() =>
  apiAlerts.value.filter(a => a.type === 'UNKNOWN').slice(-50).length
)

// ── Settings modal ────────────────────────────────────────────────────────────
const showSettingsModal    = ref(false)
const settingPollingMs     = ref(250)
const settingStreamQuality = ref<'HD' | 'SD'>('HD')
const settingAutoAlert     = ref(true)
const settingDarkMode      = ref(true)
let   pollTimer:  ReturnType<typeof setInterval> | null = null
let   clockTimer: ReturnType<typeof setInterval> | null = null

function applySettings(): void {
  // Re-start polling with new interval
  if (pollTimer) clearInterval(pollTimer)
  pollTimer = setInterval(pollData, settingPollingMs.value)
  localStorage.setItem('settingPollingMs',     String(settingPollingMs.value))
  localStorage.setItem('settingStreamQuality', settingStreamQuality.value)
  localStorage.setItem('settingAutoAlert',     String(settingAutoAlert.value))
  showSettingsModal.value = false
}

// ── Computed: detected people ─────────────────────────────────────────────────
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

// ── Computed: access log rows ─────────────────────────────────────────────────
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

// ── Data polling ──────────────────────────────────────────────────────────────
async function pollData(): Promise<void> {
  try {
    const res = await fetch(DATA_URL, { cache: 'no-store' })
    if (!res.ok) throw new Error('Non-OK response')
    const d: ApiPayload = await res.json()
    errorCount.value    = 0
    systemOnline.value  = !d._offline
    counts.value        = d.counts  ?? { known: 0, unknown: 0, total: 0 }
    knownFaces.value    = d.known   ?? []
    unknownFaces.value  = d.unknown ?? []
    apiAlerts.value     = (d.alerts ?? []).slice(-200)
    if (d.timestamp) {
      lastUpdate.value = new Date(d.timestamp * 1000).toLocaleTimeString('en-US', { hour12: false })
      frameTs.value    = d.timestamp
    }
  } catch {
    errorCount.value++
    if (errorCount.value > 4) systemOnline.value = false
  }
}

// ── People modal ──────────────────────────────────────────────────────────────
const showPeopleModal = ref(false)
const frameTs         = ref(0)

function faceImgUrl(coords: FaceCoords | null): string {
  if (!coords) return ''
  const { x, y, w, h } = coords
  return `/face_crop?x=${x}&y=${y}&w=${w}&h=${h}&t=${frameTs.value}`
}

const inDatabasePeople = computed(() =>
  knownFaces.value
    .filter(p => p.name !== 'SCANNING...')
    .map((p, i) => ({ id: `k-${i}`, name: p.name, coords: p.coords }))
)
const notInDatabasePeople = computed(() =>
  unknownFaces.value.map((u, i) => ({ id: `u-${i}`, coords: u }))
)

// ── Face Database Modal ───────────────────────────────────────────────────────
interface FaceDbEntry { filename: string; name: string; dataUrl: string }
const showFaceDbModal    = ref(false)
const faceDbEntries      = ref<FaceDbEntry[]>([])
const faceDbLoading      = ref(false)
const faceDbDragOver     = ref(false)
const faceDbUploadStatus = ref<string | null>(null)

async function openFaceDb(): Promise<void> {
  showFaceDbModal.value = true
  await fetchFaceDb()
}
async function fetchFaceDb(): Promise<void> {
  faceDbLoading.value = true
  try {
    const res = await fetch('/face_db', { cache: 'no-store' })
    faceDbEntries.value = res.ok ? await res.json() : []
  } catch {
    faceDbEntries.value = []
  } finally {
    faceDbLoading.value = false
  }
}
async function deleteFaceDbEntry(filename: string): Promise<void> {
  await fetch(`/face_db/${encodeURIComponent(filename)}`, { method: 'DELETE' })
  await fetchFaceDb()
}
function onFaceDbDragOver(e: DragEvent): void { e.preventDefault(); faceDbDragOver.value = true }
function onFaceDbDragLeave(): void { faceDbDragOver.value = false }
async function onFaceDbDrop(e: DragEvent): Promise<void> {
  e.preventDefault()
  faceDbDragOver.value = false
  const files = Array.from(e.dataTransfer?.files ?? []).filter(f => f.type.startsWith('image/'))
  await uploadFaceDbFiles(files)
}
async function onFaceDbFileInput(e: Event): Promise<void> {
  const files = Array.from((e.target as HTMLInputElement).files ?? []).filter(f => f.type.startsWith('image/'))
  await uploadFaceDbFiles(files)
}
async function uploadFaceDbFiles(files: File[]): Promise<void> {
  if (!files.length) return
  faceDbUploadStatus.value = `Uploading ${files.length} file${files.length !== 1 ? 's' : ''}…`
  const fd = new FormData()
  files.forEach(f => fd.append('images', f, f.name))
  await fetch('/face_db/upload', { method: 'POST', body: fd })
  faceDbUploadStatus.value = null
  await fetchFaceDb()
}

// ── Copilot AI Analysis ───────────────────────────────────────────────────────
const showCopilotModal = ref(false)
const copilotLoading   = ref(false)
const copilotResult    = ref<string | null>(null)
const copilotSubject   = ref<string>('')
const copilotError     = ref<string | null>(null)

async function analyzWithCopilot(person: { name: string; coords: FaceCoords | null }): Promise<void> {
  copilotSubject.value   = person.name
  copilotResult.value    = null
  copilotError.value     = null
  copilotLoading.value   = true
  showCopilotModal.value = true
  try {
    const res = await fetch('/copilot/analyze', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ subject: person.name, coords: person.coords }),
    })
    const data = await res.json()
    if (!res.ok || data.error) throw new Error(data.error ?? 'Request failed')
    copilotResult.value = data.analysis
  } catch (err: any) {
    copilotError.value = err.message ?? 'Analysis failed'
  } finally {
    copilotLoading.value = false
  }
}

// ── Sidebar toggle ────────────────────────────────────────────────────────────
function toggleSidebar(): void {
  sidebarOpen.value = !sidebarOpen.value
  localStorage.setItem('sidebarOpen', String(sidebarOpen.value))
}

// ── Lifecycle ─────────────────────────────────────────────────────────────────
onMounted(() => {
  const saved = localStorage.getItem('sidebarOpen')
  if (saved !== null) sidebarOpen.value = saved === 'true'
  const savedPolling = localStorage.getItem('settingPollingMs')
  if (savedPolling) settingPollingMs.value = Number(savedPolling)
  const savedQuality = localStorage.getItem('settingStreamQuality') as 'HD' | 'SD' | null
  if (savedQuality) settingStreamQuality.value = savedQuality
  const savedAutoAlert = localStorage.getItem('settingAutoAlert')
  if (savedAutoAlert !== null) settingAutoAlert.value = savedAutoAlert === 'true'

  pollData()
  pollTimer  = setInterval(pollData, settingPollingMs.value)
  const tick = () => {
    const now = new Date()
    clock.value       = now.toLocaleTimeString('en-US', { hour12: false })
    currentDate.value = now.toLocaleDateString('en-CA')
  }
  tick()
  clockTimer = setInterval(tick, 1000)
})

onUnmounted(() => {
  if (pollTimer)      clearInterval(pollTimer)
  if (clockTimer)     clearInterval(clockTimer)
  if (_retryTimer)    clearTimeout(_retryTimer)
  if (_countdownTimer) clearInterval(_countdownTimer)
})
</script>

<template>
  <div class="app-shell">

    <!-- ── NARROW ICON SIDEBAR ──────────────────────────────────── -->
    <nav class="icon-sidebar">
      <!-- System label (no logo) -->
      <div class="sidebar-brand">
        <span class="sys-label">SV<span class="sys-dot">·</span>1</span>
        <span class="sys-status-dot" :class="systemOnline ? 'online' : 'offline'"></span>
      </div>

      <ul class="nav-icons">
        <li :class="{ active: currentPage === 'dashboard' }"
            @click="currentPage = 'dashboard'; activeTab = 'live'"
            title="Dashboard">
          <component :is="LayoutDashboard" :size="20" />
        </li>

        <li :class="{ active: showFaceDbModal }"
            @click="openFaceDb()"
            title="Face Database">
          <component :is="Camera" :size="20" />
        </li>

        <li :class="{ active: currentPage === 'dashboard' && activeTab === 'detected' }"
            @click="currentPage = 'dashboard'; activeTab = 'detected'"
            title="Detections">
          <component :is="Eye" :size="20" />
        </li>

        <li :class="{ active: currentPage === 'logs' }"
            @click="currentPage = 'logs'"
            title="Access Logs">
          <component :is="ClipboardList" :size="20" />
        </li>

        <li :class="{ active: currentPage === 'activity' }"
            @click="currentPage = 'activity'"
            title="Copilot Activity Analysis">
          <component :is="Zap" :size="20" />
        </li>

        <li :class="{ active: currentPage === 'signal' }"
            @click="currentPage = 'signal'"
            title="Signal Intelligence">
          <component :is="Signal" :size="20" />
        </li>

        <li :class="{ active: currentPage === 'monitor' }"
            @click="currentPage = 'monitor'"
            title="System Monitor">
          <component :is="Monitor" :size="20" />
        </li>

        <li :class="{ active: currentPage === 'shield' }"
            @click="currentPage = 'shield'"
            title="Threat Shield">
          <component :is="Shield" :size="20" />
        </li>
      </ul>

      <ul class="nav-icons nav-icons-bottom">
        <li @click="showSettingsModal = true" title="Settings">
          <component :is="Settings" :size="20" />
        </li>
      </ul>
    </nav>

    <!-- ── MAIN AREA ─────────────────────────────────────────────── -->
    <main class="main-area">

      <!-- Page header -->
      <header class="page-header">
        <div class="ph-left">
          <div class="ph-breadcrumb">
            <span class="ph-system">SENTINEL</span>
            <component :is="ChevronRight" :size="12" class="ph-sep" />
            <span class="ph-page">
              <span v-if="currentPage === 'dashboard'">Dashboard</span>
              <span v-else-if="currentPage === 'logs'">Access Logs</span>
              <span v-else-if="currentPage === 'activity'">Activity Analysis</span>
              <span v-else-if="currentPage === 'signal'">Signal Intel</span>
              <span v-else-if="currentPage === 'monitor'">System Monitor</span>
              <span v-else>Threat Shield</span>
            </span>
          </div>
          <h1 v-if="currentPage === 'dashboard'">Dashboard</h1>
          <h1 v-else-if="currentPage === 'logs'">Access Logs</h1>
          <h1 v-else-if="currentPage === 'activity'">Copilot Activity Analysis</h1>
          <h1 v-else-if="currentPage === 'signal'">Signal Intelligence</h1>
          <h1 v-else-if="currentPage === 'monitor'">System Monitor</h1>
          <h1 v-else>Threat Shield</h1>
          <p class="ph-sub">
            <span v-if="isAuthenticated">Operator: <strong>{{ user.name }}</strong></span>
            <span v-else>Operator: <strong>SecureView</strong></span>
            &nbsp;·&nbsp;
            <span :class="['ph-status', systemOnline ? 'online' : 'offline']">
              {{ systemOnline ? '● ONLINE' : '● OFFLINE' }}
            </span>
          </p>
        </div>

        <div class="ph-right">
          <!-- Everyone modal trigger -->
          <button @click="showPeopleModal = true" class="hdr-icon-btn everyone" title="Everyone Detected">
            <component :is="Users" :size="18" />
          </button>

          <!-- Notifications bell with badge -->
          <button
            class="hdr-icon-btn notif-btn"
            :class="{ active: showNotificationsPanel }"
            title="Notifications"
            @click="showNotificationsPanel = !showNotificationsPanel"
          >
            <component :is="Bell" :size="18" />
            <span v-if="unreadAlertCount > 0" class="notif-badge">{{ unreadAlertCount > 99 ? '99+' : unreadAlertCount }}</span>
          </button>

          <!-- Auth area -->
          <div v-if="isLoading">
            <button class="hdr-icon-btn" title="Loading…">
              <div class="auth-spinner"></div>
            </button>
          </div>
          <div v-else-if="isAuthenticated" class="auth-area">
            <img :src="user.picture" :alt="user.name" class="user-avatar" />
            <button
              @click="logout({ logoutParams: { returnTo: logoutRedirectUri }})"
              class="hdr-icon-btn logout-btn"
              title="Logout"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
                <polyline points="16 17 21 12 16 7"></polyline>
                <line x1="21" y1="12" x2="9" y2="12"></line>
              </svg>
            </button>
          </div>
          <button v-else @click="loginWithRedirect()" class="hdr-icon-btn login-btn" title="Login">
            <component :is="UserPlus" :size="18" />
          </button>
        </div>
      </header>

      <!-- ── NOTIFICATIONS PANEL ─────────────────────────────────── -->
      <Transition name="notif-slide">
        <div v-if="showNotificationsPanel" class="notif-panel">
          <div class="notif-panel-header">
            <span class="notif-panel-title">
              <component :is="Bell" :size="14" />
              Threat Notifications
            </span>
            <span class="notif-panel-count">{{ recentAlerts.length }} events</span>
            <button class="notif-panel-close" @click="showNotificationsPanel = false">
              <component :is="X" :size="16" />
            </button>
          </div>
          <div class="notif-panel-body">
            <div v-if="recentAlerts.length === 0" class="notif-empty">
              <component :is="Shield" :size="28" />
              <p>No alerts recorded</p>
            </div>
            <div
              v-for="(alert, i) in recentAlerts"
              :key="i"
              :class="['notif-item', alert.type === 'UNKNOWN' ? 'threat' : 'clear']"
            >
              <div class="notif-icon">
                <component :is="alert.type === 'UNKNOWN' ? AlertTriangle : UserCheck" :size="14" />
              </div>
              <div class="notif-content">
                <span class="notif-name">{{ alert.name === 'INTRUDER' ? 'Unknown Person' : alert.name }}</span>
                <span :class="['notif-type', alert.type === 'UNKNOWN' ? 'threat' : 'clear']">
                  {{ alert.type === 'UNKNOWN' ? 'ACCESS DENIED' : 'AUTHORIZED' }}
                </span>
              </div>
              <span class="notif-time">{{ alert.time }}</span>
            </div>
          </div>
        </div>
      </Transition>

      <div class="page-body">

        <!-- ── 4 STAT CARDS ─────────────────────────────────────── -->
        <div class="metrics-row">
          <!-- Clock / date -->
          <div class="metric-card clock-card">
            <div class="mc-clock-label">SYS CLOCK</div>
            <div class="mc-clock">{{ clock }}</div>
            <div class="mc-date">
              <component :is="Calendar" :size="11" />
              {{ currentDate }}
            </div>
          </div>

          <!-- Last update -->
          <div class="metric-card">
            <div class="mc-label">Last Frame</div>
            <div class="mc-dual">
              <div class="mc-dual-val">{{ lastUpdate }}</div>
            </div>
            <div class="mc-sublabel">PROCESSING TIME</div>
          </div>

          <!-- Status -->
          <div class="metric-card status-card">
            <div class="mc-label">System Status</div>
            <div class="mc-status-body">
              <component :is="CloudUpload" :size="28" :class="['mc-status-icon', systemOnline ? 'green' : 'red']" />
              <div :class="['mc-status-text', systemOnline ? 'green' : 'red']">
                {{ systemOnline ? 'Online' : 'Offline' }}
              </div>
              <div class="mc-status-ver">v1.0-alpha</div>
            </div>
          </div>

          <!-- Detection summary -->
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

        <!-- ═════════════════════════════════════════════════════════ -->
        <!--                     DASHBOARD PAGE                       -->
        <!-- ═════════════════════════════════════════════════════════ -->
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

            <!-- CAM-01 LIVE -->
            <div class="cam-card" :class="{ 'cam-live': systemOnline && !streamError && !streamPaused }">
              <div class="cam-header">
                <span class="cam-name">CAM-01 · Main Entrance</span>
                <span class="cam-live-badge" v-if="systemOnline && !streamError && !streamPaused">● LIVE</span>
                <span v-if="streamPaused" class="cam-paused-badge">⏸ PAUSED</span>
                <span :class="['cam-dot', systemOnline && !streamError ? 'online' : 'offline']"></span>
              </div>
              <div class="cam-body">
                <!-- Scanline overlay -->
                <div class="scanlines"></div>
                <!-- Corner brackets -->
                <div class="corner tl"></div>
                <div class="corner tr"></div>
                <div class="corner bl"></div>
                <div class="corner br"></div>

                <img
                  v-if="!streamError && !streamPaused"
                  :src="`${STREAM_URL}?k=${streamRefreshKey}`"
                  class="cam-stream"
                  alt="Live feed"
                  @error="streamError = true"
                />
                <div v-if="streamPaused && !streamError" class="cam-pause-overlay">
                  <component :is="Pause" :size="40" />
                  <p>STREAM PAUSED</p>
                  <button @click="toggleStreamPause">▶ Resume</button>
                </div>
                <div v-if="streamError" class="cam-offline-overlay">
                  <svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M23 7l-7 5 7 5V7z"/>
                    <rect x="1" y="5" width="15" height="14" rx="2" ry="2"/>
                    <line x1="1" y1="1" x2="23" y2="23"/>
                  </svg>
                  <p>STREAM OFFLINE</p>
                  <button @click="retryStream">↺ Retry</button>
                </div>
              </div>
              <div class="cam-footer">
                <span class="cam-ts">Updated {{ lastUpdate }}</span>
                <button
                  class="cam-ctrl-btn"
                  :title="streamPaused ? 'Resume stream' : 'Pause stream'"
                  @click="toggleStreamPause"
                >
                  <component :is="streamPaused ? Play : Pause" :size="12" />
                </button>
                <button class="cam-ctrl-btn" title="Refresh stream" @click="retryStream">
                  <component :is="RefreshCw" :size="12" />
                </button>
              </div>
            </div>

            <!-- CAM-02 PLACEHOLDER -->
            <div class="cam-card">
              <div class="cam-header">
                <span class="cam-name">CAM-02 · Entrance</span>
                <span class="cam-dot offline"></span>
              </div>
              <div class="cam-body cam-placeholder">
                <div class="scanlines"></div>
                <component :is="Camera" :size="32" class="cam-ph-icon" />
                <span class="cam-ph-label">NOT CONNECTED</span>
              </div>
              <div class="cam-footer">
                <span class="cam-ts">No signal</span>
                <button class="cam-ctrl-btn" title="Pause" disabled>
                  <component :is="Pause" :size="12" />
                </button>
                <button class="cam-ctrl-btn" title="Attempt reconnection" @click="retryStream">
                  <component :is="RefreshCw" :size="12" />
                </button>
              </div>
            </div>

          <!-- ── INLINE PEOPLE PANEL (replaces CAM-03) ──────── -->
          <div class="cam-card people-inline-card">
            <div class="cam-header">
              <span class="cam-name">Detected · In Frame</span>
              <span class="ipl-badge" :class="detectedPeople.length > 0 ? 'active' : ''">
                {{ detectedPeople.length }}
              </span>
            </div>

            <div class="ipl-body">
              <!-- Empty state -->
              <div v-if="detectedPeople.length === 0" class="ipl-empty">
                <component :is="Eye" :size="30" />
                <span>No faces in frame</span>
              </div>

              <!-- People list -->
              <div v-else class="ipl-list">
                <div
                  v-for="person in detectedPeople"
                  :key="person.id"
                  :class="['ipl-item', person.type]"
                >
                  <!-- Face crop thumbnail -->
                  <div :class="['ipl-avatar', person.type]">
                    <img
                      v-if="person.coords"
                      :src="faceImgUrl(person.coords)"
                      class="ipl-face-img"
                      alt=""
                      @error="(e: Event) => ((e.target as HTMLImageElement).style.display = 'none')"
                    />
                    <span class="ipl-avatar-letter">
                      {{ person.type === 'unknown' ? '?' : person.type === 'scanning' ? '…' : person.name.charAt(0) }}
                    </span>
                  </div>

                  <div class="ipl-info">
                    <span class="ipl-name">{{ person.name }}</span>
                    <span :class="['ipl-chip', person.type]">
                      <span v-if="person.type === 'known'">✓ VERIFIED</span>
                      <span v-else-if="person.type === 'scanning'">⟳ SCANNING</span>
                      <span v-else>✗ UNKNOWN</span>
                    </span>
                  </div>

                  <button
                    class="ipl-ai-btn"
                    title="Analyze with Copilot"
                    @click="analyzWithCopilot(person)"
                  >
                    <component :is="Bot" :size="12" />
                  </button>
                </div>
              </div>
            </div>

            <div class="cam-footer">
              <span class="cam-ts">Updated {{ lastUpdate }}</span>
              <span class="ipl-summary">
                <span class="green">{{ counts.known }} id</span>
                &nbsp;·&nbsp;
                <span class="red">{{ counts.unknown }} unk</span>
              </span>
            </div>
          </div>
        </div>

          <!-- ── SYSTEM METRICS ROW ────────────── -->
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

          <!-- Detected People tab -->
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
                <div class="detected-top">
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
                </div>

                <div class="detected-actions">
                  <button v-if="person.type === 'unknown'" class="add-person-btn">
                    <component :is="UserPlus" :size="14" />
                    Enroll
                  </button>
                  <button
                    class="analyze-ai-btn"
                    title="Analyze with Microsoft Copilot"
                    @click="analyzWithCopilot(person)"
                  >
                    <component :is="Bot" :size="14" />
                    Analyze
                  </button>
                </div>
              </div>
            </div>
          </div>
        </template>

        <!-- ═════════════════════════════════════════════════════════ -->
        <!--                      LOGS PAGE                           -->
        <!-- ═════════════════════════════════════════════════════════ -->
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

        <!-- ═════════════════════════════════════════════════════════ -->
        <!--                    ACTIVITY PAGE                         -->
        <!-- ═════════════════════════════════════════════════════════ -->
        <template v-if="currentPage === 'activity'">
          <div class="activity-view">
            <ActivityAnalyzer />
          </div>
        </template>

        <!-- ═════════════════════════════════════════════════════════ -->
        <!--                   SIGNAL INTEL PAGE                      -->
        <!-- ═════════════════════════════════════════════════════════ -->
        <template v-if="currentPage === 'signal'">
          <div class="dev-page">
            <div class="dev-card">
              <div class="dev-icon-wrap signal">
                <component :is="Radio" :size="48" />
              </div>
              <div class="dev-tag">MODULE · SIGNAL INTEL</div>
              <h2 class="dev-title">Signal Intelligence</h2>
              <p class="dev-desc">
                Real-time RF spectrum monitoring, wireless intrusion detection, and
                signal-source triangulation are currently being integrated into the
                Sentinel platform.
              </p>
              <div class="dev-features">
                <div class="dev-feature"><span class="dev-check">◈</span> RF Spectrum Analysis</div>
                <div class="dev-feature"><span class="dev-check">◈</span> Wireless Intrusion Detection</div>
                <div class="dev-feature"><span class="dev-check">◈</span> Bluetooth / BLE Tracking</div>
                <div class="dev-feature"><span class="dev-check">◈</span> Signal Source Triangulation</div>
              </div>
              <div class="dev-status-bar">
                <span class="dev-status-label">DEVELOPMENT STATUS</span>
                <div class="dev-progress-track"><div class="dev-progress-fill" style="width: 42%"></div></div>
                <span class="dev-progress-pct">42%</span>
              </div>
            </div>
          </div>
        </template>

        <!-- ═════════════════════════════════════════════════════════ -->
        <!--                  SYSTEM MONITOR PAGE                     -->
        <!-- ═════════════════════════════════════════════════════════ -->
        <template v-if="currentPage === 'monitor'">
          <div class="dev-page">
            <div class="dev-card">
              <div class="dev-icon-wrap monitor">
                <component :is="Cpu" :size="48" />
              </div>
              <div class="dev-tag">MODULE · SYSTEM MONITOR</div>
              <h2 class="dev-title">System Monitor</h2>
              <p class="dev-desc">
                Full hardware telemetry, GPU utilization dashboards, thermal management,
                and process-level performance profiling coming to the Sentinel platform.
              </p>
              <div class="dev-features">
                <div class="dev-feature"><span class="dev-check">◈</span> CPU / GPU Utilization</div>
                <div class="dev-feature"><span class="dev-check">◈</span> Memory & Thermal Telemetry</div>
                <div class="dev-feature"><span class="dev-check">◈</span> Network I/O Monitoring</div>
                <div class="dev-feature"><span class="dev-check">◈</span> Process Health Dashboard</div>
              </div>
              <div class="dev-status-bar">
                <span class="dev-status-label">DEVELOPMENT STATUS</span>
                <div class="dev-progress-track"><div class="dev-progress-fill monitor" style="width: 67%"></div></div>
                <span class="dev-progress-pct">67%</span>
              </div>
            </div>
          </div>
        </template>

        <!-- ═════════════════════════════════════════════════════════ -->
        <!--                   THREAT SHIELD PAGE                     -->
        <!-- ═════════════════════════════════════════════════════════ -->
        <template v-if="currentPage === 'shield'">
          <div class="dev-page">
            <div class="dev-card">
              <div class="dev-icon-wrap shield">
                <component :is="Lock" :size="48" />
              </div>
              <div class="dev-tag">MODULE · THREAT SHIELD</div>
              <h2 class="dev-title">Threat Shield</h2>
              <p class="dev-desc">
                Automated threat classification, perimeter breach alerting, multi-zone
                security rules, and active countermeasure orchestration planned for
                the next Sentinel release.
              </p>
              <div class="dev-features">
                <div class="dev-feature"><span class="dev-check">◈</span> Automated Threat Classification</div>
                <div class="dev-feature"><span class="dev-check">◈</span> Perimeter Breach Alerting</div>
                <div class="dev-feature"><span class="dev-check">◈</span> Multi-Zone Security Rules</div>
                <div class="dev-feature"><span class="dev-check">◈</span> Countermeasure Orchestration</div>
              </div>
              <div class="dev-status-bar">
                <span class="dev-status-label">DEVELOPMENT STATUS</span>
                <div class="dev-progress-track"><div class="dev-progress-fill shield" style="width: 28%"></div></div>
                <span class="dev-progress-pct">28%</span>
              </div>
            </div>
          </div>
        </template>

      </div><!-- /page-body -->
    </main>

    <!-- ── PEOPLE MODAL ─────────────────────────────────────────── -->
    <Teleport to="body">
      <div v-if="showPeopleModal" class="people-modal-backdrop" @click.self="showPeopleModal = false">
        <div class="people-modal">
          <div class="pm-header">
            <h2>Everyone Detected</h2>
            <button class="pm-close" @click="showPeopleModal = false">
              <component :is="X" :size="18" />
            </button>
          </div>
          <div class="pm-body">
            <section class="pm-section">
              <div class="pm-section-title in-db">
                <component :is="UserCheck" :size="15" />
                In Database
                <span class="pm-count">{{ inDatabasePeople.length }}</span>
              </div>
              <div v-if="inDatabasePeople.length === 0" class="pm-empty">No recognised faces in frame</div>
              <div v-else class="pm-list">
                <div v-for="p in inDatabasePeople" :key="p.id" class="pm-item in-db">
                  <div class="pm-avatar in-db">
                    <img
                      v-if="p.coords"
                      :src="faceImgUrl(p.coords)"
                      class="pm-face-img"
                      alt=""
                      @error="(e: Event) => ((e.target as HTMLImageElement).style.display = 'none')"
                    />
                    <span class="pm-avatar-letter">{{ p.name.charAt(0) }}</span>
                  </div>
                  <div class="pm-info">
                    <span class="pm-name">{{ p.name }}</span>
                    <span class="pm-badge in-db">✓ VERIFIED</span>
                  </div>
                  <span v-if="p.coords" class="pm-coords">{{ p.coords.w }}×{{ p.coords.h }}px</span>
                </div>
              </div>
            </section>
            <div class="pm-divider"></div>
            <section class="pm-section">
              <div class="pm-section-title not-db">
                <component :is="AlertTriangle" :size="15" />
                Not in Database
                <span class="pm-count">{{ notInDatabasePeople.length }}</span>
              </div>
              <div v-if="notInDatabasePeople.length === 0" class="pm-empty">No unknown faces in frame</div>
              <div v-else class="pm-list">
                <div v-for="p in notInDatabasePeople" :key="p.id" class="pm-item not-db">
                  <div class="pm-avatar not-db">
                    <img
                      v-if="p.coords"
                      :src="faceImgUrl(p.coords)"
                      class="pm-face-img"
                      alt=""
                      @error="(e: Event) => ((e.target as HTMLImageElement).style.display = 'none')"
                    />
                    <span class="pm-avatar-letter">?</span>
                  </div>
                  <div class="pm-info">
                    <span class="pm-name">Unknown Person</span>
                    <span class="pm-badge not-db">✗ UNRECOGNIZED</span>
                  </div>
                  <span v-if="p.coords" class="pm-coords">{{ p.coords.w }}×{{ p.coords.h }}px</span>
                </div>
              </div>
            </section>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- ── FACE DATABASE MODAL ──────────────────────────────────── -->
    <Teleport to="body">
      <div v-if="showFaceDbModal" class="facedb-backdrop" @click.self="showFaceDbModal = false">
        <div class="facedb-modal">
          <div class="facedb-header">
            <div class="facedb-title">
              <component :is="Database" :size="16" />
              Face Database
              <span class="facedb-count">{{ faceDbEntries.length }}</span>
            </div>
            <button class="pm-close" @click="showFaceDbModal = false">
              <component :is="X" :size="18" />
            </button>
          </div>
          <div class="facedb-body">
            <div v-if="faceDbLoading" class="facedb-loading">
              <div class="facedb-spinner"></div>
              <span>Loading database…</span>
            </div>
            <div v-else-if="!faceDbLoading && faceDbEntries.length === 0" class="facedb-empty">
              <component :is="Database" :size="40" class="facedb-empty-icon" />
              <p>No faces enrolled yet</p>
              <p class="empty-sub">Drop photos below to add people</p>
            </div>
            <div v-if="faceDbEntries.length > 0" class="facedb-grid">
              <div v-for="entry in faceDbEntries" :key="entry.filename" class="facedb-card">
                <div class="facedb-img-wrap">
                  <img :src="entry.dataUrl" :alt="entry.name" class="facedb-img" />
                </div>
                <div class="facedb-card-footer">
                  <span class="facedb-name" :title="entry.filename">{{ entry.name }}</span>
                  <button
                    class="facedb-del-btn"
                    :title="`Remove ${entry.name}`"
                    @click="deleteFaceDbEntry(entry.filename)"
                  >
                    <component :is="Trash2" :size="12" />
                  </button>
                </div>
              </div>
            </div>
            <div
              :class="['facedb-dropzone', { 'drag-over': faceDbDragOver }]"
              @dragover="onFaceDbDragOver"
              @dragleave="onFaceDbDragLeave"
              @drop="onFaceDbDrop"
              @click="($refs.faceDbInput as HTMLInputElement).click()"
            >
              <component :is="ImagePlus" :size="22" />
              <span v-if="!faceDbUploadStatus">Drop photos here or <u>click to browse</u></span>
              <span v-else class="facedb-uploading">{{ faceDbUploadStatus }}</span>
              <span class="facedb-hint">JPEG · PNG · WEBP — filename becomes the person's name</span>
              <input
                ref="faceDbInput"
                type="file"
                accept="image/*"
                multiple
                class="facedb-file-input"
                @change="onFaceDbFileInput"
              />
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- ── COPILOT AI ANALYSIS MODAL ─────────────────────────────── -->
    <Teleport to="body">
      <div v-if="showCopilotModal" class="copilot-backdrop" @click.self="showCopilotModal = false">
        <div class="copilot-modal">
          <div class="copilot-header">
            <div class="copilot-title-row">
              <component :is="Bot" :size="18" class="copilot-bot-icon" />
              <span class="copilot-title-text">AI Analysis</span>
              <span class="copilot-brand">Microsoft Copilot</span>
            </div>
            <button class="pm-close" @click="showCopilotModal = false">
              <component :is="X" :size="18" />
            </button>
          </div>
          <div class="copilot-body">
            <div class="copilot-subject-row">
              <span class="copilot-subject-label">Subject</span>
              <span :class="['copilot-subject-val', copilotSubject === 'Unknown Person' || !copilotSubject ? 'unknown' : 'known']">
                {{ copilotSubject || 'Unknown' }}
              </span>
            </div>
            <div v-if="copilotLoading" class="copilot-loading">
              <div class="copilot-dots"><span></span><span></span><span></span></div>
              <p class="copilot-loading-label">Analyzing footage with Microsoft Copilot…</p>
            </div>
            <div v-else-if="copilotError" class="copilot-error">
              <component :is="AlertTriangle" :size="18" />
              <div>
                <p class="copilot-err-title">Analysis Failed</p>
                <p class="copilot-err-msg">{{ copilotError }}</p>
              </div>
            </div>
            <div v-else-if="copilotResult" class="copilot-result-wrap">
              <p class="copilot-result-label">Behavioral Analysis Report</p>
              <div class="copilot-result-text">{{ copilotResult }}</div>
              <div class="copilot-timestamp">Generated by Microsoft Copilot (Azure OpenAI)</div>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- ── SETTINGS MODAL ─────────────────────────────────────────── -->
    <Teleport to="body">
      <div v-if="showSettingsModal" class="settings-backdrop" @click.self="showSettingsModal = false">
        <div class="settings-modal">
          <div class="settings-header">
            <div class="settings-title">
              <component :is="Settings" :size="16" />
              System Settings
            </div>
            <button class="pm-close" @click="showSettingsModal = false">
              <component :is="X" :size="18" />
            </button>
          </div>
          <div class="settings-body">

            <div class="settings-section">
              <div class="settings-section-label">Data Acquisition</div>
              <div class="settings-row">
                <div class="settings-row-info">
                  <span class="settings-label">Polling Interval</span>
                  <span class="settings-desc">How often to fetch frame data from the backend (ms)</span>
                </div>
                <div class="settings-input-group">
                  <button class="settings-stepper" @click="settingPollingMs = Math.max(100, settingPollingMs - 50)">−</button>
                  <span class="settings-val">{{ settingPollingMs }} ms</span>
                  <button class="settings-stepper" @click="settingPollingMs = Math.min(5000, settingPollingMs + 50)">+</button>
                </div>
              </div>
            </div>

            <div class="settings-section">
              <div class="settings-section-label">Stream</div>
              <div class="settings-row">
                <div class="settings-row-info">
                  <span class="settings-label">Stream Quality</span>
                  <span class="settings-desc">Resolution profile for the live camera feed</span>
                </div>
                <div class="settings-toggle-group">
                  <button
                    :class="['settings-toggle-btn', { active: settingStreamQuality === 'HD' }]"
                    @click="settingStreamQuality = 'HD'"
                  >HD</button>
                  <button
                    :class="['settings-toggle-btn', { active: settingStreamQuality === 'SD' }]"
                    @click="settingStreamQuality = 'SD'"
                  >SD</button>
                </div>
              </div>
            </div>

            <div class="settings-section">
              <div class="settings-section-label">Alerts</div>
              <div class="settings-row">
                <div class="settings-row-info">
                  <span class="settings-label">Auto-Alert on Unknown Faces</span>
                  <span class="settings-desc">Trigger notification immediately when an unrecognized face is detected</span>
                </div>
                <button
                  :class="['settings-switch', { on: settingAutoAlert }]"
                  @click="settingAutoAlert = !settingAutoAlert"
                >
                  <span class="settings-switch-thumb"></span>
                </button>
              </div>
            </div>

          </div>
          <div class="settings-footer">
            <button class="settings-cancel-btn" @click="showSettingsModal = false">Cancel</button>
            <button class="settings-save-btn" @click="applySettings">Apply &amp; Save</button>
          </div>
        </div>
      </div>
    </Teleport>

  </div>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

/* ── CSS VARIABLES ────────────────────────────────────────────────────────── */
.app-shell {
  --bg:          #080b0f;
  --sidebar-bg:  #090d12;
  --surface:     #0d1117;
  --surface-2:   #161b22;
  --surface-3:   #21262d;
  --border:      #2d333b;
  --border-soft: #1c2128;
  --accent:      #ef4444;
  --accent-dim:  rgba(239,68,68,0.12);
  --accent-line: rgba(239,68,68,0.35);
  --accent-glow: rgba(239,68,68,0.25);
  --green:       #22c55e;
  --green-glow:  rgba(34,197,94,0.2);
  --amber:       #f59e0b;
  --blue:        #3b82f6;
  --cyan:        #06b6d4;
  --indigo:      #6366f1;
  --text:        #e1e8ed;
  --text-dim:    #8b95a5;
  --text-muted:  #4b5563;
  --mono:        'JetBrains Mono', monospace;
  --sans:        'Space Grotesk', system-ui, sans-serif;
  --sidebar-w:   64px;
  --radius:      10px;
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

/* ── BRAND AREA (logo removed) ────────────────────────────────────────────── */
.sidebar-brand {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 14px 0 12px;
  border-bottom: 1px solid var(--border-soft);
  margin-bottom: 8px;
  gap: 6px;
}
.sys-label {
  font-family: var(--mono);
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: var(--text-muted);
  text-transform: uppercase;
}
.sys-dot { color: var(--accent); }
.sys-status-dot {
  width: 6px; height: 6px;
  border-radius: 50%;
  transition: all 0.4s ease;
}
.sys-status-dot.online  { background: var(--green); box-shadow: 0 0 6px var(--green-glow); animation: pulse-dot 2s ease-in-out infinite; }
.sys-status-dot.offline { background: var(--text-muted); }

@keyframes pulse-dot {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0.4; }
}

/* ── NAV ICONS ────────────────────────────────────────────────────────────── */
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
  position: relative;
}

/* ── PAGE HEADER ──────────────────────────────────────────────────────────── */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 28px;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.ph-breadcrumb {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
}
.ph-system {
  font-family: var(--mono);
  font-size: 0.6rem;
  font-weight: 700;
  letter-spacing: 0.15em;
  color: var(--accent);
  text-transform: uppercase;
}
.ph-sep  { color: var(--text-muted); flex-shrink: 0; }
.ph-page { font-family: var(--mono); font-size: 0.6rem; letter-spacing: 0.1em; color: var(--text-muted); text-transform: uppercase; }
.ph-left h1 {
  font-family: var(--sans);
  font-size: 1.35rem;
  font-weight: 700;
  color: var(--text);
  letter-spacing: -0.02em;
  line-height: 1.1;
}
.ph-sub {
  font-size: 0.75rem;
  color: var(--text-dim);
  margin-top: 2px;
  font-family: var(--mono);
}
.ph-sub strong { color: var(--text); font-weight: 600; }
.ph-status {
  font-family: var(--mono);
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.08em;
}
.ph-status.online  { color: var(--green); }
.ph-status.offline { color: var(--accent); }
.ph-right { display: flex; align-items: center; gap: 8px; }

/* ── HEADER ICON BUTTONS ──────────────────────────────────────────────────── */
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
  position: relative;
}
.hdr-icon-btn:hover { color: var(--text); background: var(--surface-3); border-color: var(--border); }
.everyone { margin-right: 4px; }
.notif-btn.active { background: var(--accent-dim); border-color: var(--accent-line); color: var(--accent); }
.login-btn:hover  { border-color: var(--green); color: var(--green); }
.logout-btn:hover { border-color: var(--accent); color: var(--accent); }

.notif-badge {
  position: absolute;
  top: -5px; right: -5px;
  background: var(--accent);
  color: #fff;
  font-size: 0.5rem;
  font-weight: 700;
  font-family: var(--mono);
  padding: 1px 4px;
  border-radius: 8px;
  min-width: 16px;
  text-align: center;
  border: 1px solid var(--bg);
}

.auth-area { display: flex; align-items: center; gap: 8px; }
.user-avatar { width: 34px; height: 34px; border-radius: 7px; object-fit: cover; border: 1px solid var(--border); }

.auth-spinner {
  width: 16px; height: 16px;
  border: 2px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ── NOTIFICATIONS PANEL ──────────────────────────────────────────────────── */
.notif-panel {
  position: absolute;
  top: 68px; right: 16px;
  width: 320px;
  max-height: 420px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  z-index: 100;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 16px 48px rgba(0,0,0,0.6);
}
.notif-panel-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 14px;
  border-bottom: 1px solid var(--border-soft);
  flex-shrink: 0;
}
.notif-panel-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.75rem;
  font-weight: 700;
  font-family: var(--mono);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text);
  flex: 1;
}
.notif-panel-count {
  font-family: var(--mono);
  font-size: 0.6rem;
  color: var(--text-muted);
  background: var(--surface-3);
  padding: 2px 7px;
  border-radius: 10px;
}
.notif-panel-close {
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  padding: 2px;
  display: flex;
  align-items: center;
  transition: color 0.15s;
}
.notif-panel-close:hover { color: var(--text); }
.notif-panel-body {
  overflow-y: auto;
  flex: 1;
}
.notif-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 40px 20px;
  color: var(--text-muted);
  font-size: 0.8rem;
  opacity: 0.5;
}
.notif-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-bottom: 1px solid var(--border-soft);
  border-left: 3px solid transparent;
  transition: background 0.15s;
}
.notif-item:last-child { border-bottom: none; }
.notif-item:hover      { background: var(--surface-2); }
.notif-item.threat     { border-left-color: var(--accent); }
.notif-item.clear      { border-left-color: var(--green); }
.notif-icon {
  width: 28px; height: 28px;
  display: flex; align-items: center; justify-content: center;
  border-radius: 6px;
  flex-shrink: 0;
}
.notif-item.threat .notif-icon { color: var(--accent); background: var(--accent-dim); }
.notif-item.clear  .notif-icon { color: var(--green);  background: rgba(34,197,94,0.1); }
.notif-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.notif-name {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.notif-type {
  font-family: var(--mono);
  font-size: 0.58rem;
  font-weight: 700;
  letter-spacing: 0.08em;
}
.notif-type.threat { color: var(--accent); }
.notif-type.clear  { color: var(--green); }
.notif-time {
  font-family: var(--mono);
  font-size: 0.62rem;
  color: var(--text-muted);
  white-space: nowrap;
  flex-shrink: 0;
}

/* ── NOTIFICATIONS TRANSITION ─────────────────────────────────────────────── */
.notif-slide-enter-active,
.notif-slide-leave-active { transition: all 0.2s cubic-bezier(0.34, 1.2, 0.64, 1); }
.notif-slide-enter-from,
.notif-slide-leave-to     { opacity: 0; transform: translateY(-10px) scale(0.97); }

/* ── PAGE BODY ────────────────────────────────────────────────────────────── */
.page-body {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

/* ── METRICS ROW ──────────────────────────────────────────────────────────── */
.metrics-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
  flex-shrink: 0;
}
.metric-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 18px 20px;
  display: flex;
  flex-direction: column;
  gap: 7px;
  min-height: 108px;
  transition: border-color 0.2s ease;
}
.metric-card:hover { border-color: var(--border); }
.mc-label {
  font-size: 0.6rem;
  text-transform: uppercase;
  letter-spacing: 0.14em;
  color: var(--text-muted);
  font-family: var(--mono);
}
.mc-clock-label { font-size: 0.6rem; text-transform: uppercase; letter-spacing: 0.14em; color: var(--text-muted); font-family: var(--mono); }
.mc-sublabel {
  font-size: 0.6rem;
  color: var(--text-muted);
  font-family: var(--mono);
  text-transform: uppercase;
  letter-spacing: 0.07em;
  margin-top: auto;
}
.clock-card { justify-content: center; }
.mc-clock {
  font-size: 2.2rem;
  font-weight: 700;
  color: var(--text);
  font-family: var(--mono);
  line-height: 1;
  letter-spacing: -0.02em;
}
.mc-date {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 0.7rem;
  color: var(--text-dim);
  font-family: var(--mono);
}
.mc-dual { display: flex; align-items: baseline; gap: 6px; flex: 1; }
.mc-dual-val { font-size: 1.5rem; font-weight: 700; color: var(--text); font-family: var(--mono); }
.status-card { position: relative; overflow: hidden; }
.mc-status-body { display: flex; flex-direction: column; align-items: flex-start; gap: 4px; flex: 1; justify-content: center; }
.mc-status-icon.green { color: var(--green); }
.mc-status-icon.red   { color: var(--accent); }
.mc-status-text { font-size: 1.05rem; font-weight: 700; }
.mc-status-text.green { color: var(--green); }
.mc-status-text.red   { color: var(--accent); }
.mc-status-ver { font-size: 0.6rem; font-family: var(--mono); color: var(--text-muted); }

.detect-summary-card {
  background: linear-gradient(135deg, #0d1f3a 0%, #0d2347 100%);
  border-color: #1a3460;
}
.ds-top { display: flex; align-items: center; gap: 10px; }
.ds-icon { color: #60a5fa; }
.ds-big  { font-size: 2.2rem; font-weight: 700; color: #fff; font-family: var(--mono); line-height: 1; }
.ds-rows { display: flex; flex-direction: column; gap: 4px; margin-top: auto; }
.ds-row  { display: flex; justify-content: space-between; font-size: 0.7rem; color: rgba(200,220,255,0.7); }
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
  padding: 10px 4px;
  margin-right: 22px;
  margin-bottom: -1px;
  color: var(--text-dim);
  font-family: var(--sans);
  font-size: 0.8rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.18s ease;
}
.tab-pill:hover  { color: var(--text); }
.tab-pill.active { color: var(--text); border-bottom-color: var(--accent); font-weight: 600; }
.tab-badge {
  background: var(--accent);
  color: #fff;
  font-size: 0.55rem;
  font-weight: 700;
  padding: 2px 5px;
  border-radius: 10px;
  font-family: var(--mono);
}

/* ── CAMERA GRID ──────────────────────────────────────────────────────────── */
.camera-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 14px;
  flex-shrink: 0;
  align-items: stretch;
}
.cam-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  transition: border-color 0.2s ease;
}
.cam-card.cam-live {
  border-color: rgba(34, 197, 94, 0.4);
  box-shadow: 0 0 0 1px rgba(34, 197, 94, 0.1);
}
.cam-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 9px 13px;
  border-bottom: 1px solid var(--border-soft);
  gap: 8px;
}
.cam-name {
  font-size: 0.72rem;
  font-weight: 600;
  color: var(--text);
  letter-spacing: 0.03em;
  flex: 1;
}
.cam-live-badge {
  font-family: var(--mono);
  font-size: 0.58rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  color: var(--green);
  animation: live-blink 1.4s ease-in-out infinite;
}
.cam-paused-badge {
  font-family: var(--mono);
  font-size: 0.58rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  color: var(--amber);
}
@keyframes live-blink { 0%,100%{opacity:1} 50%{opacity:0.35} }
.cam-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.cam-dot.online  { background: var(--green); box-shadow: 0 0 6px rgba(34,197,94,0.7); animation: pulse-dot 2s ease-in-out infinite; }
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

/* Scanline overlay */
.scanlines {
  position: absolute;
  inset: 0;
  z-index: 3;
  pointer-events: none;
  background: repeating-linear-gradient(
    0deg,
    transparent,
    transparent 2px,
    rgba(0, 0, 0, 0.07) 2px,
    rgba(0, 0, 0, 0.07) 4px
  );
}

/* Corner brackets */
.corner {
  position: absolute;
  width: 14px; height: 14px;
  border-color: rgba(239, 68, 68, 0.55);
  border-style: solid;
  z-index: 4;
  transition: border-color 0.3s ease;
}
.cam-card.cam-live .corner { border-color: rgba(34, 197, 94, 0.6); }
.tl { top: 10px;    left: 10px;    border-width: 2px 0 0 2px; }
.tr { top: 10px;    right: 10px;   border-width: 2px 2px 0 0; }
.bl { bottom: 10px; left: 10px;    border-width: 0 0 2px 2px; }
.br { bottom: 10px; right: 10px;   border-width: 0 2px 2px 0; }

.cam-placeholder {
  flex-direction: column;
  gap: 10px;
  background: var(--surface-2);
}
.cam-ph-icon  { color: var(--text-muted); opacity: 0.2; z-index: 5; }
.cam-ph-label {
  font-size: 0.58rem;
  letter-spacing: 0.14em;
  color: var(--text-muted);
  text-transform: uppercase;
  font-family: var(--mono);
  z-index: 5;
}

.cam-pause-overlay,
.cam-offline-overlay {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  position: absolute; inset: 0;
  background: rgba(8,11,15,0.92);
  color: var(--text-muted);
  z-index: 5;
  justify-content: center;
  text-align: center;
}
.cam-pause-overlay svg { color: var(--amber); opacity: 0.7; }
.cam-offline-overlay svg { color: var(--accent); opacity: 0.5; }
.cam-pause-overlay p   { font-size: 0.7rem; font-weight: 700; color: var(--amber); letter-spacing: 0.1em; text-transform: uppercase; font-family: var(--mono); }
.cam-offline-overlay p { font-size: 0.7rem; font-weight: 700; color: var(--accent); letter-spacing: 0.1em; text-transform: uppercase; font-family: var(--mono); }
.cam-pause-overlay button,
.cam-offline-overlay button {
  background: var(--surface-3);
  border: 1px solid var(--border);
  color: var(--text);
  padding: 6px 16px;
  border-radius: 5px;
  font-size: 0.75rem;
  cursor: pointer;
  font-family: var(--sans);
  transition: all 0.15s;
}
.cam-pause-overlay button:hover   { border-color: var(--amber);  color: var(--amber); }
.cam-offline-overlay button:hover { border-color: var(--accent); color: var(--accent); }

.cam-footer {
  display: flex;
  align-items: center;
  padding: 7px 11px;
  gap: 7px;
  border-top: 1px solid var(--border-soft);
}
.cam-ts {
  font-size: 0.6rem;
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
  transition: all 0.15s ease;
}
.cam-ctrl-btn:hover:not(:disabled) { color: var(--text); background: var(--surface-3); border-color: var(--text-muted); }
.cam-ctrl-btn:disabled { opacity: 0.3; cursor: not-allowed; }

/* ── INLINE PEOPLE PANEL ─────────────────────────────────────────────────── */
.people-inline-card { display: flex; flex-direction: column; min-height: 0; }
.ipl-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 22px;
  padding: 1px 7px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 700;
  background: var(--surface-3);
  color: var(--text-muted);
  font-family: var(--mono);
  transition: all 0.2s;
}
.ipl-badge.active { background: var(--accent-dim); color: var(--accent); border: 1px solid var(--accent-line); }
.ipl-body { flex: 1; overflow-y: auto; display: flex; flex-direction: column; min-height: 0; background: #000; }
.ipl-empty {
  flex: 1; display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 10px;
  color: var(--text-muted); font-size: 12px; opacity: 0.4;
  padding: 24px; font-family: var(--mono); text-transform: uppercase; letter-spacing: 0.08em;
}
.ipl-list { display: flex; flex-direction: column; gap: 0; padding: 4px 0; }
.ipl-item {
  display: flex; align-items: center; gap: 9px;
  padding: 7px 10px;
  border-bottom: 1px solid #111116;
  transition: background 0.15s;
  cursor: default;
}
.ipl-item:last-child { border-bottom: none; }
.ipl-item:hover { background: #111116; }
.ipl-item.known    { border-left: 2px solid var(--green); }
.ipl-item.unknown  { border-left: 2px solid var(--accent); }
.ipl-item.scanning { border-left: 2px solid var(--amber); }
.ipl-avatar {
  width: 40px; height: 40px; border-radius: 6px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  font-size: 13px; font-weight: 700; overflow: hidden; position: relative;
}
.ipl-avatar.known    { background: rgba(34,197,94,0.15);  border: 1px solid rgba(34,197,94,0.3);   color: var(--green); }
.ipl-avatar.unknown  { background: rgba(239,68,68,0.15);  border: 1px solid rgba(239,68,68,0.3);   color: var(--accent); }
.ipl-avatar.scanning { background: rgba(245,158,11,0.15); border: 1px solid rgba(245,158,11,0.3);  color: var(--amber); }
.ipl-face-img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; border-radius: 5px; }
.ipl-avatar-letter { position: relative; z-index: 0; }
.ipl-info { flex: 1; display: flex; flex-direction: column; gap: 3px; min-width: 0; }
.ipl-name { font-size: 12px; font-weight: 600; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.ipl-chip {
  font-size: 9px; font-weight: 700; letter-spacing: 0.06em;
  padding: 1px 6px; border-radius: 3px; width: fit-content;
  font-family: var(--mono); border: 1px solid;
}
.ipl-chip.known    { background: rgba(34,197,94,0.1);  color: var(--green);  border-color: rgba(34,197,94,0.25); }
.ipl-chip.unknown  { background: rgba(239,68,68,0.1);  color: var(--accent); border-color: rgba(239,68,68,0.25); }
.ipl-chip.scanning { background: rgba(245,158,11,0.1); color: var(--amber);  border-color: rgba(245,158,11,0.25); }
.ipl-ai-btn {
  display: flex; align-items: center; justify-content: center;
  width: 26px; height: 26px; flex-shrink: 0;
  background: rgba(59,130,246,0.07);
  border: 1px solid rgba(59,130,246,0.2);
  border-radius: 5px;
  color: #60a5fa; cursor: pointer; transition: all 0.15s;
}
.ipl-ai-btn:hover {
  background: rgba(59,130,246,0.18);
  border-color: rgba(59,130,246,0.45);
  color: #93c5fd;
}

.ipl-summary {
  font-size: 11px;
  font-family: var(--mono);
  margin-left: auto;
}
.ipl-summary .green { color: var(--green); font-weight: 600; }
.ipl-summary .red   { color: var(--accent); font-weight: 600; }

/* ── SYSTEM METRICS ROW ───────────────────────────────────────────────────── */
.sysmetrics-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
  flex-shrink: 0;
}
.sysm-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 16px 18px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.sysm-label { font-size: 0.58rem; text-transform: uppercase; letter-spacing: 0.14em; color: var(--text-muted); font-family: var(--mono); }
.sysm-big   { font-size: 1.9rem; font-weight: 700; color: var(--text); font-family: var(--mono); line-height: 1; }
.sysm-big.green { color: var(--green); }
.sysm-big.red   { color: var(--accent); }
.sysm-track { height: 5px; background: var(--surface-3); border-radius: 3px; overflow: hidden; margin-top: 4px; }
.sysm-alert { background: rgba(239,68,68,0.1); }
.sysm-fill  { height: 100%; background: var(--text-dim); border-radius: 3px; transition: width 0.4s ease; }
.sysm-fill.green { background: var(--green); }
.sysm-fill.red   { background: var(--accent); }

/* ── CARDS ──────────────────────────────────────────────────────────────────── */
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.card.full-width { width: 100%; flex: 1; }
.card-header {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 13px 18px;
  border-bottom: 1px solid var(--border-soft);
  background: var(--surface-2);
  flex-shrink: 0;
}
.card-header h3 { font-size: 0.85rem; font-weight: 600; color: var(--text); margin: 0; }
.detection-count,
.log-count {
  margin-left: auto;
  font-size: 0.65rem;
  color: var(--text-muted);
  letter-spacing: 0.06em;
  text-transform: uppercase;
  font-family: var(--mono);
}

/* ── DETECTED PEOPLE ────────────────────────────────────────────────────────── */
.detected-container {
  padding: 18px;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px;
  overflow-y: auto;
  flex: 1;
}
.detected-item {
  display: flex; align-items: center; gap: 12px;
  padding: 13px 14px;
  border: 1px solid var(--border-soft);
  border-radius: 8px;
  background: var(--surface-2);
  transition: border-color 0.18s ease, background 0.18s ease;
}
.detected-top {
  display: flex;
  align-items: center;
  gap: 14px;
  min-width: 0;
}
.detected-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.detected-item:hover { border-color: var(--border); background: var(--surface-3); }
.detected-item.unknown { border-left: 3px solid var(--accent); }
.detected-item.known   { border-left: 3px solid var(--green); }
.detected-item.scanning { border-left: 3px solid var(--amber); }
.person-avatar {
  width: 42px; height: 42px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 1rem; font-weight: 700; flex-shrink: 0; border: 1.5px solid;
}
.person-avatar.known    { background: rgba(34,197,94,0.12);  border-color: rgba(34,197,94,0.4);   color: var(--green); }
.person-avatar.scanning { background: rgba(245,158,11,0.12); border-color: rgba(245,158,11,0.4);  color: var(--amber); }
.person-avatar.unknown  { background: rgba(239,68,68,0.12);  border-color: rgba(239,68,68,0.4);   color: var(--accent); }
.person-info { display: flex; flex-direction: column; gap: 4px; flex: 1; min-width: 0; }
.person-name { font-size: 0.875rem; font-weight: 600; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.match-badge {
  display: inline-flex; align-items: center;
  font-size: 0.58rem; font-weight: 700;
  padding: 2px 7px; border-radius: 3px; border: 1px solid;
  text-transform: uppercase; letter-spacing: 0.06em;
  font-family: var(--mono); width: fit-content;
}
.match-badge.known    { background: rgba(34,197,94,0.1);  color: var(--green);  border-color: rgba(34,197,94,0.3); }
.match-badge.scanning { background: rgba(245,158,11,0.1); color: var(--amber);  border-color: rgba(245,158,11,0.3); }
.match-badge.unknown  { background: rgba(239,68,68,0.1);  color: var(--accent); border-color: rgba(239,68,68,0.3); }
.coords { font-size: 0.6rem; color: var(--text-muted); font-family: var(--mono); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.add-person-btn {
  display: flex; align-items: center; gap: 6px;
  background: var(--surface-3);
  color: var(--text-dim);
  border: 1px solid var(--border);
  padding: 6px 12px; border-radius: 5px;
  font-family: var(--sans); font-size: 0.73rem; font-weight: 600;
  cursor: pointer; flex-shrink: 0; transition: all 0.18s ease;
}
.add-person-btn:hover { color: var(--text); border-color: var(--green); color: var(--green); }
.empty-state {
  grid-column: 1 / -1;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 12px; padding: 60px 20px;
  color: var(--text-muted); text-align: center; font-size: 0.875rem;
}
.empty-state svg { opacity: 0.2; }
.empty-sub { font-size: 0.7rem; color: var(--text-muted); opacity: 0.7; }

/* ── ANALYZE AI BUTTON ────────────────────────────────────────────────────── */
.analyze-ai-btn {
  display: flex; align-items: center; gap: 5px;
  background: rgba(59,130,246,0.08);
  color: #60a5fa;
  border: 1px solid rgba(59,130,246,0.25);
  padding: 6px 11px; border-radius: 5px;
  font-family: var(--sans); font-size: 0.72rem; font-weight: 600;
  cursor: pointer; flex-shrink: 0; margin-left: 4px;
}
.analyze-ai-btn:hover { background: rgba(59,130,246,0.18); border-color: rgba(59,130,246,0.5); color: #93c5fd; }

/* ── LOGS ─────────────────────────────────────────────────────────────────── */
.logs-view { padding: 0; overflow-y: auto; flex: 1; }
.logs-card { width: 100%; }
.logs-empty { padding: 80px 20px; }
.table-container { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; }
th {
  background: var(--surface-2);
  padding: 11px 16px;
  font-size: 0.65rem;
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
td { padding: 11px 16px; border-bottom: 1px solid var(--border-soft); font-size: 0.85rem; color: var(--text); }
tr:hover td { background: var(--surface-2); }
.row-num   { color: var(--text-muted); font-size: 0.7rem; font-family: var(--mono); width: 48px; }
.time-cell { color: var(--text-muted); font-size: 0.75rem; font-family: var(--mono); white-space: nowrap; }
.status-badge {
  display: inline-block;
  padding: 3px 8px; border-radius: 4px;
  font-size: 0.65rem; font-weight: 600;
  text-transform: uppercase; letter-spacing: 0.07em;
  font-family: var(--mono); border: 1px solid;
}
.status-badge.authorized { background: rgba(34,197,94,0.1);  color: var(--green);  border-color: rgba(34,197,94,0.3); }
.status-badge.denied     { background: rgba(239,68,68,0.1);  color: var(--accent); border-color: rgba(239,68,68,0.3); }

/* ── ACTIVITY VIEW ──────────────────────────────────────────────────────────── */
.activity-view { padding: 0; overflow-y: auto; flex: 1; animation: fade-in 0.3s ease-out; }
@keyframes fade-in { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }

/* ── "IN DEVELOPMENT" PAGES ──────────────────────────────────────────────── */
.dev-page {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 24px;
}
.dev-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 40px 48px;
  max-width: 520px;
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 20px;
  position: relative;
  overflow: hidden;
}
.dev-card::before {
  content: '';
  position: absolute;
  inset: 0;
  background: repeating-linear-gradient(
    45deg,
    transparent,
    transparent 20px,
    rgba(255,255,255,0.013) 20px,
    rgba(255,255,255,0.013) 21px
  );
  pointer-events: none;
}
.dev-icon-wrap {
  width: 72px; height: 72px;
  border-radius: 14px;
  display: flex; align-items: center; justify-content: center;
}
.dev-icon-wrap.signal  { background: rgba(6,182,212,0.1);  color: var(--cyan);   border: 1px solid rgba(6,182,212,0.25); }
.dev-icon-wrap.monitor { background: rgba(59,130,246,0.1); color: var(--blue);   border: 1px solid rgba(59,130,246,0.25); }
.dev-icon-wrap.shield  { background: rgba(99,102,241,0.1); color: var(--indigo); border: 1px solid rgba(99,102,241,0.25); }
.dev-tag {
  font-family: var(--mono);
  font-size: 0.58rem;
  font-weight: 700;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--text-muted);
}
.dev-title {
  font-size: 1.6rem;
  font-weight: 700;
  color: var(--text);
  letter-spacing: -0.02em;
}
.dev-desc {
  font-size: 0.85rem;
  color: var(--text-dim);
  line-height: 1.6;
}
.dev-features { display: flex; flex-direction: column; gap: 8px; }
.dev-feature {
  display: flex; align-items: center; gap: 10px;
  font-size: 0.82rem;
  color: var(--text-dim);
}
.dev-check { color: var(--text-muted); font-size: 0.9rem; }
.dev-status-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-top: 8px;
  border-top: 1px solid var(--border-soft);
}
.dev-status-label {
  font-family: var(--mono);
  font-size: 0.55rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--text-muted);
  white-space: nowrap;
}
.dev-progress-track {
  flex: 1;
  height: 4px;
  background: var(--surface-3);
  border-radius: 2px;
  overflow: hidden;
}
.dev-progress-fill {
  height: 100%;
  background: var(--accent);
  border-radius: 2px;
  transition: width 1s ease;
}
.dev-progress-fill.monitor { background: var(--blue); }
.dev-progress-fill.shield  { background: var(--indigo); }
.dev-progress-pct {
  font-family: var(--mono);
  font-size: 0.65rem;
  font-weight: 700;
  color: var(--text-dim);
  white-space: nowrap;
}

/* ── SETTINGS MODAL ──────────────────────────────────────────────────────── */
.settings-backdrop {
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.65);
  backdrop-filter: blur(4px);
  z-index: 9999;
  display: flex; align-items: center; justify-content: center;
}
.settings-modal {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 14px;
  width: 480px; max-width: 96vw;
  display: flex; flex-direction: column;
  overflow: hidden;
  box-shadow: 0 24px 64px rgba(0,0,0,0.75);
}
.settings-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 16px 20px 14px;
  border-bottom: 1px solid var(--border);
}
.settings-title {
  display: flex; align-items: center; gap: 8px;
  font-size: 14px; font-weight: 600; color: var(--text);
  letter-spacing: 0.01em;
}
.settings-body {
  padding: 18px 20px;
  display: flex; flex-direction: column; gap: 24px;
}
.settings-section { display: flex; flex-direction: column; gap: 12px; }
.settings-section-label {
  font-family: var(--mono);
  font-size: 0.58rem; font-weight: 700;
  letter-spacing: 0.16em; text-transform: uppercase;
  color: var(--text-muted);
  padding-bottom: 6px;
  border-bottom: 1px solid var(--border-soft);
}
.settings-row {
  display: flex; align-items: center; justify-content: space-between; gap: 16px;
}
.settings-row-info { display: flex; flex-direction: column; gap: 3px; flex: 1; }
.settings-label { font-size: 0.85rem; font-weight: 500; color: var(--text); }
.settings-desc  { font-size: 0.7rem; color: var(--text-muted); }
.settings-input-group { display: flex; align-items: center; gap: 8px; }
.settings-stepper {
  width: 28px; height: 28px;
  background: var(--surface-3);
  border: 1px solid var(--border);
  border-radius: 5px;
  color: var(--text);
  font-size: 1rem; font-weight: 700;
  cursor: pointer; display: flex; align-items: center; justify-content: center;
  transition: all 0.15s;
}
.settings-stepper:hover { background: var(--surface-2); border-color: var(--accent); color: var(--accent); }
.settings-val { font-family: var(--mono); font-size: 0.8rem; font-weight: 600; color: var(--text); min-width: 58px; text-align: center; }
.settings-toggle-group { display: flex; border: 1px solid var(--border); border-radius: 6px; overflow: hidden; }
.settings-toggle-btn {
  padding: 5px 14px;
  background: var(--surface-3);
  border: none;
  color: var(--text-muted);
  font-size: 0.75rem; font-weight: 600;
  cursor: pointer; transition: all 0.15s;
  font-family: var(--mono);
}
.settings-toggle-btn:first-child { border-right: 1px solid var(--border); }
.settings-toggle-btn.active { background: var(--accent-dim); color: var(--accent); }
.settings-switch {
  width: 42px; height: 24px;
  background: var(--surface-3);
  border: 1px solid var(--border);
  border-radius: 12px;
  cursor: pointer;
  position: relative;
  transition: all 0.25s ease;
  flex-shrink: 0;
}
.settings-switch.on { background: rgba(34,197,94,0.25); border-color: rgba(34,197,94,0.5); }
.settings-switch-thumb {
  position: absolute;
  top: 3px; left: 3px;
  width: 16px; height: 16px;
  border-radius: 50%;
  background: var(--text-muted);
  transition: all 0.25s cubic-bezier(0.34,1.56,0.64,1);
}
.settings-switch.on .settings-switch-thumb { transform: translateX(18px); background: var(--green); }
.settings-footer {
  display: flex; justify-content: flex-end; gap: 8px;
  padding: 14px 20px;
  border-top: 1px solid var(--border);
}
.settings-cancel-btn {
  padding: 8px 16px; border-radius: 7px;
  background: var(--surface-2); border: 1px solid var(--border);
  color: var(--text-dim); font-family: var(--sans); font-size: 0.82rem; font-weight: 500;
  cursor: pointer; transition: all 0.15s;
}
.settings-cancel-btn:hover { color: var(--text); }
.settings-save-btn {
  padding: 8px 20px; border-radius: 7px;
  background: var(--accent-dim); border: 1px solid var(--accent-line);
  color: var(--accent); font-family: var(--sans); font-size: 0.82rem; font-weight: 600;
  cursor: pointer; transition: all 0.15s;
}
.settings-save-btn:hover { background: rgba(239,68,68,0.2); }

/* ── PEOPLE MODAL ────────────────────────────────────────────────────────── */
.people-modal-backdrop {
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.65);
  backdrop-filter: blur(4px);
  z-index: 9999;
  display: flex; align-items: center; justify-content: center;
}
.people-modal {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 14px;
  width: 440px; max-width: 96vw; max-height: 80vh;
  display: flex; flex-direction: column;
  overflow: hidden;
  box-shadow: 0 24px 64px rgba(0,0,0,0.7);
}
.pm-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 16px 20px 13px;
  border-bottom: 1px solid var(--border);
}
.pm-header h2 { font-size: 14px; font-weight: 600; color: var(--text); letter-spacing: 0.01em; }
.pm-close {
  background: none; border: none; color: var(--text-muted);
  cursor: pointer; padding: 4px; border-radius: 6px;
  display: flex; align-items: center; transition: color .15s, background .15s;
}
.pm-close:hover { color: var(--text); background: var(--surface-3); }
.pm-body { overflow-y: auto; padding: 14px 18px 18px; display: flex; flex-direction: column; gap: 0; }
.pm-section { display: flex; flex-direction: column; gap: 8px; }
.pm-section-title {
  display: flex; align-items: center; gap: 6px;
  font-size: 10px; font-weight: 700;
  letter-spacing: 0.1em; text-transform: uppercase;
  padding: 4px 0 2px;
  font-family: var(--mono);
}
.pm-section-title.in-db  { color: var(--green); }
.pm-section-title.not-db { color: var(--accent); }
.pm-count {
  margin-left: auto; background: var(--surface-3);
  border-radius: 20px; padding: 1px 8px;
  font-size: 11px; color: var(--text-muted); font-weight: 500;
}
.pm-divider { border-top: 1px solid var(--border); margin: 12px 0; }
.pm-list { display: flex; flex-direction: column; gap: 6px; }
.pm-empty { font-size: 12px; color: var(--text-muted); padding: 8px 0 4px; font-style: italic; }
.pm-item {
  display: flex; align-items: center; gap: 12px;
  padding: 10px 12px; border-radius: 8px;
  background: var(--surface-2); border: 1px solid var(--border-soft);
}
.pm-item.in-db  { border-left: 3px solid var(--green); }
.pm-item.not-db { border-left: 3px solid var(--accent); }
.pm-avatar {
  width: 50px; height: 50px; border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  font-size: 14px; font-weight: 700; flex-shrink: 0;
  overflow: hidden; position: relative;
}
.pm-avatar.in-db  { background: rgba(34,197,94,0.12);  color: var(--green);  border: 1px solid rgba(34,197,94,0.3); }
.pm-avatar.not-db { background: rgba(239,68,68,0.12);  color: var(--accent); border: 1px solid rgba(239,68,68,0.3); }
.pm-face-img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; border-radius: 7px; }
.pm-avatar-letter { position: relative; z-index: 0; font-size: 14px; font-weight: 700; }
.pm-info { display: flex; flex-direction: column; gap: 3px; flex: 1; min-width: 0; }
.pm-name { font-size: 13px; font-weight: 600; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.pm-badge {
  font-size: 9.5px; font-weight: 600; letter-spacing: 0.05em;
  padding: 1px 6px; border-radius: 4px; width: fit-content; font-family: var(--mono);
}
.pm-badge.in-db  { background: rgba(34,197,94,0.12);  color: var(--green); }
.pm-badge.not-db { background: rgba(239,68,68,0.12);  color: var(--accent); }
.pm-coords { font-size: 9.5px; color: var(--text-muted); font-family: var(--mono); white-space: nowrap; flex-shrink: 0; }

/* ── FACE DATABASE MODAL ─────────────────────────────────────────────────── */
.facedb-backdrop {
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.65); backdrop-filter: blur(4px);
  z-index: 9999;
  display: flex; align-items: center; justify-content: center;
}
.facedb-modal {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 14px;
  width: 620px; max-width: 96vw; max-height: 82vh;
  display: flex; flex-direction: column;
  overflow: hidden;
  box-shadow: 0 24px 64px rgba(0,0,0,0.75);
}
.facedb-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 15px 18px 13px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.facedb-title {
  display: flex; align-items: center; gap: 8px;
  font-size: 14px; font-weight: 600; color: var(--text); letter-spacing: 0.01em;
}
.facedb-count {
  background: var(--surface-3); border-radius: 20px;
  padding: 1px 9px; font-size: 11px; color: var(--text-muted); font-weight: 500;
}
.facedb-body {
  overflow-y: auto; padding: 16px 16px 14px;
  flex: 1; display: flex; flex-direction: column; gap: 14px;
}
.facedb-loading {
  display: flex; align-items: center; gap: 12px;
  color: var(--text-muted); font-size: 13px;
  justify-content: center; padding: 40px 0;
}
.facedb-spinner {
  width: 20px; height: 20px;
  border: 2px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
.facedb-empty {
  display: flex; flex-direction: column; align-items: center;
  gap: 10px; padding: 40px 0 10px;
  color: var(--text-muted); text-align: center; font-size: 13px;
}
.facedb-empty-icon { opacity: 0.2; }
.facedb-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 10px; }
.facedb-card {
  background: var(--surface-2); border: 1px solid var(--border-soft);
  border-radius: 8px; overflow: hidden;
  display: flex; flex-direction: column; transition: border-color 0.17s;
}
.facedb-card:hover { border-color: var(--border); }
.facedb-img-wrap { aspect-ratio: 1; background: #0a0c0f; overflow: hidden; display: flex; align-items: center; justify-content: center; }
.facedb-img { width: 100%; height: 100%; object-fit: cover; display: block; }
.facedb-card-footer {
  display: flex; align-items: center; gap: 6px;
  padding: 6px 8px; border-top: 1px solid var(--border-soft); min-width: 0;
}
.facedb-name { font-size: 11px; font-weight: 600; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; flex: 1; }
.facedb-del-btn {
  display: flex; align-items: center; justify-content: center;
  width: 22px; height: 22px; flex-shrink: 0;
  background: none; border: 1px solid transparent; border-radius: 4px;
  color: var(--text-muted); cursor: pointer; transition: all 0.15s;
}
.facedb-del-btn:hover { color: var(--accent); background: var(--accent-dim); border-color: var(--accent-line); }
.facedb-dropzone {
  border: 1.5px dashed var(--border);
  border-radius: 9px; padding: 22px 14px;
  display: flex; flex-direction: column; align-items: center; gap: 8px;
  color: var(--text-muted); cursor: pointer; text-align: center; font-size: 13px;
  transition: all 0.2s ease; position: relative; flex-shrink: 0;
}
.facedb-dropzone:hover,
.facedb-dropzone.drag-over { border-color: var(--accent); background: var(--accent-dim); color: var(--text); }
.facedb-dropzone u { color: var(--blue); text-decoration-color: rgba(59,130,246,0.5); }
.facedb-hint { font-size: 10px; color: var(--text-muted); font-family: var(--mono); letter-spacing: 0.04em; }
.facedb-uploading { color: var(--green); font-weight: 600; }
.facedb-file-input { position: absolute; inset: 0; opacity: 0; cursor: pointer; width: 100%; height: 100%; pointer-events: none; }

/* ── COPILOT MODAL ───────────────────────────────────────────────────────── */
.copilot-backdrop {
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.65); backdrop-filter: blur(4px);
  z-index: 9999;
  display: flex; align-items: center; justify-content: center;
}
.copilot-modal {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 14px;
  width: 500px; max-width: 96vw; max-height: 80vh;
  display: flex; flex-direction: column;
  overflow: hidden;
  box-shadow: 0 24px 64px rgba(0,0,0,0.75);
}
.copilot-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 15px 18px 13px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
  background: linear-gradient(90deg, rgba(59,130,246,0.06) 0%, transparent 100%);
}
.copilot-title-row { display: flex; align-items: center; gap: 8px; }
.copilot-bot-icon { color: #60a5fa; }
.copilot-title-text { font-size: 14px; font-weight: 600; color: var(--text); }
.copilot-brand {
  font-size: 9.5px; font-weight: 600; color: #60a5fa;
  background: rgba(59,130,246,0.1); border: 1px solid rgba(59,130,246,0.25);
  border-radius: 4px; padding: 1px 7px; letter-spacing: 0.04em; text-transform: uppercase;
  font-family: var(--mono);
}
.copilot-body { padding: 16px 18px 18px; overflow-y: auto; flex: 1; display: flex; flex-direction: column; gap: 14px; }
.copilot-subject-row {
  display: flex; align-items: center; gap: 10px;
  padding: 9px 13px; background: var(--surface-2);
  border: 1px solid var(--border-soft); border-radius: 7px;
}
.copilot-subject-label {
  font-size: 9.5px; font-weight: 600; text-transform: uppercase;
  letter-spacing: 0.1em; color: var(--text-muted);
  font-family: var(--mono); flex-shrink: 0;
}
.copilot-subject-val { font-size: 13px; font-weight: 600; color: var(--text); }
.copilot-subject-val.unknown { color: #f87171; }
.copilot-subject-val.known   { color: #4ade80; }
.copilot-loading { display: flex; flex-direction: column; align-items: center; gap: 16px; padding: 36px 0; }
.copilot-dots { display: flex; gap: 6px; }
.copilot-dots span {
  width: 8px; height: 8px; background: #60a5fa;
  border-radius: 50%; animation: copilot-pulse 1.2s ease-in-out infinite;
}
.copilot-dots span:nth-child(2) { animation-delay: 0.2s; }
.copilot-dots span:nth-child(3) { animation-delay: 0.4s; }
@keyframes copilot-pulse { 0%, 100% { opacity: 0.25; transform: scale(0.8); } 50% { opacity: 1; transform: scale(1.1); } }
.copilot-loading-label { font-size: 12px; color: var(--text-muted); text-align: center; }
.copilot-error {
  display: flex; align-items: flex-start; gap: 12px;
  padding: 13px 14px;
  background: rgba(239,68,68,0.08); border: 1px solid rgba(239,68,68,0.25);
  border-radius: 8px; color: var(--accent);
}
.copilot-err-title { font-size: 13px; font-weight: 600; color: #f87171; margin-bottom: 4px; }
.copilot-err-msg   { font-size: 11.5px; color: var(--text-muted); font-family: var(--mono); }
.copilot-result-wrap { display: flex; flex-direction: column; gap: 10px; }
.copilot-result-label {
  font-size: 9.5px; font-weight: 600; text-transform: uppercase;
  letter-spacing: 0.1em; color: var(--text-muted); font-family: var(--mono);
}
.copilot-result-text {
  background: var(--surface-2); border: 1px solid var(--border-soft);
  border-left: 3px solid #3b82f6; border-radius: 8px;
  padding: 14px; font-size: 13px; line-height: 1.65; color: #d4d4e0;
  white-space: pre-wrap;
}
.copilot-timestamp { font-size: 9.5px; color: var(--text-muted); font-family: var(--mono); text-align: right; }

/* ── SCROLLBARS ─────────────────────────────────────────────────────────────── */
::-webkit-scrollbar       { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--surface-3); border-radius: 2px; }
::-webkit-scrollbar-thumb:hover { background: #3a3a42; }

/* ── RESPONSIVE ─────────────────────────────────────────────────────────────── */
@media (max-width: 1100px) {
  .metrics-row    { grid-template-columns: repeat(2, 1fr); }
  .camera-grid    { grid-template-columns: repeat(2, 1fr); }
  .sysmetrics-row { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 700px) {
  .icon-sidebar   { width: 48px; min-width: 48px; }
  .metrics-row    { grid-template-columns: 1fr; }
  .camera-grid    { grid-template-columns: 1fr; }
  .sysmetrics-row { grid-template-columns: 1fr; }
  .page-header    { padding: 12px 14px; }
  .page-body      { padding: 12px 10px; }
  .notif-panel    { width: calc(100vw - 16px); right: 8px; }
}
</style>