<template>
  <div class="data-sources">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>数据源管理</span>
          <div class="header-buttons">
            <el-button type="success" @click="refreshDataSources" :loading="refreshing">
              <el-icon><Refresh /></el-icon>
              刷新数据源
            </el-button>
            <el-button type="primary" @click="showCreateDialog">
              <el-icon><Plus /></el-icon>
              新增数据源
            </el-button>
          </div>
        </div>
      </template>
      
      <el-table :data="dataSources" v-loading="loading" empty-text="暂无数据源">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="name" label="名称" width="150" />
        <el-table-column prop="type" label="类型" width="120" />
        <el-table-column prop="host" label="主机" width="150" />
        <el-table-column prop="port" label="端口" width="80" />
        <el-table-column prop="database" label="数据库" width="150" />
        <el-table-column prop="username" label="用户名" width="120" />
        <el-table-column prop="is_active" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'danger'">
              {{ row.is_active ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="200" />
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-button size="small" type="primary" plain @click="testConnection(row)" class="action-btn">
                <el-icon><Connection /></el-icon>
                测试连接
              </el-button>
              <el-button size="small" type="success" plain @click="editDataSource(row)" class="action-btn">
                <el-icon><Edit /></el-icon>
                编辑
              </el-button>
              <el-dropdown trigger="click" class="action-dropdown">
                <el-button size="small" type="info" plain class="action-btn">
                  更多操作
                  <el-icon class="el-icon--right"><ArrowDown /></el-icon>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item @click="toggleStatus(row)">
                      <el-icon><Switch /></el-icon>
                      {{ row.is_active ? '禁用数据源' : '启用数据源' }}
                    </el-dropdown-item>
                    <el-dropdown-item divided @click="deleteDataSource(row)" class="danger-item">
                      <el-icon><Delete /></el-icon>
                      删除数据源
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 创建/编辑数据源对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑数据源' : '新增数据源'"
      width="600px"
      @close="resetForm"
    >
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="100px"
      >
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入数据源名称" />
        </el-form-item>
        
        <el-form-item label="类型" prop="type">
          <el-select v-model="form.type" placeholder="请选择数据源类型" style="width: 100%">
            <el-option label="MySQL" value="mysql" />
            <el-option label="AnalyticDB" value="adb" />
            <el-option label="PostgreSQL" value="postgresql" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="主机" prop="host">
          <el-input v-model="form.host" placeholder="请输入主机地址" />
        </el-form-item>
        
        <el-form-item label="端口" prop="port">
          <el-input-number v-model="form.port" :min="1" :max="65535" style="width: 100%" />
        </el-form-item>
        
        <el-form-item label="数据库" prop="database">
          <el-input v-model="form.database" placeholder="请输入数据库名" />
        </el-form-item>
        
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" placeholder="请输入用户名" />
        </el-form-item>
        
        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            show-password
          />
        </el-form-item>
        
        <el-form-item label="字符集" prop="charset">
          <el-select v-model="form.charset" placeholder="请选择字符集" style="width: 100%">
            <el-option label="utf8mb4" value="utf8mb4" />
            <el-option label="utf8" value="utf8" />
            <el-option label="latin1" value="latin1" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="描述">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="3"
            placeholder="请输入描述信息"
          />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="submitForm" :loading="submitting">
            {{ isEdit ? '更新' : '创建' }}
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Plus,
  Connection,
  Edit,
  Switch,
  Delete,
  ArrowDown,
  Refresh
} from '@element-plus/icons-vue'
import api from '../utils/api'

const dataSources = ref([])
const loading = ref(false)
const refreshing = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const submitting = ref(false)
const formRef = ref()

const form = reactive({
  id: null,
  name: '',
  type: 'mysql',
  host: '',
  port: 3306,
  database: '',
  username: '',
  password: '',
  charset: 'utf8mb4',
  description: ''
})

const rules = {
  name: [
    { required: true, message: '请输入数据源名称', trigger: 'blur' }
  ],
  type: [
    { required: true, message: '请选择数据源类型', trigger: 'change' }
  ],
  host: [
    { required: true, message: '请输入主机地址', trigger: 'blur' }
  ],
  port: [
    { required: true, message: '请输入端口号', trigger: 'blur' }
  ],
  database: [
    { required: true, message: '请输入数据库名', trigger: 'blur' }
  ],
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' }
  ]
}

