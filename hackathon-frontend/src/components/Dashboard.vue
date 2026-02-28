<script setup>
import { ref, onMounted } from 'vue'
import { Menu, X } from 'lucide-vue-next'

const activeTab = ref('live')
const currentPage = ref('dashboard') // 'dashboard' or 'logs'
const sidebarOpen = ref(true)

const people = ref([
  { id: 1, name: 'Alice Johnson', status: 'Authorized', time: '10:42 AM' },
  { id: 2, name: 'Bob Smith', status: 'Pending', time: '10:45 AM' },
  { id: 3, name: 'Charlie Brown', status: 'Denied', time: '10:48 AM' },
  { id: 4, name: 'Diana Prince', status: 'Authorized', time: '10:50 AM' },
  { id: 5, name: 'Evan Wright', status: 'Authorized', time: '10:55 AM' },
])

const detectedPeople = ref([
  { id: 101, name: 'Alice Johnson', type: 'known', match: '98%' },
  { id: 102, name: 'Unknown', type: 'unknown', match: '-' },
  { id: 103, name: 'Evan Wright', type: 'known', match: '92%' },
])

const toggleSidebar = () => {
  sidebarOpen.value = !sidebarOpen.value
  localStorage.setItem('sidebarOpen', sidebarOpen.value)
}

onMounted(() => {
  // Load sidebar state from localStorage
  const savedState = localStorage.getItem('sidebarOpen')
  if (savedState !== null) {
    sidebarOpen.value = savedState === 'true'
  }
})
</script>

