import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, vi } from 'vitest'

import {
  fetchSearchTermMetrics,
  fetchTargetingMetrics,
} from '@/features/analytics/api/analyticsApi'
import SearchTermMetricsPage from '@/features/analytics/pages/SearchTermMetricsPage.vue'
import TargetingMetricsPage from '@/features/analytics/pages/TargetingMetricsPage.vue'
import { useTenantContextStore } from '@/features/tenant-context/stores/tenantContext'

vi.mock('@/features/analytics/api/analyticsApi', () => ({
  fetchTargetingMetrics: vi.fn(),
  fetchSearchTermMetrics: vi.fn(),
}))

const targetingMock = vi.mocked(fetchTargetingMetrics)
const searchTermMock = vi.mocked(fetchSearchTermMetrics)
const formulas = {
  ctr: { value: '0.05', reason: null },
  cpc: { value: '1.25', reason: null },
  cvr: { value: '0.25', reason: null },
  acos: { value: '0.20', reason: null },
  roas: { value: '5', reason: null },
}

function establishContext(): void {
  useTenantContextStore().$patch({
    tenantId: 'tenant-1',
    storeId: 'store-1',
    storeMarketplaceId: 'store-market-1',
    profileId: 'profile-1',
    status: 'ready',
  })
}

describe('Targeting and Search Term authoritative metric pages', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    setActivePinia(createPinia())
    establishContext()
  })

  it('renders targeting bid and state snapshots', async () => {
    targetingMock.mockResolvedValue([
      {
        id: 'target-metric-1',
        campaignId: '1',
        campaignName: 'Demo Campaign',
        adGroupId: '1',
        adGroupName: 'Demo Ad Group',
        targetType: 'KEYWORD',
        targetId: 'keyword-001',
        targetText: 'running shoes',
        matchType: 'EXACT',
        reportDate: '2026-07-20',
        currencyCode: 'USD',
        impressions: 300,
        clicks: 20,
        spend: '25.00',
        orders: 5,
        sales: '125.00',
        calculationReasons: {},
        bidSnapshot: '1.25',
        stateSnapshot: 'ENABLED',
        ...formulas,
        sourceBatchId: '2',
      },
    ])

    const wrapper = mount(TargetingMetricsPage, {
      global: { stubs: { RouterLink: { template: '<a><slot /></a>' } } },
    })
    await flushPromises()

    expect(wrapper.text()).toContain('running shoes')
    expect(wrapper.text()).toContain('ENABLED')
    expect(wrapper.text()).toContain('Batch #2')
  })

  it('keeps customer search term separate from targeting expression', async () => {
    searchTermMock.mockResolvedValue([
      {
        id: 'search-metric-1',
        campaignId: '1',
        campaignName: 'Demo Campaign',
        adGroupId: '1',
        adGroupName: 'Demo Ad Group',
        searchTermId: '1',
        searchTerm: 'best running shoes',
        targetingExpression: 'running shoes',
        reportDate: '2026-07-20',
        currencyCode: 'USD',
        impressions: 120,
        clicks: 10,
        spend: '12.00',
        orders: 3,
        sales: '75.00',
        calculationReasons: {},
        ...formulas,
        sourceBatchId: '3',
      },
    ])

    const wrapper = mount(SearchTermMetricsPage, {
      global: { stubs: { RouterLink: { template: '<a><slot /></a>' } } },
    })
    await flushPromises()

    expect(wrapper.text()).toContain('best running shoes')
    expect(wrapper.text()).toContain('匹配来源：running shoes')
    expect(wrapper.text()).toContain('Batch #3')
  })
})
