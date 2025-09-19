import axios from 'axios'
import { ElMessage } from 'element-plus'

// 从环境变量获取API基础URL，如果未设置则使用默认值
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5001'

// 创建默认axios实例
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000, // 1分钟超时，用于一般操作
  headers: {
    'Content-Type': 'application/json'
  }
})

// 创建长时间操作的axios实例（用于任务执行等）
const longTaskApi = axios.create({
  baseURL: API_BASE_URL,
  timeout: 3600000, // 1小时超时，用于长查询任务
  headers: {
    'Content-Type': 'application/json'
  }
})

// 通用请求拦截器配置
const setupInterceptors = (instance: any) => {
  // 请求拦截器
  instance.interceptors.request.use(
    (config: any) => {
      // 自动添加Authorization头
      const token = localStorage.getItem('token')
      if (token) {
        config.headers.Authorization = `Bearer ${token}`
      }
      return config
    },
    (error: any) => {
      return Promise.reject(error)
    }
  )

  // 响应拦截器
  instance.interceptors.response.use(
    (response: any) => {
      return response
    },
    (error: any) => {
      if (error.response?.status === 401) {
        // Token无效或过期，清除本地存储并跳转到登录页
        localStorage.removeItem('token')
        localStorage.removeItem('username')
        ElMessage.error('登录已过期，请重新登录')
        // 跳转到登录页
        window.location.href = '/login'
      } else if (error.code === 'ECONNABORTED' && error.message.includes('timeout')) {
        ElMessage.error('请求超时，请稍后重试')
      } else {
        ElMessage.error(error.response?.data?.error || error.message || '请求失败')
      }
      return Promise.reject(error)
    }
  )
}

// 为两个实例配置拦截器
setupInterceptors(api)
setupInterceptors(longTaskApi)

export default api
export { longTaskApi }