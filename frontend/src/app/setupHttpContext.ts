import type { Pinia } from 'pinia'
import type { Router } from 'vue-router'

import {
  setAccessTokenProvider,
  setRefreshHandler,
  setRequestIdObserver,
  setTenantIdProvider,
} from '@/shared/api/httpClient'
import { useAuthStore } from '@/features/auth/stores/auth'
import { useTenantContextStore } from '@/features/tenant-context/stores/context'
import { usePlatformStore } from '@/shared/stores/platform'

export function installHttpContext(pinia: Pinia, router: Router): void {
  const authStore = useAuthStore(pinia)
  const platformStore = usePlatformStore(pinia)
  const contextStore = useTenantContextStore(pinia)

  setAccessTokenProvider(() => authStore.accessToken)
  setTenantIdProvider(() => contextStore.selectedTenantId)
  setRefreshHandler(async () => {
    try {
      await authStore.refreshSession()
    } catch (error) {
      authStore.clearSession()
      contextStore.clear()
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
