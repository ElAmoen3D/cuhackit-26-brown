<script setup>
import { ref } from 'vue'

const activeTab = ref('live')
const currentPage = ref('dashboard') // 'dashboard' or 'logs'

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
</script>

<template>
  <div class="dashboard-container">
    <!-- Sidebar -->
    <aside class="sidebar">
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
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&display=swap');

/* CSS Variables for SOC Theme */
:root {
  --soc-midnight: #0B0E14;
  --soc-midnight-light: #161B22;
  --soc-midnight-lighter: #21262D;
  --soc-indigo: #6366F1;
  --soc-indigo-bright: #818CF8;
  --soc-indigo-dark: #4F46E5;
  --soc-neon-red: #FF3131;
  --soc-red-glow: rgba(255, 49, 49, 0.3);
  --soc-text-primary: #E1E8ED;
  --soc-text-secondary: #8B95A5;
  --soc-border: #2D333B;
  --soc-grid: rgba(99, 102, 241, 0.1);
}

/* Layout */
.dashboard-container {
  display: flex;
  height: 100vh;
  background-color: var(--soc-midnight);
  color: var(--soc-text-primary);
  font-family: 'JetBrains Mono', monospace;
}

/* Sidebar */
.sidebar {
  width: 250px;
  background: linear-gradient(180deg, var(--soc-midnight) 0%, var(--soc-midnight-light) 100%);
  color: var(--soc-text-primary);
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  border-right: 1px solid var(--soc-border);
  box-shadow: inset -1px 0 0 rgba(99, 102, 241, 0.1);
}

.logo {
  padding: 24px 20px;
  border-bottom: 1px solid var(--soc-border);
  flex-shrink: 0;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.1) 0%, transparent 100%);
}

.logo h2 {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--soc-indigo-bright);
  letter-spacing: 0.05em;
  text-transform: uppercase;
  text-shadow: 0 0 20px rgba(99, 102, 241, 0.3);
}

.sidebar nav ul {
  list-style: none;
  padding: 0;
  margin: 0;
  flex-shrink: 0;
}

.sidebar nav li {
  padding: 14px 20px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  color: var(--soc-text-secondary);
  border-left: 3px solid transparent;
  position: relative;
}

.sidebar nav li:hover {
  background-color: rgba(99, 102, 241, 0.1);
  color: var(--soc-indigo-bright);
  border-left-color: var(--soc-indigo);
}

.sidebar nav li.active {
  background-color: rgba(99, 102, 241, 0.15);
  color: var(--soc-indigo-bright);
  border-left-color: var(--soc-indigo);
  box-shadow: inset 0 0 20px rgba(99, 102, 241, 0.05);
}

/* Main Content */
.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: linear-gradient(135deg, var(--soc-midnight) 0%, var(--soc-midnight-light) 100%);
}

/* Header */
.top-bar {
  background: linear-gradient(90deg, var(--soc-midnight-light) 0%, var(--soc-midnight-lighter) 100%);
  padding: 20px 30px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.5), 0 0 1px var(--soc-indigo);
  border-bottom: 1px solid var(--soc-border);
}

.top-bar h1 {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--soc-indigo-bright);
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.login-btn {
  background: linear-gradient(135deg, var(--soc-indigo) 0%, var(--soc-indigo-dark) 100%);
  color: white;
  border: 1px solid var(--soc-indigo-bright);
  padding: 10px 20px;
  border-radius: 4px;
  cursor: pointer;
  font-weight: 600;
  font-family: 'JetBrains Mono', monospace;
  transition: all 0.3s ease;
  box-shadow: 0 0 10px rgba(99, 102, 241, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.1);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.login-btn:hover {
  background: linear-gradient(135deg, var(--soc-indigo-bright) 0%, var(--soc-indigo) 100%);
  box-shadow: 0 0 20px rgba(99, 102, 241, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.2);
}

.login-btn:active {
  box-shadow: 0 0 20px rgba(99, 102, 241, 0.5), inset 0 2px 4px rgba(0, 0, 0, 0.3);
}

/* Dashboard Grid */
.dashboard-grid {
  padding: 30px;
  display: flex;
  gap: 30px;
  overflow-y: auto;
  height: 100%;
  flex: 1;
  background: radial-gradient(circle at 20% 50%, rgba(99, 102, 241, 0.05) 0%, transparent 50%);
}

.card {
  background: linear-gradient(135deg, var(--soc-midnight-light) 0%, var(--soc-midnight-lighter) 100%);
  border-radius: 6px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4), 0 0 20px rgba(99, 102, 241, 0.1);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid var(--soc-border);
  position: relative;
  backdrop-filter: blur(10px);
}

