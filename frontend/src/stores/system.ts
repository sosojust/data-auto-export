import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../utils/api'

export const useSystemStore = defineStore('system', () => {
  const systemStatus = ref({
    running: false,
    scheduler_running: false,
    total_tasks: 0,
    active_tasks: 0,
    data_sources: 0,
    recent_success_rate: '0/0',
    uptime: '0秒'
  })

  const loading = ref(false)

  const fetchSystemStatus = async () => {
    loading.value = true
    try {
      const response = await api.get('/api/status')
      if (response.data.success) {
        systemStatus.value = response.data.data
      }
    } catch (error) {
      console.error('获取系统状态失败:', error)
    } finally {
      loading.value = false
    }
  }

  return {
    systemStatus,
    loading,
    fetchSystemStatus
  }
})