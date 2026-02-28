import { ref, watch } from 'vue'

const API_BASE_URL = 'http://localhost:8080'

export function useSurveillanceAPI() {
  const data = ref({
    known: [],
    unknown: [],
    counts: { known: 0, unknown: 0, total: 0 },
    alerts: [],
    timestamp: Date.now() / 1000,
    _offline: false,
  })
  
  const isLoading = ref(false)
  const error = ref(null)
  const lastUpdate = ref(null)

  const fetchSurveillanceData = async () => {
    try {
      isLoading.value = true
      error.value = null
      
      const response = await fetch(`${API_BASE_URL}/data`, {
        cache: 'no-store',
      })
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      
      const result = await response.json()
      data.value = result
      lastUpdate.value = new Date()
      
      return result
    } catch (err) {
      error.value = err.message
      console.error('Failed to fetch surveillance data:', err)
      // Return offline state
      data.value._offline = true
      return null
    } finally {
      isLoading.value = false
    }
  }

  const checkHealth = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/health`, {
        cache: 'no-store',
      })
      return response.ok
    } catch (err) {
      return false
    }
  }

  const getStreamUrl = () => {
    return `${API_BASE_URL}/live`
  }

  // Start polling for data
  let pollInterval = null

  const startPolling = (interval = 250) => {
    if (pollInterval) {
      clearInterval(pollInterval)
    }
    fetchSurveillanceData()
    pollInterval = setInterval(() => {
      fetchSurveillanceData()
    }, interval)
  }

  const stopPolling = () => {
    if (pollInterval) {
      clearInterval(pollInterval)
      pollInterval = null
    }
  }

  return {
    data,
    isLoading,
    error,
    lastUpdate,
    fetchSurveillanceData,
    checkHealth,
    getStreamUrl,
    startPolling,
    stopPolling,
  }
}
