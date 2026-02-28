<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { Menu, X } from 'lucide-vue-next'
import { useSurveillanceAPI } from '../composables/useSurveillanceAPI'

const { data, lastUpdate, getStreamUrl, startPolling, stopPolling } = useSurveillanceAPI()

const activeTab = ref('live')
const currentPage = ref('dashboard')
const sidebarOpen = ref(true)
const currentTime = ref(new Date())
const systemOnline = computed(() => !data.value._offline)

// Update clock
const updateClock = () => {
  currentTime.value = new Date()
}

const toggleSidebar = () => {
  sidebarOpen.value = !sidebarOpen.value
  localStorage.setItem('sidebarOpen', sidebarOpen.value)
}

// Separate known faces from scanning
const knownFaces = computed(() => {
  return (data.value.known || []).filter(p => p.name !== 'SCANNING...')
})

const scanningFaces = computed(() => {
  return (data.value.known || []).filter(p => p.name === 'SCANNING...')
})

const unknownFaces = computed(() => {
  return data.value.unknown || []
})

const recentAlerts = computed(() => {
  return (data.value.alerts || []).slice().reverse().slice(0, 50)
})

const getAlertType = (alert) => {
  return alert.type === 'KNOWN' ? 'known' : 'unknown'
}

const formatCoord = (value) => {
  return value ? `${value}px` : '-'
}

const formatTime = (timestamp) => {
  if (!timestamp) return '--:--:--'
  const date = new Date(timestamp * 1000)
  return date.toLocaleTimeString('en-US', { hour12: false })
}

onMounted(() => {
  const savedState = localStorage.getItem('sidebarOpen')
  if (savedState !== null) {
    sidebarOpen.value = savedState === 'true'
  }
  
  // Start polling for data
  startPolling(250)
  
  // Update clock
  const clockInterval = setInterval(updateClock, 1000)
  
  onUnmounted(() => {
    clearInterval(clockInterval)
    stopPolling()
  })
})
</script>