<template>
  <div class="dashboard-container">
    <!-- Sidebar Toggle Button -->
    <button 
      class="sidebar-toggle-btn"
      @click="toggleSidebar"
      title="Toggle sidebar"
      :aria-label="sidebarOpen ? 'Close sidebar' : 'Open sidebar'"
    >
      <Menu v-if="sidebarOpen" :size="24" />
      <X v-else :size="24" />
    </button>

    <!-- Sidebar -->
    <aside class="sidebar" :class="{ 'sidebar-collapsed': !sidebarOpen }">
      <div class="logo">
        <h2>SecureView</h2>
      </div>
      <nav>
        <ul>
          <li :class="{ active: currentPage === 'dashboard' }" @click="currentPage = 'dashboard'">Dashboard</li>
          <li>Live Feed</li>
          <li :class="{ active: currentPage === 'logs' }" @click="currentPage = 'logs'">Recent Access Logs</li>
          <li>Settings</li>
        </ul>
      </nav>
    </aside>

    <!-- Main Content -->
    <main class="main-content">
      <!-- Header -->
      <header class="top-bar">
        <h1>{{ currentPage === 'dashboard' ? 'Dashboard Overview' : 'Recent Access Logs' }}</h1>
        <button class="login-btn">Login</button>
      </header>

      <!-- Dashboard View -->
      <template v-if="currentPage === 'dashboard'">
        <!-- Tabs for Live Feed and Detected People -->
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
            Detected People
          </button>
        </div>

        <!-- Dashboard Grid -->
        <div class="dashboard-grid">
          <!-- Live Feed Section -->
          <div v-if="activeTab === 'live'" class="card camera-card full-width">
            <div class="card-header">
              <span class="live-indicator">● LIVE</span>
            </div>
            <div class="video-placeholder">
              <div class="camera-overlay">
                <p>Camera 01 - Main Entrance</p>
              </div>
              <!-- Placeholder for video stream -->
              <div class="placeholder-content">
                <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M23 7l-7 5 7 5V7z"></path><rect x="1" y="5" width="15" height="14" rx="2" ry="2"></rect></svg>
                <p>Video Feed Unavailable in Prototype</p>
              </div>
            </div>
          </div>

          <!-- Detected People Section -->
          <div v-if="activeTab === 'detected'" class="card detected-card full-width">
            <div class="card-header">
              <h3>Detected People</h3>
            </div>
            <div class="detected-container">
              <div v-for="person in detectedPeople" :key="person.id" class="detected-item">
                <div class="person-info">
                  <span class="person-name">{{ person.name }}</span>
                  <span :class="['match-badge', person.type]">{{ person.type === 'known' ? 'Match: ' + person.match : 'Unknown' }}</span>
                </div>
                <button v-if="person.type === 'unknown'" class="add-person-btn">Add Person</button>
              </div>
            </div>
          </div>
        </div>
      </template>

      <!-- Recent Access Logs View -->
      <template v-if="currentPage === 'logs'">
        <div class="logs-view">
          <div class="card logs-card">
            <div class="card-header">
              <h3>All Access Logs</h3>
            </div>
            <div class="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Status</th>
                    <th>Time</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="person in people" :key="person.id">
                    <td>{{ person.name }}</td>
                    <td>
                      <span :class="['status-badge', person.status.toLowerCase()]">
                        {{ person.status }}
                      </span>
                    </td>
                    <td>{{ person.time }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </template>
    </main>
  </div>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=Space+Mono:wght@400;700&family=IBM+Plex+Mono:wght@400;600;700&display=swap');

/* CSS Variables for SOC Theme */
:root {
  --soc-midnight: #0B0E14;
  --soc-midnight-light: #161B22;
  --soc-midnight-lighter: #21262D;
  --soc-deep-void: #0a0d11;
  --soc-indigo: #6366F1;
  --soc-indigo-bright: #818CF8;
  --soc-indigo-dark: #4F46E5;
  --soc-indigo-ultra: #7C3AED;
  --soc-neon-red: #FF3131;
  --soc-neon-red-alt: #FF1744;
  --soc-red-glow: rgba(255, 49, 49, 0.3);
  --soc-red-glow-strong: rgba(255, 49, 49, 0.5);
  --soc-cyan: #00D9FF;
  --soc-cyan-glow: rgba(0, 217, 255, 0.2);
  --soc-text-primary: #E1E8ED;
  --soc-text-secondary: #8B95A5;
  --soc-text-muted: #6B7280;
  --soc-border: #2D333B;
  --soc-grid: rgba(99, 102, 241, 0.1);
  --soc-accent-gold: #FFD700;
}

/* Layout */
.dashboard-container {
  display: flex;
  height: 100vh;
  background: linear-gradient(135deg, var(--soc-deep-void) 0%, var(--soc-midnight) 50%, var(--soc-deep-void) 100%);
  background-attachment: fixed;
  color: var(--soc-text-primary);
  font-family: 'IBM Plex Mono', 'JetBrains Mono', monospace;
  position: relative;
  overflow: hidden;
}

/* Animated Background Grid */
.dashboard-container::before {
  content: '';
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-image: 
    linear-gradient(0deg, transparent 24%, rgba(99, 102, 241, 0.05) 25%, rgba(99, 102, 241, 0.05) 26%, transparent 27%, transparent 74%, rgba(99, 102, 241, 0.05) 75%, rgba(99, 102, 241, 0.05) 76%, transparent 77%, transparent),
    linear-gradient(90deg, transparent 24%, rgba(99, 102, 241, 0.05) 25%, rgba(99, 102, 241, 0.05) 26%, transparent 27%, transparent 74%, rgba(99, 102, 241, 0.05) 75%, rgba(99, 102, 241, 0.05) 76%, transparent 77%, transparent);
  background-size: 50px 50px;
  pointer-events: none;
  z-index: 0;
  animation: grid-shift 20s linear infinite;
}

@keyframes grid-shift {
  0% { transform: translate(0, 0); }
  100% { transform: translate(50px, 50px); }
}

/* Radial gradient accent */
.dashboard-container::after {
  content: '';
  position: fixed;
  top: 50%;
  left: 50%;
  width: 200%;
  height: 200%;
  background: radial-gradient(circle at 30% 50%, rgba(99, 102, 241, 0.08) 0%, transparent 50%),
              radial-gradient(circle at 70% 30%, rgba(0, 217, 255, 0.05) 0%, transparent 50%);
  transform: translate(-50%, -50%);
  pointer-events: none;
  z-index: 0;
  animation: radial-pulse 15s ease-in-out infinite;
}

@keyframes radial-pulse {
  0%, 100% { opacity: 0.5; }
  50% { opacity: 1; }
}

/* Sidebar Toggle Button */
.sidebar-toggle-btn {
  position: fixed;
  top: 20px;
  left: 20px;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.2) 0%, rgba(99, 102, 241, 0.05) 100%);
  border: 1px solid rgba(99, 102, 241, 0.4);
  color: #818CF8;
  cursor: pointer;
  padding: 10px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;
  width: 44px;
  height: 44px;
  z-index: 100;
}

