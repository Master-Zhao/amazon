import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, vi } from 'vitest'

import {
  fetchMarketplaces,
  fetchProfiles,
  fetchStores,
  fetchTenants,
} from '@/features/tenant-context/api/contextApi'
import { useTenantContextStore } from '@/features/tenant-context/stores/context'

vi.mock('@/features/tenant-context/api/contextApi', () => ({
  fetchTenants: vi.fn(),
  fetchStores: vi.fn(),
  fetchMarketplaces: vi.fn(),
  fetchProfiles: vi.fn(),
}))

const tenant = {
  id: 'tenant-1',
  name: 'Tenant',
  tenantType: 'PERSONAL' as const,
  membershipRole: 'OWNER' as const,
  permissionCodes: ['roles.manage'],
}
const store = { id: 'store-1', name: 'Store', externalStoreId: 'external' }
const marketplace = {
  id: 'scope-1',
  marketplace: {
    id: 'market-1',
    code: 'US',
    name: 'Amazon.com',
    countryCode: 'US',
    currency: 'USD',
    timezone: 'America/Los_Angeles',
  },
}
const profile = {
  id: 'profile-1',
  externalProfileId: 'external-profile',
  name: 'Profile',
  currency: 'USD',
  timezone: 'America/Los_Angeles',
  accessLevel: 'MANAGE' as const,
}

describe('tenant context store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.resetAllMocks()
    vi.mocked(fetchTenants).mockResolvedValue([tenant])
    vi.mocked(fetchStores).mockResolvedValue([store])
    vi.mocked(fetchMarketplaces).mockResolvedValue([marketplace])
    vi.mocked(fetchProfiles).mockResolvedValue([profile])
  })

  it('auto-selects each level only when there is one option', async () => {
    const context = useTenantContextStore()

    await context.initialize()

    expect(context.selectedTenantId).toBe(tenant.id)
    expect(context.selectedStoreId).toBe(store.id)
    expect(context.selectedStoreMarketplaceId).toBe(marketplace.id)
    expect(context.selectedProfileId).toBe(profile.id)
    expect(context.permissionCodes).toEqual(['roles.manage'])
  })

  it('does not auto-select when multiple tenants are available', async () => {
    vi.mocked(fetchTenants).mockResolvedValue([
      tenant,
      { ...tenant, id: 'tenant-2', name: 'Tenant 2' },
    ])
    const context = useTenantContextStore()

    await context.initialize()

    expect(context.selectedTenantId).toBeNull()
    expect(fetchStores).not.toHaveBeenCalled()
  })

  it('clears all server-derived context on logout', async () => {
    const context = useTenantContextStore()
    await context.initialize()

    context.clear()

    expect(context.tenants).toEqual([])
    expect(context.selectedTenantId).toBeNull()
    expect(context.selectedProfileId).toBeNull()
  })
})
