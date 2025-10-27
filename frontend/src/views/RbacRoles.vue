<template>
  <div class="rbac-roles">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>角色管理</span>
          <div class="header-actions">
            <el-button type="primary" @click="dialogVisible = true" v-if="canCreate">
              <el-icon><Plus /></el-icon>
              新增角色
            </el-button>
            <el-button @click="fetchRoles" :loading="loading">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
          </div>
        </div>
      </template>

      <el-table :data="roles" v-loading="loading" empty-text="暂无角色">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="name" label="名称" width="200" />
        <el-table-column prop="description" label="描述" min-width="240" />
        <el-table-column prop="is_active" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'danger'">
              {{ row.is_active ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180" />
        <el-table-column prop="updated_at" label="更新时间" width="180" />
        <!-- 新增：授权资源管理按钮列 -->
        <el-table-column label="授权资源" width="160">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="openAuthDialog(row)" :disabled="!canAuthorize">
              授权管理
            </el-button>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="260">
          <template #default="{ row }">
            <el-button size="small" @click="openEdit(row)" :disabled="!canUpdate">
              编辑
            </el-button>
            <el-button size="small" :type="row.is_active ? 'warning' : 'success'" @click="toggleActive(row)" :disabled="!canUpdate">
              {{ row.is_active ? '禁用' : '启用' }}
            </el-button>
            <el-button type="danger" size="small" plain @click="remove(row)" :disabled="!canDelete || isBuiltinRole(row.name)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" title="新增角色" width="500px" @close="resetForm">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入角色名称" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input v-model="form.description" type="textarea" placeholder="描述信息（可选）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="submitting" @click="submit">创建</el-button>
        </div>
      </template>
    </el-dialog>

    <el-dialog v-model="editDialogVisible" title="编辑角色" width="500px">
      <el-form :model="editForm" label-width="90px">
        <el-form-item label="名称">
          <el-input v-model="editForm.name" placeholder="请输入角色名称" :disabled="isBuiltinRole(editForm.name)" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="editForm.description" type="textarea" placeholder="描述信息（可选）" />
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="editForm.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="editDialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="editSubmitting" @click="updateRole">保存</el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 新增：角色授权资源管理弹窗 -->
    <el-dialog v-model="authDialogVisible" :title="`授权资源管理 - ${currentRole?.name || ''}`" width="800px" @close="closeAuthDialog">
      <div class="auth-dialog-body">
        <el-form label-width="100px" class="authorize-form">
          <el-form-item label="新增授权">
            <div class="auth-actions">
              <el-select v-model="selectedResourceId" filterable placeholder="选择资源" style="width: 420px">
                <el-option
                  v-for="res in resources"
                  :key="res.id"
                  :label="formatResourceLabel(res)"
                  :value="res.id"
                />
              </el-select>
              <el-button type="primary" @click="authorize" :disabled="!canAuthorize || !selectedResourceId" :loading="authorizing">
                授权
              </el-button>
            </div>
          </el-form-item>
        </el-form>

        <el-card shadow="never" style="margin-top: 10px">
          <template #header>已授权资源</template>
          <el-table :data="authorizedResources" v-loading="loadingAuthorized" empty-text="暂无授权">
            <el-table-column prop="id" label="ID" width="80" />
            <el-table-column label="资源">
              <template #default="{ row }">
                <span>{{ formatResourceLabel(row) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="120">
              <template #default="{ row }">
                <el-button type="danger" size="small" plain @click="revoke(row)" :disabled="!canAuthorize" :loading="revoking">
                  撤销
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </div>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="authDialogVisible = false">关闭</el-button>
          <el-button @click="reloadAuth" :loading="loadingAuthorized">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox, FormInstance, FormRules } from 'element-plus'
import { Plus, Refresh } from '@element-plus/icons-vue'
import api from '../utils/api'
import { useAuthStore } from '../stores/auth'

interface Role {
  id?: number
  name: string
  description?: string
  is_active?: boolean
  created_at?: string
  updated_at?: string
}

interface Resource { id: number; name: string; path: string; method: string | null; match_type: 'exact' | 'prefix' }

const authStore = useAuthStore()
const roles = ref<Role[]>([])
const loading = ref(false)
const dialogVisible = ref(false)
const submitting = ref(false)
const editDialogVisible = ref(false)
const editSubmitting = ref(false)
const editForm = reactive<Role>({ id: undefined, name: '', description: '', is_active: true })

const canCreate = computed(() => authStore.hasPermission('/api/rbac/roles', 'POST'))
const canAuthorize = computed(() => authStore.hasPermission('/api/rbac/authorize', 'POST'))
const canUpdate = computed(() => authStore.hasPermission('/api/rbac/roles/', 'PUT'))
const canDelete = computed(() => authStore.hasPermission('/api/rbac/roles/', 'DELETE'))

const formRef = ref<FormInstance>()
const form = reactive<Role>({
  name: '',
  description: ''
})

const rules: FormRules<Role> = {
  name: [{ required: true, message: '请输入角色名称', trigger: 'blur' }]
}

const fetchRoles = async () => {
  loading.value = true
  try {
    const resp = await api.get('/api/rbac/roles')
    if (resp.data?.success) {
      roles.value = resp.data.roles || []
    }
  } catch (e) {
    ElMessage.error('获取角色失败')
  } finally {
    loading.value = false
  }
}

const resetForm = () => {
  form.name = ''
  form.description = ''
}

const submit = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    submitting.value = true
    try {
      const resp = await api.post('/api/rbac/roles', {
        name: form.name,
        description: form.description
      })
      if (resp.data?.success) {
        ElMessage.success(resp.data.message || '角色创建成功')
        dialogVisible.value = false
        await fetchRoles()
      }
    } catch (e) {
      ElMessage.error('创建失败，请检查输入或权限')
    } finally {
      submitting.value = false
    }
  })
}