.sidebar-toggle-btn:hover {
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.3) 0%, rgba(99, 102, 241, 0.15) 100%);
  border-color: rgba(99, 102, 241, 0.6);
  color: #E1E8ED;
  transform: scale(1.1);
}

.sidebar-toggle-btn:active {
  transform: scale(0.95);
}

/* Sidebar */
.sidebar {
  width: 280px;
  background: linear-gradient(180deg, var(--soc-midnight-light) 0%, var(--soc-midnight) 100%);
  color: var(--soc-text-primary);
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  border-right: 2px solid var(--soc-indigo);
  box-shadow: inset -8px 0 32px rgba(99, 102, 241, 0.08), -4px 0 16px rgba(0, 0, 0, 0.5);
  position: relative;
  z-index: 10;
  transition: width 0.3s ease, transform 0.3s ease, opacity 0.3s ease;
}

.sidebar.sidebar-collapsed {
  width: 0;
  transform: translateX(-100%);
  opacity: 0;
  pointer-events: none;
  overflow: hidden;
}

/* Sidebar animated accent line */
.sidebar::before {
  content: '';
  position: absolute;
  top: 0;
  right: 0;
  width: 2px;
  height: 100%;
  background: linear-gradient(180deg, var(--soc-indigo) 0%, var(--soc-neon-red) 50%, transparent 100%);
  opacity: 0.3;
  animation: shimmer-vertical 3s ease-in-out infinite;
}

@keyframes shimmer-vertical {
  0%, 100% { opacity: 0.2; }
  50% { opacity: 0.6; }
}

.logo {
  padding: 28px 24px;
  border-bottom: 2px solid var(--soc-indigo);
  flex-shrink: 0;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.15) 0%, transparent 100%);
  position: relative;
  overflow: hidden;
}

/* Logo glow background */
.logo::before {
  content: '';
  position: absolute;
  top: -50%;
  right: -50%;
  width: 200%;
  height: 200%;
  background: radial-gradient(circle, rgba(99, 102, 241, 0.2) 0%, transparent 70%);
  animation: rotate-glow 8s linear infinite;
}

@keyframes rotate-glow {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.logo h2 {
  margin: 0;
  font-size: 1.4rem;
  font-weight: 700;
  color: var(--soc-indigo-bright);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  text-shadow: 0 0 20px rgba(99, 102, 241, 0.5), 0 0 40px rgba(99, 102, 241, 0.2);
  position: relative;
  z-index: 2;
  animation: logo-glow 2s ease-in-out infinite;
}

@keyframes logo-glow {
  0%, 100% { text-shadow: 0 0 20px rgba(99, 102, 241, 0.5), 0 0 40px rgba(99, 102, 241, 0.2); }
  50% { text-shadow: 0 0 30px rgba(99, 102, 241, 0.8), 0 0 60px rgba(99, 102, 241, 0.4); }
}

.sidebar nav ul {
  list-style: none;
  padding: 0;
  margin: 0;
  flex-shrink: 0;
}

.sidebar nav li {
  padding: 16px 24px;
  cursor: pointer;
  transition: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
  color: var(--soc-text-secondary);
  border-left: 4px solid transparent;
  position: relative;
  font-size: 0.9rem;
  font-weight: 600;
  letter-spacing: 0.03em;
  text-transform: uppercase;
  overflow: hidden;
}

/* Navigation item hover effect */
.sidebar nav li::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent 0%, rgba(99, 102, 241, 0.2) 50%, transparent 100%);
  transition: left 0.6s ease;
}

