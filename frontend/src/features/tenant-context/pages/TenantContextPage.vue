<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'

import { useTenantContextStore } from '@/features/tenant-context/stores/tenantContext'

const contextStore = useTenantContextStore()
const router = useRouter()

onMounted(() => contextStore.initialize())

function goToDataCenter() {
  router.push({ name: 'report-imports' })
}
</script>

<template>
  <section class="context-card">
    <header>
      <div>
        <p class="eyebrow">AUTHORIZED DATA SCOPE</p>
        <h2>选择广告数据上下文</h2>
      </div>
      <span v-if="contextStore.isComplete" class="success-badge">上下文已就绪</span>
    </header>

    <p>
      选择顺序固定为卖家空间、Amazon Store、Marketplace、Advertising Profile。
      每一层选项均来自后端数据库授权结果。
    </p>

    <p v-if="contextStore.status === 'loading'" role="status">正在加载授权范围…</p>
    <div v-else-if="contextStore.status === 'error'" class="error-panel">
      <strong>上下文加载失败</strong>
      <p>{{ contextStore.errorMessage }}</p>
      <button type="button" @click="contextStore.initialize">重新加载</button>
    </div>
    <p v-else-if="contextStore.tenants.length === 0" class="empty-panel">
      当前账号没有有效的卖家空间 Membership。
    </p>

    <div v-else class="context-grid">
      <label>
        <span>1. 卖家空间</span>
        <select
          :value="contextStore.tenantId ?? ''"
          @change="
            contextStore.selectTenant(
              ($event.target as HTMLSelectElement).value || null,
            )
          "
        >
          <option value="">请选择卖家空间</option>
          <option
            v-for="tenant in contextStore.tenants"
            :key="tenant.id"
            :value="tenant.id"
          >
            {{ tenant.name }} · {{ tenant.tenantType }}
          </option>
        </select>
      </label>

      <label>
        <span>2. Amazon Store</span>
        <select
          :disabled="!contextStore.tenantId"
          :value="contextStore.storeId ?? ''"
          @change="
            contextStore.selectStore(
              ($event.target as HTMLSelectElement).value || null,
            )
          "
        >
          <option value="">请选择店铺</option>
          <option v-for="store in contextStore.stores" :key="store.id" :value="store.id">
            {{ store.name }}
          </option>
        </select>
      </label>

      <label>
        <span>3. Marketplace</span>
        <select
          :disabled="!contextStore.storeId"
          :value="contextStore.storeMarketplaceId ?? ''"
          @change="
            contextStore.selectMarketplace(
              ($event.target as HTMLSelectElement).value || null,
            )
          "
        >
          <option value="">请选择站点</option>
          <option
            v-for="item in contextStore.marketplaces"
            :key="item.storeMarketplaceId"
            :value="item.storeMarketplaceId"
          >
            {{ item.marketplace.name }} · {{ item.marketplace.currencyCode }}
          </option>
        </select>
      </label>

      <label>
        <span>4. Advertising Profile</span>
        <select
          :disabled="!contextStore.storeMarketplaceId"
          :value="contextStore.profileId ?? ''"
          @change="
            contextStore.selectProfile(
              ($event.target as HTMLSelectElement).value || null,
            )
          "
        >
          <option value="">请选择 Profile</option>
          <option
            v-for="profile in contextStore.profiles"
            :key="profile.id"
            :value="profile.id"
          >
            {{ profile.name }} · {{ profile.accessLevel }}
          </option>
        </select>
      </label>
    </div>

    <footer v-if="contextStore.isComplete" class="context-summary">
      <div class="summary-info">
        <strong>{{ contextStore.currentTenant?.name }}</strong>
        <span>{{ contextStore.currentStore?.name }}</span>
        <span>{{ contextStore.currentMarketplace?.marketplace.code }}</span>
        <span>{{ contextStore.currentProfile?.name }}</span>
      </div>
      <button type="button" class="primary-button" @click="goToDataCenter">
        进入数据中心
      </button>
    </footer>
  </section>
</template>
