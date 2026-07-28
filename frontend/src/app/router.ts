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
    path: '/context',
    name: 'tenant-context',
    component: () =>
      import('@/features/tenant-context/pages/TenantContextPage.vue'),
    meta: { title: '卖家空间', requiresAuth: true },
  },
  {
    path: '/login',
    name: 'login',
    component: () => import('@/features/auth/pages/LoginPage.vue'),
    meta: { title: '登录', guestOnly: true },
  },
  {
    path: '/reports/imports',
    name: 'report-imports',
    component: () =>
      import('@/features/reports/pages/ReportImportsPage.vue'),
    meta: { title: 'Campaign 报表导入', requiresAuth: true },
  },
  {
    path: '/campaigns',
    name: 'campaign-metrics',
    component: () =>
      import('@/features/analytics/pages/CampaignMetricsPage.vue'),
    meta: { title: 'Campaign 指标与异常', requiresAuth: true },
  },
  {
    path: '/campaigns/:campaignId',
    name: 'campaign-detail',
    component: () =>
      import('@/features/analytics/pages/CampaignDetailPage.vue'),
    meta: { title: 'Campaign 详情与趋势', requiresAuth: true },
  },
  {
    path: '/analytics/configuration',
    name: 'analytics-configuration',
    component: () =>
      import('@/features/analytics/pages/AnalyticsConfigurationPage.vue'),
    meta: { title: '目标 ACOS 与异常规则', requiresAuth: true },
  },
  {
    path: '/dashboard',
    name: 'analytics-dashboard',
    component: () => import('@/features/analytics/pages/DashboardPage.vue'),
    meta: { title: '广告工作台', requiresAuth: true },
  },
  {
    path: '/targeting',
    name: 'targeting-metrics',
    component: () =>
      import('@/features/analytics/pages/TargetingMetricsPage.vue'),
    meta: { title: 'Targeting 指标', requiresAuth: true },
  },
  {
    path: '/search-terms',
    name: 'search-term-metrics',
    component: () =>
      import('@/features/analytics/pages/SearchTermMetricsPage.vue'),
    meta: { title: 'Search Term 指标', requiresAuth: true },
  },
  {
    path: '/analysis',
    name: 'analysis-recommendations',
    component: () =>
      import('@/features/analysis/pages/AnalysisRecommendationsPage.vue'),
    meta: { title: 'AI 分析与建议', requiresAuth: true },
  },
  {
    path: '/actions',
    name: 'approval-execution',
    component: () =>
      import('@/features/actions/pages/ApprovalExecutionPage.vue'),
    meta: { title: '审批与执行', requiresAuth: true },
  },
  {
    path: '/audit',
    name: 'audit-log',
    component: () => import('@/features/audit/pages/AuditLogPage.vue'),
    meta: { title: '审计日志', requiresAuth: true },
  },
  {
    path: '/knowledge',
    name: 'knowledge-center',
    component: () =>
      import('@/features/knowledge/pages/KnowledgeCenterPage.vue'),
    meta: { title: '知识中心', requiresAuth: true },
  },
  {
    path: '/system',
    name: 'system-management',
    component: () =>
      import('@/features/system/pages/RoleManagementPage.vue'),
    meta: { title: '系统管理', requiresAuth: true },
  },
  {
    path: '/diagnostics/health',
    name: 'health-diagnostics',
    component: () =>
      import('@/features/diagnostics/pages/HealthDiagnosticsPage.vue'),
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
