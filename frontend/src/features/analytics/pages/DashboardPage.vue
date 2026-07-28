<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import {
  fetchDashboard,
  type DashboardRow,
  type FormulaValue,
} from '@/features/analytics/api/analyticsApi'
import { useTenantContextStore } from '@/features/tenant-context/stores/tenantContext'
import { normalizeApiError } from '@/shared/api/httpClient'
import { init, type ECharts } from '@/shared/charts/echarts'

const context = useTenantContextStore()
const rows = ref<DashboardRow[]>([])
const loading = ref(false)
const errorMessage = ref<string | null>(null)
const chartElement = ref<globalThis.HTMLElement | null>(null)
let chart: ECharts | null = null

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

async function renderChart(): Promise<void> {
  await nextTick()
  if (!chartElement.value || rows.value.length === 0) {
    chart?.dispose()
    chart = null
    return
  }
  chart ??= init(chartElement.value)
  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['Spend', 'Sales'] },
    xAxis: {
      type: 'category',
      data: rows.value.map(
        (row) => `${row.marketplaceCode} · ${row.currencyCode}`,
      ),
    },
    yAxis: { type: 'value' },
    series: [
      {
        name: 'Spend',
        type: 'bar',
        data: rows.value.map((row) => Number(row.spend)),
      },
      {
        name: 'Sales',
        type: 'bar',
        data: rows.value.map((row) => Number(row.sales)),
      },
    ],
  })
}

async function refresh(): Promise<void> {
  if (!context.tenantId || !context.profileId) {
    rows.value = []
    return
  }
  loading.value = true
  errorMessage.value = null
  try {
    rows.value = await fetchDashboard(context.tenantId, context.profileId)
    await renderChart()
  } catch (error) {
    errorMessage.value = normalizeApiError(error).message
  } finally {
    loading.value = false
  }
}

function resizeChart(): void {
  chart?.resize()
}

watch(
  () => [context.tenantId, context.profileId],
  () => void refresh(),
)
onMounted(async () => {
  globalThis.addEventListener('resize', resizeChart)
  if (context.status === 'idle') await context.initialize()
  await refresh()
})
onBeforeUnmount(() => {
  globalThis.removeEventListener('resize', resizeChart)
  chart?.dispose()
})
</script>

<template>
  <section class="report-page">
    <header class="report-heading">
      <div>
        <p class="eyebrow">CAMPAIGN-GRAIN DASHBOARD</p>
        <h2>广告工作台</h2>
        <p>
          汇总只来自 Campaign Daily Metric，并按 Marketplace 和 currency
          分组；不会把 Targeting 或 Search Term 重复相加。
        </p>
      </div>
      <button type="button" :disabled="loading" @click="refresh">
        {{ loading ? '刷新中…' : '刷新' }}
      </button>
    </header>

    <nav class="task-toolbar" aria-label="广告分析页面">
      <RouterLink class="secondary-link" to="/campaigns">Campaign 指标</RouterLink>
      <RouterLink class="secondary-link" to="/targeting">Targeting 指标</RouterLink>
      <RouterLink class="secondary-link" to="/search-terms">Search Term 指标</RouterLink>
      <RouterLink class="secondary-link" to="/analytics/configuration">
        目标 ACOS 与异常规则
      </RouterLink>
    </nav>

    <div v-if="!context.isComplete" class="empty-panel">
      请先完成 Tenant、Store、Marketplace 和 Profile 上下文选择。
    </div>
    <template v-else>
      <div v-if="errorMessage" class="error-panel" role="alert">{{ errorMessage }}</div>
      <p v-if="loading && rows.length === 0" role="status">正在加载工作台…</p>
      <p v-else-if="rows.length === 0" class="empty-panel">
        当前 Profile 尚无 Campaign Daily Metric。
      </p>
      <template v-else>
        <div ref="chartElement" class="dashboard-chart" aria-label="按站点和币种分组的花费与销售额图表" />
        <div class="metric-cards">
          <article v-for="row in rows" :key="`${row.marketplaceCode}-${row.currencyCode}`" class="metric-card">
            <header>
              <div>
                <small>{{ row.marketplaceName }}</small>
                <h3>{{ row.marketplaceCode }} · {{ row.currencyCode }}</h3>
                <code>{{ row.authoritativeGrain }}</code>
              </div>
              <strong>{{ row.anomalyCount }} 个异常</strong>
            </header>
            <dl class="metric-grid">
              <div><dt>Campaign</dt><dd>{{ row.campaignCount }}</dd></div>
              <div><dt>曝光</dt><dd>{{ row.impressions }}</dd></div>
              <div><dt>点击</dt><dd>{{ row.clicks }}</dd></div>
              <div><dt>花费</dt><dd>{{ money(row.spend, row.currencyCode) }}</dd></div>
              <div><dt>销售额</dt><dd>{{ money(row.sales, row.currencyCode) }}</dd></div>
              <div><dt>订单</dt><dd>{{ row.orders }}</dd></div>
              <div><dt>CTR</dt><dd>{{ ratio(row.ctr) }}</dd></div>
              <div class="metric-highlight"><dt>ACOS</dt><dd>{{ ratio(row.acos) }}</dd></div>
            </dl>
          </article>
        </div>
      </template>
    </template>
  </section>
</template>
