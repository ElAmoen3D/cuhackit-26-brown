<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { AlertTriangle, TrendingUp, Shield, Activity, Zap, Clock } from 'lucide-vue-next'

interface SuspiciousActivity {
  face_id: string
  suspicion_score: number
  risk_level: string
  activities: string[]
  reasoning: string
  timestamp: number
  time_str: string
}

interface ActivitySummary {
  face_id: string
  total_detections: number
  suspicious_count: number
  avg_suspicion: number
  max_suspicion: number
  risk_trend: string
  latest_analysis?: SuspiciousActivity
}

const suspiciousActivities = ref<SuspiciousActivity[]>([])
const totalSuspiciousCount = ref(0)
const isLoading = ref(false)
const lastFetched = ref<string>('--:--:--')
let fetchTimer: ReturnType<typeof setInterval> | null = null

const riskColors = {
  'LOW': '#22c55e',
  'MEDIUM': '#f59e0b',
  'HIGH': '#ff3131'
}

const trendIcons = {
  'INCREASING': '📈',
  'DECREASING': '📉',
  'STABLE': '➡️',
  'INSUFFICIENT_DATA': '❓'
}

async function fetchSuspiciousActivities() {
  try {
    isLoading.value = true
    const response = await fetch('/suspicious-activities')
    const ct = response.headers.get('content-type') ?? ''
    if (!ct.includes('application/json')) {
      // Server returned HTML (e.g. error page) — treat as offline
      suspiciousActivities.value = []
      return
    }
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }
    const data = await response.json()
    suspiciousActivities.value = data.activities || []
    totalSuspiciousCount.value = data.total_count || 0
    lastFetched.value = new Date().toLocaleTimeString('en-US', { hour12: false })
  } catch (error) {
    console.error('Failed to fetch suspicious activities:', error)
    // Silently fail - backend might not be available yet
  } finally {
    isLoading.value = false
  }
}

async function getActivitySummary(faceId: string): Promise<ActivitySummary | null> {
  try {
    const response = await fetch(`/activity-summary/${faceId}`)
    if (!response.ok) return null
    const ct = response.headers.get('content-type') ?? ''
    if (!ct.includes('application/json')) return null
    return await response.json()
  } catch (error) {
    console.error(`Failed to fetch activity summary for ${faceId}:`, error)
    return null
  }
}

const highRiskActivities = computed(() => {
  return suspiciousActivities.value.filter(a => a.risk_level === 'HIGH')
})

const mediumRiskActivities = computed(() => {
  return suspiciousActivities.value.filter(a => a.risk_level === 'MEDIUM')
})

const lowRiskActivities = computed(() => {
  return suspiciousActivities.value.filter(a => a.risk_level === 'LOW')
})

const riskDistribution = computed(() => {
  return {
    high: highRiskActivities.value.length,
    medium: mediumRiskActivities.value.length,
    low: lowRiskActivities.value.length,
    total: suspiciousActivities.value.length
  }
})

const averageSuspicion = computed(() => {
  if (suspiciousActivities.value.length === 0) return 0
  const sum = suspiciousActivities.value.reduce((acc, a) => acc + a.suspicion_score, 0)
  return (sum / suspiciousActivities.value.length).toFixed(3)
})

onMounted(() => {
  fetchSuspiciousActivities()
  fetchTimer = setInterval(fetchSuspiciousActivities, 3000) // Fetch every 3 seconds
})

onUnmounted(() => {
  if (fetchTimer) clearInterval(fetchTimer)
})

const getSuspicionColor = (score: number): string => {
  if (score >= 0.7) return '#ff3131'
  if (score >= 0.4) return '#f59e0b'
  return '#22c55e'
}
</script>

