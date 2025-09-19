<template>
  <div class="logs">
    <el-card>
      <template #header>
        <div class="card-header">
          <span v-if="taskName">执行日志 - {{ taskName }}</span>
          <span v-else>执行日志</span>
          <div v-if="taskName">
            <el-button @click="$router.push('/tasks')">返回任务列表</el-button>
            <el-button @click="$router.push('/logs')">查看所有日志</el-button>
          </div>
        </div>
      </template>
      
      <el-table :data="logs" v-loading="loading" empty-text="暂无执行日志">
        <el-table-column prop="execution_id" label="执行ID" width="120">
          <template #default="{ row }">
            {{ row.execution_id?.substring(0, 8) }}...
          </template>
        </el-table-column>
        <el-table-column prop="task_name" label="任务名称" width="200" />
        <el-table-column prop="status_text" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">{{ row.status_text }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="start_time" label="开始时间" width="180" />
        <el-table-column prop="end_time" label="结束时间" width="180" />
        <el-table-column prop="duration_text" label="耗时" width="100" />
        <el-table-column prop="rows_affected" label="影响行数" width="100" />
        <el-table-column prop="error_message" label="错误信息" min-width="200">
          <template #default="{ row }">
            <span v-if="row.error_message">
              {{ row.error_message.length > 50 ? row.error_message.substring(0, 50) + '...' : row.error_message }}
            </span>
            <span v-else>-</span>
          </template>
        </el-table-column>
      </el-table>
      
      <!-- 分页组件 -->
      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[20, 50, 100, 200]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import api from '../utils/api'

const route = useRoute()
const logs = ref([])
const loading = ref(false)
const taskName = ref('')
const currentPage = ref(1)
const pageSize = ref(50)
const total = ref(0)

const taskId = computed(() => route.query.task_id)

const getStatusType = (status) => {
  const statusMap = {
    success: 'success',
    failed: 'danger',
    running: 'warning',
    cancelled: 'info'
  }
  return statusMap[status] || 'info'
}

const formatDuration = (duration) => {
  if (!duration) return '-'
  if (duration < 1) return `${Math.round(duration * 1000)}ms`
  return `${duration.toFixed(2)}s`
}

const getStatusText = (status) => {
  const statusMap = {
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
    let url = `/api/logs?page=${currentPage.value}&per_page=${pageSize.value}`
    if (taskId.value) {
      url += `&task_id=${taskId.value}`
    }
    
    const response = await api.get(url)
    if (response.data.success) {
      const data = response.data.data
      
      // 处理数据，添加前端需要的字段
      logs.value = data.logs.map((log) => ({
        ...log,
        status_text: getStatusText(log.status),
        duration_text: formatDuration(log.duration)
      }))
      
      // 更新分页信息
      total.value = data.total
      
      // 如果是按任务过滤，获取任务名称
      if (taskId.value && logs.value.length > 0) {
        taskName.value = logs.value[0].task_name
      }
    }
  } catch (error) {
    console.error('获取执行日志失败:', error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchLogs()
})

// 分页事件处理
const handleSizeChange = (newSize) => {
  pageSize.value = newSize
  currentPage.value = 1 // 重置到第一页
  fetchLogs()
}

const handleCurrentChange = (newPage) => {
  currentPage.value = newPage
  fetchLogs()
}

// 监听路由参数变化
watch(() => route.query.task_id, () => {
  taskName.value = '' // 清空任务名称
  currentPage.value = 1 // 重置分页
  fetchLogs()
}, { immediate: false })
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.pagination-wrapper {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}
</style>