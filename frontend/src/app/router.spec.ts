import { routes } from '@/app/router'

describe('router foundation', () => {
  it('registers only real Phase 1 platform pages', () => {
    expect(routes.map((route) => route.name)).toEqual([
      'home',
      'health-diagnostics',
    ])
    expect(routes.some((route) => String(route.path).includes('login'))).toBe(false)
    expect(routes.some((route) => String(route.path).includes('campaign'))).toBe(false)
  })
})
