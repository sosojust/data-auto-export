<template>
  <div class="home">
    <el-row :gutter="20" class="stats-row">
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-number">{{ stats.total_tasks }}</div>
            <div class="stat-label">总任务数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-number">{{ stats.active_tasks }}</div>
            <div class="stat-label">活跃任务</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-number">{{ stats.recent_success_rate }}</div>
            <div class="stat-label">最近成功率</div>
          </div>
        </el-card>
      </el-col>
    </el-row>



    <el-row>
      <el-col :span="24">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>最近执行日志</span>
              <el-button text @click="$router.push('/logs')">
                查看全部
              </el-button>
            </div>
          </template>
          <RecentLogs />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import RecentLogs from '../components/RecentLogs.vue'
import api from '../utils/api'

const stats = ref({
  total_tasks: 0,
  active_tasks: 0,
  recent_success_rate: '0%'
})

const fetchStats = async () => {
  try {
    // 获取任务统计 - 先获取总数
    const tasksResponse = await api.get('/api/tasks?per_page=1')
    if (tasksResponse.data.success) {
      stats.value.total_tasks = tasksResponse.data.data.total
    }
    
    // 获取所有任务来统计活跃任务数量
    const allTasksResponse = await api.get('/api/tasks?per_page=1000') // 获取足够多的任务
    if (allTasksResponse.data.success) {
      stats.value.active_tasks = allTasksResponse.data.data.tasks.filter((task: any) => task.status === 'active').length
    }
    
    // 获取最近执行成功率（可以根据需要实现）
    const logsResponse = await api.get('/api/logs?per_page=10')
    if (logsResponse.data.success) {
      const logs = logsResponse.data.data.logs
      const successCount = logs.filter((log: any) => log.status === 'success').length
      stats.value.recent_success_rate = logs.length > 0 ? `${Math.round(successCount / logs.length * 100)}%` : '0%'
    }
  } catch (error) {
    console.error('获取统计数据失败:', error)
  }
}

onMounted(() => {
  fetchStats()
})
</script>

<style scoped>
.home {
  padding: 0;
}

.stats-row {
  margin-bottom: 20px;
}

.stat-card {
  text-align: center;
}

.stat-content {
  padding: 20px;
}

.stat-number {
  font-size: 2.5em;
  font-weight: bold;
  color: #3498db;
  margin-bottom: 10px;
}

.stat-label {
  color: #7f8c8d;
  font-size: 14px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>