<template>
  <div class="dashboard-container">
    <!-- Sidebar -->
    <aside class="sidebar" :class="{ 'sidebar-collapsed': !sidebarOpen }">
      <div class="logo">
        <h2>NEXUS</h2>
        <p class="subtitle">Surveillance Intelligence</p>
      </div>
      <nav>
        <ul>
          <li :class="{ active: currentPage === 'dashboard' }" @click="currentPage = 'dashboard'">Dashboard</li>
          <li :class="{ active: currentPage === 'logs' }" @click="currentPage = 'logs'">Detection Log</li>
          <li>Settings</li>
        </ul>
      </nav>
      <button 
        class="sidebar-toggle-btn"
        @click="toggleSidebar"
        title="Toggle sidebar"
        :aria-label="sidebarOpen ? 'Close sidebar' : 'Open sidebar'"
      >
        <Menu v-if="sidebarOpen" :size="20" />
        <X v-else :size="20" />
      </button>
    </aside>

    <!-- Main Content -->
    <main class="main-content">
      <!-- Header -->
      <header class="top-bar">
        <div class="header-left">
          <h1>SURVEILLANCE INTELLIGENCE v2.1</h1>
        </div>
        <div class="header-right">
          <div class="sysline">
            <div class="dot" :class="systemOnline ? 'dot-g' : 'dot-r'"></div>
            <span>{{ systemOnline ? 'SYSTEM ONLINE' : 'RECOGNITION OFFLINE' }}</span>
          </div>
          <div class="clock">{{ currentTime.toLocaleTimeString('en-US', { hour12: false }) }}</div>
        </div>
      </header>

      <!-- Stats Bar -->
      <div class="stats-bar">
        <div class="stat-card">
          <div class="stat-icon">👁</div>
          <div class="stat-info">
            <div class="stat-label">Detected</div>
            <div class="stat-value">{{ data.counts?.total ?? 0 }}</div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon">✅</div>
          <div class="stat-info">
            <div class="stat-label">Identified</div>
            <div class="stat-value green">{{ data.counts?.known ?? 0 }}</div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon">⚠️</div>
          <div class="stat-info">
            <div class="stat-label">Unknown</div>
            <div class="stat-value red">{{ data.counts?.unknown ?? 0 }}</div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon">🕐</div>
          <div class="stat-info">
            <div class="stat-label">Last Update</div>
            <div class="stat-value yellow">{{ formatTime(data.timestamp) }}</div>
          </div>
        </div>
      </div>

      <!-- Main Content Grid -->
      <div class="content-grid">
        <!-- Left: Video Section -->
        <div class="left-panel">
          <!-- Tabs -->
          <div class="main-tabs">
            <button 
              :class="['main-tab-btn', { active: activeTab === 'live' }]" 
              @click="activeTab = 'live'"
            >
              Live Feed
            </button>
            <button 
              :class="['main-tab-btn', { active: activeTab === 'detected' }]" 
              @click="activeTab = 'detected'"
            >
              Detection Details
            </button>
          </div>

          <!-- Live Feed Tab -->
          <div v-if="activeTab === 'live'" class="card camera-card">
            <div class="video-container">
              <img 
                :src="getStreamUrl()" 
                alt="Live Feed" 
                class="live-stream"
              >
              <div class="corner corner-tl"></div>
              <div class="corner corner-tr"></div>
              <div class="corner corner-bl"></div>
              <div class="corner corner-br"></div>
              <div class="live-badge">● REC LIVE</div>
              <div class="video-info">
                CAM-01 // FACES: {{ data.counts?.total ?? 0 }} // {{ currentTime.toLocaleTimeString('en-US', { hour12: false }) }}
              </div>
            </div>
          </div>

          <!-- Detection Details Tab -->
          <div v-if="activeTab === 'detected'" class="card detection-card">
            <div class="detection-content">
              <!-- Known Faces -->
              <div v-if="knownFaces.length > 0 || scanningFaces.length > 0" class="detection-section">
                <h3 class="section-title known-title">IDENTIFIED PERSONS</h3>
                <div class="faces-list">
                  <div v-for="face in knownFaces" :key="`known-${face.id}`" class="face-item known">
                    <div class="face-header">
                      <span class="face-name">{{ face.name }}</span>
                      <span class="badge badge-known">CLEARED</span>
                    </div>
                    <div class="face-grid">
                      <div class="grid-item">
                        <span class="grid-key">X</span>
                        <span class="grid-val">{{ formatCoord(face.coords?.x) }}</span>
                      </div>
                      <div class="grid-item">
                        <span class="grid-key">Y</span>
                        <span class="grid-val">{{ formatCoord(face.coords?.y) }}</span>
                      </div>
                      <div class="grid-item">
                        <span class="grid-key">W</span>
                        <span class="grid-val">{{ formatCoord(face.coords?.w) }}</span>
                      </div>
                      <div class="grid-item">
                        <span class="grid-key">H</span>
                        <span class="grid-val">{{ formatCoord(face.coords?.h) }}</span>
                      </div>
                      <div class="grid-item">
                        <span class="grid-key">CX</span>
                        <span class="grid-val">{{ formatCoord(face.coords?.center_x) }}</span>
                      </div>
                      <div class="grid-item">
                        <span class="grid-key">CY</span>
                        <span class="grid-val">{{ formatCoord(face.coords?.center_y) }}</span>
                      </div>
                    </div>
                  </div>
                  <div v-for="face in scanningFaces" :key="`scan-${face.id}`" class="face-item scanning">
                    <div class="face-header">
                      <span class="face-name">ANALYZING...</span>
                      <span class="badge badge-scanning">SCANNING</span>
                    </div>
                    <div class="face-grid">
                      <div class="grid-item">
                        <span class="grid-key">X</span>
                        <span class="grid-val">{{ formatCoord(face.coords?.x) }}</span>
                      </div>
                      <div class="grid-item">
                        <span class="grid-key">Y</span>
                        <span class="grid-val">{{ formatCoord(face.coords?.y) }}</span>
                      </div>
                      <div class="grid-item">
                        <span class="grid-key">W</span>
                        <span class="grid-val">{{ formatCoord(face.coords?.w) }}</span>
                      </div>
                      <div class="grid-item">
                        <span class="grid-key">H</span>
                        <span class="grid-val">{{ formatCoord(face.coords?.h) }}</span>
                      </div>
                      <div class="grid-item">
                        <span class="grid-key">CX</span>
                        <span class="grid-val">{{ formatCoord(face.coords?.center_x) }}</span>
                      </div>
                      <div class="grid-item">
                        <span class="grid-key">CY</span>
                        <span class="grid-val">{{ formatCoord(face.coords?.center_y) }}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Unknown Faces -->
              <div v-if="unknownFaces.length > 0" class="detection-section">
                <h3 class="section-title unknown-title">UNKNOWN INTRUDERS</h3>
                <div class="faces-list">
                  <div v-for="(face, idx) in unknownFaces" :key="`unknown-${idx}`" class="face-item unknown">
                    <div class="face-header">
                      <span class="face-name">INTRUDER #{{ idx + 1 }}</span>
                      <span class="badge badge-unknown">THREAT</span>
                    </div>
                    <div class="face-grid">
                      <div class="grid-item">
                        <span class="grid-key">X</span>
                        <span class="grid-val">{{ formatCoord(face.x) }}</span>
                      </div>
                      <div class="grid-item">
                        <span class="grid-key">Y</span>
                        <span class="grid-val">{{ formatCoord(face.y) }}</span>
                      </div>
                      <div class="grid-item">
                        <span class="grid-key">W</span>
                        <span class="grid-val">{{ formatCoord(face.w) }}</span>
                      </div>
                      <div class="grid-item">
                        <span class="grid-key">H</span>
                        <span class="grid-val">{{ formatCoord(face.h) }}</span>
                      </div>
                      <div class="grid-item">
                        <span class="grid-key">CX</span>
                        <span class="grid-val">{{ formatCoord(face.center_x) }}</span>
                      </div>
                      <div class="grid-item">
                        <span class="grid-key">CY</span>
                        <span class="grid-val">{{ formatCoord(face.center_y) }}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Empty State -->
              <div v-if="knownFaces.length === 0 && scanningFaces.length === 0 && unknownFaces.length === 0" class="empty-state">
                <p>NO DETECTIONS</p>
              </div>
            </div>
          </div>
        </div>

        <!-- Right: Panels -->
        <div class="right-panel">
          <!-- Known Faces Panel -->
          <div class="side-section">
            <div class="section-header known-header">
              <div class="dot dot-g"></div>
              <span>IDENTIFIED PERSONS</span>
            </div>
            <div class="section-body">
              <div v-if="knownFaces.length === 0 && scanningFaces.length === 0" class="empty-message">
                NO KNOWN FACES DETECTED
              </div>
              <div v-for="face in knownFaces" :key="`panel-known-${face.id}`" class="side-card known">
                <div class="card-name">{{ face.name }}</div>
                <div class="card-coords">{{ formatCoord(face.coords?.x) }} / {{ formatCoord(face.coords?.y) }}</div>
              </div>
              <div v-for="face in scanningFaces" :key="`panel-scan-${face.id}`" class="side-card scanning">
                <div class="card-name">ANALYZING...</div>
                <div class="card-coords">{{ formatCoord(face.coords?.x) }} / {{ formatCoord(face.coords?.y) }}</div>
              </div>
            </div>
          </div>

          <!-- Unknown Faces Panel -->
          <div class="side-section">
            <div class="section-header unknown-header">
              <div class="dot dot-r"></div>
              <span>UNKNOWN INTRUDERS</span>
            </div>
            <div class="section-body">
              <div v-if="unknownFaces.length === 0" class="empty-message">
                AREA CLEAR
              </div>
              <div v-for="(face, idx) in unknownFaces" :key="`panel-unknown-${idx}`" class="side-card unknown">
                <div class="card-name">INTRUDER #{{ idx + 1 }}</div>
                <div class="card-coords">{{ formatCoord(face.x) }} / {{ formatCoord(face.y) }}</div>
              </div>
            </div>
          </div>

          <!-- Alert Log Panel -->
          <div class="side-section grow">
            <div class="section-header alert-header">
              <div class="dot dot-y"></div>
              <span>DETECTION LOG</span>
            </div>
            <div class="section-body">
              <div v-if="recentAlerts.length === 0" class="empty-message">
                AWAITING DETECTIONS...
              </div>
              <div v-for="alert in recentAlerts" :key="`alert-${alert.time}-${alert.name}`" class="alert-item" :class="getAlertType(alert)">
                <span class="alert-time">{{ alert.time }}</span>
                <span class="alert-type">[{{ alert.type }}]</span>
                <span class="alert-name">{{ alert.name }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>

    <!-- Sidebar Uncollapse Button -->
    <button 
      v-if="!sidebarOpen"
      class="sidebar-uncollapse-btn"
      @click="toggleSidebar"
      title="Open sidebar"
      aria-label="Open sidebar"
    >
      <Menu :size="24" />
    </button>
  </div>
</template>

<style scoped>
:root {
  --bg: #040608;
  --panel: #07090c;
  --border: #0e2218;
  --green: #00ff88;
  --gd: #00bb60;
  --red: #ff2244;
  --rd: #991122;
  --yellow: #ffcc00;
  --cyan: #00ccff;
  --text: #c0d8c0;
  --dim: #3a5a4a;
  --glow: 0 0 14px rgba(0, 255, 136, 0.3);
  --glow-r: 0 0 14px rgba(255, 34, 68, 0.35);
}

* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

.dashboard-container {
  display: flex;
  height: 100vh;
  background: var(--bg);
  color: var(--text);
  font-family: 'Rajdhani', 'JetBrains Mono', monospace;
  overflow: hidden;
  background-image: 
    repeating-linear-gradient(0deg, transparent, transparent 39px, rgba(0, 255, 136, 0.018) 40px),
    repeating-linear-gradient(90deg, transparent, transparent 39px, rgba(0, 255, 136, 0.018) 40px);
}

/* Scanlines */
.dashboard-container::after {
  content: '';
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 9999;
  background: repeating-linear-gradient(to bottom, transparent 0, transparent 2px, rgba(0, 0, 0, 0.06) 2px, rgba(0, 0, 0, 0.06) 4px);
}

/* ── SIDEBAR ── */
.sidebar {
  width: 280px;
  background: linear-gradient(180deg, var(--panel), var(--bg));
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  transition: width 0.3s ease, transform 0.3s ease;
  position: relative;
  z-index: 10;
}

.sidebar.sidebar-collapsed {
  width: 0;
  transform: translateX(-100%);
  opacity: 0;
  pointer-events: none;
}

.logo {
  padding: 20px;
  border-bottom: 1px solid var(--border);
  background: linear-gradient(180deg, #060d09, var(--panel));
}

.logo h2 {
  font-family: 'Share Tech Mono', monospace;
  font-size: 1.4rem;
  color: var(--green);
  text-shadow: var(--glow);
  letter-spacing: 5px;
  margin: 0;
  line-height: 1;
}

.logo .subtitle {
  font-family: 'Share Tech Mono', monospace;
  font-size: 0.6rem;
  letter-spacing: 3px;
  color: var(--dim);
  margin-top: 4px;
}

.sidebar nav ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.sidebar nav li {
  padding: 14px 18px;
  cursor: pointer;
  transition: all 0.2s;
  color: var(--dim);
  border-left: 3px solid transparent;
  font-size: 0.85rem;
  letter-spacing: 2px;
}

.sidebar nav li:hover {
  background: rgba(0, 255, 136, 0.1);
  color: var(--green);
  border-left-color: var(--green);
}

.sidebar nav li.active {
  background: rgba(0, 255, 136, 0.15);
  color: var(--green);
  border-left-color: var(--green);
  box-shadow: inset -2px 0 8px rgba(0, 255, 136, 0.1);
}

.sidebar-toggle-btn {
  position: absolute;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(0, 255, 136, 0.15);
  border: 1px solid var(--border);
  color: var(--green);
  cursor: pointer;
  padding: 8px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  z-index: 100;
}

.sidebar-toggle-btn:hover {
  background: rgba(0, 255, 136, 0.25);
  box-shadow: var(--glow);
}

.sidebar-uncollapse-btn {
  position: fixed;
  bottom: 30px;
  right: 30px;
  background: rgba(0, 255, 136, 0.15);
  border: 1px solid var(--border);
  color: var(--green);
  cursor: pointer;
  padding: 10px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 99;
  transition: all 0.2s;
}

.sidebar-uncollapse-btn:hover {
  background: rgba(0, 255, 136, 0.25);
  box-shadow: var(--glow);
}

/* ── MAIN CONTENT ── */
.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative;
  z-index: 5;
}

/* ── HEADER ── */
.top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 22px;
  border-bottom: 1px solid var(--border);
  background: linear-gradient(180deg, #060d09, var(--bg));
  height: 52px;
}

.header-left h1 {
  margin: 0;
  font-family: 'Share Tech Mono', monospace;
  font-size: 0.95rem;
  color: var(--text);
  letter-spacing: 2px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 20px;
}

.sysline {
  display: flex;
  align-items: center;
  gap: 7px;
  font-family: 'Share Tech Mono', monospace;
  font-size: 0.7rem;
  color: var(--dim);
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.dot-g {
  background: var(--green);
  box-shadow: var(--glow);
  animation: pulse 2s infinite;
}

.dot-r {
  background: var(--red);
  box-shadow: var(--glow-r);
}

.dot-y {
  background: var(--yellow);
}

.clock {
  font-family: 'Share Tech Mono', monospace;
  font-size: 0.85rem;
  color: var(--green);
  letter-spacing: 2px;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.35; transform: scale(0.8); }
}

/* ── STATS BAR ── */
.stats-bar {
  display: flex;
  gap: 1px;
  background: var(--border);
  border-bottom: 1px solid var(--border);
}

.stat-card {
  flex: 1;
  background: var(--panel);
  padding: 8px 18px;
  display: flex;
  align-items: center;
  gap: 10px;
  transition: background 0.2s;
  cursor: default;
}

.stat-card:hover {
  background: #080f0b;
}

.stat-icon {
  font-size: 1.2rem;
}

.stat-info {
  display: flex;
  flex-direction: column;
}

.stat-label {
  font-size: 0.58rem;
  letter-spacing: 2px;
  color: var(--dim);
  text-transform: uppercase;
}

.stat-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--green);
  line-height: 1;
}

