import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, vi } from 'vitest'

import {
  fetchRemoteCampaignMetrics,
} from '@/features/analytics/api/analyticsApi'
import RemoteCampaignDataPage from '@/features/analytics/pages/RemoteCampaignDataPage.vue'
import { useTenantContextStore } from '@/features/tenant-context/stores/tenantContext'

vi.mock('@/features/analytics/api/analyticsApi', () => ({
  fetchRemoteCampaignMetrics: vi.fn(),
}))

const fetchMock = vi.mocked(fetchRemoteCampaignMetrics)

describe('RemoteCampaignDataPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setActivePinia(createPinia())
    useTenantContextStore().$patch({
      tenantId: 'tenant-1',
      storeId: 'store-1',
      storeMarketplaceId: 'store-marketplace-1',
      profileId: 'profile-1',
      status: 'ready',
    })
  })

  it('renders metrics returned by both read-only remote sources', async () => {
    fetchMock.mockResolvedValue([
      {
        id: 'remote:2026-07-29:campaign-100',
        externalCampaignId: 'campaign-100',
        campaignName: 'Remote Campaign',
        reportDate: '2026-07-29',
        currencyCode: 'USD',
        impressions: 1000,
        clicks: 50,
        spend: '75.00',
        orders: 10,
        sales: '300.00',
        dailyBudget: '100.00',
        state: 'enabled',
        ctr: { value: '0.05', reason: null },
        cpc: { value: '1.5', reason: null },
        cvr: { value: '0.2', reason: null },
        acos: { value: '0.25', reason: null },
        roas: { value: '4', reason: null },
        scmMatched: true,
        sourceSystem: 'REMOTE_MYSQL',
      },
    ])

    const wrapper = mount(RemoteCampaignDataPage, {
      global: {
        stubs: { RouterLink: true },
      },
    })
    await flushPromises()

    expect(fetchMock).toHaveBeenCalledWith('tenant-1', 'profile-1', {})
    expect(wrapper.text()).toContain('Remote Campaign')
    expect(wrapper.text()).toContain('SCM 已匹配')
    expect(wrapper.text()).toContain('25.00%')
    expect(wrapper.text()).toContain('US$300.00')
  })

  it('shows a recoverable remote configuration error', async () => {
    fetchMock.mockRejectedValue({
      status: 503,
      code: 'SERVICE_NOT_READY',
      message: '当前 Profile 尚未配置远程商户映射',
      requestId: 'req-1',
      fieldErrors: {},
      retryable: true,
    })

    const wrapper = mount(RemoteCampaignDataPage, {
      global: {
        stubs: { RouterLink: true },
      },
    })
    await flushPromises()

    expect(wrapper.get('[role="alert"]').text()).toContain(
      '当前 Profile 尚未配置远程商户映射',
    )
  })
})