.card.full-width {
  width: 100%;
  flex: 1;
}

.card-header {
  padding: 20px;
  border-bottom: 1px solid var(--soc-border);
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: linear-gradient(90deg, rgba(99, 102, 241, 0.05) 0%, transparent 100%);
}

.card-header h3 {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--soc-indigo-bright);
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

/* Main Tabs */
.main-tabs {
  padding: 0 30px;
  display: flex;
  gap: 30px;
  border-bottom: 1px solid var(--soc-border);
  background: linear-gradient(90deg, var(--soc-midnight-light) 0%, var(--soc-midnight-lighter) 100%);
}

.main-tab-btn {
  background: none;
  border: none;
  font-size: 1rem;
  font-weight: 600;
  color: var(--soc-text-secondary);
  cursor: pointer;
  padding: 15px 0;
  border-bottom: 3px solid transparent;
  transition: all 0.3s ease;
  font-family: 'JetBrains Mono', monospace;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  position: relative;
}

.main-tab-btn:hover {
  color: var(--soc-indigo-bright);
  background: rgba(99, 102, 241, 0.05);
}

.main-tab-btn.active {
  color: var(--soc-indigo-bright);
  border-bottom-color: var(--soc-indigo);
  box-shadow: 0 2px 8px rgba(99, 102, 241, 0.2);
}

/* Live Feed Specifics */
.live-indicator {
  color: var(--soc-neon-red);
  font-weight: 700;
  font-size: 0.8rem;
  animation: pulse-glow 1.5s cubic-bezier(0.4, 0, 0.6, 1) infinite;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  filter: drop-shadow(0 0 8px var(--soc-red-glow));
}

@keyframes pulse-glow {
  0% {
    opacity: 1;
    filter: drop-shadow(0 0 8px var(--soc-red-glow));
  }
  50% {
    opacity: 0.6;
    filter: drop-shadow(0 0 4px var(--soc-red-glow));
  }
  100% {
    opacity: 1;
    filter: drop-shadow(0 0 8px var(--soc-red-glow));
  }
}

.video-placeholder {
  background: linear-gradient(135deg, #000814 0%, #1a1a2e 100%);
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
      rgba(99, 102, 241, 0.03) 0px,
      rgba(99, 102, 241, 0.03) 1px,
      transparent 1px,
      transparent 2px
    );
  pointer-events: none;
  animation: flicker 0.15s infinite;
}

@keyframes flicker {
  0% { opacity: 0.97; }
  50% { opacity: 0.98; }
  100% { opacity: 0.97; }
}

.camera-overlay {
  position: absolute;
  top: 15px;
  left: 15px;
  color: var(--soc-indigo-bright);
  background: rgba(11, 14, 20, 0.8);
  padding: 8px 12px;
  border-radius: 4px;
  font-size: 0.8rem;
  border: 1px solid var(--soc-indigo);
  box-shadow: 0 0 10px rgba(99, 102, 241, 0.3);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-weight: 600;
}

.placeholder-content {
  text-align: center;
  z-index: 10;
  position: relative;
}

.placeholder-content svg {
  stroke: var(--soc-indigo-bright);
  filter: drop-shadow(0 0 10px rgba(99, 102, 241, 0.4));
  margin-bottom: 12px;
}

.placeholder-content p {
  color: var(--soc-text-secondary);
  font-size: 0.9rem;
}

/* Detected People Tab */
.detected-container {
  padding: 20px;
  flex: 1;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.03) 0%, transparent 100%);
  overflow-y: auto;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 15px;
  border-top: 1px solid var(--soc-border);
}

.detected-item {
  background: linear-gradient(135deg, var(--soc-midnight-light) 0%, var(--soc-midnight-lighter) 100%);
  padding: 15px;
  border-radius: 6px;
  border: 1px solid var(--soc-border);
  display: flex;
  flex-direction: column;
  gap: 10px;
  transition: all 0.3s ease;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

.detected-item:hover {
  border-color: var(--soc-indigo);
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.2);
  background: linear-gradient(135deg, var(--soc-midnight-lighter) 0%, rgba(99, 102, 241, 0.05) 100%);
}

