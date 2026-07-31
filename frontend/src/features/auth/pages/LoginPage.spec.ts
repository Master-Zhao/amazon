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

  it('accepts an alphanumeric account identifier without email validation', async () => {
    const { router, pinia } = createTestContext()
    await router.push('/login')
    await router.isReady()
    const wrapper = mount(LoginPage, {
      global: { plugins: [pinia, router] },
    })

    const submitButton = wrapper.get('button[type="submit"]')
    expect(submitButton.attributes('disabled')).toBeDefined()
    expect(wrapper.get('input[name="password"]').attributes('type')).toBe(
      'password',
    )

    const identifierInput = wrapper.get('input[name="identifier"]')
    expect(identifierInput.attributes('type')).toBe('text')
    expect(identifierInput.attributes('autocomplete')).toBe('username')
    expect(identifierInput.attributes('autocapitalize')).toBe('none')
    expect(identifierInput.attributes('spellcheck')).toBe('false')
    expect(wrapper.get('label[for="identifier"]').text()).toBe('账号或邮箱')

    await identifierInput.setValue('W0765')
    await wrapper.get('input[name="password"]').setValue('secret')
    expect(wrapper.text()).not.toContain('请输入有效的邮箱地址')
    expect(submitButton.attributes('disabled')).toBeUndefined()
  })

  it('rejects an identifier containing only whitespace', async () => {
    const { router, pinia } = createTestContext()
    await router.push('/login')
    await router.isReady()
    const wrapper = mount(LoginPage, {
      global: { plugins: [pinia, router] },
    })

    await wrapper.get('input[name="identifier"]').setValue('   ')
    await wrapper.get('input[name="password"]').setValue('secret')

    expect(wrapper.text()).toContain('请输入账号或邮箱')
    expect(
      wrapper.get('button[type="submit"]').attributes('disabled'),
    ).toBeDefined()
  })

  it('toggles password visibility without submitting the form', async () => {
    const { router, pinia } = createTestContext()
    await router.push('/login')
    await router.isReady()
    const wrapper = mount(LoginPage, {
      global: { plugins: [pinia, router] },
    })

    await wrapper.get('button[aria-label="显示密码"]').trigger('click')
    expect(wrapper.get('input[name="password"]').attributes('type')).toBe(
      'text',
    )
    expect(wrapper.get('button[aria-label="隐藏密码"]')).toBeTruthy()
    expect(loginAccount).not.toHaveBeenCalled()
  })

  it('locks the form and reports progress while login is pending', async () => {
    let resolveLogin: ((value: unknown) => void) | undefined
    vi.mocked(loginAccount).mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveLogin = resolve
        }) as ReturnType<typeof loginAccount>,
    )
    const { router, pinia } = createTestContext()
    await router.push('/login')
    await router.isReady()
    const wrapper = mount(LoginPage, {
      global: { plugins: [pinia, router] },
    })

    await wrapper
      .get('input[name="identifier"]')
      .setValue('demo@example.invalid')
    await wrapper.get('input[name="password"]').setValue('local-password')
    await wrapper.get('form').trigger('submit')

    expect(wrapper.get('form').attributes('aria-busy')).toBe('true')
    expect(wrapper.get('button[type="submit"]').text()).toContain('正在登录')
    expect(
      wrapper.get('input[name="identifier"]').attributes('disabled'),
    ).toBeDefined()

    resolveLogin?.({
      accessToken: 'access',
      user: {
        id: '1',
        email: 'demo@example.invalid',
        username: 'demo',
        firstName: '',
        lastName: '',
      },
    })
    await flushPromises()
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

    await wrapper.get('input[name="identifier"]').setValue('W0765')
    await wrapper.get('input[name="password"]').setValue('local-password')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(loginAccount).toHaveBeenCalledWith(
      'W0765',
      'local-password',
    )
    expect(router.currentRoute.value.name).toBe('home')
  })

  it('shows stable backend error and requestId on login failure', async () => {
    vi.mocked(loginAccount).mockRejectedValue({
      status: 401,
      code: 'AUTH_INVALID_CREDENTIALS',
      message: '账号或密码错误',
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

    await wrapper
      .get('input[name="identifier"]')
      .setValue('demo@example.invalid')
    await wrapper.get('input[name="password"]').setValue('wrong')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(wrapper.get('[role="alert"]').text()).toContain(
      'AUTH_INVALID_CREDENTIALS',
    )
    expect(wrapper.get('[role="alert"]').text()).toContain('req_login_failed')

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
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(loginAccount).toHaveBeenCalledTimes(2)
    expect(wrapper.find('[role="alert"]').exists()).toBe(false)
  })
})