.sidebar nav li::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  width: 0;
  height: 2px;
  background: var(--soc-indigo);
  transition: width 0.3s ease;
}

.sidebar nav li:hover::before {
  left: 100%;
}

.sidebar nav li:hover::after {
  width: 100%;
}

.sidebar nav li:hover {
  background-color: rgba(99, 102, 241, 0.12);
  color: var(--soc-indigo-bright);
  border-left-color: var(--soc-indigo);
  padding-left: 28px;
  box-shadow: inset 4px 0 12px rgba(99, 102, 241, 0.1);
}

.sidebar nav li.active {
  background: linear-gradient(90deg, rgba(99, 102, 241, 0.2) 0%, transparent 100%);
  color: var(--soc-indigo-bright);
  border-left-color: var(--soc-neon-red);
  box-shadow: inset 0 0 20px rgba(99, 102, 241, 0.08), inset -2px 0 8px rgba(255, 49, 49, 0.1);
  border-left-width: 4px;
  position: relative;
}

.sidebar nav li.active::after {
  content: '';
  position: absolute;
  right: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: var(--soc-neon-red);
  box-shadow: 0 0 8px var(--soc-neon-red);
}

/* Main Content */
.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: linear-gradient(135deg, var(--soc-midnight) 0%, var(--soc-midnight-light) 100%);
  position: relative;
  z-index: 5;
}

/* Header */
.top-bar {
  background: linear-gradient(90deg, var(--soc-midnight-light) 0%, var(--soc-midnight-lighter) 100%);
  padding: 24px 40px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.6), 0 0 1px var(--soc-indigo);
  border-bottom: 1px solid var(--soc-indigo);
  position: relative;
  overflow: hidden;
}

/* Header glow effect */
.top-bar::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 200%;
  height: 100%;
  background: linear-gradient(90deg, transparent 0%, rgba(99, 102, 241, 0.1) 50%, transparent 100%);
  animation: sweep 6s ease-in-out infinite;
}

@keyframes sweep {
  0%, 100% { left: -100%; }
  50% { left: 100%; }
}

.top-bar h1 {
  margin: 0;
  font-size: 1.6rem;
  font-weight: 700;
  color: var(--soc-indigo-bright);
  letter-spacing: 0.06em;
  text-transform: uppercase;
  text-shadow: 0 0 15px rgba(99, 102, 241, 0.4);
  position: relative;
  z-index: 2;
}

.login-btn {
  background: linear-gradient(135deg, var(--soc-indigo) 0%, var(--soc-indigo-dark) 100%);
  color: white;
  border: 2px solid var(--soc-indigo-bright);
  padding: 12px 28px;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 700;
  font-family: 'IBM Plex Mono', 'JetBrains Mono', monospace;
  transition: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
  box-shadow: 0 0 20px rgba(99, 102, 241, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.1);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  position: relative;
  overflow: hidden;
  z-index: 2;
  font-size: 0.85rem;
}

/* Button shine effect */
.login-btn::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent 0%, rgba(255, 255, 255, 0.2) 50%, transparent 100%);
  transition: left 0.5s ease;
}

.login-btn:hover::before {
  left: 100%;
}

.login-btn:hover {
  background: linear-gradient(135deg, var(--soc-indigo-bright) 0%, var(--soc-indigo) 100%);
  box-shadow: 0 0 40px rgba(99, 102, 241, 0.8), inset 0 1px 0 rgba(255, 255, 255, 0.2), 0 0 20px rgba(99, 102, 241, 0.6);
  transform: translateY(-2px);
}

.login-btn:active {
  box-shadow: 0 0 20px rgba(99, 102, 241, 0.6), inset 0 2px 4px rgba(0, 0, 0, 0.3);
  transform: translateY(0);
}

