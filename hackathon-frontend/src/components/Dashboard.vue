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
/* Layout */
.dashboard-container {
  display: flex;
  height: 100vh;
  background-color: #eafaf1;
  color: #1f2937;
}

/* Sidebar */
.sidebar {
  width: 250px;
  background-color: #065f46;
  color: white;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}

.logo {
  padding: 20px;
  border-bottom: 1px solid #059669;
  flex-shrink: 0;
}

.logo h2 {
  margin: 0;
  font-size: 1.5rem;
  color: var(--vt-c-green-light);
}

.sidebar nav ul {
  list-style: none;
  padding: 0;
  margin: 20px 0;
  flex-shrink: 0;
}

.sidebar nav li {
  padding: 15px 20px;
  cursor: pointer;
  transition: background 0.2s;
}

.sidebar nav li:hover, .sidebar nav li.active {
  background-color: #059669;
  border-left: 4px solid var(--vt-c-green-light);
}

/* Main Content */
.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* Header */
.top-bar {
  background-color: white;
  padding: 15px 30px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.top-bar h1 {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--vt-c-green-dark);
}

.login-btn {
  background-color: var(--vt-c-green-dark);
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
  transition: background 0.2s;
}

.login-btn:hover {
  background-color: var(--vt-c-green);
}

/* Dashboard Grid */
.dashboard-grid {
  padding: 30px;
  display: flex;
  gap: 30px;
  overflow-y: auto;
  height: 100%;
  flex: 1;
}

.card {
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.card.full-width {
  width: 100%;
  flex: 1;
}

.card-header {
  padding: 20px;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header h3 {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--vt-c-green-dark);
}

/* Main Tabs */
.main-tabs {
  padding: 0 30px;
  display: flex;
  gap: 30px;
  border-bottom: 1px solid #e5e7eb;
  background: white;
}

.main-tab-btn {
  background: none;
  border: none;
  font-size: 1.1rem;
  font-weight: 500;
  color: #6b7280;
  cursor: pointer;
  padding: 15px 0;
  border-bottom: 3px solid transparent;
  transition: all 0.2s;
}

.main-tab-btn.active {
  color: var(--vt-c-green-dark);
  border-bottom-color: var(--vt-c-green-dark);
}

.main-tab-btn:hover {
  color: var(--vt-c-green-dark);
}

/* Live Feed Specifics */
.live-indicator {
  color: var(--vt-c-green-dark);
  font-weight: bold;
  font-size: 0.8rem;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% { opacity: 1; }
  50% { opacity: 0.5; }
  100% { opacity: 1; }
}

.video-placeholder {
  background-color: #000;
  flex: 1;
  min-height: 500px;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #6b7280;
}

.camera-overlay {
  position: absolute;
  top: 15px;
  left: 15px;
  color: white;
  background: rgba(0,0,0,0.5);
  padding: 5px 10px;
  border-radius: 4px;
  font-size: 0.8rem;
}

.placeholder-content {
  text-align: center;
}

/* Detected People Tab */
.detected-container {
  padding: 20px;
  flex: 1;
  background-color: #f9fafb;
  overflow-y: auto;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 15px;
}

.detected-item {
  background: white;
  padding: 15px;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.person-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.person-name {
  font-weight: 600;
  color: var(--vt-c-green-dark);
}

.match-badge {
  font-size: 0.75rem;
  padding: 2px 8px;
  border-radius: 4px;
  background-color: #e5e7eb;
  color: #374151;
}

.match-badge.known {
  background-color: #d1fae5;
  color: #065f46;
}

.match-badge.unknown {
  background-color: #d1fae5;
  color: #065f46;
}

.add-person-btn {
  background-color: var(--vt-c-green-dark);
  color: white;
  border: none;
  padding: 6px 12px;
  border-radius: 4px;
  font-size: 0.85rem;
  cursor: pointer;
}

.add-person-btn:hover {
  background-color: var(--vt-c-green);
}

/* Logs View */
.logs-view {
  padding: 30px;
  overflow-y: auto;
  height: 100%;
}

.logs-card {
  width: 100%;
}

.table-container {
  padding: 0;
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
}

th {
  background-color: #f9fafb;
  padding: 12px 20px;
  font-weight: 600;
  font-size: 0.85rem;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

td {
  padding: 15px 20px;
  border-bottom: 1px solid #e5e7eb;
  font-size: 0.95rem;
}

.status-badge {
  padding: 4px 8px;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 600;
}

.status-badge.authorized {
  background-color: #d1fae5;
  color: #065f46;
}

.status-badge.pending {
  background-color: #fbbf24;
  color: #78350f;
}

.status-badge.denied {
  background-color: #f87171;
  color: #7f1d1d;
}

/* Responsive */
@media (max-width: 1024px) {
  .dashboard-grid {
    flex-direction: column;
  }

  .sidebar {
    width: 200px;
  }
}
</style>