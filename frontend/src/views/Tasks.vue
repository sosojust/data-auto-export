<template>
  <div class="tasks">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>任务管理</span>
          <div class="header-buttons">
            <el-button type="warning" @click="reloadAllTasks">
              <el-icon><Refresh /></el-icon>
              重载所有定时任务
            </el-button>
            <el-button type="primary" @click="$router.push('/tasks/create')">
              <el-icon><Plus /></el-icon>
              创建新任务
            </el-button>
          </div>
        </div>
      </template>
      
      <el-table :data="tasks" v-loading="loading" empty-text="暂无任务">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="name" label="任务名称" width="200" />
        <el-table-column prop="created_by" label="创建人" width="120" />
        <el-table-column prop="data_source_name" label="数据源" width="150" />
        <el-table-column prop="execution_type_text" label="执行类型" width="120" />
        <el-table-column prop="status_text" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'danger'">
              {{ row.status_text }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="cron_expression" label="Cron表达式" width="150" />
        <el-table-column prop="last_execution_time" label="最后执行" width="180" />
        <el-table-column label="操作" width="300">
          <template #default="{ row }">
            <el-button size="small" type="success" @click="executeTask(row.id)">
              执行
            </el-button>
            <el-button size="small" type="warning" @click="testTask(row.id)">
              测试
            </el-button>
            <el-button size="small" @click="$router.push(`/tasks/${row.id}/edit`)">
              编辑
            </el-button>
            <el-button size="small" @click="$router.push(`/logs?task_id=${row.id}`)">
              执行日志
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
    
    <!-- 测试结果弹窗 -->
    <el-dialog
      v-model="testResultVisible"
      title="任务测试结果"
      width="80%"
      :before-close="closeTestResult"
    >
      <div v-if="testResult">
        <div class="test-info">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="执行状态">
              <el-tag :type="testResult.success ? 'success' : 'danger'">
                {{ testResult.success ? '成功' : '失败' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="数据行数">{{ testResult.row_count || 0 }}</el-descriptions-item>
            <el-descriptions-item label="执行时间">{{ testResult.execution_time?.toFixed(2) || 0 }}秒</el-descriptions-item>
            <el-descriptions-item label="字段数量">{{ testResult.columns?.length || 0 }}</el-descriptions-item>
          </el-descriptions>
        </div>
        
        <!-- 错误信息 -->
        <div v-if="testResult.errors && testResult.errors.length > 0" class="error-section">
          <h4>错误信息：</h4>
          <el-alert
            v-for="(error, index) in testResult.errors"
            :key="index"
            :title="error"
            type="error"
            :closable="false"
            style="margin-bottom: 8px;"
          />
        </div>
        
        <!-- 数据预览表格 -->
        <div v-if="testResult.data_preview && testResult.data_preview.length > 0" class="data-preview">
          <h4>数据预览（前10行）：</h4>
          <el-table
            :data="testResult.data_preview"
            border
            stripe
            max-height="400"
            style="width: 100%"
          >
            <el-table-column
              v-for="column in testResult.columns"
              :key="column"
              :prop="column"
              :label="column"
              :width="getColumnWidth(column)"
              show-overflow-tooltip
            >
              <template #default="{ row }">
                <span>{{ formatCellValue(row[column]) }}</span>
              </template>
            </el-table-column>
          </el-table>
        </div>
        
        <div v-else-if="testResult.success" class="no-data">
          <el-empty description="查询成功但无数据返回" />
        </div>
      </div>
      
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="closeTestResult">关闭</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElLoading } from 'element-plus'
import api, { longTaskApi } from '../utils/api'

const tasks = ref([])
const loading = ref(false)
const testResultVisible = ref(false)
const testResult = ref(null)

const getStatusText = (status) => {
  const statusMap = {
    active: '活跃',
    inactive: '停用',
    paused: '暂停'
  }
  return statusMap[status] || status
}

const getExecutionTypeText = (type) => {
  const typeMap = {
    sql: 'SQL查询',
    script: '脚本执行'
  }
  return typeMap[type] || type
}

const fetchTasks = async () => {
  loading.value = true
  try {
    const response = await api.get('/api/tasks')
    if (response.data.success) {
      // 处理数据，添加前端需要的字段
      tasks.value = response.data.data.tasks.map((task) => ({
        ...task,
        status_text: getStatusText(task.status),
        execution_type_text: getExecutionTypeText(task.execution_type)
        // data_source_name 现在直接从API返回，无需额外处理
      }))
    }
  } catch (error) {
    console.error('获取任务列表失败:', error)
  } finally {
    loading.value = false
  }
}

const executeTask = async (taskId) => {
  const loadingInstance = ElLoading.service({
    lock: true,
    text: '任务执行中，请耐心等待...',
    background: 'rgba(0, 0, 0, 0.7)'
  })
  
  try {
    // 使用长时间操作的API实例，支持1小时超时
    const response = await longTaskApi.post(`/api/tasks/${taskId}/execute`)
    if (response.data.success) {
      const result = response.data
      ElMessage.success(`任务执行成功！耗时: ${result.duration?.toFixed(2)}秒，处理行数: ${result.rows_affected || 0}`)
      fetchTasks()
    } else {
      ElMessage.error(response.data.error_message || '任务执行失败')
    }
  } catch (error) {
    console.error('执行任务失败:', error)
    if (error.code === 'ECONNABORTED' && error.message.includes('timeout')) {
      ElMessage.error('任务执行超时，请检查任务配置或稍后重试')
    } else {
      ElMessage.error(error.response?.data?.error || error.message || '任务执行失败')
    }
  } finally {
    loadingInstance.close()
  }
}

const testTask = async (taskId) => {
  const loadingInstance = ElLoading.service({
    lock: true,
    text: '正在测试任务...',
    background: 'rgba(0, 0, 0, 0.7)'
  })
  
  try {
    const response = await api.post(`/api/tasks/${taskId}/test`)
    testResult.value = response.data
    testResultVisible.value = true
    
    if (response.data.success) {
      ElMessage.success('任务测试完成！')
    } else {
      ElMessage.warning('任务测试完成，但存在问题，请查看详细信息')
    }
  } catch (error) {
    console.error('测试任务失败:', error)
    testResult.value = {
      success: false,
      errors: [error.response?.data?.error || error.message || '测试失败'],
      row_count: 0,
      execution_time: 0,
      columns: [],
      data_preview: []
    }
    testResultVisible.value = true
    ElMessage.error('任务测试失败')
  } finally {
    loadingInstance.close()
  }
}

const reloadAllTasks = async () => {
  try {
    ElMessage.info('正在重载所有定时任务...')
    const response = await api.post('/api/scheduler/reload')
    if (response.data.success) {
      ElMessage.success('所有定时任务重载成功！')
      // 重新获取任务列表以显示最新状态
      fetchTasks()
    } else {
      ElMessage.error(`重载失败: ${response.data.error || '未知错误'}`)
    }
  } catch (error) {
    console.error('重载所有定时任务失败:', error)
    ElMessage.error('重载所有定时任务失败，请检查调度器是否正常运行')
  }
}

// 测试结果弹窗相关方法
const closeTestResult = () => {
  testResultVisible.value = false
  testResult.value = null
}

const formatCellValue = (value) => {
  if (value === null || value === undefined) {
    return ''
  }
  if (typeof value === 'object') {
    return JSON.stringify(value)
  }
  return String(value)
}

const getColumnWidth = (columnName) => {
  // 根据列名长度和内容动态计算列宽
  const baseWidth = Math.max(columnName.length * 12, 100)
  return Math.min(baseWidth, 200)
}

onMounted(() => {
  fetchTasks()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-buttons {
  display: flex;
  gap: 12px;
  align-items: center;
}

/* 测试结果弹窗样式 */
.test-info {
  margin-bottom: 20px;
}

.error-section {
  margin: 20px 0;
}

.error-section h4 {
  margin-bottom: 10px;
  color: #f56c6c;
}

.data-preview {
  margin-top: 20px;
}

.data-preview h4 {
  margin-bottom: 15px;
  color: #409eff;
}

.no-data {
  margin: 20px 0;
  text-align: center;
}

.dialog-footer {
  text-align: right;
}

/* 表格样式优化 */
.data-preview .el-table {
  font-size: 12px;
}

.data-preview .el-table th {
  background-color: #f5f7fa;
  font-weight: 600;
}

.data-preview .el-table td {
  padding: 8px 12px;
}
</style>