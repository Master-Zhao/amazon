import { defineStore } from 'pinia'

import {
  fetchMarketplaces,
  fetchProfiles,
  fetchStores,
  fetchTenants,
  type MarketplaceContext,
  type ProfileContext,
  type StoreContext,
  type TenantContext,
} from '@/features/tenant-context/api/contextApi'

interface ContextState {
  tenants: TenantContext[]
  stores: StoreContext[]
  marketplaces: MarketplaceContext[]
  profiles: ProfileContext[]
  selectedTenantId: string | null
  selectedStoreId: string | null
  selectedStoreMarketplaceId: string | null
  selectedProfileId: string | null
  loading: boolean
  error: string | null
}

function choose(current: string | null, ids: string[]): string | null {
  if (current && ids.includes(current)) return current
  return ids.length === 1 ? ids[0] : null
}

export const useTenantContextStore = defineStore('tenant-context', {
  state: (): ContextState => ({
    tenants: [],
    stores: [],
    marketplaces: [],
    profiles: [],
    selectedTenantId: null,
    selectedStoreId: null,
    selectedStoreMarketplaceId: null,
    selectedProfileId: null,
    loading: false,
    error: null,
  }),
  getters: {
    currentTenant: (state) =>
      state.tenants.find((item) => item.id === state.selectedTenantId) ?? null,
    currentProfile: (state) =>
      state.profiles.find((item) => item.id === state.selectedProfileId) ?? null,
    permissionCodes(): string[] {
      return this.currentTenant?.permissionCodes ?? []
    },
  },
  actions: {
    clear() {
      this.$reset()
    },
    async initialize() {
      this.loading = true
      this.error = null
      try {
        this.tenants = await fetchTenants()
        this.selectedTenantId = choose(
          this.selectedTenantId,
          this.tenants.map((item) => item.id),
        )
        if (this.selectedTenantId) await this.selectTenant(this.selectedTenantId)
      } catch (error) {
        this.error = '无法加载卖家空间'
        throw error
      } finally {
        this.loading = false
      }
    },
    async selectTenant(tenantId: string) {
      this.selectedTenantId = tenantId
      this.selectedStoreId = null
      this.selectedStoreMarketplaceId = null
      this.selectedProfileId = null
      this.stores = await fetchStores(tenantId)
      this.selectedStoreId = choose(null, this.stores.map((item) => item.id))
      if (this.selectedStoreId) await this.selectStore(this.selectedStoreId)
    },
    async selectStore(storeId: string) {
      if (!this.selectedTenantId) return
      this.selectedStoreId = storeId
      this.selectedStoreMarketplaceId = null
      this.selectedProfileId = null
      this.marketplaces = await fetchMarketplaces(this.selectedTenantId, storeId)
      this.selectedStoreMarketplaceId = choose(
        null,
        this.marketplaces.map((item) => item.id),
      )
      if (this.selectedStoreMarketplaceId) {
        await this.selectMarketplace(this.selectedStoreMarketplaceId)
      }
    },
    async selectMarketplace(storeMarketplaceId: string) {
      if (!this.selectedTenantId) return
      this.selectedStoreMarketplaceId = storeMarketplaceId
      this.selectedProfileId = null
      this.profiles = await fetchProfiles(
        this.selectedTenantId,
        storeMarketplaceId,
      )
      this.selectedProfileId = choose(null, this.profiles.map((item) => item.id))
    },
    selectProfile(profileId: string) {
      this.selectedProfileId = profileId
    },
  },
})
