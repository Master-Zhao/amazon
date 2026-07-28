import { defineStore } from 'pinia'

interface PlatformState {
  accessToken: string | null
  tenantId: string | null
  lastRequestId: string | null
}

export const usePlatformStore = defineStore('platform', {
  state: (): PlatformState => ({
    accessToken: null,
    tenantId: null,
    lastRequestId: null,
  }),
  actions: {
    captureRequestId(requestId: string) {
      this.lastRequestId = requestId
    },
    clearFutureAuthContext() {
      this.accessToken = null
      this.tenantId = null
    },
  },
})
