import { createPinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'

import App from '@/app/App.vue'
import { router } from '@/app/router'
import { useAuthStore } from '@/features/auth/stores/auth'

describe('application shell', () => {
  it('mounts the authenticated Phase 2A shell', async () => {
    const pinia = createPinia()
    const authStore = useAuthStore(pinia)
    authStore.accessToken = 'memory-only-token'
    authStore.currentUser = {
      id: '1',
      email: 'demo@example.invalid',
      username: 'demo',
      firstName: '',
      lastName: '',
    }
    await router.push('/')
    await router.isReady()

    const wrapper = mount(App, {
      global: {
        plugins: [pinia, router],
      },
    })
    await flushPromises()

    expect(wrapper.text()).toContain('账号认证工作台')
    expect(wrapper.text()).toContain('欢迎回来，demo')
  })
})