<template>
  <div class="activity-analyzer">
    <div class="analyzer-header">
      <div class="header-title">
        <Zap :size="20" style="color: #6366f1" />
        <h3>Gemini Activity Analysis</h3>
      </div>
      <div class="header-stats">
        <span class="stat-badge high">
          <AlertTriangle :size="14" />
          {{ riskDistribution.high }} HIGH
        </span>
        <span class="stat-badge medium">
          <Activity :size="14" />
          {{ riskDistribution.medium }} MEDIUM
        </span>
        <span class="stat-badge low">
          <Shield :size="14" />
          {{ riskDistribution.low }} LOW
        </span>
      </div>
      <div class="last-update">
        Updated: {{ lastFetched }}
      </div>
    </div>

    <!-- Risk Distribution Chart -->
    <div class="distribution-card">
      <div class="dist-title">Risk Distribution</div>
      <div class="dist-bars">
        <div class="dist-bar">
          <div class="bar-label">HIGH RISK</div>
          <div class="bar-container">
            <div 
              class="bar-fill high"
              :style="{ width: riskDistribution.total > 0 ? (riskDistribution.high / riskDistribution.total * 100) + '%' : '0%' }"
            >
              {{ riskDistribution.high }}
            </div>
          </div>
        </div>
        <div class="dist-bar">
          <div class="bar-label">MEDIUM RISK</div>
          <div class="bar-container">
            <div 
              class="bar-fill medium"
              :style="{ width: riskDistribution.total > 0 ? (riskDistribution.medium / riskDistribution.total * 100) + '%' : '0%' }"
            >
              {{ riskDistribution.medium }}
            </div>
          </div>
        </div>
        <div class="dist-bar">
          <div class="bar-label">LOW RISK</div>
          <div class="bar-container">
            <div 
              class="bar-fill low"
              :style="{ width: riskDistribution.total > 0 ? (riskDistribution.low / riskDistribution.total * 100) + '%' : '0%' }"
            >
              {{ riskDistribution.low }}
            </div>
          </div>
        </div>
      </div>
      <div class="dist-summary">
        Total Detections: {{ riskDistribution.total }} | Avg Suspicion: {{ averageSuspicion }}
      </div>
    </div>

    <!-- Activity List -->
    <div class="activities-section">
      <div class="section-title">Recent Suspicious Activities</div>
      
      <div v-if="suspiciousActivities.length === 0" class="empty-state">
        <Shield :size="40" />
        <p>No suspicious activities detected</p>
        <p class="empty-sub">Unknown faces will be analyzed in real-time</p>
      </div>

      <div v-else class="activities-list">
        <div
          v-for="(activity, idx) in suspiciousActivities"
          :key="`${activity.face_id}-${activity.timestamp}`"
          class="activity-item"
          :class="activity.risk_level.toLowerCase()"
        >
          <div class="activity-risk">
            <div class="risk-badge" :style="{ backgroundColor: riskColors[activity.risk_level] }">
              {{ activity.risk_level }}
            </div>
            <div class="risk-score">
              Suspicion: <strong>{{ (activity.suspicion_score * 100).toFixed(1) }}%</strong>
            </div>
          </div>

          <div class="activity-content">
            <div class="activity-id">
              <strong>Face ID:</strong> {{ activity.face_id }}
            </div>
            <div class="activity-time">
              <Clock :size="13" />
              {{ activity.time_str }}
            </div>
            
            <div v-if="activity.activities && activity.activities.length > 0" class="activities-tags">
              <span 
                v-for="act in activity.activities.filter(a => a.trim())"
                :key="act"
                class="tag"
              >
                {{ act.trim() }}
              </span>
            </div>

            <div class="activity-reasoning">
              <p>{{ activity.reasoning }}</p>
            </div>
          </div>

          <div class="activity-score-indicator">
            <div 
              class="score-bar"
              :style="{
                backgroundColor: getSuspicionColor(activity.suspicion_score),
                height: (activity.suspicion_score * 100) + '%'
              }"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
:root {
  --bg:            #080b10;
  --bg-mid:        #0d1117;
  --bg-light:      #161b22;
  --indigo:        #6366f1;
  --indigo-bright: #818cf8;
  --neon-red:      #ff3131;
  --cyan:          #00d9ff;
  --green:         #22c55e;
  --amber:         #f59e0b;
  --text:          #e1e8ed;
  --text-dim:      #8b95a5;
  --text-muted:    #4b5563;
  --border:        #2d333b;
  --mono:          'IBM Plex Mono', 'JetBrains Mono', monospace;
}

.activity-analyzer {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 16px;
  background: linear-gradient(135deg, var(--bg-light) 0%, var(--bg-mid) 100%);
  border: 1px solid var(--border);
  border-radius: 8px;
  font-family: var(--mono);
  color: var(--text);
}

.analyzer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border);
  flex-wrap: wrap;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
  min-width: 250px;
}

.header-title h3 {
  font-size: 0.95rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--indigo-bright);
  margin: 0;
}