.person-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.person-name {
  font-weight: 700;
  color: var(--soc-indigo-bright);
  font-size: 0.95rem;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.match-badge {
  font-size: 0.75rem;
  padding: 4px 8px;
  border-radius: 4px;
  background-color: rgba(99, 102, 241, 0.2);
  color: var(--soc-indigo-bright);
  border: 1px solid var(--soc-indigo);
  text-transform: uppercase;
  letter-spacing: 0.03em;
  font-weight: 600;
  width: fit-content;
}

.match-badge.known {
  background-color: rgba(34, 197, 94, 0.2);
  color: #22C55E;
  border-color: #22C55E;
}

.match-badge.unknown {
  background-color: var(--soc-red-glow);
  color: var(--soc-neon-red);
  border-color: var(--soc-neon-red);
  box-shadow: 0 0 10px var(--soc-red-glow);
}

.add-person-btn {
  background: linear-gradient(135deg, var(--soc-indigo) 0%, var(--soc-indigo-dark) 100%);
  color: white;
  border: 1px solid var(--soc-indigo-bright);
  padding: 6px 12px;
  border-radius: 4px;
  font-size: 0.85rem;
  cursor: pointer;
  font-family: 'JetBrains Mono', monospace;
  font-weight: 600;
  transition: all 0.3s ease;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  box-shadow: 0 0 8px rgba(99, 102, 241, 0.2);
}

.add-person-btn:hover {
  background: linear-gradient(135deg, var(--soc-indigo-bright) 0%, var(--soc-indigo) 100%);
  box-shadow: 0 0 15px rgba(99, 102, 241, 0.4);
}

/* Logs View */
.logs-view {
  padding: 30px;
  overflow-y: auto;
  height: 100%;
  background: radial-gradient(circle at 20% 50%, rgba(99, 102, 241, 0.05) 0%, transparent 50%);
}

.logs-card {
  width: 100%;
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
  background: linear-gradient(90deg, rgba(99, 102, 241, 0.1) 0%, transparent 100%);
  padding: 14px 20px;
  font-weight: 700;
  font-size: 0.8rem;
  color: var(--soc-indigo-bright);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  border-bottom: 1px solid var(--soc-indigo);
  border-right: 1px solid var(--soc-border);
}

th:last-child {
  border-right: none;
}

td {
  padding: 14px 20px;
  border-bottom: 1px solid var(--soc-border);
  font-size: 0.9rem;
  color: var(--soc-text-primary);
  font-family: 'JetBrains Mono', monospace;
  transition: all 0.2s ease;
}

tr:hover td {
  background-color: rgba(99, 102, 241, 0.05);
}

.status-badge {
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border: 1px solid;
  display: inline-block;
}

.status-badge.authorized {
  background-color: rgba(34, 197, 94, 0.2);
  color: #22C55E;
  border-color: #22C55E;
  box-shadow: 0 0 8px rgba(34, 197, 94, 0.2);
}

.status-badge.pending {
  background-color: rgba(245, 158, 11, 0.2);
  color: #F59E0B;
  border-color: #F59E0B;
  box-shadow: 0 0 8px rgba(245, 158, 11, 0.2);
}

.status-badge.denied {
  background-color: var(--soc-red-glow);
  color: var(--soc-neon-red);
  border-color: var(--soc-neon-red);
  box-shadow: 0 0 12px var(--soc-red-glow), inset 0 0 8px var(--soc-red-glow);
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
    font-size: 1.2rem;
  }

  .top-bar h1 {
    font-size: 1.2rem;
  }
}

/* Scrollbar Styling */
::-webkit-scrollbar {
  width: 10px;
}

::-webkit-scrollbar-track {
  background: var(--soc-midnight);
}

::-webkit-scrollbar-thumb {
  background: linear-gradient(180deg, var(--soc-indigo) 0%, var(--soc-indigo-dark) 100%);
  border-radius: 5px;
  border: 2px solid var(--soc-midnight-light);
}

::-webkit-scrollbar-thumb:hover {
  background: linear-gradient(180deg, var(--soc-indigo-bright) 0%, var(--soc-indigo) 100%);
  box-shadow: 0 0 10px rgba(99, 102, 241, 0.5);
}
</style>