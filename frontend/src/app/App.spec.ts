import { createPinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'

import App from '@/app/App.vue'
import { router } from '@/app/router'

describe('application shell', () => {
  it('mounts with router and Pinia', async () => {
    await router.push('/')
    await router.isReady()

    const wrapper = mount(App, {
      global: {
        plugins: [createPinia(), router],
      },
    })
    await flushPromises()

    expect(wrapper.text()).toContain('基础工程运行框架')
    expect(wrapper.text()).toContain('这里只展示真实的基础工程状态')
  })
})