.stat-value.red {
  color: var(--red);
}

.stat-value.yellow {
  color: var(--yellow);
  font-size: 0.85rem;
}

/* ── CONTENT GRID ── */
.content-grid {
  display: grid;
  grid-template-columns: 1fr 320px;
  grid-template-rows: 1fr;
  gap: 1px;
  height: 100%;
  overflow: hidden;
  background: var(--border);
}

.left-panel {
  background: var(--bg);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.right-panel {
  background: var(--panel);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-left: 1px solid var(--border);
}

/* ── TABS ── */
.main-tabs {
  display: flex;
  gap: 1px;
  background: var(--border);
  border-bottom: 1px solid var(--border);
}

.main-tab-btn {
  flex: 1;
  background: var(--panel);
  border: none;
  color: var(--dim);
  padding: 8px 12px;
  cursor: pointer;
  font-family: 'Share Tech Mono', monospace;
  font-size: 0.6rem;
  letter-spacing: 2px;
  text-transform: uppercase;
  transition: all 0.15s;
}

.main-tab-btn:hover {
  background: #080f0b;
  color: var(--green);
}

.main-tab-btn.active {
  background: rgba(0, 255, 136, 0.1);
  color: var(--green);
  border-bottom: 2px solid var(--green);
}

/* ── VIDEO ── */
.card {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--bg);
  border-right: 1px solid var(--border);
}

