import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, vi } from 'vitest'

import HealthDiagnosticsPage from '@/features/diagnostics/pages/HealthDiagnosticsPage.vue'
import { fetchLiveHealth, fetchReadyHealth } from '@/shared/api/healthApi'

vi.mock('@/shared/api/healthApi', () => ({
  fetchLiveHealth: vi.fn(),
  fetchReadyHealth: vi.fn(),
}))

const liveMock = vi.mocked(fetchLiveHealth)
const readyMock = vi.mocked(fetchReadyHealth)

describe('health diagnostics page', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('shows healthy dependency state from real API-shaped responses', async () => {
    liveMock.mockResolvedValue({
      code: 'SUCCESS',
      message: 'ok',
      data: { status: 'alive' },
      requestId: 'req_live',
    })
    readyMock.mockResolvedValue({
      code: 'SUCCESS',
      message: 'ok',
      data: {
        status: 'ready',
        dependencies: {
          database: 'available',
          redis: 'available',
          configuration: 'available',
        },
      },
      requestId: 'req_ready',
    })

    const wrapper = mount(HealthDiagnosticsPage)
    await flushPromises()

    expect(wrapper.text()).toContain('alive')
    expect(wrapper.text()).toContain('ready')
    expect(wrapper.text()).toContain('req_live · req_ready')
  })

  it('shows a degraded state and requestId on readiness failure', async () => {
    liveMock.mockResolvedValue({
      code: 'SUCCESS',
      message: 'ok',
      data: { status: 'alive' },
      requestId: 'req_live',
    })
    readyMock.mockRejectedValue({
      status: 503,
      code: 'SERVICE_NOT_READY',
      message: '服务尚未就绪',
      requestId: 'req_degraded',
      fieldErrors: {},
      retryable: true,
    })

    const wrapper = mount(HealthDiagnosticsPage)
    await flushPromises()

    expect(wrapper.text()).toContain('SERVICE_NOT_READY')
    expect(wrapper.text()).toContain('req_degraded')
    expect(wrapper.text()).toContain('not_ready')
  })
})
