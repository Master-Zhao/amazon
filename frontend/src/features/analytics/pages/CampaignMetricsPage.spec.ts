import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, vi } from 'vitest'

import { fetchCampaignMetrics } from '@/features/analytics/api/analyticsApi'
import CampaignMetricsPage from '@/features/analytics/pages/CampaignMetricsPage.vue'
import { useTenantContextStore } from '@/features/tenant-context/stores/tenantContext'

vi.mock('@/features/analytics/api/analyticsApi', () => ({
  fetchCampaignMetrics: vi.fn(),
}))

const metricsMock = vi.mocked(fetchCampaignMetrics)

describe('Campaign metrics page', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    setActivePinia(createPinia())
    useTenantContextStore().$patch({
      tenantId: 'tenant-1',
      storeId: 'store-1',
      storeMarketplaceId: 'store-market-1',
      profileId: 'profile-1',
      status: 'ready',
      membershipRole: 'OWNER',
      permissionCodes: ['analytics.view'],
      tenants: [
        {
          id: 'tenant-1',
          name: 'Demo Tenant',
          tenantType: 'TEAM',
          membershipRole: 'OWNER',
        },
      ],
      stores: [
        { id: 'store-1', name: 'Demo Store', externalStoreId: 'demo-store' },
      ],
      marketplaces: [
        {
          storeMarketplaceId: 'store-market-1',
          marketplace: {
            id: 'market-1',
            code: 'US',
            name: 'United States',
            currencyCode: 'USD',
            timezone: 'America/Los_Angeles',
          },
        },
      ],
      profiles: [
        {
          id: 'profile-1',
          name: 'Demo Profile',
          externalProfileId: 'demo-profile-001',
          currencyCode: 'USD',
          timezone: 'America/Los_Angeles',
          accessLevel: 'MANAGE',
        },
      ],
    })
  })

  it('renders deterministic ACOS and versioned anomaly evidence', async () => {
    metricsMock.mockResolvedValue([
      {
        id: 'metric-1',
        campaignId: '1',
        externalCampaignId: 'campaign-001',
        campaignName: 'Demo Running Shoes',
        reportDate: '2026-07-20',
        currencyCode: 'USD',
        impressions: 1000,
        clicks: 50,
        spend: '75.5000',
        orders: 10,
        sales: '250.0000',
        calculationReasons: {},
        dailyBudgetSnapshot: '50.0000',
        snapshotHourLocal: 12,
        stateSnapshot: 'ENABLED',
        targetAcos: '0.2800',
        ctr: { value: '0.05', reason: null },
        cpc: { value: '1.51', reason: null },
        cvr: { value: '0.2', reason: null },
        acos: { value: '0.302', reason: null },
        roas: { value: '3.311', reason: null },
        sourceBatchId: '1',
        anomalies: [
          {
            id: 'anomaly-1',
            ruleCode: 'HIGH_ACOS',
            ruleVersion: 1,
            status: 'ANOMALY',
            riskLevel: 'MEDIUM',
            observedValue: '0.302',
            thresholdValue: '0.2800',
            reasonCode: 'ACOS_ABOVE_TARGET',
            explanation: 'ACOS 0.3020 is above target 0.2800.',
          },
        ],
      },
    ])

    const wrapper = mount(CampaignMetricsPage, {
      global: {
        stubs: { RouterLink: { template: '<a><slot /></a>' } },
      },
    })
    await flushPromises()

    expect(wrapper.text()).toContain('Demo Running Shoes')
    expect(wrapper.text()).toContain('30.20% / 28.00%')
    expect(wrapper.text()).toContain('HIGH_ACOS · v1')
    expect(wrapper.text()).toContain('ACOS 0.3020 is above target 0.2800.')
  })
})
