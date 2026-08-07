import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, vi } from 'vitest'

import { createActionPreview } from '@/features/actions/api/actionsApi'
import {
  acceptRecommendation,
  cancelAgentRun,
  createAgentRun,
  dismissRecommendation,
  fetchAgentRuns,
  fetchRecommendations,
  reviseRecommendation,
} from '@/features/analysis/api/analysisApi'
import AnalysisRecommendationsPage from '@/features/analysis/pages/AnalysisRecommendationsPage.vue'
import { useTenantContextStore } from '@/features/tenant-context/stores/tenantContext'

vi.mock('@/features/actions/api/actionsApi', () => ({
  createActionPreview: vi.fn(),
}))

vi.mock('@/features/analysis/api/analysisApi', () => ({
  fetchAgentRuns: vi.fn(),
  createAgentRun: vi.fn(),
  cancelAgentRun: vi.fn(),
  fetchRecommendations: vi.fn(),
  acceptRecommendation: vi.fn(),
  reviseRecommendation: vi.fn(),
  dismissRecommendation: vi.fn(),
}))

const runsMock = vi.mocked(fetchAgentRuns)
const recommendationsMock = vi.mocked(fetchRecommendations)
const runMock = vi.mocked(createAgentRun)
const cancelMock = vi.mocked(cancelAgentRun)
const acceptMock = vi.mocked(acceptRecommendation)
const reviseMock = vi.mocked(reviseRecommendation)
const dismissMock = vi.mocked(dismissRecommendation)
const previewMock = vi.mocked(createActionPreview)

function buildRecommendation() {
  return {
    id: 'rec-1',
    status: 'ACTIVE',
    actionType: 'UPDATE_BID',
    campaignName: 'Demo Running Shoes',
    externalCampaignId: 'camp-001',
    agentRunId: 'run-1',
    currentRevisionNumber: 1,
    currentRevision: {
      id: 'rev-1',
      revisionNumber: 1,
      schemaVersion: '1.0',
      actionType: 'UPDATE_BID',
      objectType: 'Campaign',
      objectId: 'camp-1',
      beforeValue: { dailyBudget: '50.00' },
      afterValue: { dailyBudget: '55.00' },
      reason: 'ACOS 0.35 above target 0.28',
      evidence: [{ source: 'metrics' }],
      riskLevel: 'MEDIUM',
      createdAt: '2026-08-07T10:00:00Z',
    },
    createdAt: '2026-08-07T10:00:00Z',
  }
}

