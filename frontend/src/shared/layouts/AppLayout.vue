<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import { useAuthStore } from '@/features/auth/stores/auth'
import { useTenantContextStore } from '@/features/tenant-context/stores/context'

const authStore = useAuthStore()
const contextStore = useTenantContextStore()
const router = useRouter()
const loggingOut = ref(false)
const permissions = computed(() => new Set(contextStore.permissionCodes))
const hasContext = computed(() => Boolean(contextStore.selectedTenantId))

function can(...codes: string[]): boolean {
  return !hasContext.value || codes.some((code) => permissions.value.has(code))
}

watch(
  () => authStore.currentUser,
  (user) => {
    if (user && contextStore.tenants.length === 0 && !contextStore.loading) {
      void contextStore.initialize().catch(() => undefined)
    }
  },
  { immediate: true },
)

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
      <RouterLink
        v-if="authStore.currentUser && can('reports.view', 'reports.import')"
        to="/reports"
      >
        数据中心
      </RouterLink>
      <RouterLink
        v-if="authStore.currentUser && can('analytics.view')"
        to="/dashboard"
      >
        广告分析
      </RouterLink>
      <RouterLink
        v-if="authStore.currentUser && can('analysis.run', 'recommendations.view')"
        to="/optimization"
      >
        智能优化
      </RouterLink>
      <RouterLink
        v-if="authStore.currentUser && can('actions.submit', 'actions.approve', 'actions.execute')"
        to="/actions"
      >
        审批执行
      </RouterLink>
      <RouterLink
        v-if="authStore.currentUser && can('knowledge.view')"
        to="/knowledge"
      >
        知识中心
      </RouterLink>
      <RouterLink
        v-if="authStore.currentUser && can('roles.manage', 'audit.view', 'context.view')"
        to="/system/roles"
      >
        系统管理
      </RouterLink>
      <RouterLink v-if="!authStore.currentUser" to="/login">登录</RouterLink>
    </nav>

    <main class="content">
      <slot />
    </main>
  </div>
</template>
