<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'

import {
  fetchTargetingMetrics,
  type FormulaValue,
  type TargetingMetricRow,
} from '@/features/analytics/api/analyticsApi'
import { useTenantContextStore } from '@/features/tenant-context/stores/tenantContext'
import { normalizeApiError } from '@/shared/api/httpClient'

const context = useTenantContextStore()
const rows = ref<TargetingMetricRow[]>([])
const loading = ref(false)
const errorMessage = ref<string | null>(null)

function money(value: string, currency: string): string {
  return new Intl.NumberFormat('zh-CN', {
    style: 'currency',
    currency,
  }).format(Number(value))
}

function ratio(metric: FormulaValue): string {
  return metric.value === null
    ? `— (${metric.reason ?? 'UNAVAILABLE'})`
    : `${(Number(metric.value) * 100).toFixed(2)}%`
}

async function refresh(): Promise<void> {
  if (!context.tenantId || !context.profileId) {
    rows.value = []
    return
  }
  loading.value = true
  errorMessage.value = null
  try {
    rows.value = await fetchTargetingMetrics(
      context.tenantId,
      context.profileId,
    )
  } catch (error) {
    errorMessage.value = normalizeApiError(error).message
  } finally {
    loading.value = false
  }
}

watch(
  () => [context.tenantId, context.profileId],
  () => void refresh(),
)
onMounted(async () => {
  if (context.status === 'idle') await context.initialize()
  await refresh()
})
</script>

<template>
  <section class="report-page">
    <header class="report-heading">
      <div>
        <p class="eyebrow">AUTHORITATIVE TARGETING GRAIN</p>
        <h2>Keyword 与 Product Target 指标</h2>
        <p>每行来自 Targeting Daily Metric，保留报表日期当时的竞价和状态快照。</p>
      </div>
      <RouterLink class="secondary-link" to="/reports/imports">导入 Targeting</RouterLink>
    </header>

    <div v-if="!context.isComplete" class="empty-panel">
      请先完成 Tenant、Store、Marketplace 和 Profile 上下文选择。
    </div>
    <template v-else>
      <div v-if="errorMessage" class="error-panel" role="alert">{{ errorMessage }}</div>
      <p v-if="loading && rows.length === 0" role="status">正在加载 Targeting 指标…</p>
      <p v-else-if="rows.length === 0" class="empty-panel">
        当前 Profile 尚无 Targeting Daily Metric。
      </p>
      <div v-else class="metric-cards">
        <article v-for="row in rows" :key="row.id" class="metric-card">
          <header>
            <div>
              <small>{{ row.reportDate }} · {{ row.targetType }} · {{ row.stateSnapshot }}</small>
              <h3>{{ row.targetText }}</h3>
              <code>{{ row.campaignName }} / {{ row.adGroupName }}</code>
            </div>
            <span>Batch #{{ row.sourceBatchId }}</span>
          </header>
          <dl class="metric-grid">
            <div><dt>匹配类型</dt><dd>{{ row.matchType ?? '—' }}</dd></div>
            <div><dt>竞价快照</dt><dd>{{ row.bidSnapshot ? money(row.bidSnapshot, row.currencyCode) : '—' }}</dd></div>
            <div><dt>曝光</dt><dd>{{ row.impressions }}</dd></div>
            <div><dt>点击</dt><dd>{{ row.clicks }}</dd></div>
            <div><dt>花费</dt><dd>{{ money(row.spend, row.currencyCode) }}</dd></div>
            <div><dt>订单</dt><dd>{{ row.orders }}</dd></div>
            <div><dt>销售额</dt><dd>{{ money(row.sales, row.currencyCode) }}</dd></div>
            <div><dt>CTR</dt><dd>{{ ratio(row.ctr) }}</dd></div>
            <div><dt>CVR</dt><dd>{{ ratio(row.cvr) }}</dd></div>
            <div class="metric-highlight"><dt>ACOS</dt><dd>{{ ratio(row.acos) }}</dd></div>
          </dl>
        </article>
      </div>
    </template>
  </section>
</template>