describe('Analysis recommendations page', () => {
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
      permissionCodes: ['analysis.view', 'analysis.run'],
      tenants: [
        {
          id: 'tenant-1',
          name: 'Demo Tenant',
          tenantType: 'TEAM',
          membershipRole: 'OWNER',
        },
      ],
      stores: [{ id: 'store-1', name: 'Demo Store', externalStoreId: 'demo-store' }],
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
          remoteAdvertisingAvailable: true,
        },
      ],
    })
  })

  it('renders agent runs and structured recommendations from ai_* tables', async () => {
    runsMock.mockResolvedValue([
      {
        id: 'run-1',
        agentCode: 'BID_OPTIMIZER',
        status: 'SUCCEEDED',
        schemaVersion: '1.0',
        celeryTaskId: 'celery-1',
        outputResult: { recommendations: 1 },
        errorCode: '',
        errorMessage: '',
        createdAt: '2026-08-07T10:00:00Z',
        startedAt: '2026-08-07T10:00:01Z',
        finishedAt: '2026-08-07T10:00:05Z',
      },
    ])
    recommendationsMock.mockResolvedValue([buildRecommendation()])

    const wrapper = mount(AnalysisRecommendationsPage, {
      global: {
        stubs: { RouterLink: { template: '<a><slot /></a>' } },
      },
    })
    await flushPromises()

    expect(wrapper.text()).toContain('Run #run-1')
    expect(wrapper.text()).toContain('SUCCEEDED')
    expect(wrapper.text()).toContain('1.0 · Task celery-1')
    expect(wrapper.text()).toContain('Demo Running Shoes')
    expect(wrapper.text()).toContain('UPDATE_BID · MEDIUM')
    expect(wrapper.text()).toContain('ACTIVE · v1')
    expect(wrapper.text()).toContain('ACOS 0.35 above target 0.28')
    expect(wrapper.text()).toContain('50.00')
    expect(wrapper.text()).toContain('55.00')
  })

  it('creates a new agent run through the orchestrator entrypoint', async () => {
    runsMock.mockResolvedValue([])
    recommendationsMock.mockResolvedValue([])
    runMock.mockResolvedValue({
      id: 'run-2',
      agentCode: 'BID_OPTIMIZER',
      status: 'QUEUED',
      schemaVersion: '1.0',
      celeryTaskId: 'celery-2',
      outputResult: {},
      errorCode: '',
      errorMessage: '',
      createdAt: '2026-08-07T10:00:00Z',
      startedAt: null,
      finishedAt: null,
    })

    const wrapper = mount(AnalysisRecommendationsPage, {
      global: { stubs: { RouterLink: { template: '<a><slot /></a>' } } },
    })
    await flushPromises()

    const runButton = wrapper
      .findAll('button')
      .find((button) => button.text() === '运行 Mock 智能分析')
    await runButton?.trigger('click')
    await flushPromises()

    expect(runMock).toHaveBeenCalledWith('tenant-1', 'profile-1')
  })

  it('cancels a running agent run', async () => {
    runsMock.mockResolvedValue([
      {
        id: 'run-1',
        agentCode: 'BID_OPTIMIZER',
        status: 'RUNNING',
        schemaVersion: '1.0',
        celeryTaskId: 'celery-1',
        outputResult: {},
        errorCode: '',
        errorMessage: '',
        createdAt: '2026-08-07T10:00:00Z',
        startedAt: '2026-08-07T10:00:01Z',
        finishedAt: null,
      },
    ])
    recommendationsMock.mockResolvedValue([])
    cancelMock.mockResolvedValue({
      id: 'run-1',
      agentCode: 'BID_OPTIMIZER',
      status: 'CANCELLED',
      schemaVersion: '1.0',
      celeryTaskId: 'celery-1',
      outputResult: {},
      errorCode: '',
      errorMessage: '',
      createdAt: '2026-08-07T10:00:00Z',
      startedAt: '2026-08-07T10:00:01Z',
      finishedAt: '2026-08-07T10:00:10Z',
    })

    const wrapper = mount(AnalysisRecommendationsPage, {
      global: { stubs: { RouterLink: { template: '<a><slot /></a>' } } },
    })
    await flushPromises()

    const cancelButton = wrapper
      .findAll('button')
      .find((button) => button.text() === '取消分析')
    await cancelButton?.trigger('click')
    await flushPromises()

    expect(cancelMock).toHaveBeenCalledWith('tenant-1', 'run-1')
  })

  it('accepts an active recommendation through the state machine', async () => {
    runsMock.mockResolvedValue([])
    recommendationsMock.mockResolvedValue([buildRecommendation()])
    acceptMock.mockResolvedValue(buildRecommendation())

    const wrapper = mount(AnalysisRecommendationsPage, {
      global: { stubs: { RouterLink: { template: '<a><slot /></a>' } } },
    })
    await flushPromises()

    const acceptButton = wrapper
      .findAll('button')
      .find((button) => button.text() === '接受建议')
    await acceptButton?.trigger('click')
    await flushPromises()

    expect(acceptMock).toHaveBeenCalledWith('tenant-1', 'rec-1')
  })

  it('dismisses a recommendation with a human review reason', async () => {
    runsMock.mockResolvedValue([])
    recommendationsMock.mockResolvedValue([buildRecommendation()])
    dismissMock.mockResolvedValue(buildRecommendation())

    const wrapper = mount(AnalysisRecommendationsPage, {
      global: { stubs: { RouterLink: { template: '<a><slot /></a>' } } },
    })
    await flushPromises()

    const dismissButton = wrapper
      .findAll('button')
      .find((button) => button.text() === '拒绝')
    await dismissButton?.trigger('click')
    await flushPromises()

    expect(dismissMock).toHaveBeenCalledWith('tenant-1', 'rec-1', 'Rejected after human review.')
  })

  it('generates an action preview from a verified recommendation', async () => {
    runsMock.mockResolvedValue([])
    recommendationsMock.mockResolvedValue([buildRecommendation()])
    previewMock.mockResolvedValue({
      id: 'preview-1',
      status: 'DRAFT',
      campaignName: 'Demo Running Shoes',
      actionType: 'UPDATE_BID',
      currentVersionNumber: 1,
      currentVersion: {
        id: 'version-1',
        versionNumber: 1,
        actionPayload: {
          schemaVersion: '1.0',
          actionType: 'UPDATE_BID',
          objectType: 'Campaign',
          objectId: 'camp-1',
          beforeValue: { dailyBudget: '50.00' },
          afterValue: { dailyBudget: '55.00' },
          reason: 'ACOS 0.35 above target 0.28',
          evidence: [],
          riskLevel: 'MEDIUM',
        },
        objectStateVersion: 'v1',
        createdAt: '2026-08-07T10:00:00Z',
      },
      approvals: [],
      executions: [],
      createdAt: '2026-08-07T10:00:00Z',
      updatedAt: '2026-08-07T10:00:00Z',
    })

    const wrapper = mount(AnalysisRecommendationsPage, {
      global: { stubs: { RouterLink: { template: '<a><slot /></a>' } } },
    })
    await flushPromises()

    const previewButton = wrapper
      .findAll('button')
      .find((button) => button.text() === '生成 Action Preview')
    await previewButton?.trigger('click')
    await flushPromises()

    expect(previewMock).toHaveBeenCalledWith('tenant-1', 'rec-1')
    expect(wrapper.text()).toContain('已创建 Preview #preview-1')
  })

  it('renders an API failure state', async () => {
    runsMock.mockRejectedValue(new Error('analysis unavailable'))
    recommendationsMock.mockRejectedValue(new Error('analysis unavailable'))
    const wrapper = mount(AnalysisRecommendationsPage, {
      global: { stubs: { RouterLink: { template: '<a><slot /></a>' } } },
    })
    await flushPromises()
    expect(wrapper.find('[role="alert"]').exists()).toBe(true)
  })

  it('revises a recommendation afterValue through a prompted JSON edit', async () => {
    runsMock.mockResolvedValue([])
    recommendationsMock.mockResolvedValue([buildRecommendation()])
    reviseMock.mockResolvedValue(buildRecommendation())
    const promptSpy = vi
      .spyOn(globalThis, 'prompt')
      .mockReturnValue(JSON.stringify({ dailyBudget: '60.00' }))

    const wrapper = mount(AnalysisRecommendationsPage, {
      global: { stubs: { RouterLink: { template: '<a><slot /></a>' } } },
    })
    await flushPromises()

    const reviseButton = wrapper
      .findAll('button')
      .find((button) => button.text() === '修订')
    await reviseButton?.trigger('click')
    await flushPromises()

    expect(promptSpy).toHaveBeenCalled()
    expect(reviseMock).toHaveBeenCalledWith('tenant-1', 'rec-1', {
      afterValue: { dailyBudget: '60.00' },
      reason: 'Revised after human review.',
      evidence: [{ source: 'human-review' }],
      riskLevel: 'MEDIUM',
    })
    promptSpy.mockRestore()
  })

  it('flags an invalid JSON edit without calling the revision API', async () => {
    runsMock.mockResolvedValue([])
    recommendationsMock.mockResolvedValue([buildRecommendation()])
    const promptSpy = vi
      .spyOn(globalThis, 'prompt')
      .mockReturnValue('{invalid json')

    const wrapper = mount(AnalysisRecommendationsPage, {
      global: { stubs: { RouterLink: { template: '<a><slot /></a>' } } },
    })
    await flushPromises()

    const reviseButton = wrapper
      .findAll('button')
      .find((button) => button.text() === '修订')
    await reviseButton?.trigger('click')
    await flushPromises()

    expect(reviseMock).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('afterValue 必须是合法 JSON。')
    promptSpy.mockRestore()
  })

  it('clears the polling timer on unmount when a run is still active', async () => {
    runsMock.mockResolvedValue([
      {
        id: 'run-1',
        agentCode: 'BID_OPTIMIZER',
        status: 'RUNNING',
        schemaVersion: '1.0',
        celeryTaskId: 'celery-1',
        outputResult: {},
        errorCode: '',
        errorMessage: '',
        createdAt: '2026-08-07T10:00:00Z',
        startedAt: '2026-08-07T10:00:01Z',
        finishedAt: null,
      },
    ])
    recommendationsMock.mockResolvedValue([])

    const wrapper = mount(AnalysisRecommendationsPage, {
      global: { stubs: { RouterLink: { template: '<a><slot /></a>' } } },
    })
    await flushPromises()

    expect(wrapper.text()).toContain('Run #run-1')
    wrapper.unmount()
  })
})