import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'

import { useAuthStore } from '@/features/auth/stores/auth'
import AppLayout from '@/shared/layouts/AppLayout.vue'

describe('AppLayout business navigation', () => {
  it('highlights data center and advertising analytics independently', async () => {
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
      ],
    })
    await router.push('/reports/imports')
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

    const dataCenterLink = wrapper.get(
      'nav.module-nav a[href="/reports/imports"]',
    )
    const analyticsLink = wrapper.get('nav.module-nav a[href="/dashboard"]')
    expect(dataCenterLink.classes()).toContain('router-link-active')
    expect(analyticsLink.classes()).not.toContain('router-link-active')

    await router.push('/dashboard')
    await flushPromises()
    expect(dataCenterLink.classes()).not.toContain('router-link-active')
    expect(analyticsLink.classes()).toContain('router-link-active')
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
    expect(
      wrapper.get('a[href="/reports/imports"]').classes(),
    ).not.toContain('router-link-active')
    expect(wrapper.get('a[href="/dashboard"]').classes()).not.toContain(
      'router-link-active',
    )

    await router.push('/help/faq/reports-guide')
    await flushPromises()
    expect(helpLink.classes()).toContain('router-link-active')
  })
})
