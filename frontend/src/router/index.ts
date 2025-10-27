import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Tasks from '../views/Tasks.vue'
import TaskCreate from '../views/TaskCreate.vue'
import TaskEdit from '../views/TaskEdit.vue'
import Logs from '../views/Logs.vue'
import DataSources from '../views/DataSources.vue'
import Users from '../views/Users.vue'
import RbacResources from '../views/RbacResources.vue'
import RbacRoles from '../views/RbacRoles.vue'
import Login from '../views/Login.vue'
import { useAuthStore } from '../stores/auth'
import { ElMessage } from 'element-plus'

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
    meta: { requiresAuth: true, requiredResource: { path: '/api/tasks', method: 'GET' } }
  },
  {
    path: '/tasks/create',
    name: 'TaskCreate',
    component: TaskCreate,
    meta: { requiresAuth: true, requiredResource: { path: '/api/tasks', method: 'POST' } }
  },
  {
    path: '/tasks/:id/edit',
    name: 'TaskEdit',
    component: TaskEdit,
    meta: { requiresAuth: true, requiredResource: { path: '/api/tasks', method: 'GET' } }
  },
  {
    path: '/logs',
    name: 'Logs',
    component: Logs,
    meta: { requiresAuth: true, requiredResource: { path: '/api/logs', method: 'GET' } }
  },
  {
    path: '/data-sources',
    name: 'DataSources',
    component: DataSources,
    meta: { requiresAuth: true, requiredResource: { path: '/api/data-sources', method: 'GET' } }
  },
  {
    path: '/users',
    name: 'Users',
    component: Users,
    meta: { requiresAuth: true, requiredResource: { path: '/api/users', method: 'GET' } }
  },
  {
    path: '/rbac/resources',
    name: 'RbacResources',
    component: RbacResources,
    meta: { requiresAuth: true, requiredResource: { path: '/api/rbac/resources', method: 'GET' } }
  },
  {
    path: '/rbac/roles',
    name: 'RbacRoles',
    component: RbacRoles,
    meta: { requiresAuth: true, requiredResource: { path: '/api/rbac/roles', method: 'GET' } }
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

    // 拉取权限（仅在缺失时）
    if (!authStore.resources?.length) {
      await authStore.fetchPermissions()
    }

    // 基于资源进行权限校验
    const req: any = to.meta.requiredResource
    if (req && !authStore.hasPermission(req.path, req.method || 'GET')) {
      ElMessage.error('无权限访问该页面')
      next('/')
      return
    }
  }
  
  next()
})

export default router