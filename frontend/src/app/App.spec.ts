import { createPinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'

import App from '@/app/App.vue'
import { router } from '@/app/router'
import { useAuthStore } from '@/features/auth/stores/auth'

describe('application shell', () => {
  it('mounts the authenticated seller workspace shell', async () => {
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

    expect(wrapper.text()).toContain('Amazon 广告智能优化')
    expect(wrapper.text()).toContain('欢迎回来，demo')
  })
})
