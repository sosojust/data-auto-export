<template>
  <div class="users-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>用户管理</span>
          <div class="header-actions">
            <el-switch
              v-model="activeOnly"
              active-text="仅活跃"
              inactive-text="全部"
              @change="handleActiveToggle"
            />
            <el-button type="primary" @click="fetchUsers" :loading="loading" style="margin-left: 12px;">
              刷新
            </el-button>
            <el-button type="success" style="margin-left: 12px;" @click="openCreateUser">
              创建用户
            </el-button>
          </div>
        </div>
      </template>

      <el-table :data="users" v-loading="loading" border style="width: 100%">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="username" label="用户名" min-width="150" />
        <el-table-column prop="email" label="邮箱" min-width="200">
          <template #default="{ row }">
            <span>{{ row.email || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="角色" min-width="280">
          <template #default="{ row }">
            <div class="roles-cell">
              <el-tag
                v-for="r in row.roles"
                :key="r.id"
                type="info"
                size="small"
                closable
                @close="revokeRole(row, r)"
                class="role-tag"
              >
                {{ r.name || ('#' + r.id) }}
              </el-tag>
              <el-button text type="primary" size="small" @click="openAssignRole(row)">
                分配角色
              </el-button>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'danger'" size="small">
              {{ row.is_active ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="140">
          <template #default="{ row }">
            <el-button text type="primary" size="small" @click="openEditUser(row)">编辑</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <!-- 分配角色对话框 -->
    <el-dialog v-model="roleDialogVisible" title="分配角色" width="500px">
      <div>
        <div class="dialog-line">为用户：<b>{{ roleDialogUser?.username }}</b> 分配角色</div>
        <el-select v-model="selectedRoleId" placeholder="选择角色" filterable style="width: 100%; margin-top: 12px;">
          <el-option
            v-for="role in assignableRoles"
            :key="role.id"
            :label="role.name"
            :value="role.id"
          />
        </el-select>
      </div>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="roleDialogVisible = false">取消</el-button>
          <el-button type="primary" :disabled="!selectedRoleId" @click="confirmAssignRole">确定</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 创建用户对话框 -->
    <el-dialog v-model="createDialogVisible" title="创建用户" width="500px">
      <div>
        <el-form :model="createForm" label-width="90px">
          <el-form-item label="用户名">
            <el-input v-model="createForm.username" placeholder="请输入用户名" />
          </el-form-item>
          <el-form-item label="邮箱">
            <el-input v-model="createForm.email" placeholder="请输入邮箱（可选）" />
          </el-form-item>
          <el-form-item label="密码">
            <el-input v-model="createForm.password" type="password" placeholder="请输入密码" />
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="createDialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="createLoading" :disabled="!canSubmitCreate" @click="confirmCreateUser">创建</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 编辑用户对话框 -->
    <el-dialog v-model="editDialogVisible" title="编辑用户" width="500px">
      <div>
        <div class="dialog-line">编辑用户：<b>{{ editForm.username }}</b></div>
        <el-form :model="editForm" label-width="90px" style="margin-top: 12px;">
          <el-form-item label="邮箱">
            <el-input v-model="editForm.email" placeholder="请输入邮箱" />
          </el-form-item>
          <el-form-item label="状态">
            <el-switch v-model="editForm.is_active" active-text="启用" inactive-text="禁用" />
          </el-form-item>
          <el-form-item label="重置密码">
            <el-input v-model="editForm.password" type="password" placeholder="留空不修改" />
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="editDialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="editLoading" @click="confirmUpdateUser">保存</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
  
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../utils/api'

type UserItem = {
  id: number
  username: string
  email?: string | null
  role?: string | null // 兼容旧字段
  is_active: boolean
  roles: { id: number; name?: string }[]
}

type RoleItem = {
  id: number
  name: string
  description?: string
  is_active?: boolean
}

const users = ref<UserItem[]>([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const activeOnly = ref(false)

const allRoles = ref<RoleItem[]>([])
const roleDialogVisible = ref(false)
const roleDialogUser = ref<UserItem | null>(null)
const selectedRoleId = ref<number | null>(null)

const assignableRoles = computed(() => {
  const user = roleDialogUser.value
  if (!user) return []
  const assignedIds = new Set(user.roles.map(r => r.id))
  // 放宽过滤逻辑，允许选择 admin 等可能被标记为不活跃的角色
  return allRoles.value.filter(r => !assignedIds.has(r.id))
})

const fetchUsers = async () => {
  loading.value = true
  try {
    const response = await api.get('/api/users', {
      params: {
        page: currentPage.value,
        per_page: pageSize.value,
        active_only: activeOnly.value ? 'true' : 'false'
      }
    })
    if (response.data.success) {
      const data = response.data.data || {}
      users.value = data.users || []
      total.value = data.total || 0
      currentPage.value = data.page || currentPage.value
      pageSize.value = data.per_page || pageSize.value
    } else {
      ElMessage.error(response.data.error || '获取用户列表失败')
    }
  } catch (error: any) {
    if (error.response?.data?.error) {
      ElMessage.error(error.response.data.error)
    } else {
      ElMessage.error('获取用户列表失败')
    }
  } finally {
    loading.value = false
  }
}

const fetchRoles = async () => {
  try {
    const response = await api.get('/api/rbac/roles')
    if (response.data.success) {
      allRoles.value = response.data.roles || []
    }
  } catch (error) {
    // 忽略错误，不影响用户列表
  }
}

const handleSizeChange = (size: number) => {
  pageSize.value = size
  currentPage.value = 1
  fetchUsers()
}

const handleCurrentChange = (page: number) => {
  currentPage.value = page
  fetchUsers()
}

const handleActiveToggle = () => {
  currentPage.value = 1
  fetchUsers()
}

const openAssignRole = async (user: UserItem) => {
  roleDialogUser.value = user
  selectedRoleId.value = null
  if (!allRoles.value.length) {
    await fetchRoles()
  }
  roleDialogVisible.value = true
}

const confirmAssignRole = async () => {
  if (!roleDialogUser.value || !selectedRoleId.value) return
  const user = roleDialogUser.value
  try {
    const response = await api.post(`/api/users/${user.id}/roles`, {
      role_id: selectedRoleId.value
    })
    if (response.data.success) {
      const assigned = allRoles.value.find(r => r.id === selectedRoleId.value)
      if (assigned) {
        user.roles.push({ id: assigned.id, name: assigned.name })
      }
      ElMessage.success('角色分配成功')
      roleDialogVisible.value = false
    } else {
      ElMessage.error(response.data.error || '角色分配失败')
    }
  } catch (error: any) {
    if (error.response?.data?.error) {
      ElMessage.error(error.response.data.error)
    } else {
      ElMessage.error('角色分配失败')
    }
  }
}

const revokeRole = async (user: UserItem, role: { id: number; name?: string }) => {
  try {
    await ElMessageBox.confirm(
      `确认撤销用户 ${user.username} 的角色「${role.name || role.id}」吗？`,
      '确认操作',
      { type: 'warning' }
    )
    const response = await api.delete(`/api/users/${user.id}/roles/${role.id}`)
    if (response.data.success) {
      user.roles = user.roles.filter(r => r.id !== role.id)
      ElMessage.success('已撤销角色')
    } else {
      ElMessage.error(response.data.error || '撤销角色失败')
    }
  } catch {
    // 用户取消
  }
}

onMounted(() => {
  fetchUsers()
  fetchRoles()
})

// ===== 创建用户逻辑 =====
const createDialogVisible = ref(false)
const createLoading = ref(false)
const createForm = ref<{ username: string; email?: string; password: string }>({ username: '', email: '', password: '' })
const canSubmitCreate = computed(() => !!createForm.value.username && !!createForm.value.password)

const openCreateUser = () => {
  createForm.value = { username: '', email: '', password: '' }
  createDialogVisible.value = true
}

const confirmCreateUser = async () => {
  if (!canSubmitCreate.value) return
  try {
    createLoading.value = true
    const payload: any = {
      username: createForm.value.username,
      password: createForm.value.password,
    }
    if (createForm.value.email) payload.email = createForm.value.email
    const response = await api.post('/api/users', payload)
    if (response.data?.success) {
      ElMessage.success('用户创建成功')
      createDialogVisible.value = false
      fetchUsers()
    } else {
      ElMessage.error(response.data?.error || '用户创建失败')
    }
  } catch (error: any) {
    if (error.response?.data?.error) {
      ElMessage.error(error.response.data.error)
    } else {
      ElMessage.error('用户创建失败')
    }
  } finally {
    createLoading.value = false
  }
}

// ===== 编辑用户逻辑 =====
const editDialogVisible = ref(false)
const editLoading = ref(false)
const editForm = ref<{ id: number; username: string; email?: string | null; is_active: boolean; password?: string }>({
  id: 0,
  username: '',
  email: '',
  is_active: true,
  password: ''
})

const openEditUser = (user: UserItem) => {
  editForm.value = { id: user.id, username: user.username, email: user.email || '', is_active: user.is_active, password: '' }
  editDialogVisible.value = true
}

const confirmUpdateUser = async () => {
  if (!editDialogVisible.value || !editForm.value.id) return
  try {
    editLoading.value = true
    const payload: any = {
      email: editForm.value.email || null,
      is_active: editForm.value.is_active,
    }
    if (editForm.value.password) payload.password = editForm.value.password
    const response = await api.put(`/api/users/${editForm.value.id}`, payload)
    if (response.data?.success) {
      ElMessage.success('用户更新成功')
      editDialogVisible.value = false
      editForm.value = { id: 0, username: '', email: '', is_active: true, password: '' }
      fetchUsers()
    } else {
      ElMessage.error(response.data?.error || '用户更新失败')
    }
  } catch (error: any) {
    if (error.response?.data?.error) {
      ElMessage.error(error.response.data.error)
    } else {
      ElMessage.error('用户更新失败')
    }
  } finally {
    editLoading.value = false
  }
}
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.header-actions {
  display: flex;
  align-items: center;
}
.roles-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.role-tag {
  margin-right: 4px;
}
.pagination-wrapper {
  margin-top: 16px;
  display: flex;
  justify-content: center;
}
.users-page {
  padding: 4px;
}
</style>