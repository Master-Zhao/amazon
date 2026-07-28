<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

import { useAuthStore } from '@/features/auth/stores/auth'
import { useTenantContextStore } from '@/features/tenant-context/stores/context'

const authStore = useAuthStore()
const contextStore = useTenantContextStore()
const router = useRouter()
const loggingOut = ref(false)

async function performLogout(): Promise<void> {
  loggingOut.value = true
  try {
    await authStore.logout()
    contextStore.clear()
    await router.replace({ name: 'login' })
  } finally {
    loggingOut.value = false
  }
}
</script>

<template>
  <div class="app-shell">
    <header class="topbar">
      <div>
        <p class="eyebrow">AMAZON ADS OPTIMIZER</p>
        <h1>Amazon 广告智能优化系统</h1>
      </div>
      <div class="account-actions">
        <span class="phase-badge">V1</span>
        <span v-if="authStore.currentUser" class="account-email">
          {{ authStore.currentUser.email }}
        </span>
        <button
          v-if="authStore.currentUser"
          class="secondary-button"
          type="button"
          :disabled="loggingOut"
          @click="performLogout"
        >
          {{ loggingOut ? '正在退出…' : '退出登录' }}
        </button>
      </div>
    </header>

    <nav class="nav" aria-label="平台导航">
      <RouterLink v-if="authStore.currentUser" to="/">工作台</RouterLink>
      <RouterLink v-if="authStore.currentUser" to="/seller-context">卖家空间</RouterLink>
      <RouterLink v-if="authStore.currentUser" to="/reports">数据中心</RouterLink>
      <RouterLink v-if="authStore.currentUser" to="/system/roles">角色与权限</RouterLink>
      <RouterLink v-else to="/login">登录</RouterLink>
      <RouterLink to="/diagnostics/health">运行诊断</RouterLink>
      <a href="/api/docs/" target="_blank" rel="noreferrer">OpenAPI</a>
    </nav>

    <main class="content">
      <slot />
    </main>
  </div>
</template>