.video-container {
  position: relative;
  flex: 1;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #000;
}

.live-stream {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
}

.corner {
  position: absolute;
  width: 18px;
  height: 18px;
  border-color: var(--green);
  border-style: solid;
  opacity: 0.6;
}

.corner-tl {
  top: 8px;
  left: 8px;
  border-width: 2px 0 0 2px;
}

.corner-tr {
  top: 8px;
  right: 8px;
  border-width: 2px 2px 0 0;
}

.corner-bl {
  bottom: 8px;
  left: 8px;
  border-width: 0 0 2px 2px;
}

.corner-br {
  bottom: 8px;
  right: 8px;
  border-width: 0 2px 2px 0;
}

.live-badge {
  position: absolute;
  top: 14px;
  left: 50%;
  transform: translateX(-50%);
  background: var(--red);
  color: #fff;
  font-family: 'Share Tech Mono', monospace;
  font-size: 0.6rem;
  letter-spacing: 3px;
  padding: 3px 10px;
  animation: blinkbg 1.2s infinite;
}

.video-info {
  position: absolute;
  bottom: 10px;
  left: 10px;
  font-family: 'Share Tech Mono', monospace;
  font-size: 0.6rem;
  color: rgba(0, 255, 136, 0.55);
  line-height: 1.9;
}

