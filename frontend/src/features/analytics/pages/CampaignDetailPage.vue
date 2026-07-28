<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import {
  fetchCampaignDetail,
  type CampaignDetail,
} from '@/features/analytics/api/analyticsApi'
import { useTenantContextStore } from '@/features/tenant-context/stores/tenantContext'
import { normalizeApiError } from '@/shared/api/httpClient'
import { init, type ECharts } from '@/shared/charts/echarts'

const context = useTenantContextStore()
const route = useRoute()
const detail = ref<CampaignDetail | null>(null)
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

async function renderChart(): Promise<void> {
  await nextTick()
  const metrics = [...(detail.value?.metrics ?? [])].sort((left, right) =>
    left.reportDate.localeCompare(right.reportDate),
  )
  if (!chartElement.value || metrics.length === 0) {
    chart?.dispose()
    chart = null
    return
  }
  chart ??= init(chartElement.value)
  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['ACOS', '目标 ACOS'] },
    xAxis: { type: 'category', data: metrics.map((row) => row.reportDate) },
    yAxis: {
      type: 'value',
      axisLabel: { formatter: (value: number) => `${(value * 100).toFixed(0)}%` },
    },
    series: [
      {
        name: 'ACOS',
        type: 'line',
        data: metrics.map((row) =>
          row.acos.value === null ? null : Number(row.acos.value),
        ),
      },
      {
        name: '目标 ACOS',
        type: 'line',
        data: metrics.map((row) =>
          row.targetAcos === null ? null : Number(row.targetAcos),
        ),
      },
    ],
  })
}

async function refresh(): Promise<void> {
  const campaignId = String(route.params.campaignId ?? '')
  if (!context.tenantId || !context.profileId || !campaignId) {
    detail.value = null
    return
  }
  loading.value = true
  errorMessage.value = null
  try {
    detail.value = await fetchCampaignDetail(
      context.tenantId,
      context.profileId,
      campaignId,
    )
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
  () => [context.tenantId, context.profileId, route.params.campaignId],
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
        <p class="eyebrow">CAMPAIGN DAILY TREND</p>
        <h2>{{ detail?.campaignName ?? 'Campaign 详情' }}</h2>
        <p v-if="detail">
          {{ detail.externalCampaignId }} · {{ detail.state }} · 有效目标 ACOS
          {{ detail.targetAcos ? `${(Number(detail.targetAcos) * 100).toFixed(2)}%` : '未配置' }}
        </p>
      </div>
      <RouterLink class="secondary-link" to="/campaigns">返回列表</RouterLink>
    </header>

    <div v-if="!context.isComplete" class="empty-panel">请先完成上下文选择。</div>
    <template v-else>
      <div v-if="errorMessage" class="error-panel" role="alert">{{ errorMessage }}</div>
      <p v-if="loading && !detail" role="status">正在加载 Campaign 趋势…</p>
      <p v-else-if="detail && detail.metrics.length === 0" class="empty-panel">
        当前 Campaign 尚无每日事实。
      </p>
      <template v-else-if="detail">
        <div
          ref="chartElement"
          class="dashboard-chart"
          aria-label="Campaign ACOS 与目标 ACOS 趋势"
        />
        <div class="metric-cards">
          <article v-for="row in detail.metrics" :key="row.id" class="metric-card">
            <header>
              <div><small>{{ row.reportDate }}</small><h3>{{ row.stateSnapshot }}</h3></div>
              <span>Batch #{{ row.sourceBatchId }}</span>
            </header>
            <dl class="metric-grid">
              <div><dt>曝光</dt><dd>{{ row.impressions }}</dd></div>
              <div><dt>点击</dt><dd>{{ row.clicks }}</dd></div>
              <div><dt>花费</dt><dd>{{ money(row.spend, row.currencyCode) }}</dd></div>
              <div><dt>销售额</dt><dd>{{ money(row.sales, row.currencyCode) }}</dd></div>
              <div><dt>订单</dt><dd>{{ row.orders }}</dd></div>
              <div class="metric-highlight">
                <dt>ACOS</dt>
                <dd>
                  {{ row.acos.value ? `${(Number(row.acos.value) * 100).toFixed(2)}%` : `— (${row.acos.reason})` }}
                </dd>
              </div>
            </dl>
          </article>
        </div>
      </template>
    </template>
  </section>
</template>