const isBuiltinRole = (name?: string) => !!name && (name === 'admin' || name === 'user')

const openEdit = (row: Role) => {
  editForm.id = row.id
  editForm.name = row.name
  editForm.description = row.description || ''
  editForm.is_active = !!row.is_active
  editDialogVisible.value = true
}

const updateRole = async () => {
  if (!editForm.id) return
  editSubmitting.value = true
  try {
    const payload: any = {
      name: editForm.name,
      description: editForm.description,
      is_active: editForm.is_active
    }
    const resp = await api.put(`/api/rbac/roles/${editForm.id}`, payload)
    if (resp.data?.success) {
      ElMessage.success(resp.data.message || '角色更新成功')
      editDialogVisible.value = false
      await fetchRoles()
    } else {
      ElMessage.error(resp.data?.error || '更新失败')
    }
  } catch (e) {
    ElMessage.error('更新失败，请检查输入或权限')
  } finally {
    editSubmitting.value = false
  }
}

const toggleActive = async (row: Role) => {
  if (!row.id) return
  try {
    const resp = await api.put(`/api/rbac/roles/${row.id}`, { is_active: !row.is_active })
    if (resp.data?.success) {
      ElMessage.success(resp.data.message || (row.is_active ? '已禁用' : '已启用'))
      await fetchRoles()
    } else {
      ElMessage.error(resp.data?.error || '操作失败')
    }
  } catch (e) {
    ElMessage.error('操作失败，请检查权限或参数')
  }
}

const remove = async (row: Role) => {
  if (!row.id) return
  if (isBuiltinRole(row.name)) {
    ElMessage.error('内置角色不可删除')
    return
  }
  try {
    await ElMessageBox.confirm(`确认删除角色 "${row.name}"？此操作不可撤销。`, '删除确认', {
      type: 'warning'
    })
    const resp = await api.delete(`/api/rbac/roles/${row.id}`)
    if (resp.data?.success) {
      ElMessage.success(resp.data.message || '删除成功')
      await fetchRoles()
    } else {
      ElMessage.error(resp.data?.error || '删除失败')
    }
  } catch (e) {
    // 用户取消或请求失败
  }
}

// 授权管理相关逻辑
const authDialogVisible = ref(false)
const currentRole = ref<Role | null>(null)
const resources = ref<Resource[]>([])
const authorizedResources = ref<Resource[]>([])
const loadingAuthorized = ref(false)
const authorizing = ref(false)
const revoking = ref(false)
const selectedResourceId = ref<number | null>(null)

const formatResourceLabel = (r: Resource) => {
  return `${r.name} | ${r.path} | ${r.method ?? 'ALL'} | ${r.match_type}`
}

const openAuthDialog = async (row: Role) => {
  currentRole.value = row
  authDialogVisible.value = true
  selectedResourceId.value = null
  await Promise.all([fetchAllResources(), fetchAuthorizedResources()])
}

const closeAuthDialog = () => {
  currentRole.value = null
  authorizedResources.value = []
  selectedResourceId.value = null
}

const fetchAllResources = async () => {
  try {
    const resp = await api.get('/api/rbac/resources')
    if (resp.data?.success) resources.value = resp.data.resources || []
  } catch (e) {
    ElMessage.error('获取资源失败')
  }
}

const fetchAuthorizedResources = async () => {
  const roleId = currentRole.value?.id
  if (!roleId) {
    authorizedResources.value = []
    return
  }
  loadingAuthorized.value = true
  try {
    const resp = await api.get(`/api/rbac/roles/${roleId}/resources`)
    if (resp.data?.success) {
      authorizedResources.value = resp.data.resources || []
    }
  } catch (e) {
    ElMessage.error('获取已授权资源失败')
  } finally {
    loadingAuthorized.value = false
  }
}

const authorize = async () => {
  const roleId = currentRole.value?.id
  const resId = selectedResourceId.value
  if (!roleId || !resId) return
  authorizing.value = true
  try {
    const resp = await api.post('/api/rbac/authorize', { role_id: roleId, resource_id: resId })
    if (resp.data?.success) {
      ElMessage.success(resp.data.message || '授权成功')
      await fetchAuthorizedResources()
      selectedResourceId.value = null
    }
  } catch (e) {
    ElMessage.error('授权失败，请检查权限或参数')
  } finally {
    authorizing.value = false
  }
}

const revoke = async (row: Resource) => {
  const roleId = currentRole.value?.id
  const resId = row.id
  if (!roleId || !resId) return
  revoking.value = true
  try {
    const resp = await api.post('/api/rbac/revoke', { role_id: roleId, resource_id: resId })
    if (resp.data?.success) {
      ElMessage.success(resp.data.message || '撤销成功')
      await fetchAuthorizedResources()
    }
  } catch (e) {
    ElMessage.error('撤销失败，请检查权限或参数')
  } finally {
    revoking.value = false
  }
}

const reloadAuth = async () => {
  await fetchAuthorizedResources()
}

onMounted(() => {
  fetchRoles()
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
.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
.authorize-form {
  max-width: 680px;
}
.auth-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}
</style>