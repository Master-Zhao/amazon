import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { beforeEach, vi } from 'vitest'

import {
  createCampaign,
  fetchCampaignOverview,
  updateCampaignEnabled,
} from '@/features/advertising/api/campaignApi'
import CampaignSection from '@/features/advertising/components/CampaignSection.vue'
import type { CampaignListResponse } from '@/features/advertising/types/campaign'
import { useTenantContextStore } from '@/features/tenant-context/stores/tenantContext'

vi.mock('@/features/advertising/api/campaignApi', () => ({
  fetchCampaignOverview: vi.fn(),
  createCampaign: vi.fn(),
  exportCampaignOverview: vi.fn(),
  updateCampaignEnabled: vi.fn(),
}))

const fetchMock = vi.mocked(fetchCampaignOverview)
const createMock = vi.mocked(createCampaign)
const updateEnabledMock = vi.mocked(updateCampaignEnabled)

const response: CampaignListResponse = {
  items: [
    {
      campaignKey: 'cmp_demo',
      name: '真实远程广告活动',
      campaignCode: 'SP-REMOTE-001',
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
      hasMetrics: true,
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
    source: 'REMOTE_MYSQL_COMPOSITE',
    currencyCode: 'USD',
    timezone: 'America/Los_Angeles',
    startDate: '2026-07-01',
    endDate: '2026-07-30',
    dataThroughDate: '2026-07-30',
    historyThroughDate: '2026-07-29',
    realtimeThroughDate: '2026-07-30',
    realtimeAsOf: '2026-07-30T12:00:00Z',
    deduplicationVersion: 'campaign-code-product-asin-realtime-v1',
    fieldMappings: {
      historicalImpressions: 'imperssion',
      realtimeImpressions: 'impression',
      campaignJoinKey: 'campaign_code->code',
    },
    totalCostSemantics: 'SPEND_ALIAS',
    attributionSemantics: 'REMOTE_FIELDS_UNVERIFIED',
    statusFilterSemantics: 'SCM_CURRENT_STATE_WITH_FACT_FALLBACK',
  },
}

async function mountSection(path = '/advertising/overview') {
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
      {
        path: '/advertising/campaigns/:campaignKey',
        name: 'advertising-campaign-detail',
        component: { template: '<div />' },
      },
      { path: '/context', component: { template: '<div />' } },
    ],
  })
  await router.push(path)
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
    createMock.mockResolvedValue({ item: response.items[0] })
    updateEnabledMock.mockResolvedValue({
      item: {
        ...response.items[0],
        enabled: false,
        status: 'PAUSED',
      },
    })
  })

  it('renders the 19-column remote Campaign table and totals', async () => {
    const { wrapper } = await mountSection()

    expect(fetchMock).toHaveBeenCalledWith(
      'tenant-1',
      'profile-1',
      {
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
    expect(wrapper.get('.campaign-create-button').attributes('disabled')).toBeUndefined()
    expect(wrapper.get('input[aria-label="选择全部广告活动"]').attributes('disabled')).toBeUndefined()
    expect(wrapper.get('input[aria-label="选择 真实远程广告活动"]').attributes('disabled')).toBeUndefined()
    expect(wrapper.get('.campaign-switch').attributes('aria-checked')).toBe('true')
    expect(wrapper.get('.campaign-switch').attributes('disabled')).toBeUndefined()
    expect(wrapper.get('.campaign-name-cell a').attributes('href')).toContain('/advertising/campaigns/cmp_demo')
    expect(wrapper.text()).toContain('正在投放')
    expect(wrapper.text()).not.toContain('已启用')
  })

  it('renders top of search share as an integer percentage', async () => {
    fetchMock.mockResolvedValueOnce({
      ...response,
      items: [
        {
          ...response.items[0],
          metrics: { ...response.items[0].metrics, topOfSearchShare: '0.30' },
        },
      ],
    })

    const { wrapper } = await mountSection()

    expect(wrapper.text()).toContain('30%')
    expect(wrapper.text()).not.toContain('30.00%')
  })

  it('selects rows from the checkbox column', async () => {
    const { wrapper } = await mountSection()

    await wrapper.get('input[aria-label="选择 真实远程广告活动"]').setValue(true)

    expect(wrapper.text()).toContain('已选择 1 个广告活动')
  })

  it('creates a real remote Campaign through the toolbar dialog and refreshes rows', async () => {
    fetchMock
      .mockResolvedValueOnce(response)
      .mockResolvedValueOnce({
        ...response,
        pagination: { page: 1, pageSize: 15, total: 2, totalPages: 1 },
      })

    const { wrapper } = await mountSection()
    await wrapper.get('.campaign-create-button').trigger('click')
    await wrapper.get('input[aria-label="广告活动名称"]').setValue('新建远程活动')
    await wrapper.get('select[aria-label="投放类型"]').setValue('AUTO')
    await wrapper.get('input[aria-label="每日预算"]').setValue('25.50')
    await wrapper.get('select[aria-label="竞价策略"]').setValue('fixed_bids')
    await wrapper.get('input[aria-label="创建开始日期"]').setValue('2026-08-05')
    await wrapper.get('.campaign-create-toggle input').setValue(false)
    await wrapper.get('.campaign-dialog-confirm').trigger('click')
    await flushPromises()

    expect(createMock).toHaveBeenCalledWith(
      'tenant-1',
      'profile-1',
      {
        name: '新建远程活动',
        targetingType: 'AUTO',
        dailyBudget: '25.50',
        biddingStrategy: 'fixed_bids',
        startDate: '2026-08-05',
        enabled: false,
      },
    )
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it('lets sellers update the enabled switch and refreshes remote rows', async () => {
    fetchMock
      .mockResolvedValueOnce(response)
      .mockResolvedValueOnce({
        ...response,
        items: [
          {
            ...response.items[0],
            enabled: false,
            status: 'PAUSED',
          },
        ],
      })

    const { wrapper } = await mountSection()
    await wrapper.get('.campaign-switch').trigger('click')
    await flushPromises()

    expect(updateEnabledMock).toHaveBeenCalledWith(
      'tenant-1',
      'profile-1',
      'cmp_demo',
      false,
      { startDate: '2026-07-01', endDate: '2026-07-30' },
    )
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it('lets sellers click the enabled switch even when SCM metadata is missing', async () => {
    fetchMock.mockResolvedValueOnce({
      ...response,
      items: [{ ...response.items[0], metadataMatched: false }],
    })

    const { wrapper } = await mountSection()
    await wrapper.get('.campaign-switch').trigger('click')
    await flushPromises()

    expect(wrapper.get('.campaign-switch').attributes('disabled')).toBeUndefined()
    expect(updateEnabledMock).toHaveBeenCalledWith(
      'tenant-1',
      'profile-1',
      'cmp_demo',
      false,
      { startDate: '2026-07-01', endDate: '2026-07-30' },
    )
  })

  it('opens the screenshot-style metric menu and sends aggregate metric filters', async () => {
    const { wrapper } = await mountSection()
    await wrapper.get('.campaign-filter-trigger').trigger('click')

    expect(wrapper.findAll('.campaign-filter-menu button')).toHaveLength(9)
    expect(wrapper.get('.campaign-filter-menu').text()).toContain('展示量')
    expect(wrapper.get('.campaign-filter-menu').text()).toContain('广告销售成本比')
    const impressions = wrapper.findAll('.campaign-filter-menu button').find((button) => button.text().includes('展示量'))
    await impressions!.trigger('click')
    expect(wrapper.get('[role="dialog"]').text()).toContain('展示量 — 筛选条件')
    await wrapper.get('input[aria-label="筛选数值"]').setValue('1000')
    await wrapper.get('.campaign-dialog-confirm').trigger('click')
    await flushPromises()

    expect(fetchMock).toHaveBeenLastCalledWith(
      'tenant-1',
      'profile-1',
      expect.objectContaining({ metricFilters: 'impressions:gte:1000' }),
      expect.any(AbortSignal),
    )
    expect(wrapper.text()).toContain('展示量 ≥ 1,000')
  })

  it('clears stale enabled and status filters when they only return metricless rows', async () => {
    fetchMock
      .mockResolvedValueOnce({
        ...response,
        items: response.items.map((item) => ({
          ...item,
          hasMetrics: false,
          metrics: {
            impressions: null,
            topOfSearchShare: null,
            spend: null,
            sales: null,
            clicks: null,
            ctr: null,
            totalCost: null,
            orders: null,
            cpc: null,
            acos: null,
            cvr: null,
          },
        })),
      })
      .mockResolvedValueOnce(response)

    const { router } = await mountSection(
      '/advertising/overview?enabled=true&status=enabled',
    )

    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      'tenant-1',
      'profile-1',
      expect.objectContaining({ enabled: true, status: 'enabled' }),
      expect.any(AbortSignal),
    )
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      'tenant-1',
      'profile-1',
      expect.not.objectContaining({ enabled: true, status: 'enabled' }),
      expect.any(AbortSignal),
    )
    expect(router.currentRoute.value.query.enabled).toBe('all')
    expect(router.currentRoute.value.query.status).toBeUndefined()
  })

  it('opens the modal rule editor for every first-level filter option', async () => {
    const { wrapper } = await mountSection()
    const labels = ['状态', '展示量', '点击量', '花费', '购买量', '单次点击成本', '广告销售成本比', '点击率', '转化率']

    for (const label of labels) {
      await wrapper.get('.campaign-filter-trigger').trigger('click')
      const option = wrapper.findAll('.campaign-filter-menu button').find((button) => button.text().includes(label))
      expect(option, `missing filter option: ${label}`).toBeDefined()
      await option!.trigger('click')
      expect(wrapper.get('[role="dialog"]').text()).toContain(`${label} — 筛选条件`)
      await wrapper.get('.campaign-dialog-cancel').trigger('click')
    }
  })

  it('keeps multiple aggregate rules and renders ratio thresholds as percentages', async () => {
    const { wrapper } = await mountSection()

    await wrapper.get('.campaign-filter-trigger').trigger('click')
    const impressions = wrapper.findAll('.campaign-filter-menu button').find((button) => button.text().includes('展示量'))
    await impressions!.trigger('click')
    await wrapper.get('input[aria-label="筛选数值"]').setValue('1000')
    await wrapper.get('.campaign-dialog-confirm').trigger('click')
    await flushPromises()

    await wrapper.get('.campaign-filter-trigger').trigger('click')
    const acos = wrapper.findAll('.campaign-filter-menu button').find((button) => button.text().includes('广告销售成本比'))
    await acos!.trigger('click')
    expect(wrapper.get('.campaign-filter-hint').text()).toContain('25% 输入 0.25')
    await wrapper.get('input[aria-label="筛选数值"]').setValue('0.25')
    await wrapper.get('.campaign-dialog-confirm').trigger('click')
    await flushPromises()

    expect(fetchMock).toHaveBeenLastCalledWith(
      'tenant-1',
      'profile-1',
      expect.objectContaining({ metricFilters: 'impressions:gte:1000;acos:gte:0.25' }),
      expect.any(AbortSignal),
    )
    expect(wrapper.text()).toContain('展示量 ≥ 1,000')
    expect(wrapper.text()).toContain('广告销售成本比 ≥ 25.00%')
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