.header-stats {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.stat-badge {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 5px 10px;
  border-radius: 4px;
  font-size: 0.65rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  border: 1px solid;
}

.stat-badge.high {
  background: rgba(255, 49, 49, 0.12);
  color: var(--neon-red);
  border-color: rgba(255, 49, 49, 0.3);
}

.stat-badge.medium {
  background: rgba(245, 158, 11, 0.12);
  color: var(--amber);
  border-color: rgba(245, 158, 11, 0.3);
}

.stat-badge.low {
  background: rgba(34, 197, 94, 0.12);
  color: var(--green);
  border-color: rgba(34, 197, 94, 0.3);
}

.last-update {
  font-size: 0.65rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.distribution-card {
  padding: 12px;
  background: rgba(99, 102, 241, 0.08);
  border: 1px solid var(--border);
  border-radius: 6px;
}

.dist-title {
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  color: var(--indigo-bright);
  letter-spacing: 0.08em;
  margin-bottom: 10px;
}

.dist-bars {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 10px;
}

.dist-bar {
  display: flex;
  align-items: center;
  gap: 8px;
}

.bar-label {
  font-size: 0.65rem;
  font-weight: 600;
  text-transform: uppercase;
  color: var(--text-muted);
  width: 90px;
}

.bar-container {
  flex: 1;
  height: 24px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 3px;
  overflow: hidden;
  border: 1px solid var(--border);
}

.bar-fill {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.65rem;
  font-weight: 700;
  color: white;
  transition: width 0.3s ease;
}

.bar-fill.high {
  background: var(--neon-red);
}

.bar-fill.medium {
  background: var(--amber);
}

.bar-fill.low {
  background: var(--green);
}

.dist-summary {
  font-size: 0.65rem;
  color: var(--text-muted);
  text-align: center;
  padding-top: 8px;
  border-top: 1px solid var(--border);
}

.activities-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.section-title {
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  color: var(--indigo-bright);
  letter-spacing: 0.08em;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 40px 20px;
  color: var(--text-muted);
  text-align: center;
}

.empty-state svg {
  opacity: 0.3;
}

.empty-sub {
  font-size: 0.7rem;
  opacity: 0.7;
}

.activities-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 400px;
  overflow-y: auto;
}

.activity-item {
  display: flex;
  gap: 12px;
  padding: 12px;
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid var(--border);
  border-radius: 6px;
  border-left: 4px solid;
  transition: all 0.3s ease;
}

.activity-item.high {
  border-left-color: var(--neon-red);
}

.activity-item.medium {
  border-left-color: var(--amber);
}

.activity-item.low {
  border-left-color: var(--green);
}

.activity-item:hover {
  background: rgba(99, 102, 241, 0.1);
  transform: translateX(4px);
}

.activity-risk {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 100px;
}

.risk-badge {
  padding: 4px 8px;
  border-radius: 3px;
  font-size: 0.6rem;
  font-weight: 700;
  color: white;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  text-align: center;
}

.risk-score {
  font-size: 0.65rem;
  color: var(--text-dim);
}

.activity-content {
  flex: 1;
  min-width: 0;
}

.activity-id {
  font-size: 0.7rem;
  color: var(--text-dim);
  margin-bottom: 4px;
}

.activity-time {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 0.65rem;
  color: var(--text-muted);
  margin-bottom: 6px;
}

.activities-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-bottom: 8px;
}

.tag {
  display: inline-block;
  padding: 2px 6px;
  background: rgba(99, 102, 241, 0.2);
  border: 1px solid rgba(99, 102, 241, 0.4);
  border-radius: 2px;
  font-size: 0.6rem;
  color: var(--indigo-bright);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.activity-reasoning {
  font-size: 0.68rem;
  color: var(--text-dim);
  line-height: 1.4;
}

.activity-reasoning p {
  margin: 0;
}

.activity-score-indicator {
  width: 4px;
  height: 80px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 2px;
  overflow: hidden;
  position: relative;
}

.score-bar {
  position: absolute;
  bottom: 0;
  width: 100%;
  transition: all 0.3s ease;
}

::-webkit-scrollbar {
  width: 4px;
}

::-webkit-scrollbar-track {
  background: var(--bg-mid);
  border-radius: 2px;
}

::-webkit-scrollbar-thumb {
  background: var(--indigo);
  border-radius: 2px;
}

::-webkit-scrollbar-thumb:hover {
  background: var(--indigo-bright);
}

@media (max-width: 600px) {
  .analyzer-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .header-stats {
    width: 100%;
  }

  .activity-item {
    flex-wrap: wrap;
  }

  .activities-list {
    max-height: 300px;
  }
}
</style>
