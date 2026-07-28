import { routes } from '@/app/router'

describe('router foundation', () => {
  it('registers authentication, context and platform pages', () => {
    expect(routes.map((route) => route.name)).toEqual([
      'home',
      'tenant-context',
      'login',
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
    ])
    expect(routes.some((route) => String(route.path).includes('login'))).toBe(true)
    expect(routes.some((route) => String(route.path).includes('reports'))).toBe(true)
  })
})
