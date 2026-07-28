import { httpClient } from '@/shared/api/httpClient'
import type { ApiEnvelope } from '@/shared/api/types'

export interface TenantOption {
  id: string
  name: string
  tenantType: 'PERSONAL' | 'TEAM' | 'COMPANY'
  membershipRole: 'OWNER' | 'ADMIN' | 'MEMBER'
}

export interface StoreOption {
  id: string
  name: string
  externalStoreId: string
}

export interface MarketplaceOption {
  storeMarketplaceId: string
  marketplace: {
    id: string
    code: string
    name: string
    currencyCode: string
    timezone: string
  }
}

export interface ProfileOption {
  id: string
  name: string
  externalProfileId: string
  currencyCode: string
  timezone: string
  accessLevel: 'VIEW' | 'OPERATE' | 'APPROVE' | 'EXECUTE' | 'MANAGE'
}

export interface ContextCapabilities {
  permissionCodes: string[]
  membershipRole: TenantOption['membershipRole']
}

async function data<T>(request: Promise<{ data: ApiEnvelope<T> }>): Promise<T> {
  return (await request).data.data
}

export function fetchTenantOptions(): Promise<TenantOption[]> {
  return data(httpClient.get('/api/v1/context/tenants'))
}

export function fetchStoreOptions(tenantId: string): Promise<StoreOption[]> {
  return data(httpClient.get(`/api/v1/context/tenants/${tenantId}/stores`))
}

export function fetchMarketplaceOptions(
  tenantId: string,
  storeId: string,
): Promise<MarketplaceOption[]> {
  return data(
    httpClient.get(
      `/api/v1/context/tenants/${tenantId}/stores/${storeId}/marketplaces`,
    ),
  )
}

export function fetchProfileOptions(
  tenantId: string,
  storeMarketplaceId: string,
): Promise<ProfileOption[]> {
  return data(
    httpClient.get(
      `/api/v1/context/tenants/${tenantId}/store-marketplaces/` +
        `${storeMarketplaceId}/profiles`,
    ),
  )
}

export function fetchContextCapabilities(
  tenantId: string,
): Promise<ContextCapabilities> {
  return data(
    httpClient.get(`/api/v1/context/tenants/${tenantId}/capabilities`),
  )
}
