<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

import { useAuthStore } from '@/features/auth/stores/auth'

const authStore = useAuthStore()
const router = useRouter()
const loggingOut = ref(false)

async function performLogout(): Promise<void> {
  loggingOut.value = true
  try {
    await authStore.logout()
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
        <h1>账号认证工作台</h1>
      </div>
      <div class="account-actions">
        <span class="phase-badge">Phase 2A</span>
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
      <RouterLink v-if="authStore.currentUser" to="/">账号首页</RouterLink>
      <RouterLink v-else to="/login">登录</RouterLink>
      <RouterLink to="/diagnostics/health">运行诊断</RouterLink>
      <a href="/api/docs/" target="_blank" rel="noreferrer">OpenAPI</a>
    </nav>

    <main class="content">
      <slot />
    </main>
  </div>
</template>
