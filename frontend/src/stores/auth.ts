import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../utils/api'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('token'))
  const username = ref<string | null>(localStorage.getItem('username'))
  const isAuthenticated = ref<boolean>(!!token.value)
  const roles = ref<string[]>(JSON.parse(localStorage.getItem('roles') || '[]'))
  const resources = ref<Array<{ id?: number; path: string; method: string | null; match_type: string }>>(JSON.parse(localStorage.getItem('resources') || '[]'))

  const setAuth = (newToken: string, newUsername: string) => {
    token.value = newToken
    username.value = newUsername
    isAuthenticated.value = true
    
    // 保存到localStorage
    localStorage.setItem('token', newToken)
    localStorage.setItem('username', newUsername)
    
    // 设置API默认header
    api.defaults.headers.common['Authorization'] = `Bearer ${newToken}`
  }

  const clearAuth = () => {
    token.value = null
    username.value = null
    isAuthenticated.value = false
    roles.value = []
    resources.value = []
    
    // 清除localStorage
    localStorage.removeItem('token')
    localStorage.removeItem('username')
    localStorage.removeItem('roles')
    localStorage.removeItem('resources')
    
    // 清除API header
    delete api.defaults.headers.common['Authorization']
  }

  const initAuth = () => {
    // 初始化时设置API header
    if (token.value) {
      api.defaults.headers.common['Authorization'] = `Bearer ${token.value}`
    }
  }

  const verifyToken = async (): Promise<boolean> => {
    if (!token.value) {
      return false
    }

    try {
      const response = await api.get('/api/auth/verify')
      return response.data.success
    } catch (error) {
      // Token无效，清除认证信息
      clearAuth()
      return false
    }
  }

  const fetchPermissions = async (): Promise<void> => {
    if (!isAuthenticated.value) return
    try {
      const resp = await api.get('/api/rbac/me/resources')
      if (resp.data.success) {
        roles.value = resp.data.roles || []
        resources.value = resp.data.resources || []
        localStorage.setItem('roles', JSON.stringify(roles.value))
        localStorage.setItem('resources', JSON.stringify(resources.value))
      }
    } catch (e) {
      // 静默失败，保留已有权限
    }
  }

  const hasPermission = (path: string, method: string = 'GET'): boolean => {
    // 资源未注册（公开资源）由后端兜底；前端只基于已授权资源判断
    for (const r of resources.value) {
      const mMatch = !r.method || r.method.toUpperCase() === method.toUpperCase()
      if (!mMatch) continue
      if (r.match_type === 'exact') {
        if (r.path === path) return true
      } else if (r.match_type === 'prefix') {
        if (path.startsWith(r.path)) return true
      }
    }
    return false
  }

  return {
    token,
    username,
    isAuthenticated,
    roles,
    resources,
    setAuth,
    clearAuth,
    initAuth,
    verifyToken,
    fetchPermissions,
    hasPermission
  }
})