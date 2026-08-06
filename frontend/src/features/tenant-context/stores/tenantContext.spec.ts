import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, vi } from 'vitest'

import {
  fetchContextCapabilities,
  fetchMarketplaceOptions,
  fetchProfileOptions,
  fetchStoreOptions,
  fetchTenantOptions,
} from '@/features/tenant-context/api/contextApi'
import { useTenantContextStore } from '@/features/tenant-context/stores/tenantContext'

vi.mock('@/features/tenant-context/api/contextApi', () => ({
  fetchTenantOptions: vi.fn(),
  fetchStoreOptions: vi.fn(),
  fetchMarketplaceOptions: vi.fn(),
  fetchProfileOptions: vi.fn(),
  fetchContextCapabilities: vi.fn(),
}))

const mockedTenants = vi.mocked(fetchTenantOptions)
const mockedStores = vi.mocked(fetchStoreOptions)
const mockedMarketplaces = vi.mocked(fetchMarketplaceOptions)
const mockedProfiles = vi.mocked(fetchProfileOptions)
const mockedCapabilities = vi.mocked(fetchContextCapabilities)

describe('tenant context store', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
    vi.resetAllMocks()
  })

  it('auto-selects each level only when there is exactly one option', async () => {
    mockedTenants.mockResolvedValue([
      {
        id: 'tenant-1',
        name: '演示空间',
        tenantType: 'PERSONAL',
        membershipRole: 'OWNER',
      },
    ])
    mockedStores.mockResolvedValue([
      { id: 'store-1', name: '演示店铺', externalStoreId: 'external-1' },
    ])
    mockedMarketplaces.mockResolvedValue([
      {
        storeMarketplaceId: 'sm-1',
        marketplace: {
          id: 'market-1',
          code: 'US',
          name: 'Amazon.com',
          currencyCode: 'USD',
          timezone: 'America/Los_Angeles',
        },
      },
    ])
    mockedProfiles.mockResolvedValue([
      {
        id: 'profile-1',
        name: 'Demo profile',
        externalProfileId: 'external-profile',
        currencyCode: 'USD',
        timezone: 'America/Los_Angeles',
        accessLevel: 'MANAGE',
        remoteAdvertisingAvailable: true,
      },
    ])
    mockedCapabilities.mockResolvedValue({
      permissionCodes: ['context.view', 'reports.upload'],
      membershipRole: 'OWNER',
    })
    const store = useTenantContextStore()

    await store.initialize()

    expect(store.isComplete).toBe(true)
    expect(store.tenantId).toBe('tenant-1')
    expect(store.storeId).toBe('store-1')
    expect(store.storeMarketplaceId).toBe('sm-1')
    expect(store.profileId).toBe('profile-1')
    expect(store.permissionCodes).toContain('reports.upload')
  })

  it('prefers a remote advertising profile when profile options are ambiguous', async () => {
    mockedTenants.mockResolvedValue([
      {
        id: 'tenant-1',
        name: '演示空间',
        tenantType: 'PERSONAL',
        membershipRole: 'OWNER',
      },
    ])
    mockedStores.mockResolvedValue([
      { id: 'store-1', name: '演示店铺', externalStoreId: 'external-1' },
    ])
    mockedMarketplaces.mockResolvedValue([
      {
        storeMarketplaceId: 'sm-1',
        marketplace: {
          id: 'market-1',
          code: 'US',
          name: 'Amazon.com',
          currencyCode: 'USD',
          timezone: 'America/Los_Angeles',
        },
      },
    ])
    mockedProfiles.mockResolvedValue([
      {
        id: 'profile-local',
        name: 'Local profile',
        externalProfileId: 'local-profile',
        currencyCode: 'USD',
        timezone: 'America/Los_Angeles',
        accessLevel: 'MANAGE',
        remoteAdvertisingAvailable: false,
      },
      {
        id: 'profile-remote',
        name: 'Remote profile',
        externalProfileId: 'remote-profile',
        currencyCode: 'USD',
        timezone: 'America/Los_Angeles',
        accessLevel: 'MANAGE',
        remoteAdvertisingAvailable: true,
      },
    ])
    mockedCapabilities.mockResolvedValue({
      permissionCodes: ['context.view', 'advertising.view'],
      membershipRole: 'OWNER',
    })
    const store = useTenantContextStore()

    await store.initialize()

    expect(store.profileId).toBe('profile-remote')
  })

  it('does not guess when multiple tenants are available', async () => {
    mockedTenants.mockResolvedValue([
      {
        id: 'tenant-1',
        name: '空间一',
        tenantType: 'TEAM',
        membershipRole: 'MEMBER',
      },
      {
        id: 'tenant-2',
        name: '空间二',
        tenantType: 'COMPANY',
        membershipRole: 'MEMBER',
      },
    ])
    const store = useTenantContextStore()

    await store.initialize()

    expect(store.tenantId).toBeNull()
    expect(mockedStores).not.toHaveBeenCalled()
    expect(store.status).toBe('ready')
  })
})