/* Dashboard Grid */
.dashboard-grid {
  padding: 40px;
  display: flex;
  gap: 40px;
  overflow-y: auto;
  height: 100%;
  flex: 1;
  background: radial-gradient(circle at 20% 50%, rgba(99, 102, 241, 0.08) 0%, transparent 50%);
  perspective: 1000px;
}

.card {
  background: linear-gradient(135deg, var(--soc-midnight-light) 0%, var(--soc-midnight-lighter) 100%);
  border-radius: 8px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5), 0 0 30px rgba(99, 102, 241, 0.15);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid var(--soc-border);
  position: relative;
  backdrop-filter: blur(10px);
  animation: card-appear 0.8s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
  opacity: 0;
}

@keyframes card-appear {
  0% {
    opacity: 0;
    transform: translateY(20px) scale(0.95);
  }
  100% {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.card.full-width {
  width: 100%;
  flex: 1;
  animation-delay: 0.2s;
}

/* Card border glow */
.card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.1) 0%, transparent 50%, rgba(0, 217, 255, 0.05) 100%);
  pointer-events: none;
  border-radius: 8px;
  opacity: 0;
  transition: opacity 0.4s ease;
}

.card:hover::before {
  opacity: 1;
}

.card-header {
  padding: 24px;
  border-bottom: 1px solid var(--soc-border);
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: linear-gradient(90deg, rgba(99, 102, 241, 0.08) 0%, transparent 100%);
  position: relative;
  z-index: 2;
}

.card-header h3 {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--soc-indigo-bright);
  letter-spacing: 0.05em;
  text-transform: uppercase;
  text-shadow: 0 0 10px rgba(99, 102, 241, 0.3);
}

/* Main Tabs */
.main-tabs {
  padding: 0 40px;
  display: flex;
  gap: 40px;
  border-bottom: 2px solid var(--soc-border);
  background: linear-gradient(90deg, var(--soc-midnight-light) 0%, var(--soc-midnight-lighter) 100%);
  position: relative;
}

/* Tab underline animation */
.main-tabs::after {
  content: '';
  position: absolute;
  bottom: -2px;
  left: 40px;
  height: 2px;
  width: 0;
  background: linear-gradient(90deg, var(--soc-indigo) 0%, var(--soc-cyan) 100%);
  transition: all 0.3s ease;
}

.main-tab-btn {
  background: none;
  border: none;
  font-size: 1rem;
  font-weight: 700;
  color: var(--soc-text-secondary);
  cursor: pointer;
  padding: 18px 0;
  border-bottom: 3px solid transparent;
  transition: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
  font-family: 'IBM Plex Mono', 'JetBrains Mono', monospace;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  position: relative;
  overflow: hidden;
}

.main-tab-btn::before {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  width: 100%;
  height: 3px;
  background: linear-gradient(90deg, var(--soc-indigo) 0%, var(--soc-cyan) 100%);
  transform: scaleX(0);
  transform-origin: right;
  transition: transform 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.main-tab-btn:hover {
  color: var(--soc-indigo-bright);
  background: rgba(99, 102, 241, 0.08);
}

.main-tab-btn:hover::before {
  transform: scaleX(1);
  transform-origin: left;
}

.main-tab-btn.active {
  color: var(--soc-indigo-bright);
  border-bottom-color: var(--soc-indigo);
  box-shadow: 0 2px 12px rgba(99, 102, 241, 0.3);
}

.main-tab-btn.active::before {
  transform: scaleX(1);
}

/* Live Feed Specifics */
.live-indicator {
  color: var(--soc-neon-red);
  font-weight: 700;
  font-size: 0.85rem;
  animation: pulse-mega 1.2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
  text-transform: uppercase;
  letter-spacing: 0.15em;
  filter: drop-shadow(0 0 12px var(--soc-red-glow-strong));
  position: relative;
  display: inline-block;
}

@keyframes pulse-mega {
  0% {
    opacity: 1;
    filter: drop-shadow(0 0 8px rgba(255, 49, 49, 0.6));
    transform: scale(1);
  }
  50% {
    opacity: 0.6;
    filter: drop-shadow(0 0 16px rgba(255, 49, 49, 0.8));
    transform: scale(1.05);
  }
  100% {
    opacity: 1;
    filter: drop-shadow(0 0 8px rgba(255, 49, 49, 0.6));
    transform: scale(1);
  }
}

.video-placeholder {
  background: linear-gradient(135deg, #000814 0%, #0a0f1f 50%, #1a1a2e 100%);
  flex: 1;
  min-height: 500px;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--soc-text-secondary);
  border-top: 1px solid var(--soc-border);
  overflow: hidden;
}

/* Animated scanlines */
.video-placeholder::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-image: 
    repeating-linear-gradient(
      0deg,
      rgba(99, 102, 241, 0.04) 0px,
      rgba(99, 102, 241, 0.04) 1px,
      transparent 1px,
      transparent 2px
    );
  pointer-events: none;
  animation: scanlines 8s linear infinite;
  z-index: 1;
}

