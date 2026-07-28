import { routes } from '@/app/router'

describe('router foundation', () => {
  it('registers the real Phase 2A login and existing platform pages', () => {
    expect(routes.map((route) => route.name)).toEqual([
      'home',
      'login',
      'health-diagnostics',
    ])
    expect(routes.some((route) => String(route.path).includes('login'))).toBe(true)
    expect(routes.some((route) => String(route.path).includes('campaign'))).toBe(false)
  })
})
