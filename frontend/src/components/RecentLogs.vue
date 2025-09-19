<template>
  <div class="recent-logs">
    <el-table :data="logs" v-loading="loading" empty-text="暂无执行日志">
      <el-table-column prop="task_name" label="任务名称" width="180" />
      <el-table-column prop="status_text" label="执行状态" width="100">
        <template #default="{ row }">
          <el-tag :type="getStatusType(row.status)">{{ row.status_text }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="start_time" label="开始时间" width="160" />
      <el-table-column prop="duration_text" label="耗时" width="80" />
      <el-table-column prop="rows_affected" label="影响行数" width="90" />
      <el-table-column prop="error_message" label="错误信息" min-width="200">
        <template #default="{ row }">
          <span v-if="row.error_message">
            {{ row.error_message.length > 40 ? row.error_message.substring(0, 40) + '...' : row.error_message }}
          </span>
          <span v-else>-</span>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '../utils/api'

const logs = ref([])
const loading = ref(false)

const getStatusType = (status: string) => {
  const statusMap: Record<string, string> = {
    success: 'success',
    failed: 'danger',
    running: 'warning',
    cancelled: 'info'
  }
  return statusMap[status] || 'info'
}

const formatDuration = (duration: number | null) => {
  if (!duration) return '-'
  if (duration < 1) return `${Math.round(duration * 1000)}ms`
  return `${duration.toFixed(2)}s`
}

const getStatusText = (status: string) => {
  const statusMap: Record<string, string> = {
    success: '成功',
    failed: '失败',
    running: '运行中',
    cancelled: '已取消'
  }
  return statusMap[status] || status
}

const fetchLogs = async () => {
  loading.value = true
  try {
    const response = await api.get('/api/logs?page=1&per_page=5')
    if (response.data.success) {
      // 处理数据，添加前端需要的字段
      logs.value = response.data.data.logs.map((log: any) => ({
        ...log,
        status_text: getStatusText(log.status),
        duration_text: formatDuration(log.duration)
      }))
    }
  } catch (error) {
    console.error('获取日志失败:', error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchLogs()
})
</script>

<style scoped>
.recent-logs {
  width: 100%;
}
</style>