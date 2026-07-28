import { httpClient } from '@/shared/api/httpClient'
import type { ApiEnvelope } from '@/shared/api/types'

export interface TenantContext {
  id: string
  name: string
  tenantType: 'PERSONAL' | 'TEAM' | 'COMPANY'
  membershipRole: 'OWNER' | 'ADMIN' | 'MEMBER'
  permissionCodes: string[]
}

export interface StoreContext {
  id: string
  name: string
  externalStoreId: string
}

export interface MarketplaceContext {
  id: string
  marketplace: {
    id: string
    code: string
    name: string
    countryCode: string
    currency: string
    timezone: string
  }
}

export interface ProfileContext {
  id: string
  externalProfileId: string
  name: string
  currency: string
  timezone: string
  accessLevel: 'VIEW' | 'OPERATE' | 'APPROVE' | 'EXECUTE' | 'MANAGE'
}

async function items<T>(url: string): Promise<T[]> {
  const response = await httpClient.get<ApiEnvelope<{ items: T[] }>>(url)
  return response.data.data.items
}

export const fetchTenants = () => items<TenantContext>('/api/v1/context/tenants')

export const fetchStores = (tenantId: string) =>
  items<StoreContext>(`/api/v1/context/tenants/${tenantId}/stores`)

export const fetchMarketplaces = (tenantId: string, storeId: string) =>
  items<MarketplaceContext>(
    `/api/v1/context/tenants/${tenantId}/stores/${storeId}/marketplaces`,
  )

export const fetchProfiles = (tenantId: string, storeMarketplaceId: string) =>
  items<ProfileContext>(
    `/api/v1/context/tenants/${tenantId}/store-marketplaces/${storeMarketplaceId}/profiles`,
  )

