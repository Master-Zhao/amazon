import { createPinia, setActivePinia } from 'pinia'

import { usePlatformStore } from '@/shared/stores/platform'

describe('platform store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('starts without a fabricated request ID', () => {
    const store = usePlatformStore()

    expect(store.lastRequestId).toBeNull()
  })

  it('captures request IDs', () => {
    const store = usePlatformStore()
    store.captureRequestId('req_123')

    expect(store.lastRequestId).toBe('req_123')
  })
})