@keyframes blinkbg {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.35; }
}

/* ── DETECTION CARD ── */
.detection-content {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.detection-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.section-title {
  font-family: 'Share Tech Mono', monospace;
  font-size: 0.65rem;
  letter-spacing: 2px;
  padding: 8px 0;
  margin: 0;
  border-bottom: 1px solid var(--border);
}

.section-title.known-title {
  color: var(--green);
}

.section-title.unknown-title {
  color: var(--red);
}

.faces-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.face-item {
  border: 1px solid var(--border);
  border-radius: 3px;
  padding: 8px 10px;
  position: relative;
  transition: background 0.15s;
}

.face-item.known {
  border-left: 3px solid var(--green);
  background: rgba(0, 255, 136, 0.025);
}

.face-item.known:hover {
  background: rgba(0, 255, 136, 0.05);
}

.face-item.unknown {
  border-left: 3px solid var(--red);
  background: rgba(255, 34, 68, 0.03);
}

.face-item.unknown:hover {
  background: rgba(255, 34, 68, 0.06);
}

.face-item.scanning {
  border-left: 3px solid var(--yellow);
  background: rgba(255, 204, 0, 0.02);
}

.face-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.face-name {
  font-size: 0.9rem;
  font-weight: 700;
  letter-spacing: 1px;
}

.face-item.known .face-name {
  color: var(--green);
}

.face-item.unknown .face-name {
  color: var(--red);
}

.face-item.scanning .face-name {
  color: var(--yellow);
}

.badge {
  position: absolute;
  top: 7px;
  right: 7px;
  font-family: 'Share Tech Mono', monospace;
  font-size: 0.5rem;
  letter-spacing: 2px;
  padding: 2px 5px;
  border-radius: 2px;
}

.badge-known {
  background: rgba(0, 255, 136, 0.12);
  color: var(--green);
}

.badge-unknown {
  background: rgba(255, 34, 68, 0.12);
  color: var(--red);
  animation: blinktext 1s infinite;
}

.badge-scanning {
  background: rgba(255, 204, 0, 0.1);
  color: var(--yellow);
}

.face-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2px 6px;
  font-family: 'Share Tech Mono', monospace;
  font-size: 0.6rem;
}

