import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, vi } from 'vitest'

import { createRole, fetchRoles } from '@/features/system/api/permissionApi'
import RoleManagementPage from '@/features/system/pages/RoleManagementPage.vue'
import { useTenantContextStore } from '@/features/tenant-context/stores/tenantContext'

vi.mock('@/features/system/api/permissionApi', () => ({
  fetchRoles: vi.fn(),
  createRole: vi.fn(),
}))

const rolesMock = vi.mocked(fetchRoles)
const createMock = vi.mocked(createRole)

describe('Role management page', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    setActivePinia(createPinia())
    useTenantContextStore().$patch({
      tenantId: 'tenant-1',
      status: 'ready',
      membershipRole: 'OWNER',
      permissionCodes: ['rbac.manage'],
    })
  })

  it('renders system and custom roles sourced from org_role + sys_permission', async () => {
    rolesMock.mockResolvedValue([
      {
        id: 'role-1',
        code: 'tenant_owner',
        name: '租户所有者',
        isSystem: true,
        permissionCodes: ['context.view', 'rbac.manage'],
      },
      {
        id: 'role-2',
        code: 'report_viewer',
        name: '报表只读',
        isSystem: false,
        permissionCodes: ['reports.view'],
      },
    ])

    const wrapper = mount(RoleManagementPage, {
      global: {
        stubs: { RouterLink: { template: '<a><slot /></a>' } },
      },
    })
    await flushPromises()

    expect(wrapper.text()).toContain('租户所有者（tenant_owner）')
    expect(wrapper.text()).toContain('系统角色')
    expect(wrapper.text()).toContain('报表只读（report_viewer）')
    expect(wrapper.text()).toContain('自定义角色')
  })

  it('creates a custom read-only role bound to fixed permission codes', async () => {
    rolesMock.mockResolvedValue([])
    createMock.mockResolvedValue(undefined)

    const wrapper = mount(RoleManagementPage, {
      global: {
        stubs: { RouterLink: { template: '<a><slot /></a>' } },
      },
    })
    await flushPromises()

    const form = wrapper.find('form.context-grid')
    await form.find('input[required][pattern]').setValue('report_viewer')
    const inputs = form.findAll('input[required]')
    await inputs[1].setValue('报表只读')
    await form.trigger('submit')
    await flushPromises()

    expect(createMock).toHaveBeenCalledWith({
      tenantId: 'tenant-1',
      code: 'report_viewer',
      name: '报表只读',
      permissionCodes: ['context.view'],
    })
  })

  it('blocks management when rbac.manage permission is missing', async () => {
    useTenantContextStore().$patch({
      tenantId: 'tenant-1',
      permissionCodes: ['context.view'],
    })
    rolesMock.mockResolvedValue([])

    const wrapper = mount(RoleManagementPage, {
      global: {
        stubs: { RouterLink: { template: '<a><slot /></a>' } },
      },
    })
    await flushPromises()

    expect(wrapper.text()).toContain('当前卖家空间内无角色管理权限。')
    expect(wrapper.find('form.context-grid').exists()).toBe(false)
  })
})