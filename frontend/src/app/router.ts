import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

import HealthDiagnosticsPage from '@/features/diagnostics/pages/HealthDiagnosticsPage.vue'
import HomePage from '@/features/home/pages/HomePage.vue'

export const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'home',
    component: HomePage,
    meta: { title: '基础工程状态' },
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

router.afterEach((to) => {
  document.title = `${String(to.meta.title ?? '平台')} · Amazon Ads Optimizer`
})
