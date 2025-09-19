/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string
  readonly VITE_APP_TITLE?: string
  readonly VITE_APP_VERSION?: string
  readonly VITE_APP_ENV?: string
  readonly VITE_ENABLE_DEBUG?: string
  readonly VITE_ENABLE_MOCK?: string
  readonly VITE_SENTRY_DSN?: string
  readonly VITE_GA_TRACKING_ID?: string
  // 更多环境变量...
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

// Vue组件类型声明
declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}