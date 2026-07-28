import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, vi } from 'vitest'

import { fetchDashboard } from '@/features/analytics/api/analyticsApi'
import DashboardPage from '@/features/analytics/pages/DashboardPage.vue'
import { useTenantContextStore } from '@/features/tenant-context/stores/tenantContext'

const setOption = vi.fn()
const dispose = vi.fn()
vi.mock('@/shared/charts/echarts', () => ({
  init: vi.fn(() => ({
    setOption,
    dispose,
    resize: vi.fn(),
  })),
}))
vi.mock('@/features/analytics/api/analyticsApi', () => ({
  fetchDashboard: vi.fn(),
}))

const dashboardMock = vi.mocked(fetchDashboard)

describe('Campaign-grain dashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setActivePinia(createPinia())
    useTenantContextStore().$patch({
      tenantId: 'tenant-1',
      storeId: 'store-1',
      storeMarketplaceId: 'store-market-1',
      profileId: 'profile-1',
      status: 'ready',
    })
  })

  it('renders server groups and charts real API values', async () => {
    dashboardMock.mockResolvedValue([
      {
        marketplaceCode: 'US',
        marketplaceName: 'United States',
        currencyCode: 'USD',
        campaignCount: 2,
        impressions: 1600,
        clicks: 68,
        spend: '117.50',
        orders: 13,
        sales: '346.00',
        ctr: { value: '0.0425', reason: null },
        cpc: { value: '1.7279', reason: null },
        cvr: { value: '0.1911', reason: null },
        acos: { value: '0.3395', reason: null },
        roas: { value: '2.9446', reason: null },
        anomalyCount: 2,
        authoritativeGrain: 'CAMPAIGN_DAILY_METRIC',
      },
    ])

    const wrapper = mount(DashboardPage)
    await flushPromises()

    expect(wrapper.text()).toContain('US · USD')
    expect(wrapper.text()).toContain('CAMPAIGN_DAILY_METRIC')
    expect(wrapper.text()).toContain('2 个异常')
    expect(setOption).toHaveBeenCalledOnce()
  })
})
