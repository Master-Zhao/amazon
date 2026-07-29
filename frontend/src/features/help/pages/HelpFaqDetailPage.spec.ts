import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { beforeEach, vi } from 'vitest'

import { fetchKnowledgeArticle } from '@/features/knowledge/api/knowledgeApi'
import HelpCenterPage from '@/features/help/pages/HelpCenterPage.vue'
import HelpFaqDetailPage from '@/features/help/pages/HelpFaqDetailPage.vue'
import { useTenantContextStore } from '@/features/tenant-context/stores/tenantContext'
import type { ApiError } from '@/shared/api/types'

vi.mock('@/features/knowledge/api/knowledgeApi', () => ({
  fetchKnowledgeArticle: vi.fn(),
  fetchKnowledgeArticles: vi.fn(),
}))

const articleMock = vi.mocked(fetchKnowledgeArticle)

function createHelpRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/help', name: 'help-center', component: HelpCenterPage },
      {
        path: '/help/faq/:slug',
        name: 'help-faq-detail',
        component: HelpFaqDetailPage,
      },
    ],
  })
}

describe('Help FAQ detail page', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    setActivePinia(createPinia())
    useTenantContextStore().$patch({
      tenantId: 'tenant-1',
      storeId: 'store-1',
      storeMarketplaceId: 'marketplace-1',
      profileId: 'profile-1',
      status: 'ready',
      membershipRole: 'OWNER',
    })
  })

  it('loads the requested slug and shows its complete answer', async () => {
    articleMock.mockResolvedValue({
      slug: 'reports-guide',
      title: '三类报表说明',
      summary: '',
      categoryCode: 'reports',
      categoryName: '报表说明',
      sortOrder: 0,
      updatedAt: '',
      body: 'Campaign、Targeting、Search Term 分别进入独立权威粒度。',
      contentHash: 'abc123',
    })
    const router = createHelpRouter()
    await router.push('/help/faq/reports-guide')
    await router.isReady()

    const wrapper = mount(HelpFaqDetailPage, {
      global: { plugins: [router] },
    })
    await flushPromises()

    expect(articleMock).toHaveBeenCalledWith('tenant-1', 'reports-guide')
    expect(wrapper.get('h2').text()).toBe('三类报表说明')
    expect(wrapper.text()).toContain(
      'Campaign、Targeting、Search Term 分别进入独立权威粒度。',
    )
    expect(document.title).toContain('三类报表说明 · 帮助中心')
    expect(
      wrapper.get('a.primary-link').attributes('href'),
    ).toBe('/help')
  })

  it('shows a help-specific not-found state for an invalid slug', async () => {
    const notFound: ApiError = {
      status: 404,
      code: 'NOT_FOUND',
      message: '文章不存在',
      requestId: 'request-1',
      fieldErrors: {},
      retryable: false,
    }
    articleMock.mockRejectedValue(notFound)
    const router = createHelpRouter()
    await router.push('/help/faq/not-exists')
    await router.isReady()

    const wrapper = mount(HelpFaqDetailPage, {
      global: { plugins: [router] },
    })
    await flushPromises()

    expect(wrapper.text()).toContain('未找到该帮助内容')
    expect(wrapper.find('[role="alert"]').exists()).toBe(false)
    expect(
      wrapper.get('a.primary-link').attributes('href'),
    ).toBe('/help')
  })
})
