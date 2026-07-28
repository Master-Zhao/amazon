import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, vi } from 'vitest'

import {
  fetchKnowledgeArticle,
  fetchKnowledgeArticles,
  fetchKnowledgeCategories,
} from '@/features/knowledge/api/knowledgeApi'
import KnowledgeCenterPage from '@/features/knowledge/pages/KnowledgeCenterPage.vue'
import { useTenantContextStore } from '@/features/tenant-context/stores/tenantContext'

vi.mock('@/features/knowledge/api/knowledgeApi', () => ({
  fetchKnowledgeCategories: vi.fn(),
  fetchKnowledgeArticles: vi.fn(),
  fetchKnowledgeArticle: vi.fn(),
}))

const categoriesMock = vi.mocked(fetchKnowledgeCategories)
const articlesMock = vi.mocked(fetchKnowledgeArticles)
const articleMock = vi.mocked(fetchKnowledgeArticle)

describe('Knowledge center page', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    setActivePinia(createPinia())
    useTenantContextStore().$patch({
      tenantId: 'tenant-1',
      status: 'ready',
      membershipRole: 'OWNER',
      permissionCodes: ['knowledge.view'],
    })
  })

  it('renders server categories, article list and detail', async () => {
    categoriesMock.mockResolvedValue([
      {
        code: 'metrics',
        name: '广告指标说明',
        description: '指标',
        sortOrder: 1,
      },
    ])
    articlesMock.mockResolvedValue([
      {
        slug: 'metrics',
        title: '核心指标',
        summary: '确定性指标口径',
        categoryCode: 'metrics',
        categoryName: '广告指标说明',
        sortOrder: 1,
        updatedAt: '2026-07-28T00:00:00Z',
      },
    ])
    articleMock.mockResolvedValue({
      slug: 'metrics',
      title: '核心指标',
      summary: '确定性指标口径',
      categoryCode: 'metrics',
      categoryName: '广告指标说明',
      sortOrder: 1,
      updatedAt: '2026-07-28T00:00:00Z',
      body: 'ACOS=花费/销售额。',
      contentHash: 'abc123',
    })

    const wrapper = mount(KnowledgeCenterPage)
    await flushPromises()
    expect(wrapper.text()).toContain('核心指标')

    const detail = wrapper
      .findAll('button')
      .find((button) => button.text() === '查看详情')
    await detail?.trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('ACOS=花费/销售额')
    expect(wrapper.text()).toContain('abc123')
  })

  it('renders a true empty state', async () => {
    categoriesMock.mockResolvedValue([])
    articlesMock.mockResolvedValue([])
    const wrapper = mount(KnowledgeCenterPage)
    await flushPromises()
    expect(wrapper.text()).toContain('当前分类暂无文章')
  })

  it('renders an API failure state', async () => {
    categoriesMock.mockRejectedValue(new Error('knowledge unavailable'))
    articlesMock.mockRejectedValue(new Error('knowledge unavailable'))
    const wrapper = mount(KnowledgeCenterPage)
    await flushPromises()
    expect(wrapper.find('[role="alert"]').exists()).toBe(true)
  })
})
