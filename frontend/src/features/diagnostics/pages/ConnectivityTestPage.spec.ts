import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, vi } from 'vitest'

import { fetchRemoteAccount } from '@/features/auth/api/authApi'
import ConnectivityTestPage from '@/features/diagnostics/pages/ConnectivityTestPage.vue'
import { fetchConnectivityTenants } from '@/shared/api/connectivityApi'

vi.mock('@/features/auth/api/authApi', () => ({
  fetchRemoteAccount: vi.fn(),
}))
vi.mock('@/shared/api/connectivityApi', () => ({
  fetchConnectivityTenants: vi.fn(),
}))

describe('connectivity test page', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    vi.mocked(fetchConnectivityTenants).mockResolvedValue({
      total: 0,
      tenants: [],
    })
  })

  it('renders the current account data returned by the protected remote API', async () => {
    vi.mocked(fetchRemoteAccount).mockResolvedValue({
      source: 'SCM_MERCHANT_ADMIN',
      externalUserId: '155',
      merchantId: '122',
      identifier: 'W0765',
      isActive: true,
    })

    const wrapper = mount(ConnectivityTestPage)
    await flushPromises()

    expect(fetchRemoteAccount).toHaveBeenCalledOnce()
    expect(wrapper.text()).toContain('远程读取成功')
    expect(wrapper.text()).toContain('W0765')
    expect(wrapper.text()).toContain('SCM_MERCHANT_ADMIN')
  })

  it('shows the backend requestId when the remote database is unavailable', async () => {
    vi.mocked(fetchRemoteAccount).mockRejectedValue({
      status: 503,
      code: 'SERVICE_NOT_READY',
      message: '远程 SCM 数据服务暂不可用',
      requestId: 'req_remote',
      fieldErrors: {},
      retryable: true,
    })

    const wrapper = mount(ConnectivityTestPage)
    await flushPromises()

    expect(wrapper.text()).toContain('SERVICE_NOT_READY')
    expect(wrapper.text()).toContain('req_remote')
  })
})
