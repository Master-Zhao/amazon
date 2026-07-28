import type { Pinia } from 'pinia'

import {
  setAccessTokenProvider,
  setRequestIdObserver,
  setTenantIdProvider,
} from '@/shared/api/httpClient'
import { usePlatformStore } from '@/shared/stores/platform'

export function installHttpContext(pinia: Pinia): void {
  const platformStore = usePlatformStore(pinia)

  setAccessTokenProvider(() => platformStore.accessToken)
  setTenantIdProvider(() => platformStore.tenantId)
  setRequestIdObserver((requestId) => platformStore.captureRequestId(requestId))
}