const fetchDataSources = async () => {
  loading.value = true
  try {
    const response = await api.get('/api/data-sources')
    if (response.data.success) {
      dataSources.value = response.data.data.data_sources
    }
  } catch (error) {
    console.error('获取数据源失败:', error)
    ElMessage.error('获取数据源列表失败')
  } finally {
    loading.value = false
  }
}

const refreshDataSources = async () => {
  refreshing.value = true
  try {
    const response = await api.post('/api/data-sources/refresh')
    if (response.data.success) {
      ElMessage.success(response.data.message)
      // 刷新完成后重新获取数据源列表
      await fetchDataSources()
    } else {
      ElMessage.error(response.data.error || '刷新数据源失败')
    }
  } catch (error) {
    console.error('刷新数据源失败:', error)
    ElMessage.error('刷新数据源失败')
  } finally {
    refreshing.value = false
  }
}

const showCreateDialog = () => {
  isEdit.value = false
  dialogVisible.value = true
  resetForm()
}

const editDataSource = (row) => {
  isEdit.value = true
  dialogVisible.value = true
  
  // 填充表单数据
  Object.keys(form).forEach(key => {
    if (row[key] !== undefined) {
      form[key] = row[key]
    }
  })
}

const resetForm = () => {
  if (formRef.value) {
    formRef.value.resetFields()
  }
  
  form.id = null
  form.name = ''
  form.type = 'mysql'
  form.host = ''
  form.port = 3306
  form.database = ''
  form.username = ''
  form.password = ''
  form.charset = 'utf8mb4'
  form.description = ''
}

const submitForm = async () => {
  if (!formRef.value) return
  
  try {
    await formRef.value.validate()
    submitting.value = true
    
    const formData = { ...form }
    delete formData.id // 移除id字段
    
    let response
    if (isEdit.value) {
      response = await api.put(`/api/data-sources/${form.id}`, formData)
    } else {
      response = await api.post('/api/data-sources', formData)
    }
    
    if (response.data.success) {
      ElMessage.success(isEdit.value ? '数据源更新成功' : '数据源创建成功')
      dialogVisible.value = false
      fetchDataSources()
    } else {
      ElMessage.error(response.data.error || '操作失败')
    }
  } catch (error) {
    console.error('提交表单失败:', error)
    ElMessage.error(error.response?.data?.error || '操作失败')
  } finally {
    submitting.value = false
  }
}

const testConnection = async (row) => {
  try {
    ElMessage.info('正在测试连接...')
    const response = await api.post(`/api/data-sources/${row.id}/test`)
    
    if (response.data.success) {
      ElMessage.success('连接测试成功')
    } else {
      ElMessage.error(response.data.error || '连接测试失败')
    }
  } catch (error) {
    console.error('测试连接失败:', error)
    ElMessage.error('连接测试失败')
  }
}

const toggleStatus = async (row) => {
  try {
    const action = row.is_active ? '禁用' : '启用'
    await ElMessageBox.confirm(
      `确定要${action}数据源 "${row.name}" 吗？`,
      '确认操作',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    const response = await api.post(`/api/data-sources/${row.id}/toggle`)
    
    if (response.data.success) {
      ElMessage.success(`数据源${action}成功`)
      fetchDataSources()
    } else {
      ElMessage.error(response.data.error || `${action}失败`)
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('切换状态失败:', error)
      ElMessage.error('操作失败')
    }
  }
}

const deleteDataSource = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除数据源 "${row.name}" 吗？此操作不可恢复！`,
      '确认删除',
      {
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        type: 'error'
      }
    )
    
    const response = await api.delete(`/api/data-sources/${row.id}`)
    
    if (response.data.success) {
      ElMessage.success('数据源删除成功')
      fetchDataSources()
    } else {
      ElMessage.error(response.data.error || '删除失败')
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除数据源失败:', error)
      ElMessage.error('删除失败')
    }
  }
}

onMounted(() => {
  fetchDataSources()
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

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.el-table {
  margin-top: 20px;
}

.action-buttons {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}

.action-btn {
  min-width: 80px;
  border-radius: 6px;
  font-weight: 500;
  transition: all 0.3s ease;
}

.action-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.action-dropdown {
  margin-left: 4px;
}

.danger-item {
  color: #f56c6c;
}

.danger-item:hover {
  background-color: #fef0f0;
  color: #f56c6c;
}

.el-dropdown-menu__item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
}

.el-table .el-table__cell {
  padding: 12px 0;
}

.el-button + .el-button {
  margin-left: 0;
}
</style>