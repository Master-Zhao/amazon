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
    meta: {
      title: '账号工作台',
      requiresAuth: true,
      directoryPath: [
        { label: '首页', route: '/' },
      ],
    },
  },
  {
    path: '/context',
    name: 'tenant-context',
    component: () =>
      import('@/features/tenant-context/pages/TenantContextPage.vue'),
    meta: {
      title: '卖家空间',
      requiresAuth: true,
      directoryPath: [
        { label: '首页', route: '/' },
        { label: 'context', route: '/context' },
      ],
    },
  },
  {
    path: '/login',
    name: 'login',
    component: () => import('@/features/auth/pages/LoginPage.vue'),
    meta: { title: '登录', guestOnly: true },
  },
  {
    path: '/advertising',
    name: 'advertising-index',
    component: () =>
      import('@/features/advertising/pages/AdvertisingOverviewPage.vue'),
    meta: {
      title: '广告管理',
      requiresAuth: true,
      directoryPath: [
        { label: '首页', route: '/' },
        { label: 'advertising', route: '/advertising' },
      ],
    },
  },
  {
    path: '/advertising/overview',
    name: 'advertising-overview',
    component: () =>
      import('@/features/advertising/pages/AdvertisingOverviewPage.vue'),
    meta: {
      title: '广告总览',
      requiresAuth: true,
      directoryPath: [
        { label: '首页', route: '/' },
        { label: 'advertising', route: '/advertising' },
        { label: 'overview', route: '/advertising/overview' },
      ],
    },
  },
  {
    path: '/advertising/create',
    name: 'advertising-create',
    component: () =>
      import('@/features/advertising/pages/AdvertisingCreatePage.vue'),
    meta: {
      title: '创建广告',
      requiresAuth: true,
      directoryPath: [
        { label: '首页', route: '/' },
        { label: 'advertising', route: '/advertising' },
        { label: 'create', route: '/advertising/create' },
      ],
    },
  },
  {
    path: '/reports',
    name: 'reports-index',
    redirect: { name: 'report-imports' },
    meta: {
      requiresAuth: true,
    },
  },
  {
    path: '/reports/imports',
    name: 'report-imports',
    component: () =>
      import('@/features/reports/pages/ReportImportsPage.vue'),
    meta: {
      title: '数据中心',
      requiresAuth: true,
      directoryPath: [
        { label: '首页', route: '/' },
        { label: 'reports', route: '/reports' },
        { label: 'imports', route: '/reports/imports' },
      ],
    },
  },
  {
    path: '/campaigns',
    name: 'campaign-metrics',
    component: () =>
      import('@/features/analytics/pages/CampaignMetricsPage.vue'),
    meta: {
      title: 'Campaign 指标与异常',
      requiresAuth: true,
      directoryPath: [
        { label: '首页', route: '/' },
        { label: 'campaigns', route: '/campaigns' },
      ],
    },
  },
  {
    path: '/remote-data',
    name: 'remote-campaign-data',
    component: () =>
      import('@/features/analytics/pages/RemoteCampaignDataPage.vue'),
    meta: {
      title: '远程 Campaign 数据',
      requiresAuth: true,
      directoryPath: [
        { label: '首页', route: '/' },
        { label: 'remote-data', route: '/remote-data' },
      ],
    },
  },
  {
    path: '/campaigns/:campaignId',
    name: 'campaign-detail',
    component: () =>
      import('@/features/analytics/pages/CampaignDetailPage.vue'),
    meta: {
      title: 'Campaign 详情与趋势',
      requiresAuth: true,
      directoryPath: [
        { label: '首页', route: '/' },
        { label: 'campaigns', route: '/campaigns' },
        { label: 'detail', route: '/campaigns' },
      ],
    },
  },
  {
    path: '/analytics/configuration',
    name: 'analytics-configuration',
    component: () =>
      import('@/features/analytics/pages/AnalyticsConfigurationPage.vue'),
    meta: {
      title: '目标 ACOS 与异常规则',
      requiresAuth: true,
      directoryPath: [
        { label: '首页', route: '/' },
        { label: 'analytics', route: '/analytics' },
        { label: 'configuration', route: '/analytics/configuration' },
      ],
    },
  },
  {
    path: '/dashboard',
    name: 'analytics-dashboard',
    component: () => import('@/features/analytics/pages/DashboardPage.vue'),
    meta: {
      title: '广告工作台',
      requiresAuth: true,
      directoryPath: [
        { label: '首页', route: '/' },
        { label: 'dashboard', route: '/dashboard' },
      ],
    },
  },
  {
    path: '/targeting',
    name: 'targeting-metrics',
    component: () =>
      import('@/features/analytics/pages/TargetingMetricsPage.vue'),
    meta: {
      title: 'Targeting 指标',
      requiresAuth: true,
      directoryPath: [
        { label: '首页', route: '/' },
        { label: 'targeting', route: '/targeting' },
      ],
    },
  },
  {
    path: '/search-terms',
    name: 'search-term-metrics',
    component: () =>
      import('@/features/analytics/pages/SearchTermMetricsPage.vue'),
    meta: {
      title: 'Search Term 指标',
      requiresAuth: true,
      directoryPath: [
        { label: '首页', route: '/' },
        { label: 'search-terms', route: '/search-terms' },
      ],
    },
  },
  {
    path: '/analysis',
    name: 'analysis-recommendations',
    component: () =>
      import('@/features/analysis/pages/AnalysisRecommendationsPage.vue'),
    meta: {
      title: 'AI 分析与建议',
      requiresAuth: true,
      directoryPath: [
        { label: '首页', route: '/' },
        { label: 'analysis', route: '/analysis' },
      ],
    },
  },
  {
    path: '/actions',
    name: 'approval-execution',
    component: () =>
      import('@/features/actions/pages/ApprovalExecutionPage.vue'),
    meta: {
      title: '审批与执行',
      requiresAuth: true,
      directoryPath: [
        { label: '首页', route: '/' },
        { label: 'actions', route: '/actions' },
      ],
    },
  },
  {
    path: '/audit',
    name: 'audit-log',
    component: () => import('@/features/audit/pages/AuditLogPage.vue'),
    meta: {
      title: '审计日志',
      requiresAuth: true,
      directoryPath: [
        { label: '首页', route: '/' },
        { label: 'audit', route: '/audit' },
      ],
    },
  },
  {
    path: '/knowledge',
    name: 'knowledge-center',
    component: () =>
      import('@/features/knowledge/pages/KnowledgeCenterPage.vue'),
    meta: {
      title: '知识中心',
      requiresAuth: true,
      directoryPath: [
        { label: '首页', route: '/' },
        { label: 'knowledge', route: '/knowledge' },
      ],
    },
  },
  {
    path: '/system',
    name: 'system-management',
    component: () =>
      import('@/features/system/pages/RoleManagementPage.vue'),
    meta: {
      title: '系统管理',
      requiresAuth: true,
      directoryPath: [
        { label: '首页', route: '/' },
        { label: 'system', route: '/system' },
      ],
    },
  },
  {
    path: '/diagnostics/health',
    name: 'health-diagnostics',
    component: () =>
      import('@/features/diagnostics/pages/HealthDiagnosticsPage.vue'),
    meta: {
      title: '运行诊断',
      directoryPath: [
        { label: '首页', route: '/' },
        { label: 'diagnostics', route: '/diagnostics/health' },
      ],
    },
  },
  {
    path: '/diagnostics/connectivity',
    name: 'connectivity-test',
    component: () =>
      import('@/features/diagnostics/pages/ConnectivityTestPage.vue'),
    meta: {
      title: '前后端连通性验证',
      directoryPath: [
        { label: '首页', route: '/' },
        { label: 'diagnostics', route: '/diagnostics/connectivity' },
      ],
    },
  },
  {
    path: '/notifications',
    name: 'notification-center',
    component: () =>
      import('@/features/notifications/pages/NotificationCenterPage.vue'),
    meta: {
      title: '通知中心',
      requiresAuth: true,
      directoryPath: [
        { label: '首页', route: '/' },
        { label: 'notifications', route: '/notifications' },
      ],
    },
  },
  {
    path: '/help',
    name: 'help-center',
    component: () =>
      import('@/features/help/pages/HelpCenterPage.vue'),
    meta: {
      title: '帮助中心',
      requiresAuth: true,
      directoryPath: [
        { label: '首页', route: '/' },
        { label: 'help', route: '/help' },
      ],
    },
  },
  {
    path: '/help/faq/:slug',
    name: 'help-faq-detail',
    component: () =>
      import('@/features/help/pages/HelpFaqDetailPage.vue'),
    meta: {
      title: '常见问题',
      requiresAuth: true,
      directoryPath: [
        { label: '首页', route: '/' },
        { label: 'help', route: '/help' },
        { label: 'faq', route: '/help' },
      ],
    },
  },
  {
    path: '/profile',
    name: 'user-profile',
    component: () =>
      import('@/features/advertising/pages/AdvertisingOverviewPage.vue'),
    meta: {
      title: '个人信息',
      requiresAuth: true,
      directoryPath: [
        { label: '首页', route: '/' },
        { label: 'profile', route: '/profile' },
      ],
    },
  },
  {
    path: '/settings',
    name: 'account-settings',
    component: () =>
      import('@/features/advertising/pages/AdvertisingOverviewPage.vue'),
    meta: {
      title: '账户设置',
      requiresAuth: true,
      directoryPath: [
        { label: '首页', route: '/' },
        { label: 'settings', route: '/settings' },
      ],
    },
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
