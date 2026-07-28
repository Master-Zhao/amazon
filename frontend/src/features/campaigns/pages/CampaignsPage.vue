<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'

import {
  fetchCampaigns,
  type Campaign,
} from '@/features/campaigns/api/campaignApi'
import { useTenantContextStore } from '@/features/tenant-context/stores/context'

const context = useTenantContextStore()
const items = ref<Campaign[]>([])
const selected = ref<Campaign | null>(null)
const loading = ref(false)
const error = ref(false)

async function load(): Promise<void> {
  if (!context.selectedProfileId) return
  loading.value = true
  error.value = false
  try {
    items.value = await fetchCampaigns(context.selectedProfileId)
    selected.value = items.value[0] ?? null
  } catch {
    error.value = true
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(() => context.selectedProfileId, load)
</script>

<template>
  <section class="panel">
    <p class="eyebrow">CAMPAIGNS</p>
    <h2>Campaign 列表与详情</h2>
    <p v-if="!context.selectedProfileId" class="empty-state">请先选择 Advertising Profile。</p>
    <p v-else-if="loading">正在加载 Campaign…</p>
    <p v-else-if="error" class="error-banner">Campaign 加载失败或无权限。</p>
    <p v-else-if="items.length === 0" class="empty-state">暂无 Campaign，请先导入报表。</p>
    <div v-else class="split-view">
      <nav class="card-list" aria-label="Campaign 列表">
        <button
          v-for="item in items"
          :key="item.id"
          class="secondary-button selection-button"
          type="button"
          @click="selected = item"
        >
          {{ item.name }} · {{ item.state }}
        </button>
      </nav>
      <article v-if="selected" class="hero-card compact-card">
        <h3>{{ selected.name }}</h3>
        <dl class="dependency-list">
          <dt>外部 ID</dt><dd>{{ selected.externalCampaignId }}</dd>
          <dt>状态</dt><dd>{{ selected.state }}</dd>
          <dt>日预算</dt><dd>{{ selected.dailyBudget ?? '未提供' }} {{ selected.currency }}</dd>
        </dl>
      </article>
    </div>
  </section>
</template>
