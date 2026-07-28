import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { beforeEach, vi } from 'vitest'

import {
  createAnomalyRuleVersion,
  fetchAnalyticsConfiguration,
  fetchCampaignDetail,
  updateTargetAcos,
} from '@/features/analytics/api/analyticsApi'
import AnalyticsConfigurationPage from '@/features/analytics/pages/AnalyticsConfigurationPage.vue'
import CampaignDetailPage from '@/features/analytics/pages/CampaignDetailPage.vue'
import { useTenantContextStore } from '@/features/tenant-context/stores/tenantContext'

const setOption = vi.fn()
vi.mock('@/shared/charts/echarts', () => ({
  init: vi.fn(() => ({
    setOption,
    dispose: vi.fn(),
    resize: vi.fn(),
  })),
}))
vi.mock('@/features/analytics/api/analyticsApi', () => ({
  fetchCampaignDetail: vi.fn(),
  fetchAnalyticsConfiguration: vi.fn(),
  updateTargetAcos: vi.fn(),
  createAnomalyRuleVersion: vi.fn(),
}))

const detailMock = vi.mocked(fetchCampaignDetail)
const configurationMock = vi.mocked(fetchAnalyticsConfiguration)
const targetMock = vi.mocked(updateTargetAcos)
const ruleMock = vi.mocked(createAnomalyRuleVersion)

const configuration = {
  tenantTargetAcos: '0.3000',
  profileTargetAcos: '0.2800',
  campaigns: [
    {
      campaignId: 'campaign-1',
      campaignName: 'Demo Campaign',
      targetAcos: null,
      effectiveTargetAcos: '0.2800',
    },
  ],
  rules: [],
}

describe('analytics configuration and Campaign detail', () => {
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
    configurationMock.mockResolvedValue(configuration)
    targetMock.mockResolvedValue(configuration)
    ruleMock.mockResolvedValue({
      id: 'rule-1',
      code: 'HIGH_ACOS',
      version: 1,
      scopeKey: 'PROFILE:profile-1',
      configuration: { minimum_clicks: 10, minimum_sales: '0.01' },
      createdAt: '2026-07-28T00:00:00Z',
    })
  })

  it('renders real Campaign trend values', async () => {
    detailMock.mockResolvedValue({
      campaignId: 'campaign-1',
      externalCampaignId: 'external-1',
      campaignName: 'Demo Campaign',
      state: 'ENABLED',
      targetAcos: '0.2800',
      metrics: [
        {
          id: 'metric-1',
          campaignId: 'campaign-1',
          externalCampaignId: 'external-1',
          campaignName: 'Demo Campaign',
          reportDate: '2026-07-20',
          currencyCode: 'USD',
          impressions: 1000,
          clicks: 40,
          spend: '80.00',
          orders: 5,
          sales: '200.00',
          calculationReasons: {},
          dailyBudgetSnapshot: '100.00',
          snapshotHourLocal: 12,
          stateSnapshot: 'ENABLED',
          targetAcos: '0.2800',
          ctr: { value: '0.04', reason: null },
          cpc: { value: '2', reason: null },
          cvr: { value: '0.125', reason: null },
          acos: { value: '0.4', reason: null },
          roas: { value: '2.5', reason: null },
          sourceBatchId: 'batch-1',
          anomalies: [],
        },
      ],
    })
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/campaigns', component: { template: '<div />' } },
        { path: '/campaigns/:campaignId', component: CampaignDetailPage },
      ],
    })
    await router.push('/campaigns/campaign-1')
    await router.isReady()

    const wrapper = mount(CampaignDetailPage, {
      global: { plugins: [router] },
    })
    await flushPromises()

    expect(wrapper.text()).toContain('Demo Campaign')
    expect(wrapper.text()).toContain('40.00%')
    expect(setOption).toHaveBeenCalledOnce()
  })

  it('loads configuration and saves target ACOS through the API', async () => {
    const wrapper = mount(AnalyticsConfigurationPage)
    await flushPromises()

    expect(wrapper.text()).toContain('Demo Campaign')
    const targetInput = wrapper.find('input')
    await targetInput.setValue('0.25')
    await wrapper.findAll('form')[0]!.trigger('submit')
    await flushPromises()

    expect(targetMock).toHaveBeenCalledWith(
      'tenant-1',
      'profile-1',
      expect.objectContaining({
        scopeType: 'PROFILE',
        targetAcos: '0.25',
      }),
    )
    expect(wrapper.text()).toContain('目标 ACOS 已保存')
  })
})