@keyframes scanlines {
  0% { transform: translateY(0); }
  100% { transform: translateY(10px); }
}

/* Vignette effect */
.video-placeholder::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: radial-gradient(circle at center, transparent 0%, rgba(0, 0, 0, 0.4) 100%);
  pointer-events: none;
  z-index: 2;
}

.camera-overlay {
  position: absolute;
  top: 24px;
  left: 24px;
  color: var(--soc-indigo-bright);
  background: rgba(11, 14, 20, 0.9);
  padding: 12px 16px;
  border-radius: 6px;
  font-size: 0.85rem;
  border: 2px solid var(--soc-indigo);
  box-shadow: 0 0 20px rgba(99, 102, 241, 0.5), inset 0 0 10px rgba(99, 102, 241, 0.1);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-weight: 700;
  z-index: 5;
  animation: float-up 3s ease-in-out infinite;
}

@keyframes float-up {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-4px); }
}

.placeholder-content {
  text-align: center;
  z-index: 10;
  position: relative;
  animation: fade-in 1s ease-out 0.4s forwards;
  opacity: 0;
}

@keyframes fade-in {
  0% { opacity: 0; transform: translateY(10px); }
  100% { opacity: 1; transform: translateY(0); }
}

.placeholder-content svg {
  stroke: var(--soc-indigo-bright);
  filter: drop-shadow(0 0 15px rgba(99, 102, 241, 0.5));
  margin-bottom: 16px;
  animation: pulse-icon 2s ease-in-out infinite;
}

@keyframes pulse-icon {
  0%, 100% { filter: drop-shadow(0 0 15px rgba(99, 102, 241, 0.5)); }
  50% { filter: drop-shadow(0 0 25px rgba(99, 102, 241, 0.8)); }
}

.placeholder-content p {
  color: var(--soc-text-secondary);
  font-size: 0.95rem;
  letter-spacing: 0.02em;
}

/* Detected People Tab */
.detected-container {
  padding: 24px;
  flex: 1;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.04) 0%, transparent 100%);
  overflow-y: auto;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 24px;
  border-top: 1px solid var(--soc-border);
}

.detected-item {
  background: linear-gradient(135deg, var(--soc-midnight-light) 0%, var(--soc-midnight-lighter) 100%);
  padding: 20px;
  border-radius: 6px;
  border: 1px solid var(--soc-border);
  display: flex;
  flex-direction: column;
  gap: 12px;
  transition: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  position: relative;
  overflow: hidden;
  animation: item-appear 0.6s ease-out forwards;
  opacity: 0;
  transform: translateY(20px);
}

@keyframes item-appear {
  0% { opacity: 0; transform: translateY(20px); }
  100% { opacity: 1; transform: translateY(0); }
}

.detected-item:nth-child(1) { animation-delay: 0.1s; }
.detected-item:nth-child(2) { animation-delay: 0.2s; }
.detected-item:nth-child(3) { animation-delay: 0.3s; }

