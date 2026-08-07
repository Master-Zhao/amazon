import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, vi } from 'vitest'

import {
  decideActionPreview,
  fetchActionPreviews,
  recordManualExecution,
  submitActionPreview,
} from '@/features/actions/api/actionsApi'
import ActionCenterPage from '@/features/actions/pages/ActionCenterPage.vue'
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
const executeMock = vi.mocked(recordManualExecution)

function buildPreview(overrides: Partial<Record<string, unknown>> = {}) {
  return {
    id: 'preview-1',
    status: 'PENDING_APPROVAL',
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
        afterValue: { dailyBudget: '60.00' },
        reason: 'ACOS above target',
        evidence: [{ source: 'metrics' }],
        riskLevel: 'MEDIUM',
      },
      objectStateVersion: 'v1',
      createdAt: '2026-08-07T10:00:00Z',
    },
    approvals: [
      {
        id: 'approval-1',
        decision: 'APPROVED',
        comment: '初审通过',
        decidedByEmail: 'approver@example.com',
        createdAt: '2026-08-07T10:05:00Z',
      },
    ],
    executions: [
      {
        id: 'exec-1',
        outcome: 'SUCCEEDED',
        actualValue: { dailyBudget: '60.00' },
        executedAt: '2026-08-07T11:00:00Z',
        note: '人工在 Amazon 后台修改',
        evidenceMetadata: { originalFilename: 'evidence.png' },
        effectEvaluations: [],
        recordedByEmail: 'operator@example.com',
        createdAt: '2026-08-07T11:00:00Z',
      },
    ],
    createdAt: '2026-08-07T10:00:00Z',
    updatedAt: '2026-08-07T11:00:00Z',
    ...overrides,
  }
}

describe('Action center page', () => {
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
      permissionCodes: ['actions.view', 'actions.decide', 'actions.execute'],
    })
  })

  it('renders action preview, approval and execution records from action_* tables', async () => {
    previewsMock.mockResolvedValue([buildPreview()])
    const wrapper = mount(ActionCenterPage)
    await flushPromises()

    expect(wrapper.text()).toContain('Demo Running Shoes')
    expect(wrapper.text()).toContain('UPDATE_BID · PENDING_APPROVAL')
    expect(wrapper.text()).toContain('版本 1')
    expect(wrapper.text()).toContain('50.00')
    expect(wrapper.text()).toContain('60.00')
    expect(wrapper.text()).toContain('ACOS above target')
    expect(wrapper.text()).toContain('APPROVED · approver@example.com · 初审通过')
    expect(wrapper.text()).toContain(
      'SUCCEEDED · operator@example.com · 人工在 Amazon 后台修改',
    )
  })

  it('submits a draft preview through the action_preview state machine', async () => {
    const draft = buildPreview({ id: 'preview-draft', status: 'DRAFT' })
    previewsMock.mockResolvedValue([draft])
    submitMock.mockResolvedValue(
      buildPreview({ id: 'preview-draft', status: 'PENDING_APPROVAL' }),
    )

    const wrapper = mount(ActionCenterPage)
    await flushPromises()

    const submitButton = wrapper
      .findAll('button')
      .find((button) => button.text() === '提交审批')
    await submitButton?.trigger('click')
    await flushPromises()

    expect(submitMock).toHaveBeenCalledWith('tenant-1', 'preview-draft')
  })

  it('records a decision with an idempotent comment', async () => {
    previewsMock.mockResolvedValue([buildPreview()])
    decideMock.mockResolvedValue(buildPreview({ status: 'APPROVED' }))

    const wrapper = mount(ActionCenterPage)
    await flushPromises()

    const approveButton = wrapper
      .findAll('button')
      .find((button) => button.text() === '审批通过')
    await approveButton?.trigger('click')
    await flushPromises()

    expect(decideMock).toHaveBeenCalledWith(
      'tenant-1',
      'preview-1',
      'APPROVED',
      '审批通过',
    )
  })

  it('records a manual execution outcome', async () => {
    const approved = buildPreview({ status: 'APPROVED', executions: [] })
    previewsMock.mockResolvedValue([approved])
    executeMock.mockResolvedValue(buildPreview())

    const wrapper = mount(ActionCenterPage)
    await flushPromises()

    const successButton = wrapper
      .findAll('button')
      .find((button) => button.text() === '确认成功')
    await successButton?.trigger('click')
    await flushPromises()

    expect(executeMock).toHaveBeenCalledWith(
      'tenant-1',
      'preview-1',
      'SUCCEEDED',
      {},
      '人工在 Amazon 后台核对后回填',
    )
  })

  it('renders an API failure state', async () => {
    previewsMock.mockRejectedValue(new Error('actions unavailable'))
    const wrapper = mount(ActionCenterPage)
    await flushPromises()
    expect(wrapper.find('[role="alert"]').exists()).toBe(true)
  })
})