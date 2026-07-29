import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { beforeEach, vi } from 'vitest'

import { fetchKnowledgeArticles } from '@/features/knowledge/api/knowledgeApi'
import HelpCenterPage from '@/features/help/pages/HelpCenterPage.vue'
import { useTenantContextStore } from '@/features/tenant-context/stores/tenantContext'

vi.mock('@/features/knowledge/api/knowledgeApi', () => ({
  fetchKnowledgeArticles: vi.fn(),
}))

const articlesMock = vi.mocked(fetchKnowledgeArticles)

describe('Help center page', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    setActivePinia(createPinia())
    useTenantContextStore().$patch({
      tenantId: 'tenant-1',
      status: 'ready',
      membershipRole: 'OWNER',
    })
  })

  it('renders server-backed FAQ links and navigates by stable slug', async () => {
    articlesMock.mockResolvedValue([
      {
        slug: 'reports-guide',
        title: '三类报表说明',
        summary: '',
        categoryCode: 'reports',
        categoryName: '报表说明',
        sortOrder: 0,
        updatedAt: '',
        body: 'Campaign、Targeting、Search Term 分别进入独立权威粒度。',
      },
      {
        slug: 'metrics-guide',
        title: '广告指标说明',
        summary: '',
        categoryCode: 'metrics',
        categoryName: '指标说明',
        sortOrder: 0,
        updatedAt: '',
      },
    ])
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/help', name: 'help-center', component: HelpCenterPage },
        {
          path: '/help/faq/:slug',
          name: 'help-faq-detail',
          component: { template: '<div />' },
        },
      ],
    })
    await router.push('/help')
    await router.isReady()

    const wrapper = mount(HelpCenterPage, {
      global: { plugins: [router] },
    })
    await flushPromises()

    const links = wrapper.findAll('a.help-faq-link')
    expect(links).toHaveLength(2)
    expect(wrapper.text()).toContain('三类报表说明')
    expect(links[0]?.attributes('href')).toBe('/help/faq/reports-guide')

    await links[0]?.trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.name).toBe('help-faq-detail')
    expect(router.currentRoute.value.params.slug).toBe('reports-guide')
  })

  it('renders an empty state when no articles are available', async () => {
    articlesMock.mockResolvedValue([])
    const wrapper = mount(HelpCenterPage, {
      global: {
        stubs: { RouterLink: true },
      },
    })
    await flushPromises()
    expect(wrapper.text()).toContain('当前没有可用的帮助内容')
  })
})