.detected-item::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, var(--soc-indigo) 0%, transparent 100%);
  opacity: 0;
  transition: opacity 0.4s ease;
}

.detected-item:hover::before {
  opacity: 1;
}

.detected-item:hover {
  border-color: var(--soc-indigo-bright);
  box-shadow: 0 8px 24px rgba(99, 102, 241, 0.25), inset 0 0 20px rgba(99, 102, 241, 0.05);
  background: linear-gradient(135deg, var(--soc-midnight-lighter) 0%, rgba(99, 102, 241, 0.08) 100%);
  transform: translateY(-4px);
}

.person-info {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.person-name {
  font-weight: 700;
  color: var(--soc-indigo-bright);
  font-size: 1rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  text-shadow: 0 0 8px rgba(99, 102, 241, 0.2);
}

.match-badge {
  font-size: 0.75rem;
  padding: 6px 10px;
  border-radius: 4px;
  background-color: rgba(99, 102, 241, 0.2);
  color: var(--soc-indigo-bright);
  border: 1.5px solid var(--soc-indigo);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-weight: 700;
  width: fit-content;
  box-shadow: 0 0 8px rgba(99, 102, 241, 0.2);
}

.match-badge.known {
  background-color: rgba(34, 197, 94, 0.2);
  color: #22C55E;
  border-color: #22C55E;
  box-shadow: 0 0 12px rgba(34, 197, 94, 0.3);
}

.match-badge.unknown {
  background-color: var(--soc-red-glow-strong);
  color: var(--soc-neon-red);
  border-color: var(--soc-neon-red);
  box-shadow: 0 0 16px var(--soc-red-glow-strong), inset 0 0 8px rgba(255, 49, 49, 0.2);
  animation: pulse-unknown 1.5s ease-in-out infinite;
}

@keyframes pulse-unknown {
  0%, 100% { box-shadow: 0 0 16px var(--soc-red-glow-strong), inset 0 0 8px rgba(255, 49, 49, 0.2); }
  50% { box-shadow: 0 0 24px var(--soc-red-glow-strong), inset 0 0 12px rgba(255, 49, 49, 0.3); }
}

.add-person-btn {
  background: linear-gradient(135deg, var(--soc-indigo) 0%, var(--soc-indigo-dark) 100%);
  color: white;
  border: 1.5px solid var(--soc-indigo-bright);
  padding: 8px 14px;
  border-radius: 4px;
  font-size: 0.8rem;
  cursor: pointer;
  font-family: 'IBM Plex Mono', 'JetBrains Mono', monospace;
  font-weight: 700;
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  box-shadow: 0 0 12px rgba(99, 102, 241, 0.3);
  position: relative;
  overflow: hidden;
}

.add-person-btn::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent 0%, rgba(255, 255, 255, 0.2) 50%, transparent 100%);
  transition: left 0.4s ease;
}

.add-person-btn:hover::before {
  left: 100%;
}

.add-person-btn:hover {
  background: linear-gradient(135deg, var(--soc-indigo-bright) 0%, var(--soc-indigo) 100%);
  box-shadow: 0 0 24px rgba(99, 102, 241, 0.6);
  transform: translateY(-2px);
}

/* Logs View */
.logs-view {
  padding: 40px;
  overflow-y: auto;
  height: 100%;
  background: radial-gradient(circle at 20% 50%, rgba(99, 102, 241, 0.08) 0%, transparent 50%);
  animation: page-load 0.8s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
  opacity: 0;
}

@keyframes page-load {
  0% { opacity: 0; transform: translateY(10px); }
  100% { opacity: 1; transform: translateY(0); }
}

.logs-card {
  width: 100%;
  animation: card-appear 0.8s cubic-bezier(0.34, 1.56, 0.64, 1) 0.2s forwards;
  opacity: 0;
}

.table-container {
  padding: 0;
  overflow-x: auto;
  border-top: 1px solid var(--soc-border);
}