.grid-item {
  display: flex;
  justify-content: space-between;
}

.grid-key {
  color: var(--dim);
}

.grid-val {
  color: var(--text);
}

@keyframes blinktext {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.25; }
}

.empty-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--dim);
  font-family: 'Share Tech Mono', monospace;
  font-size: 0.8rem;
  letter-spacing: 2px;
}

/* ── SIDE PANEL ── */
.side-section {
  border-bottom: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  min-height: 0;
  background: var(--panel);
}

.side-section.grow {
  flex: 1;
  overflow: hidden;
}

.section-header {
  padding: 8px 14px;
  font-family: 'Share Tech Mono', monospace;
  font-size: 0.6rem;
  letter-spacing: 3px;
  color: var(--dim);
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  gap: 7px;
  flex-shrink: 0;
  text-transform: uppercase;
}

.section-header.known-header {
  color: var(--green);
}

.section-header.unknown-header {
  color: var(--red);
}

.section-header.alert-header {
  color: var(--yellow);
}

.section-body {
  padding: 8px;
  overflow-y: auto;
  max-height: 200px;
  flex: 1;
}

.side-section.grow .section-body {
  max-height: none;
}

.side-card {
  border: 1px solid var(--border);
  border-radius: 3px;
  padding: 8px 10px;
  margin-bottom: 6px;
  position: relative;
  transition: background 0.15s;
}

