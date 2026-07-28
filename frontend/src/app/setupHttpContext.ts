import type { Pinia } from 'pinia'
import type { Router } from 'vue-router'

import {
  setAccessTokenProvider,
  setRefreshHandler,
  setRequestIdObserver,
} from '@/shared/api/httpClient'
import { useAuthStore } from '@/features/auth/stores/auth'
import { usePlatformStore } from '@/shared/stores/platform'

export function installHttpContext(pinia: Pinia, router: Router): void {
  const authStore = useAuthStore(pinia)
  const platformStore = usePlatformStore(pinia)

  setAccessTokenProvider(() => authStore.accessToken)
  setRefreshHandler(async () => {
    try {
      await authStore.refreshSession()
    } catch (error) {
      authStore.clearSession()
      if (router.currentRoute.value.name !== 'login') {
        await router.push({
          name: 'login',
          query: { redirect: router.currentRoute.value.fullPath },
        })
      }
      throw error
    }
  })
  setRequestIdObserver((requestId) => platformStore.captureRequestId(requestId))
}
