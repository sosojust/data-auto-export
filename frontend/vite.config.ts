import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  // 加载环境变量
  const env = loadEnv(mode, process.cwd(), '')
  const API_BASE_URL = env.VITE_API_BASE_URL || 'http://localhost:5001'

  return {
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  server: {
    // host: '0.0.0.0',
    port: 3000,
    hmr: false, // 禁用热模块替换
    allowedHosts: ['aexport.insgeek.cn'],
    watch: {
      ignored: ['**/*'] // 禁用文件监听
    },
    proxy: {
      '/api': {
        target: API_BASE_URL,
        changeOrigin: true,
        secure: false
      }
    }
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    sourcemap: false,
    rollupOptions: {
      external: ['fsevents']
    }
  },
  optimizeDeps: {
    exclude: ['fsevents']
  }
  }
})
