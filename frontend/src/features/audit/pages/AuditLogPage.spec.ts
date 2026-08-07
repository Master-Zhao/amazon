import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, vi } from 'vitest'

import { fetchAuditLogs } from '@/features/audit/api/auditApi'
import AuditLogPage from '@/features/audit/pages/AuditLogPage.vue'
import { useTenantContextStore } from '@/features/tenant-context/stores/tenantContext'

vi.mock('@/features/audit/api/auditApi', () => ({
  fetchAuditLogs: vi.fn(),
}))

const logsMock = vi.mocked(fetchAuditLogs)

describe('Audit log page', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    setActivePinia(createPinia())
    useTenantContextStore().$patch({
      tenantId: 'tenant-1',
      status: 'ready',
      membershipRole: 'OWNER',
      permissionCodes: ['audit.view'],
    })
  })

  it('renders append-only audit events sourced from audit_log', async () => {
    logsMock.mockResolvedValue([
      {
        id: 'log-1',
        event: 'ACTION_PREVIEW_SUBMITTED',
        objectType: 'ActionPreview',
        objectId: 'preview-1',
        requestId: 'req-001',
        taskId: 'task-001',
        actorEmail: 'approver@example.com',
        beforeData: { status: 'DRAFT' },
        afterData: { status: 'PENDING_APPROVAL' },
        metadata: { ip: '10.0.0.1' },
        createdAt: '2026-08-07T10:00:00Z',
      },
    ])

    const wrapper = mount(AuditLogPage)
    await flushPromises()

    expect(wrapper.text()).toContain('ACTION_PREVIEW_SUBMITTED')
    expect(wrapper.text()).toContain('ActionPreview #preview-1')
    expect(wrapper.text()).toContain('approver@example.com')
    expect(wrapper.text()).toContain('requestId=req-001')
    expect(wrapper.text()).toContain('taskId=task-001')

    await wrapper.get('details > summary').trigger('click')
    expect(wrapper.text()).toContain('"status": "DRAFT"')
    expect(wrapper.text()).toContain('"status": "PENDING_APPROVAL"')
  })

  it('renders a true empty state when no audit rows exist', async () => {
    logsMock.mockResolvedValue([])
    const wrapper = mount(AuditLogPage)
    await flushPromises()
    expect(wrapper.text()).toContain('当前 Tenant 暂无可见审计事件。')
  })

  it('renders an API failure state', async () => {
    logsMock.mockRejectedValue(new Error('audit unavailable'))
    const wrapper = mount(AuditLogPage)
    await flushPromises()
    expect(wrapper.find('[role="alert"]').exists()).toBe(true)
  })
})