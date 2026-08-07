import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import {
  createEffectEvaluation,
  decideActionPreview,
  fetchActionPreviews,
  recordManualExecution,
  reviseReturnedActionPreview,
  submitActionPreview,
  withdrawActionPreview,
} from '@/features/actions/api/actionsApi'
import ApprovalExecutionPage from '@/features/actions/pages/ApprovalExecutionPage.vue'
import { useTenantContextStore } from '@/features/tenant-context/stores/tenantContext'

vi.mock('@/features/actions/api/actionsApi', () => ({
  fetchActionPreviews: vi.fn(),
  submitActionPreview: vi.fn(),
  decideActionPreview: vi.fn(),
  recordManualExecution: vi.fn(),
  createActionPreview: vi.fn(),
  withdrawActionPreview: vi.fn(),
  reviseReturnedActionPreview: vi.fn(),
  createEffectEvaluation: vi.fn(),
}))

const previewsMock = vi.mocked(fetchActionPreviews)
const submitMock = vi.mocked(submitActionPreview)
const decideMock = vi.mocked(decideActionPreview)
const reviseMock = vi.mocked(reviseReturnedActionPreview)
const withdrawMock = vi.mocked(withdrawActionPreview)
const executeMock = vi.mocked(recordManualExecution)
const evaluationMock = vi.mocked(createEffectEvaluation)

function buildPreview(overrides: Partial<Record<string, unknown>> = []) {
  return {
    id: 'preview-1',
    status: 'APPROVED',
    campaignName: 'Demo Running Shoes',
    actionType: 'UPDATE_BID',
    currentVersionNumber: 2,
    currentVersion: {
      id: 'version-2',
      versionNumber: 2,
      actionPayload: {
        schemaVersion: '1.0',
        actionType: 'UPDATE_BID',
        objectType: 'Campaign',
        objectId: 'camp-1',
        beforeValue: { dailyBudget: '50.00' },
        afterValue: { dailyBudget: '65.00' },
        reason: 'Revised bid after anomaly review',
        evidence: [{ source: 'human-review' }],
        riskLevel: 'HIGH',
      },
      objectStateVersion: 'v2',
      createdAt: '2026-08-07T10:00:00Z',
    },
    approvals: [
      {
        id: 'approval-1',
        decision: 'APPROVED',
        comment: 'Approved after review',
        decidedByEmail: 'approver@example.com',
        createdAt: '2026-08-07T10:05:00Z',
      },
    ],
    executions: [
      {
        id: 'exec-1',
        outcome: 'SUCCEEDED',
        actualValue: { dailyBudget: '65.00' },
        executedAt: '2026-08-07T11:00:00Z',
        note: 'Manual Amazon console update',
        evidenceMetadata: {
          originalFilename: 'evidence.png',
          sha256: 'abc123',
        },
        effectEvaluations: [
          {
            id: 'eval-1',
            status: 'COMPLETED',
            baselineStart: '2026-07-31',
            baselineEnd: '2026-08-06',
            observationStart: '2026-08-07',
            observationEnd: '2026-08-13',
            result: { acosDelta: '-0.03' },
            reasonCode: 'WINDOW_COMPARE',
            errorMessage: '',
            createdAt: '2026-08-14T00:00:00Z',
          },
        ],
        recordedByEmail: 'operator@example.com',
        createdAt: '2026-08-07T11:00:00Z',
      },
    ],
    createdAt: '2026-08-07T10:00:00Z',
    updatedAt: '2026-08-07T11:00:00Z',
    ...overrides,
  }
}

function mountPage() {
  const router = createRouter({ history: createMemoryHistory(), routes: [] })
  return mount(ApprovalExecutionPage, {
    global: {
      plugins: [router],
      stubs: { RouterLink: { template: '<a><slot /></a>' } },
    },
  })
}

