import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'

import { useAuthStore } from '@/features/auth/stores/auth'
import AppLayout from '@/shared/layouts/AppLayout.vue'

describe('AppLayout shell navigation', () => {
  it('removes the legacy horizontal business navigation and keeps the advertising sidebar', async () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        {
          path: '/advertising/overview',
          name: 'advertising-overview',
          component: { template: '<div />' },
        },
        {
          path: '/advertising/create',
          name: 'advertising-create',
          component: { template: '<div />' },
        },
      ],
    })
    await router.push('/advertising/overview')
    await router.isReady()

    const wrapper = mount(AppLayout, {
      global: {
        plugins: [createPinia(), router],
        stubs: {
          DirectoryBreadcrumb: true,
          NotificationBell: true,
          UserAvatarMenu: true,
        },
      },
      slots: { default: '<div>content</div>' },
    })

    expect(wrapper.find('nav.module-nav').exists()).toBe(false)
    expect(wrapper.find('[aria-label="业务导航"]').exists()).toBe(false)
    expect(wrapper.get('a[aria-label="创建广告"]').attributes('href')).toBe(
      '/advertising/create',
    )
    const overviewLink = wrapper.get('a[aria-label="广告总览"]')
    expect(overviewLink.attributes('href')).toBe('/advertising/overview')
    expect(overviewLink.classes()).toContain('router-link-active')
    expect(wrapper.text()).toContain('content')
  })

  it('opens help from the question icon without activating business modules', async () => {
    const pinia = createPinia()
    const auth = useAuthStore(pinia)
    auth.$patch({
      accessToken: 'token',
      currentUser: {
        id: 'user-1',
        email: 'demo@example.invalid',
        username: 'demo',
        firstName: '',
        lastName: '',
      },
      initializationStatus: 'ready',
    })
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        {
          path: '/reports/imports',
          name: 'report-imports',
          component: { template: '<div />' },
        },
        {
          path: '/dashboard',
          name: 'analytics-dashboard',
          component: { template: '<div />' },
        },
        {
          path: '/help',
          name: 'help-center',
          component: { template: '<div />' },
        },
        {
          path: '/help/faq/:slug',
          name: 'help-faq-detail',
          component: { template: '<div />' },
        },
      ],
    })
    await router.push('/dashboard')
    await router.isReady()

    const wrapper = mount(AppLayout, {
      global: {
        plugins: [pinia, router],
        stubs: {
          DirectoryBreadcrumb: true,
          NotificationBell: true,
          UserAvatarMenu: true,
        },
      },
      slots: { default: '<div>content</div>' },
    })

    const helpLink = wrapper.get('a[aria-label="帮助中心"]')
    expect(helpLink.attributes('href')).toBe('/help')
    await helpLink.trigger('click')
    await flushPromises()

    expect(router.currentRoute.value.name).toBe('help-center')
    expect(wrapper.find('nav.module-nav').exists()).toBe(false)

    await router.push('/help/faq/reports-guide')
    await flushPromises()
    expect(helpLink.classes()).toContain('router-link-active')
  })
})
