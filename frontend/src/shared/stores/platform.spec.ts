import { createPinia, setActivePinia } from 'pinia'

import { usePlatformStore } from '@/shared/stores/platform'

describe('platform store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('starts without fabricated auth or tenant context', () => {
    const store = usePlatformStore()

    expect(store.accessToken).toBeNull()
    expect(store.tenantId).toBeNull()
    expect(store.lastRequestId).toBeNull()
  })

  it('captures request IDs and clears future auth context', () => {
    const store = usePlatformStore()
    store.captureRequestId('req_123')
    store.accessToken = 'test-memory-token'
    store.tenantId = 'tenant-test'

    store.clearFutureAuthContext()

    expect(store.lastRequestId).toBe('req_123')
    expect(store.accessToken).toBeNull()
    expect(store.tenantId).toBeNull()
  })
})
