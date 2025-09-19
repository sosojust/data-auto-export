import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../utils/api'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('token'))
  const username = ref<string | null>(localStorage.getItem('username'))
  const isAuthenticated = ref<boolean>(!!token.value)

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
    
    // 清除localStorage
    localStorage.removeItem('token')
    localStorage.removeItem('username')
    
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

  return {
    token,
    username,
    isAuthenticated,
    setAuth,
    clearAuth,
    initAuth,
    verifyToken
  }
})