describe('Approval execution page', () => {
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
      permissionCodes: ['actions.view', 'actions.execute', 'actions.evaluate'],
    })
  })

  it('renders preview, execution evidence and effect evaluation from action_* tables', async () => {
    previewsMock.mockResolvedValue([buildPreview()])
    const wrapper = mountPage()
    await flushPromises()

    expect(wrapper.text()).toContain('Demo Running Shoes')
    expect(wrapper.text()).toContain('Preview #preview-1 · v2')
    expect(wrapper.text()).toContain('Revised bid after anomaly review')
    expect(wrapper.text()).toContain('APPROVED · approver@example.com · Approved after review')
    expect(wrapper.text()).toContain(
      'SUCCEEDED · operator@example.com · Manual Amazon console update',
    )
    expect(wrapper.text()).toContain('evidence.png · abc123')
    expect(wrapper.text()).toContain('#eval-1 · COMPLETED')
    expect(wrapper.text()).toContain('2026-07-31—2026-08-06 / 2026-08-07—2026-08-13')
  })

  it('withdraws a pending preview through the state machine', async () => {
    const pending = buildPreview({ status: 'PENDING_APPROVAL' })
    previewsMock.mockResolvedValue([pending])
    withdrawMock.mockResolvedValue(buildPreview({ status: 'WITHDRAWN' }))

    const wrapper = mountPage()
    await flushPromises()

    const withdrawButton = wrapper
      .findAll('button')
      .find((button) => button.text() === '撤回')
    await withdrawButton?.trigger('click')
    await flushPromises()

    expect(withdrawMock).toHaveBeenCalledWith('tenant-1', 'preview-1')
  })

  it('records a manual execution with evidence payload', async () => {
    const approved = buildPreview({ status: 'APPROVED', executions: [] })
    previewsMock.mockResolvedValue([approved])
    executeMock.mockResolvedValue(buildPreview())

    const wrapper = mountPage()
    await flushPromises()

    const successButton = wrapper
      .findAll('button')
      .find((button) => button.text() === '回填人工执行成功')
    await successButton?.trigger('click')
    await flushPromises()

    expect(executeMock).toHaveBeenCalledWith(
      'tenant-1',
      'preview-1',
      'SUCCEEDED',
      { dailyBudget: '65.00' },
      'SUCCEEDED recorded after fictional manual Amazon console work.',
      undefined,
    )
  })

  it('queues an effect evaluation with observed ACOS and window', async () => {
    previewsMock.mockResolvedValue([buildPreview()])
    evaluationMock.mockResolvedValue({
      id: 'eval-2',
      status: 'QUEUED',
      baselineStart: '2026-07-31',
      baselineEnd: '2026-08-06',
      observationStart: '2026-08-07',
      observationEnd: '2026-08-14',
      result: {},
      reasonCode: 'WINDOW_COMPARE',
      errorMessage: '',
      createdAt: '2026-08-14T00:00:00Z',
    })

    const wrapper = mountPage()
    await flushPromises()

    const acosInput = wrapper.find('input[inputmode="decimal"]')
    await acosInput.setValue('0.25')
    const daysInput = wrapper.find('input[type="number"]')
    await daysInput.setValue('7')

    const evalButton = wrapper
      .findAll('button')
      .find((button) => button.text() === '创建效果评估')
    await evalButton?.trigger('click')
    await flushPromises()

    expect(evaluationMock).toHaveBeenCalledWith('tenant-1', 'preview-1', 'exec-1', {
      acos: '0.25',
      windowDays: 7,
    })
  })

  it('renders an API failure state', async () => {
    previewsMock.mockRejectedValue(new Error('actions unavailable'))
    const wrapper = mountPage()
    await flushPromises()
    expect(wrapper.find('[role="alert"]').exists()).toBe(true)
  })

  it('submits a draft preview for approval', async () => {
    const draft = buildPreview({ id: 'preview-draft', status: 'DRAFT', executions: [] })
    previewsMock.mockResolvedValue([draft])
    submitMock.mockResolvedValue(buildPreview({ id: 'preview-draft', status: 'PENDING_APPROVAL' }))

    const wrapper = mountPage()
    await flushPromises()

    const submitButton = wrapper
      .findAll('button')
      .find((button) => button.text() === '提交审批')
    await submitButton?.trigger('click')
    await flushPromises()

    expect(submitMock).toHaveBeenCalledWith('tenant-1', 'preview-draft')
  })

  it('decides a pending preview with approved, rejected and returned outcomes', async () => {
    const pending = buildPreview({ status: 'PENDING_APPROVAL', executions: [] })
    previewsMock.mockResolvedValue([pending])
    decideMock.mockResolvedValue(buildPreview())

    const wrapper = mountPage()
    await flushPromises()

    for (const label of ['批准', '拒绝', '退回']) {
      const button = wrapper.findAll('button').find((b) => b.text() === label)
      await button?.trigger('click')
      await flushPromises()
    }

    expect(decideMock).toHaveBeenNthCalledWith(1, 'tenant-1', 'preview-1', 'APPROVED', expect.any(String))
    expect(decideMock).toHaveBeenNthCalledWith(2, 'tenant-1', 'preview-1', 'REJECTED', expect.any(String))
    expect(decideMock).toHaveBeenNthCalledWith(3, 'tenant-1', 'preview-1', 'RETURNED', expect.any(String))
  })

  it('creates a revised version after a returned decision via prompt', async () => {
    const returned = buildPreview({ status: 'RETURNED', executions: [] })
    previewsMock.mockResolvedValue([returned])
    reviseMock.mockResolvedValue(buildPreview({ status: 'PENDING_APPROVAL' }))
    const promptSpy = vi
      .spyOn(globalThis, 'prompt')
      .mockReturnValue(JSON.stringify({ dailyBudget: '70.00' }))

    const wrapper = mountPage()
    await flushPromises()

    const reviseButton = wrapper
      .findAll('button')
      .find((button) => button.text() === '创建修订版本')
    await reviseButton?.trigger('click')
    await flushPromises()

    expect(promptSpy).toHaveBeenCalled()
    expect(reviseMock).toHaveBeenCalledWith(
      'tenant-1',
      'preview-1',
      expect.objectContaining({
        afterValue: { dailyBudget: '70.00' },
        reason: 'Revised after RETURNED decision.',
      }),
    )
    promptSpy.mockRestore()
  })

  it('records failed and skipped manual execution outcomes', async () => {
    const approved = buildPreview({ status: 'APPROVED', executions: [] })
    previewsMock.mockResolvedValue([approved])
    executeMock.mockResolvedValue(buildPreview())

    const wrapper = mountPage()
    await flushPromises()

    for (const label of ['回填失败', '回填跳过']) {
      const button = wrapper.findAll('button').find((b) => b.text() === label)
      await button?.trigger('click')
      await flushPromises()
    }

    expect(executeMock).toHaveBeenNthCalledWith(
      1,
      'tenant-1',
      'preview-1',
      'FAILED',
      {},
      'FAILED recorded after fictional manual Amazon console work.',
      undefined,
    )
    expect(executeMock).toHaveBeenNthCalledWith(
      2,
      'tenant-1',
      'preview-1',
      'SKIPPED',
      {},
      'SKIPPED recorded after fictional manual Amazon console work.',
      undefined,
    )
  })

  it('attaches an evidence file when recording a succeeded execution', async () => {
    const approved = buildPreview({ status: 'APPROVED', executions: [] })
    previewsMock.mockResolvedValue([approved])
    executeMock.mockResolvedValue(buildPreview())

    const wrapper = mountPage()
    await flushPromises()

    const evidence = new File(['proof'], 'evidence.png', { type: 'image/png' })
    const fileInput = wrapper.find('input[type="file"]')
    Object.defineProperty(fileInput.element, 'files', {
      value: [evidence],
      configurable: true,
    })
    await fileInput.trigger('change')

    const successButton = wrapper
      .findAll('button')
      .find((button) => button.text() === '回填人工执行成功')
    await successButton?.trigger('click')
    await flushPromises()

    expect(executeMock).toHaveBeenCalledWith(
      'tenant-1',
      'preview-1',
      'SUCCEEDED',
      { dailyBudget: '65.00' },
      'SUCCEEDED recorded after fictional manual Amazon console work.',
      evidence,
    )
  })
})