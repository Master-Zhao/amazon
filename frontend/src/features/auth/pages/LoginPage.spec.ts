import { createPinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { beforeEach, vi } from 'vitest'

import { loginAccount } from '@/features/auth/api/authApi'
import LoginPage from '@/features/auth/pages/LoginPage.vue'

vi.mock('@/features/auth/api/authApi', () => ({
  loginAccount: vi.fn(),
  fetchCurrentUser: vi.fn(),
  logoutAccount: vi.fn(),
  refreshAccessToken: vi.fn(),
}))

function createTestContext() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'home', component: { template: '<div>home</div>' } },
      { path: '/login', name: 'login', component: LoginPage },
    ],
  })
  return { router, pinia: createPinia() }
}

describe('login page', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('submits credentials and redirects after successful login', async () => {
    vi.mocked(loginAccount).mockResolvedValue({
      accessToken: 'access',
      user: {
        id: '1',
        email: 'demo@example.invalid',
        username: 'demo',
        firstName: '',
        lastName: '',
      },
    })
    const { router, pinia } = createTestContext()
    await router.push('/login?redirect=/')
    await router.isReady()
    const wrapper = mount(LoginPage, {
      global: { plugins: [pinia, router] },
    })

    await wrapper.get('input[name="email"]').setValue('demo@example.invalid')
    await wrapper.get('input[name="password"]').setValue('local-password')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(loginAccount).toHaveBeenCalledWith(
      'demo@example.invalid',
      'local-password',
    )
    expect(router.currentRoute.value.name).toBe('home')
  })

  it('shows stable backend error and requestId on login failure', async () => {
    vi.mocked(loginAccount).mockRejectedValue({
      status: 401,
      code: 'AUTH_INVALID_CREDENTIALS',
      message: '邮箱或密码错误',
      requestId: 'req_login_failed',
      fieldErrors: {},
      retryable: false,
    })
    const { router, pinia } = createTestContext()
    await router.push('/login')
    await router.isReady()
    const wrapper = mount(LoginPage, {
      global: { plugins: [pinia, router] },
    })

    await wrapper.get('input[name="email"]').setValue('demo@example.invalid')
    await wrapper.get('input[name="password"]').setValue('wrong')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(wrapper.get('[role="alert"]').text()).toContain(
      'AUTH_INVALID_CREDENTIALS',
    )
    expect(wrapper.get('[role="alert"]').text()).toContain('req_login_failed')
  })
})
