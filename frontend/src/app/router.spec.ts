import { routes } from '@/app/router'

describe('router foundation', () => {
  it('registers authentication and M1 context pages', () => {
    expect(routes.map((route) => route.name)).toEqual([
      'home',
      'login',
      'dashboard',
      'targeting-analytics',
      'search-term-analytics',
      'reports',
      'optimization',
      'knowledge',
      'audit',
      'seller-context',
      'role-management',
      'health-diagnostics',
    ])
    expect(routes.some((route) => String(route.path).includes('login'))).toBe(true)
    expect(routes.some((route) => String(route.path).includes('campaign'))).toBe(false)
  })
})
