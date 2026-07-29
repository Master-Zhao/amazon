import { routes } from '@/app/router'

describe('router foundation', () => {
  it('registers authentication, context and platform pages', () => {
    expect(routes.map((route) => route.name)).toEqual([
      'home',
      'tenant-context',
      'login',
      'advertising-index',
      'advertising-overview',
      'advertising-create',
      'reports-index',
      'report-imports',
      'campaign-metrics',
      'campaign-detail',
      'analytics-configuration',
      'analytics-dashboard',
      'targeting-metrics',
      'search-term-metrics',
      'analysis-recommendations',
      'approval-execution',
      'audit-log',
      'knowledge-center',
      'system-management',
      'health-diagnostics',
      'connectivity-test',
      'notification-center',
      'help-center',
      'help-faq-detail',
      'user-profile',
      'account-settings',
    ])
    expect(routes.some((route) => String(route.path).includes('login'))).toBe(true)
    expect(routes.some((route) => String(route.path).includes('reports'))).toBe(true)
  })

  it('keeps data center and advertising analytics as independent routes', () => {
    const reportsIndex = routes.find((route) => route.name === 'reports-index')
    const dataCenter = routes.find((route) => route.name === 'report-imports')
    const advertisingAnalytics = routes.find(
      (route) => route.name === 'analytics-dashboard',
    )

    expect(reportsIndex?.redirect).toEqual({ name: 'report-imports' })
    expect(dataCenter?.path).toBe('/reports/imports')
    expect(dataCenter?.redirect).toBeUndefined()
    expect(advertisingAnalytics?.path).toBe('/dashboard')
    expect(dataCenter?.name).not.toBe(advertisingAnalytics?.name)
  })

  it('keeps FAQ detail, data center and advertising analytics independent', () => {
    const helpCenter = routes.find((route) => route.name === 'help-center')
    const faqDetail = routes.find((route) => route.name === 'help-faq-detail')
    const dataCenter = routes.find((route) => route.name === 'report-imports')
    const advertisingAnalytics = routes.find(
      (route) => route.name === 'analytics-dashboard',
    )

    expect(helpCenter?.path).toBe('/help')
    expect(faqDetail?.path).toBe('/help/faq/:slug')
    expect(faqDetail?.meta?.requiresAuth).toBe(true)
    expect(faqDetail?.name).not.toBe(dataCenter?.name)
    expect(faqDetail?.name).not.toBe(advertisingAnalytics?.name)
  })
})
