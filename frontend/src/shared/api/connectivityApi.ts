import { httpClient } from '@/shared/api/httpClient'
import type { ApiEnvelope } from '@/shared/api/types'

export interface TenantItem {
  id: string
  name: string
  tenantType: string
  targetAcos: string | null
  isActive: boolean
  createdAt: string
  updatedAt: string
}

export interface ConnectivityData {
  total: number
  tenants: TenantItem[]
}

export async function fetchConnectivityTenants(): Promise<ConnectivityData> {
  const response = await httpClient.get<ApiEnvelope<ConnectivityData>>(
    '/api/v1/connectivity/',
  )
  return response.data.data
}