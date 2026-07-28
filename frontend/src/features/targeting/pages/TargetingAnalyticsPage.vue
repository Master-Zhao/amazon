<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { fetchAnalyticsList } from '@/features/dashboard/api/analyticsApi'
import { useTenantContextStore } from '@/features/tenant-context/stores/context'

const context = useTenantContextStore()
const items = ref<Array<Record<string, unknown>>>([])
const error = ref(false)
onMounted(async () => {
  if (!context.selectedProfileId) return
  try {
    items.value = (
      await fetchAnalyticsList('/api/v1/analytics/targeting', context.selectedProfileId)
    ).items
  } catch {
    error.value = true
  }
})
</script>

<template>
  <section class="panel">
    <p class="eyebrow">TARGETING AUTHORITY</p><h2>Keyword / Product Target 分析</h2>
    <p v-if="error" class="error-banner">Targeting 指标加载失败。</p>
    <p v-else-if="items.length === 0" class="empty-state">暂无 Targeting 日指标。</p>
    <pre v-else>{{ items }}</pre>
  </section>
</template>

