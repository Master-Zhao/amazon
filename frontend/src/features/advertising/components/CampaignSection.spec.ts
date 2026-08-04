import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { beforeEach, vi } from 'vitest'

import { fetchCampaignOverview } from '@/features/advertising/api/campaignApi'
import CampaignSection from '@/features/advertising/components/CampaignSection.vue'
import type { CampaignListResponse } from '@/features/advertising/types/campaign'
import { useTenantContextStore } from '@/features/tenant-context/stores/tenantContext'

vi.mock('@/features/advertising/api/campaignApi', () => ({
  fetchCampaignOverview: vi.fn(),
  exportCampaignOverview: vi.fn(),
}))

const fetchMock = vi.mocked(fetchCampaignOverview)

const response: CampaignListResponse = {
  items: [
    {
      campaignKey: 'cmp_demo',
      name: '真实远程广告活动',
      referenceCode: 'SP-REMOTE-001',
      enabled: true,
      targetingType: 'AUTO',
      status: 'DELIVERING',
      biddingStrategy: 'FIXED_BIDS',
      startDate: '2026-07-01',
      endDate: null,
      dailyBudget: { amount: '100.00', currencyCode: 'USD' },
      metrics: {
        impressions: 1000,
        topOfSearchShare: null,
        spend: { amount: '75.00', currencyCode: 'USD' },
        sales: { amount: '300.00', currencyCode: 'USD' },
        clicks: 50,
        ctr: '0.05',
        totalCost: { amount: '75.00', currencyCode: 'USD' },
        orders: 10,
        cpc: { amount: '1.50', currencyCode: 'USD' },
        acos: '0.25',
        cvr: '0.20',
      },
      metadataMatched: true,
      partialFields: ['topOfSearchShare', 'ordersAttributionWindow'],
    },
  ],
  summary: {
    impressions: 1000,
    topOfSearchShare: null,
    spend: { amount: '75.00', currencyCode: 'USD' },
    sales: { amount: '300.00', currencyCode: 'USD' },
    clicks: 50,
    ctr: '0.05',
    totalCost: { amount: '75.00', currencyCode: 'USD' },
    orders: 10,
    cpc: { amount: '1.50', currencyCode: 'USD' },
    acos: '0.25',
    cvr: '0.20',
  },
  dashboard: {
    trend: [],
    riskLevels: [
      { level: 'VERY_HIGH', count: 0 },
      { level: 'HIGH', count: 0 },
      { level: 'MEDIUM', count: 0 },
      { level: 'LOW', count: 0 },
      { level: 'VERY_LOW', count: 1 },
    ],
    evaluatedCampaigns: 1,
    targetAcos: '0.25',
    unavailableRuleCodes: ['BUDGET_EARLY_EXHAUSTION'],
    riskSemantics: 'SYSTEM_RULES_AGGREGATED',
  },
  pagination: { page: 1, pageSize: 15, total: 1, totalPages: 1 },
  meta: {
    source: 'REMOTE_MYSQL',
    currencyCode: 'USD',
    timezone: 'America/Los_Angeles',
    startDate: '2026-07-01',
    endDate: '2026-07-30',
    dataThroughDate: '2026-07-30',
    totalCostSemantics: 'SPEND_ALIAS',
    attributionSemantics: 'REMOTE_FIELDS_UNVERIFIED',
    statusFilterSemantics: 'ANALYSIS_FILTER_SCM_DISPLAY',
  },
}

async function mountSection() {
  const pinia = createPinia()
  setActivePinia(pinia)
  useTenantContextStore().$patch({
    tenantId: 'tenant-1',
    storeId: 'store-1',
    storeMarketplaceId: 'store-marketplace-1',
    profileId: 'profile-1',
    status: 'ready',
  })
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/advertising/overview', component: { template: '<div />' } },
      { path: '/context', component: { template: '<div />' } },
    ],
  })
  await router.push('/advertising/overview')
  await router.isReady()
  const wrapper = mount(CampaignSection, {
    global: { plugins: [pinia, router] },
  })
  await flushPromises()
  return { wrapper, router }
}

describe('CampaignSection', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    fetchMock.mockResolvedValue(response)
  })

  it('renders the 19-column read-only remote Campaign table and totals', async () => {
    const { wrapper } = await mountSection()

    expect(fetchMock).toHaveBeenCalledWith(
      'tenant-1',
      'profile-1',
      {
        enabled: true,
        ordering: '-spend',
        page: 1,
        pageSize: 15,
        includeSummary: true,
      },
      expect.any(AbortSignal),
    )
    expect(wrapper.findAll('[role="columnheader"]')).toHaveLength(19)
    expect(wrapper.text()).toContain('真实远程广告活动')
    expect(wrapper.text()).toContain('SP-REMOTE-001')
    expect(wrapper.text()).toContain('25.00%')
    expect(wrapper.text()).toContain('合计')
    expect(wrapper.get('.campaign-create-button').attributes('disabled')).toBeDefined()
    expect(wrapper.get('.campaign-switch').attributes('aria-checked')).toBe('true')
  })

  it('debounces search, resets the page, and exposes the active filter chip', async () => {
    vi.useFakeTimers()
    try {
      const { wrapper, router } = await mountSection()
      const input = wrapper.get('input[aria-label="查找广告活动"]')
      await input.setValue('remote shoes')
      await input.trigger('input')

      expect(fetchMock).toHaveBeenCalledTimes(1)
      await vi.advanceTimersByTimeAsync(300)
      await flushPromises()

      expect(fetchMock).toHaveBeenLastCalledWith(
        'tenant-1',
        'profile-1',
        expect.objectContaining({ search: 'remote shoes', page: 1 }),
        expect.any(AbortSignal),
      )
      expect(wrapper.text()).toContain('搜索：remote shoes')
      expect(router.currentRoute.value.query.search).toBe('remote shoes')
    } finally {
      vi.useRealTimers()
    }
  })
})
