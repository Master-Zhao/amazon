import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, vi } from 'vitest'

import { fetchCampaigns } from '@/features/campaigns/api/campaignApi'
import CampaignsPage from '@/features/campaigns/pages/CampaignsPage.vue'
import { useTenantContextStore } from '@/features/tenant-context/stores/context'

vi.mock('@/features/campaigns/api/campaignApi', () => ({
  fetchCampaigns: vi.fn(),
}))

const campaignsMock = vi.mocked(fetchCampaigns)

describe('Campaigns page', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    setActivePinia(createPinia())
    useTenantContextStore().$patch({
      selectedTenantId: 'tenant-1',
      selectedStoreId: 'store-1',
      selectedStoreMarketplaceId: 'store-market-1',
      selectedProfileId: 'profile-1',
    })
  })

  it('renders campaign list and detail sourced from ads_campaign', async () => {
    campaignsMock.mockResolvedValue([
      {
        id: 'camp-1',
        externalCampaignId: 'amzn-campaign-001',
        name: 'Demo Running Shoes',
        state: 'ENABLED',
        dailyBudget: '50.00',
        currency: 'USD',
      },
      {
        id: 'camp-2',
        externalCampaignId: 'amzn-campaign-002',
        name: 'Demo Walking Shoes',
        state: 'PAUSED',
        dailyBudget: null,
        currency: 'USD',
      },
    ])

    const wrapper = mount(CampaignsPage)
    await flushPromises()

    expect(wrapper.text()).toContain('Demo Running Shoes · ENABLED')
    expect(wrapper.text()).toContain('Demo Walking Shoes · PAUSED')
    expect(wrapper.text()).toContain('amzn-campaign-001')
    expect(wrapper.text()).toContain('50.00 USD')

    const secondButton = wrapper
      .findAll('button')
      .find((button) => button.text().includes('Demo Walking Shoes'))
    await secondButton?.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('amzn-campaign-002')
    expect(wrapper.text()).toContain('未提供 USD')
  })

  it('renders an empty state when no campaigns exist', async () => {
    campaignsMock.mockResolvedValue([])
    const wrapper = mount(CampaignsPage)
    await flushPromises()
    expect(wrapper.text()).toContain('暂无 Campaign，请先导入报表。')
  })

  it('renders a failure state when the API rejects', async () => {
    campaignsMock.mockRejectedValue(new Error('forbidden'))
    const wrapper = mount(CampaignsPage)
    await flushPromises()
    expect(wrapper.text()).toContain('Campaign 加载失败或无权限。')
  })
})