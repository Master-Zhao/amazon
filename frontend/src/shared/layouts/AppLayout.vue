<script setup lang="ts">
import { computed, watch } from 'vue'
import { useRoute } from 'vue-router'

import { useAuthStore } from '@/features/auth/stores/auth'
import { useTenantContextStore } from '@/features/tenant-context/stores/tenantContext'
import DirectoryBreadcrumb from '@/shared/components/DirectoryBreadcrumb.vue'
import UserAvatarMenu from '@/shared/components/UserAvatarMenu.vue'
import NotificationBell from '@/features/notifications/components/NotificationBell.vue'

const authStore = useAuthStore()
const tenantContextStore = useTenantContextStore()
const route = useRoute()

const permissions = computed(
  () => new Set(tenantContextStore.permissionCodes),
)
const hasTenantContext = computed(() => Boolean(tenantContextStore.tenantId))

function can(...codes: string[]): boolean {
  return (
    !hasTenantContext.value ||
    codes.some((code) => permissions.value.has(code))
  )
}

watch(
  () => authStore.currentUser,
  (user) => {
    if (user && tenantContextStore.status === 'idle') {
      void tenantContextStore.initialize()
    }
  },
  { immediate: true },
)

const isLoginPage = computed(() => route.name === 'login')
</script>

<template>
  <div v-if="isLoginPage" class="login-shell">
    <slot />
  </div>

  <div v-else class="app-shell">
    <header class="topbar">
      <div class="topbar-left">
        <span class="brand-label">amazon ads</span>
        <span class="topbar-separator">|</span>
        <DirectoryBreadcrumb />
      </div>
      <div class="topbar-right">
        <div v-if="authStore.currentUser" class="topbar-user-label">
          {{ authStore.currentUser.username || authStore.currentUser.email }}
        </div>
        <NotificationBell v-if="authStore.currentUser" />
        <RouterLink
          v-if="authStore.currentUser"
          class="topbar-help-btn"
          :class="{ 'router-link-active': route.path.startsWith('/help') }"
          :to="{ name: 'help-center' }"
          title="帮助中心"
          aria-label="帮助中心"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10" />
            <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
            <line x1="12" y1="17" x2="12.01" y2="17" />
          </svg>
        </RouterLink>
        <UserAvatarMenu v-if="authStore.currentUser" />
      </div>
    </header>

    <div class="shell-body">
      <nav class="sidebar" aria-label="平台导航">
        <RouterLink
          class="sidebar-icon-btn"
          to="/advertising/create"
          aria-label="创建广告"
          title="创建广告"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
        </RouterLink>
        <RouterLink
          class="sidebar-icon-btn"
          to="/advertising/overview"
          aria-label="广告总览"
          title="广告总览"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="2" y="7" width="20" height="14" rx="2" ry="2" />
            <path d="M16 7V5a4 4 0 0 0-8 0v2" />
            <line x1="12" y1="12" x2="12" y2="16" />
            <line x1="10" y1="14" x2="14" y2="14" />
          </svg>
        </RouterLink>
      </nav>

      <div class="main-area">
        <nav class="module-nav" aria-label="业务导航">
          <RouterLink to="/">工作台</RouterLink>
          <RouterLink to="/context">卖家空间</RouterLink>
          <RouterLink to="/advertising/overview">广告总览</RouterLink>
          <RouterLink
            v-if="can('reports.view', 'reports.upload')"
            to="/reports/imports"
          >
            数据中心
          </RouterLink>
          <RouterLink v-if="can('analytics.view')" to="/dashboard">
            广告分析
          </RouterLink>
          <RouterLink v-if="can('analytics.view')" to="/remote-data">
            远程数据
          </RouterLink>
          <RouterLink
            v-if="can('analysis.run', 'recommendations.view')"
            to="/analysis"
          >
            智能优化
          </RouterLink>
          <RouterLink
            v-if="
              can('actions.operate', 'approvals.approve', 'executions.execute')
            "
            to="/actions"
          >
            审批执行
          </RouterLink>
          <RouterLink v-if="can('knowledge.view')" to="/knowledge">
            知识中心
          </RouterLink>
          <RouterLink
            v-if="can('context.view', 'rbac.manage', 'audit.view')"
            to="/system"
          >
            系统管理
          </RouterLink>
        </nav>
        <main class="content">
          <slot />
        </main>
      </div>
    </div>
  </div>
</template>