table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
}

th {
  background: linear-gradient(90deg, rgba(99, 102, 241, 0.15) 0%, rgba(0, 217, 255, 0.05) 100%);
  padding: 16px 20px;
  font-weight: 700;
  font-size: 0.85rem;
  color: var(--soc-indigo-bright);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  border-bottom: 2px solid var(--soc-indigo);
  border-right: 1px solid var(--soc-border);
  position: sticky;
  top: 0;
}

th:last-child {
  border-right: none;
}

td {
  padding: 16px 20px;
  border-bottom: 1px solid var(--soc-border);
  font-size: 0.9rem;
  color: var(--soc-text-primary);
  font-family: 'IBM Plex Mono', 'JetBrains Mono', monospace;
  transition: all 0.2s ease;
}

tr {
  transition: all 0.3s ease;
}

tr:hover {
  background-color: rgba(99, 102, 241, 0.08);
  box-shadow: inset 0 0 15px rgba(99, 102, 241, 0.05);
}

tr:hover td {
  color: var(--soc-indigo-bright);
}

.status-badge {
  padding: 6px 12px;
  border-radius: 4px;
  font-size: 0.8rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  border: 1.5px solid;
  display: inline-block;
  font-family: 'IBM Plex Mono', 'JetBrains Mono', monospace;
}

.status-badge.authorized {
  background-color: rgba(34, 197, 94, 0.2);
  color: #22C55E;
  border-color: #22C55E;
  box-shadow: 0 0 12px rgba(34, 197, 94, 0.3), inset 0 0 8px rgba(34, 197, 94, 0.1);
}

.status-badge.pending {
  background-color: rgba(245, 158, 11, 0.2);
  color: #F59E0B;
  border-color: #F59E0B;
  box-shadow: 0 0 12px rgba(245, 158, 11, 0.3), inset 0 0 8px rgba(245, 158, 11, 0.1);
}

.status-badge.denied {
  background-color: var(--soc-red-glow-strong);
  color: var(--soc-neon-red);
  border-color: var(--soc-neon-red);
  box-shadow: 0 0 16px var(--soc-red-glow-strong), inset 0 0 10px rgba(255, 49, 49, 0.2);
  animation: pulse-denied 1.5s ease-in-out infinite;
}

@keyframes pulse-denied {
  0%, 100% { box-shadow: 0 0 16px var(--soc-red-glow-strong), inset 0 0 10px rgba(255, 49, 49, 0.2); }
  50% { box-shadow: 0 0 24px var(--soc-red-glow-strong), inset 0 0 14px rgba(255, 49, 49, 0.3); }
}

/* Responsive */
@media (max-width: 1024px) {
  .dashboard-grid {
    flex-direction: column;
  }

  .sidebar {
    width: 200px;
  }

  .logo h2 {
    font-size: 1.1rem;
  }

  .top-bar h1 {
    font-size: 1.3rem;
  }

  .top-bar {
    padding: 16px 24px;
  }

  .dashboard-grid {
    padding: 24px;
    gap: 24px;
  }

  .main-tabs {
    padding: 0 24px;
  }
}

/* Scrollbar Styling */
::-webkit-scrollbar {
  width: 12px;
  height: 12px;
}

::-webkit-scrollbar-track {
  background: linear-gradient(180deg, var(--soc-midnight-light) 0%, var(--soc-midnight) 100%);
}

::-webkit-scrollbar-thumb {
  background: linear-gradient(180deg, var(--soc-indigo) 0%, var(--soc-cyan) 100%);
  border-radius: 6px;
  border: 3px solid var(--soc-midnight);
  box-shadow: 0 0 10px rgba(99, 102, 241, 0.4);
}

::-webkit-scrollbar-thumb:hover {
  background: linear-gradient(180deg, var(--soc-indigo-bright) 0%, var(--soc-indigo) 100%);
  box-shadow: 0 0 20px rgba(99, 102, 241, 0.8);
}
</style>
