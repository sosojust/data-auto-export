<template>
  <div class="rbac-resources">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>资源权限管理</span>
          <div class="header-actions">
            <el-button type="primary" @click="showCreate" :loading="loading" v-if="canCreate">
              <el-icon><Plus /></el-icon>
              新增资源
            </el-button>
            <el-button @click="fetchResources" :loading="loading">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
          </div>
        </div>
      </template>

      <el-table :data="resources" v-loading="loading" empty-text="暂无资源">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="name" label="名称" width="160" />
        <el-table-column prop="path" label="路径" min-width="220" />
        <el-table-column prop="method" label="方法" width="120">
          <template #default="{ row }">
            <el-tag type="info">{{ row.method || 'ALL' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="match_type" label="匹配" width="120">
          <template #default="{ row }">
            <el-tag :type="row.match_type === 'exact' ? 'success' : 'warning'">
              {{ row.match_type }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="is_active" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'danger'">
              {{ row.is_active ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="200" />
        <el-table-column label="操作" width="320" fixed="right">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-button size="small" type="success" plain @click="edit(row)" class="action-btn" v-if="canUpdate">
                <el-icon><Edit /></el-icon>
                编辑
              </el-button>
              <el-button size="small" type="warning" plain @click="toggleActive(row)" class="action-btn" v-if="canUpdate">
                <el-icon><Switch /></el-icon>
                {{ row.is_active ? '禁用' : '启用' }}
              </el-button>
              <el-button size="small" type="danger" plain @click="remove(row)" class="action-btn" v-if="canDelete">
                <el-icon><Delete /></el-icon>
                删除
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑资源' : '新增资源'" width="600px" @close="resetForm">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入资源名称" />
        </el-form-item>
        <el-form-item label="路径" prop="path">
          <el-input v-model="form.path" placeholder="例如 /api/tasks 或 /api/tasks/" />
        </el-form-item>
        <el-form-item label="方法" prop="method">
          <el-select v-model="form.method" style="width: 100%" placeholder="选择HTTP方法（可为空表示全部）" clearable>
            <el-option label="ALL" :value="null" />
            <el-option label="GET" value="GET" />
            <el-option label="POST" value="POST" />
            <el-option label="PUT" value="PUT" />
            <el-option label="DELETE" value="DELETE" />
          </el-select>
        </el-form-item>
        <el-form-item label="匹配类型" prop="match_type">
          <el-select v-model="form.match_type" style="width: 100%">
            <el-option label="exact（精确匹配）" value="exact" />
            <el-option label="prefix（前缀匹配）" value="prefix" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input v-model="form.description" type="textarea" placeholder="描述信息（可选）" />
        </el-form-item>
        <el-form-item label="启用授权" prop="is_active">
          <el-switch v-model="form.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="submitting" @click="submit">
            {{ isEdit ? '保存' : '创建' }}
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox, FormInstance, FormRules } from 'element-plus'
import { Plus, Refresh, Edit, Delete, Switch } from '@element-plus/icons-vue'
import api from '../utils/api'
import { useAuthStore } from '../stores/auth'

interface Resource {
  id?: number
  name: string
  path: string
  method: string | null
  match_type: 'exact' | 'prefix'
  description?: string
  is_active: boolean
  created_at?: string
  updated_at?: string
}

const authStore = useAuthStore()
const resources = ref<Resource[]>([])
const loading = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const submitting = ref(false)
const currentId = ref<number | null>(null)

const canCreate = computed(() => authStore.hasPermission('/api/rbac/resources', 'POST'))
const canUpdate = computed(() => authStore.hasPermission('/api/rbac/resources/', 'PUT'))
const canDelete = computed(() => authStore.hasPermission('/api/rbac/resources/', 'DELETE'))

const formRef = ref<FormInstance>()
const form = reactive<Resource>({
  name: '',
  path: '',
  method: null,
  match_type: 'exact',
  description: '',
  is_active: true
})

const rules: FormRules<Resource> = {
  name: [{ required: true, message: '请输入资源名称', trigger: 'blur' }],
  path: [{ required: true, message: '请输入资源路径', trigger: 'blur' }],
  match_type: [{ required: true, message: '请选择匹配类型', trigger: 'change' }]
}

const fetchResources = async () => {
  loading.value = true
  try {
    const resp = await api.get('/api/rbac/resources')
    if (resp.data?.success) {
      resources.value = resp.data.resources || []
    }
  } catch (e) {
    ElMessage.error('获取资源列表失败')
  } finally {
    loading.value = false
  }
}

const showCreate = () => {
  isEdit.value = false
  currentId.value = null
  dialogVisible.value = true
}

const edit = (row: Resource) => {
  if (!canUpdate.value) return
  isEdit.value = true
  currentId.value = row.id || null
  Object.assign(form, row)
  dialogVisible.value = true
}

const resetForm = () => {
  form.name = ''
  form.path = ''
  form.method = null
  form.match_type = 'exact'
  form.description = ''
  form.is_active = true
}

const submit = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    submitting.value = true
    try {
      if (isEdit.value && currentId.value) {
        const resp = await api.put(`/api/rbac/resources/${currentId.value}`, form)
        if (resp.data?.success) {
          ElMessage.success(resp.data.message || '资源更新成功')
          dialogVisible.value = false
          await fetchResources()
        }
      } else {
        const resp = await api.post('/api/rbac/resources', form)
        if (resp.data?.success) {
          ElMessage.success(resp.data.message || '资源创建成功')
          dialogVisible.value = false
          await fetchResources()
        }
      }
    } catch (e) {
      ElMessage.error('提交失败，请检查输入或权限')
    } finally {
      submitting.value = false
    }
  })
}

const toggleActive = async (row: Resource) => {
  if (!canUpdate.value || !row.id) return
  try {
    const resp = await api.put(`/api/rbac/resources/${row.id}`, { ...row, is_active: !row.is_active })
    if (resp.data?.success) {
      ElMessage.success('状态已更新')
      await fetchResources()
    }
  } catch (e) {
    ElMessage.error('更新状态失败')
  }
}

const remove = async (row: Resource) => {
  if (!canDelete.value || !row.id) return
  try {
    await ElMessageBox.confirm(
      `确认删除资源 “${row.name}” ?`,
      '提示',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
    const resp = await api.delete(`/api/rbac/resources/${row.id}`)
    if (resp.data?.success) {
      ElMessage.success(resp.data.message || '删除成功')
      await fetchResources()
    }
  } catch (e) {
    // 用户取消或请求失败
  }
}


onMounted(() => {
  fetchResources()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.header-actions {
  display: flex;
  gap: 8px;
}
.action-buttons {
  display: flex;
  gap: 8px;
  align-items: center;
}
.action-btn {
  min-width: 72px;
}
.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>