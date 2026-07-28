<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { LineChart } from 'echarts/charts'
import {
  GridComponent,
  LegendComponent,
  TooltipComponent,
} from 'echarts/components'
import * as echarts from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'

import {
  fetchDashboard,
  type DashboardData,
} from '@/features/dashboard/api/analyticsApi'
import { useTenantContextStore } from '@/features/tenant-context/stores/context'

echarts.use([
  LineChart,
  GridComponent,
  LegendComponent,
  TooltipComponent,
  CanvasRenderer,
])

const context = useTenantContextStore()
const data = ref<DashboardData | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)
const chartElement = ref<globalThis.HTMLElement | null>(null)
let chart: echarts.EChartsType | null = null

const hasData = computed(() => Boolean(data.value?.series.length))

function renderChart(): void {
  if (!chartElement.value || !data.value) return
  chart ??= echarts.init(chartElement.value)
  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['花费', '销售额'] },
    xAxis: { type: 'category', data: data.value.series.map((item) => item.date) },
    yAxis: { type: 'value' },
    series: [
      { name: '花费', type: 'line', data: data.value.series.map((item) => Number(item.spend)) },
      { name: '销售额', type: 'line', data: data.value.series.map((item) => Number(item.sales)) },
    ],
  })
}

async function load(): Promise<void> {
  if (!context.selectedProfileId) return
  loading.value = true
  error.value = null
  try {
    data.value = await fetchDashboard(context.selectedProfileId)
    globalThis.queueMicrotask(renderChart)
  } catch {
    error.value = 'Dashboard 加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(() => context.selectedProfileId, load)
onUnmounted(() => chart?.dispose())
</script>

<template>
  <section class="panel">
    <p class="eyebrow">CAMPAIGN AUTHORITY</p>
    <h2>广告工作台</h2>
    <p v-if="!context.selectedProfileId" class="empty-state">请先选择 Advertising Profile。</p>
    <p v-else-if="loading" role="status">正在加载 Campaign 权威指标…</p>
    <p v-else-if="error" class="error-banner">{{ error }}</p>
    <p v-else-if="!hasData" class="empty-state">暂无 Campaign 日指标，请先导入报表。</p>
    <template v-else-if="data">
      <div class="capability-grid">
        <article><span>Spend</span><h3>{{ data.totals.spend }} {{ data.currency }}</h3></article>
        <article><span>Sales</span><h3>{{ data.totals.sales }} {{ data.currency }}</h3></article>
        <article><span>ACOS</span><h3>{{ data.totals.acos ?? '—' }}</h3></article>
      </div>
      <div ref="chartElement" style="height: 320px" aria-label="花费与销售额趋势图" />
      <ul>
        <li v-for="item in data.series" :key="`${item.date}-${item.campaignId}`">
          {{ item.date }} · {{ item.campaignName }} · {{ item.stateSnapshot }}
          <strong v-if="item.anomalies.some((entry) => entry.status === 'ANOMALOUS')">异常</strong>
        </li>
      </ul>
    </template>
  </section>
</template>
