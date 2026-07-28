<script setup lang="ts">
import { onMounted } from 'vue'

import { useTenantContextStore } from '@/features/tenant-context/stores/context'

const context = useTenantContextStore()
onMounted(() => context.initialize())
</script>

<template>
  <section class="panel context-page">
    <p class="eyebrow">TENANT CONTEXT</p>
    <h2>卖家空间与广告账户</h2>
    <p>按卖家空间 → 店铺 → Marketplace → Advertising Profile 选择工作范围。</p>

    <p v-if="context.loading" role="status">正在加载可访问范围…</p>
    <div v-else-if="context.error" class="error-banner">{{ context.error }}</div>
    <div v-else-if="context.tenants.length === 0" class="empty-state">
      当前账号没有有效卖家空间，请联系管理员。
    </div>
    <div v-else class="context-grid">
      <label>
        卖家空间
        <select
          :value="context.selectedTenantId ?? ''"
          @change="context.selectTenant(($event.target as HTMLSelectElement).value)"
        >
          <option value="" disabled>请选择</option>
          <option v-for="item in context.tenants" :key="item.id" :value="item.id">
            {{ item.name }} · {{ item.tenantType }}
          </option>
        </select>
      </label>
      <label>
        Amazon 店铺
        <select
          :value="context.selectedStoreId ?? ''"
          :disabled="!context.selectedTenantId"
          @change="context.selectStore(($event.target as HTMLSelectElement).value)"
        >
          <option value="" disabled>请选择</option>
          <option v-for="item in context.stores" :key="item.id" :value="item.id">
            {{ item.name }}
          </option>
        </select>
      </label>
      <label>
        Marketplace
        <select
          :value="context.selectedStoreMarketplaceId ?? ''"
          :disabled="!context.selectedStoreId"
          @change="context.selectMarketplace(($event.target as HTMLSelectElement).value)"
        >
          <option value="" disabled>请选择</option>
          <option
            v-for="item in context.marketplaces"
            :key="item.id"
            :value="item.id"
          >
            {{ item.marketplace.name }} · {{ item.marketplace.currency }}
          </option>
        </select>
      </label>
      <label>
        Advertising Profile
        <select
          :value="context.selectedProfileId ?? ''"
          :disabled="!context.selectedStoreMarketplaceId"
          @change="context.selectProfile(($event.target as HTMLSelectElement).value)"
        >
          <option value="" disabled>请选择</option>
          <option v-for="item in context.profiles" :key="item.id" :value="item.id">
            {{ item.name }} · {{ item.accessLevel }}
          </option>
        </select>
      </label>
    </div>
  </section>
</template>

