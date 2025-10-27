<template>
  <div id="app">
    <!-- 登录页面 -->
    <router-view v-if="$route.name === 'Login'" />
    
    <!-- 主应用布局 -->
    <el-container v-else class="layout-container">
      <!-- 顶部导航 -->
      <el-header class="layout-header">
        <div class="header-content">
          <div class="logo">
            <el-icon><DataAnalysis /></el-icon>
            <span class="title">数据导出系统</span>
          </div>
          
          <div class="header-actions">
            <el-dropdown @command="handleCommand">
              <span class="user-info">
                <el-icon><User /></el-icon>
                {{ authStore.username }}
                <el-icon class="el-icon--right"><ArrowDown /></el-icon>
              </span>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="logout">
                    <el-icon><SwitchButton /></el-icon>
                    退出登录
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>
      </el-header>

      <el-container>
        <!-- 侧边导航 -->
        <el-aside width="200px" class="layout-aside">
          <el-menu
            :default-active="$route.path"
            router
            class="sidebar-menu"
          >
            <el-menu-item index="/">
              <el-icon><House /></el-icon>
              <span>首页</span>
            </el-menu-item>
            <el-menu-item index="/tasks" v-if="authStore.hasPermission('/api/tasks','GET')">
              <el-icon><List /></el-icon>
              <span>任务管理</span>
            </el-menu-item>
            <el-menu-item index="/logs" v-if="authStore.hasPermission('/api/logs','GET')">
              <el-icon><Document /></el-icon>
              <span>执行日志</span>
            </el-menu-item>
            <el-menu-item index="/data-sources" v-if="authStore.hasPermission('/api/data-sources','GET')">
              <el-icon><Coin /></el-icon>
              <span>数据源</span>
            </el-menu-item>
            <el-menu-item index="/users" v-if="authStore.hasPermission('/api/users','GET')">
              <el-icon><User /></el-icon>
              <span>用户管理</span>
            </el-menu-item>
            <el-menu-item index="/rbac/resources" v-if="authStore.hasPermission('/api/rbac/resources','GET')">
              <el-icon><Lock /></el-icon>
              <span>资源权限</span>
            </el-menu-item>
            <el-menu-item index="/rbac/roles" v-if="authStore.hasPermission('/api/rbac/roles','GET')">
              <el-icon><User /></el-icon>
              <span>角色管理</span>
            </el-menu-item>
            <!-- 已移除授权管理页面入口 -->
          </el-menu>
        </el-aside>

        <!-- 主内容区 -->
        <el-main class="layout-main">
          <router-view />
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from './stores/auth'
import {
  DataAnalysis,
  House,
  List,
  Document,
  Coin,
  User,
  ArrowDown,
  SwitchButton,
  Lock,
  Key
} from '@element-plus/icons-vue'

const router = useRouter()
const authStore = useAuthStore()

const handleCommand = async (command: string) => {
  if (command === 'logout') {
    try {
      await ElMessageBox.confirm(
        '确定要退出登录吗？',
        '提示',
        {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning'
        }
      )
      
      authStore.clearAuth()
      ElMessage.success('已退出登录')
      router.push('/login')
    } catch {
      // 用户取消
    }
  }
}

onMounted(() => {
  // 初始化认证状态
  authStore.initAuth()
})
</script>

<style scoped>
.layout-container {
  height: 100vh;
}

.layout-header {
  background-color: #2c3e50;
  color: white;
  display: flex;
  align-items: center;
  padding: 0 20px;
}

.header-content {
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
}

.title {
  font-size: 20px;
  font-weight: bold;
}

.header-actions {
  display: flex;
  align-items: center;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  color: white;
  cursor: pointer;
  padding: 8px 12px;
  border-radius: 6px;
  transition: background-color 0.3s;
}

.user-info:hover {
  background-color: rgba(255, 255, 255, 0.1);
}

.layout-aside {
  background-color: #34495e;
}

.sidebar-menu {
  border: none;
  background-color: #34495e;
}

.sidebar-menu .el-menu-item {
  color: #ecf0f1;
}

.sidebar-menu .el-menu-item:hover {
  background-color: #2c3e50;
}

.sidebar-menu .el-menu-item.is-active {
  background-color: #3498db;
}

.layout-main {
  background-color: #f5f5f5;
  padding: 20px;
}
</style>