.side-card.known {
  border-left: 3px solid var(--green);
  background: rgba(0, 255, 136, 0.025);
}

.side-card.known:hover {
  background: rgba(0, 255, 136, 0.05);
}

.side-card.unknown {
  border-left: 3px solid var(--red);
  background: rgba(255, 34, 68, 0.03);
}

.side-card.unknown:hover {
  background: rgba(255, 34, 68, 0.06);
}

.side-card.scanning {
  border-left: 3px solid var(--yellow);
  background: rgba(255, 204, 0, 0.02);
}

.card-name {
  font-size: 0.9rem;
  font-weight: 700;
  letter-spacing: 1px;
  margin-bottom: 4px;
}

.side-card.known .card-name {
  color: var(--green);
}

.side-card.unknown .card-name {
  color: var(--red);
}

.side-card.scanning .card-name {
  color: var(--yellow);
}

.card-coords {
  font-family: 'Share Tech Mono', monospace;
  font-size: 0.55rem;
  color: var(--dim);
  letter-spacing: 1px;
}

.side-card:last-child {
  margin-bottom: 0;
}

/* ── ALERT LOG ── */
.alert-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 6px;
  margin-bottom: 2px;
  border-radius: 2px;
  font-family: 'Share Tech Mono', monospace;
  font-size: 0.6rem;
  animation: fadeIn 0.25s ease;
}

.alert-item.known {
  background: rgba(0, 255, 136, 0.05);
  color: var(--gd);
}

.alert-item.unknown {
  background: rgba(255, 34, 68, 0.07);
  color: var(--red);
}

.alert-time {
  color: var(--dim);
  flex-shrink: 0;
}

.alert-name {
  font-weight: bold;
  letter-spacing: 2px;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateX(6px);
  }
  to {
    opacity: 1;
    transform: none;
  }
}

.empty-message {
  text-align: center;
  padding: 20px 8px;
  font-family: 'Share Tech Mono', monospace;
  font-size: 0.62rem;
  color: var(--dim);
  letter-spacing: 2px;
}

/* ── SCROLLBAR ── */
::-webkit-scrollbar {
  width: 3px;
}

::-webkit-scrollbar-track {
  background: var(--bg);
}

::-webkit-scrollbar-thumb {
  background: var(--border);
  border-radius: 2px;
}
</style>
