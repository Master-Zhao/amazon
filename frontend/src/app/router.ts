import type { Pinia } from 'pinia'
import {
  createRouter,
  createWebHistory,
  type RouteRecordRaw,
  type Router,
} from 'vue-router'

import { useAuthStore } from '@/features/auth/stores/auth'
export const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'home',
    component: () => import('@/features/home/pages/HomePage.vue'),
    meta: { title: '账号工作台', requiresAuth: true },
  },
  {
    path: '/login',
    name: 'login',
    component: () => import('@/features/auth/pages/LoginPage.vue'),
    meta: { title: '登录', guestOnly: true },
  },
  {
    path: '/dashboard',
    name: 'dashboard',
    component: () => import('@/features/dashboard/pages/DashboardPage.vue'),
    meta: { title: '广告工作台', requiresAuth: true },
  },
  {
    path: '/advertising/targeting',
    name: 'targeting-analytics',
    component: () => import('@/features/targeting/pages/TargetingAnalyticsPage.vue'),
    meta: { title: 'Targeting 分析', requiresAuth: true },
  },
  {
    path: '/advertising/search-terms',
    name: 'search-term-analytics',
    component: () =>
      import('@/features/search-terms/pages/SearchTermAnalyticsPage.vue'),
    meta: { title: 'Search Term 分析', requiresAuth: true },
  },
  {
    path: '/reports',
    name: 'reports',
    component: () => import('@/features/reports/pages/ReportCenterPage.vue'),
    meta: { title: '数据中心', requiresAuth: true },
  },
  {
    path: '/optimization',
    name: 'optimization',
    component: () =>
      import('@/features/optimization/pages/OptimizationWorkflowPage.vue'),
    meta: { title: '优化工作流', requiresAuth: true },
  },
  {
    path: '/knowledge',
    name: 'knowledge',
    component: () => import('@/features/knowledge/pages/KnowledgePage.vue'),
    meta: { title: '知识库', requiresAuth: true },
  },
  {
    path: '/audit',
    name: 'audit',
    component: () => import('@/features/audit/pages/AuditLogPage.vue'),
    meta: { title: '审计日志', requiresAuth: true },
  },
  {
    path: '/seller-context',
    name: 'seller-context',
    component: () =>
      import('@/features/tenant-context/pages/SellerContextPage.vue'),
    meta: { title: '卖家空间', requiresAuth: true },
  },
  {
    path: '/system/roles',
    name: 'role-management',
    component: () => import('@/features/system/pages/RoleManagementPage.vue'),
    meta: { title: '角色与权限', requiresAuth: true },
  },
  {
    path: '/diagnostics/health',
    name: 'health-diagnostics',
    component: () =>
      import('@/features/diagnostics/pages/HealthDiagnosticsPage.vue'),
    meta: { title: '运行诊断' },
  },
  {
    path: '/advertising/campaigns',
    name: 'campaigns',
    component: () => import('@/features/campaigns/pages/CampaignsPage.vue'),
    meta: { title: 'Campaign', requiresAuth: true },
  },
  {
    path: '/actions',
    name: 'actions',
    component: () => import('@/features/actions/pages/ActionCenterPage.vue'),
    meta: { title: '审批执行', requiresAuth: true },
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
