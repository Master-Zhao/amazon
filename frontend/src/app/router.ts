import type { Pinia } from 'pinia'
import {
  createRouter,
  createWebHistory,
  type RouteRecordRaw,
  type Router,
} from 'vue-router'

import { useAuthStore } from '@/features/auth/stores/auth'
import LoginPage from '@/features/auth/pages/LoginPage.vue'
import HealthDiagnosticsPage from '@/features/diagnostics/pages/HealthDiagnosticsPage.vue'
import HomePage from '@/features/home/pages/HomePage.vue'

export const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'home',
    component: HomePage,
    meta: { title: '账号工作台', requiresAuth: true },
  },
  {
    path: '/login',
    name: 'login',
    component: LoginPage,
    meta: { title: '登录', guestOnly: true },
  },
  {
    path: '/diagnostics/health',
    name: 'health-diagnostics',
    component: HealthDiagnosticsPage,
    meta: { title: '运行诊断' },
  },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
})

export function installAuthRouterGuards(
  targetRouter: Router,
  pinia: Pinia,
): void {
  targetRouter.beforeEach(async (to) => {
    const authStore = useAuthStore(pinia)
    await authStore.initialize()

    if (to.meta.requiresAuth && !authStore.isAuthenticated) {
      return { name: 'login', query: { redirect: to.fullPath } }
    }
    if (to.meta.guestOnly && authStore.isAuthenticated) {
      return { name: 'home' }
    }
    return true
  })
}

router.afterEach((to) => {
  document.title = `${String(to.meta.title ?? '平台')} · Amazon Ads Optimizer`
})
