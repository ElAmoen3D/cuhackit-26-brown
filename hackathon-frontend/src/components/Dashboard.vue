<script setup>
import { ref } from 'vue'

const activeTab = ref('live')

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
          <li class="active">Dashboard</li>
          <li>Live Feed</li>
          <li>Database</li>
          <li>Settings</li>
        </ul>
      </nav>
    </aside>

    <!-- Main Content -->
    <main class="main-content">
      <!-- Header -->
      <header class="top-bar">
        <h1>Dashboard Overview</h1>
        <button class="login-btn">Login</button>
      </header>

      <!-- Dashboard Grid -->
      <div class="dashboard-grid">
        <!-- Live Feed Section -->
        <div class="card camera-card">
          <div class="card-header">
            <div class="tabs">
              <button 
                :class="['tab-btn', { active: activeTab === 'live' }]" 
                @click="activeTab = 'live'"
              >
                Live Feed
              </button>
              <button 
                :class="['tab-btn', { active: activeTab === 'detected' }]" 
                @click="activeTab = 'detected'"
              >
                Detected People
              </button>
            </div>
            <span v-if="activeTab === 'live'" class="live-indicator">● LIVE</span>
          </div>
          <div v-if="activeTab === 'live'" class="video-placeholder">
            <div class="camera-overlay">
              <p>Camera 01 - Main Entrance</p>
            </div>
            <!-- Placeholder for video stream -->
            <div class="placeholder-content">
              <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M23 7l-7 5 7 5V7z"></path><rect x="1" y="5" width="15" height="14" rx="2" ry="2"></rect></svg>
              <p>Video Feed Unavailable in Prototype</p>
            </div>
          </div>
          <div v-else class="detected-container">
            <div v-for="person in detectedPeople" :key="person.id" class="detected-item">
              <div class="person-info">
                <span class="person-name">{{ person.name }}</span>
                <span :class="['match-badge', person.type]">{{ person.type === 'known' ? 'Match: ' + person.match : 'Unknown' }}</span>
              </div>
              <button v-if="person.type === 'unknown'" class="add-person-btn">Add Person</button>
            </div>
          </div>
        </div>

        <!-- Database Section -->
        <div class="card database-card">
          <div class="card-header">
            <h3>Recent Access Logs</h3>
            <button class="view-all-btn">View All</button>
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
    </main>
  </div>
</template>

<style scoped>
/* Layout */
.dashboard-container {
  display: flex;
  height: 100vh;
  background-color: #f3f4f6;
  color: #1f2937;
}

/* Sidebar */
.sidebar {
  width: 250px;
  background-color: #111827;
  color: white;
  display: flex;
  flex-direction: column;
}

.logo {
  padding: 20px;
  border-bottom: 1px solid #374151;
}

.logo h2 {
  margin: 0;
  font-size: 1.5rem;
  color: #60a5fa;
}

.sidebar nav ul {
  list-style: none;
  padding: 0;
  margin: 20px 0;
}

.sidebar nav li {
  padding: 15px 20px;
  cursor: pointer;
  transition: background 0.2s;
}

.sidebar nav li:hover, .sidebar nav li.active {
  background-color: #1f2937;
  border-left: 4px solid #60a5fa;
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
}

.login-btn {
  background-color: #2563eb;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
  transition: background 0.2s;
}

.login-btn:hover {
  background-color: #1d4ed8;
}

/* Dashboard Grid */
.dashboard-grid {
  padding: 30px;
  display: grid;
  grid-template-columns: 1fr;
  gap: 30px;
  overflow-y: auto;
  height: 100%;
}

.card {
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
  overflow: hidden;
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
}

/* Tabs */
.tabs {
  display: flex;
  gap: 20px;
}

.tab-btn {
  background: none;
  border: none;
  font-size: 1.1rem;
  font-weight: 500;
  color: #6b7280;
  cursor: pointer;
  padding-bottom: 5px;
  border-bottom: 2px solid transparent;
}

.tab-btn.active {
  color: #2563eb;
  border-bottom-color: #2563eb;
}

/* Live Feed Specifics */
.live-indicator {
  color: #ef4444;
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
  min-height: 400px;
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
  min-height: 400px;
  background-color: #f9fafb;
}

.detected-item {
  background: white;
  padding: 15px;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  margin-bottom: 10px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.person-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.person-name {
  font-weight: 600;
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
  background-color: #fee2e2;
  color: #991b1b;
}

.add-person-btn {
  background-color: #10b981;
  color: white;
  border: none;
  padding: 6px 12px;
  border-radius: 4px;
  font-size: 0.85rem;
  cursor: pointer;
}

.add-person-btn:hover {
  background-color: #059669;
}

/* Database Specifics */
.view-all-btn {
  background: none;
  border: none;
  color: #2563eb;
  cursor: pointer;
  font-size: 0.9rem;
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
  background-color: #fef3c7;
  color: #92400e;
}

.status-badge.denied {
  background-color: #fee2e2;
  color: #991b1b;
}

/* Responsive */
@media (max-width: 1024px) {
  .dashboard-grid {
    grid-template-columns: 1fr;
  }
}
</style>