import { defineStore } from 'pinia'

import {
  fetchContextCapabilities,
  fetchMarketplaceOptions,
  fetchProfileOptions,
  fetchStoreOptions,
  fetchTenantOptions,
  type ContextCapabilities,
  type MarketplaceOption,
  type ProfileOption,
  type StoreOption,
  type TenantOption,
} from '@/features/tenant-context/api/contextApi'

const STORAGE_KEY = 'amazon-ads-context-v1'

interface StoredContext {
  tenantId: string | null
  storeId: string | null
  storeMarketplaceId: string | null
  profileId: string | null
}

interface TenantContextState extends StoredContext {
  tenants: TenantOption[]
  stores: StoreOption[]
  marketplaces: MarketplaceOption[]
  profiles: ProfileOption[]
  permissionCodes: string[]
  membershipRole: ContextCapabilities['membershipRole'] | null
  status: 'idle' | 'loading' | 'ready' | 'error'
  errorMessage: string | null
}

function storedContext(): StoredContext {
  try {
    const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '{}')
    return {
      tenantId: typeof parsed.tenantId === 'string' ? parsed.tenantId : null,
      storeId: typeof parsed.storeId === 'string' ? parsed.storeId : null,
      storeMarketplaceId:
        typeof parsed.storeMarketplaceId === 'string'
          ? parsed.storeMarketplaceId
          : null,
      profileId: typeof parsed.profileId === 'string' ? parsed.profileId : null,
    }
  } catch {
    return {
      tenantId: null,
      storeId: null,
      storeMarketplaceId: null,
      profileId: null,
    }
  }
}

function chooseId<T extends { id: string }>(
  options: T[],
  preferred: string | null,
): string | null {
  if (preferred && options.some((item) => item.id === preferred)) {
    return preferred
  }
  return options.length === 1 ? options[0].id : null
}

export const useTenantContextStore = defineStore('tenant-context', {
  state: (): TenantContextState => ({
    ...storedContext(),
    tenants: [],
    stores: [],
    marketplaces: [],
    profiles: [],
    permissionCodes: [],
    membershipRole: null,
    status: 'idle',
    errorMessage: null,
  }),
  getters: {
    isComplete: (state) =>
      Boolean(
        state.tenantId &&
          state.storeId &&
          state.storeMarketplaceId &&
          state.profileId,
      ),
    currentTenant: (state) =>
      state.tenants.find((item) => item.id === state.tenantId) ?? null,
    currentStore: (state) =>
      state.stores.find((item) => item.id === state.storeId) ?? null,
    currentMarketplace: (state) =>
      state.marketplaces.find(
        (item) => item.storeMarketplaceId === state.storeMarketplaceId,
      ) ?? null,
    currentProfile: (state) =>
      state.profiles.find((item) => item.id === state.profileId) ?? null,
  },
  actions: {
    persist() {
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({
          tenantId: this.tenantId,
          storeId: this.storeId,
          storeMarketplaceId: this.storeMarketplaceId,
          profileId: this.profileId,
        }),
      )
    },
    clear() {
      this.tenantId = null
      this.storeId = null
      this.storeMarketplaceId = null
      this.profileId = null
      this.tenants = []
      this.stores = []
      this.marketplaces = []
      this.profiles = []
      this.permissionCodes = []
      this.membershipRole = null
      this.status = 'idle'
      this.errorMessage = null
      localStorage.removeItem(STORAGE_KEY)
    },
    async initialize() {
      if (this.status === 'loading') return
      const preferred = {
        tenantId: this.tenantId,
        storeId: this.storeId,
        storeMarketplaceId: this.storeMarketplaceId,
        profileId: this.profileId,
      }
      this.status = 'loading'
      this.errorMessage = null
      try {
        this.tenants = await fetchTenantOptions()
        const tenantId = chooseId(this.tenants, preferred.tenantId)
        await this.selectTenant(tenantId, preferred)
        this.status = 'ready'
      } catch (error) {
        this.status = 'error'
        this.errorMessage =
          error instanceof Error ? error.message : '上下文加载失败'
      }
    },
    async selectTenant(
      tenantId: string | null,
      preferred: Partial<StoredContext> = {},
    ) {
      this.tenantId = tenantId
      this.storeId = null
      this.storeMarketplaceId = null
      this.profileId = null
      this.stores = []
      this.marketplaces = []
      this.profiles = []
      this.permissionCodes = []
      this.membershipRole = null
      if (!tenantId) {
        this.persist()
        return
      }
      const [stores, capabilities] = await Promise.all([
        fetchStoreOptions(tenantId),
        fetchContextCapabilities(tenantId),
      ])
      this.stores = stores
      this.permissionCodes = capabilities.permissionCodes
      this.membershipRole = capabilities.membershipRole
      await this.selectStore(chooseId(stores, preferred.storeId ?? null), preferred)
    },
    async selectStore(
      storeId: string | null,
      preferred: Partial<StoredContext> = {},
    ) {
      this.storeId = storeId
      this.storeMarketplaceId = null
      this.profileId = null
      this.marketplaces = []
      this.profiles = []
      if (!this.tenantId || !storeId) {
        this.persist()
        return
      }
      this.marketplaces = await fetchMarketplaceOptions(this.tenantId, storeId)
      const preferredStoreMarketplace = preferred.storeMarketplaceId ?? null
      const selected =
        preferredStoreMarketplace &&
        this.marketplaces.some(
          (item) => item.storeMarketplaceId === preferredStoreMarketplace,
        )
          ? preferredStoreMarketplace
          : this.marketplaces.length === 1
            ? this.marketplaces[0].storeMarketplaceId
            : null
      await this.selectMarketplace(selected, preferred)
    },
    async selectMarketplace(
      storeMarketplaceId: string | null,
      preferred: Partial<StoredContext> = {},
    ) {
      this.storeMarketplaceId = storeMarketplaceId
      this.profileId = null
      this.profiles = []
      if (!this.tenantId || !storeMarketplaceId) {
        this.persist()
        return
      }
      this.profiles = await fetchProfileOptions(
        this.tenantId,
        storeMarketplaceId,
      )
      this.profileId = chooseId(this.profiles, preferred.profileId ?? null)
      this.persist()
    },
    selectProfile(profileId: string | null) {
      this.profileId = profileId
      this.persist()
    },
  },
})
