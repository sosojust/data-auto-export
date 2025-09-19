import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Tasks from '../views/Tasks.vue'
import TaskCreate from '../views/TaskCreate.vue'
import TaskEdit from '../views/TaskEdit.vue'
import Logs from '../views/Logs.vue'
import DataSources from '../views/DataSources.vue'
import Login from '../views/Login.vue'
import { useAuthStore } from '../stores/auth'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    name: 'Home',
    component: Home,
    meta: { requiresAuth: true }
  },
  {
    path: '/tasks',
    name: 'Tasks',
    component: Tasks,
    meta: { requiresAuth: true }
  },
  {
    path: '/tasks/create',
    name: 'TaskCreate',
    component: TaskCreate,
    meta: { requiresAuth: true }
  },
  {
    path: '/tasks/:id/edit',
    name: 'TaskEdit',
    component: TaskEdit,
    meta: { requiresAuth: true }
  },
  {
    path: '/logs',
    name: 'Logs',
    component: Logs,
    meta: { requiresAuth: true }
  },
  {
    path: '/data-sources',
    name: 'DataSources',
    component: DataSources,
    meta: { requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach(async (to, _from, next) => {
  const authStore = useAuthStore()
  
  // 初始化认证状态
  authStore.initAuth()
  
  // 如果访问登录页面且已登录，重定向到首页
  if (to.name === 'Login' && authStore.isAuthenticated) {
    next('/')
    return
  }
  
  // 如果页面需要认证
  if (to.meta.requiresAuth) {
    if (!authStore.isAuthenticated) {
      // 未登录，重定向到登录页
      next('/login')
      return
    }
    
    // 验证token有效性
    const isValid = await authStore.verifyToken()
    if (!isValid) {
      // Token无效，重定向到登录页
      next('/login')
      return
    }
  }
  
  next()
})

export default router