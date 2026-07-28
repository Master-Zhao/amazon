import { defineStore } from 'pinia'

interface PlatformState {
  lastRequestId: string | null
}

export const usePlatformStore = defineStore('platform', {
  state: (): PlatformState => ({
    lastRequestId: null,
  }),
  actions: {
    captureRequestId(requestId: string) {
      this.lastRequestId = requestId
    },
  },
})
