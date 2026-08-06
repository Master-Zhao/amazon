import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { vi } from 'vitest'

import TenantContextPage from '@/features/tenant-context/pages/TenantContextPage.vue'
import { useTenantContextStore } from '@/features/tenant-context/stores/tenantContext'

const { pushMock } = vi.hoisted(() => ({
  pushMock: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: pushMock }),
}))

describe('TenantContextPage', () => {
  it('enters the real data center instead of advertising analytics', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const context = useTenantContextStore()
    const initializeMock = vi
      .spyOn(context, 'initialize')
      .mockResolvedValue(undefined)
    context.$patch({
      tenantId: 'tenant-1',
      storeId: 'store-1',
      storeMarketplaceId: 'store-marketplace-1',
      profileId: 'profile-1',
      status: 'ready',
      tenants: [
        {
          id: 'tenant-1',
          name: 'Demo Tenant',
          tenantType: 'PERSONAL',
          membershipRole: 'OWNER',
        },
      ],
      stores: [
        {
          id: 'store-1',
          name: 'Demo Store',
          externalStoreId: 'demo-store',
        },
      ],
      marketplaces: [
        {
          storeMarketplaceId: 'store-marketplace-1',
          marketplace: {
            id: 'marketplace-1',
            code: 'US',
            name: 'Amazon.com',
            currencyCode: 'USD',
            timezone: 'America/Los_Angeles',
          },
        },
      ],
      profiles: [
        {
          id: 'profile-1',
          name: 'Demo Profile',
          externalProfileId: 'demo-profile',
          currencyCode: 'USD',
          timezone: 'America/Los_Angeles',
          accessLevel: 'MANAGE',
          remoteAdvertisingAvailable: true,
        },
      ],
    })

    const wrapper = mount(TenantContextPage, {
      global: { plugins: [pinia] },
    })
    await wrapper
      .get('button.primary-button')
      .trigger('click')

    expect(pushMock).toHaveBeenCalledWith({ name: 'report-imports' })
    expect(pushMock).not.toHaveBeenCalledWith({ name: 'analytics-dashboard' })
    expect(initializeMock).toHaveBeenCalledOnce()
  })
})
