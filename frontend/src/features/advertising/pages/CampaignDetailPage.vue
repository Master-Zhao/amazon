<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import { fetchCampaignDetail } from '@/features/advertising/api/campaignApi'
import type {
  CampaignDetailResponse,
  CampaignMetrics,
  MoneyValue,
} from '@/features/advertising/types/campaign'
import { useTenantContextStore } from '@/features/tenant-context/stores/tenantContext'
import { normalizeApiError } from '@/shared/api/httpClient'

const route = useRoute()
const context = useTenantContextStore()
const detail = ref<CampaignDetailResponse | null>(null)
const loading = ref(false)
const errorMessage = ref('')
let controller: AbortController | null = null

const campaignKey = computed(() => String(route.params.campaignKey ?? ''))
const startDate = computed(() => typeof route.query.startDate === 'string' ? route.query.startDate : undefined)
const endDate = computed(() => typeof route.query.endDate === 'string' ? route.query.endDate : undefined)

function number(value: number | null): string {
  return value === null ? '—' : new Intl.NumberFormat('zh-CN').format(value)
}

function money(value: MoneyValue | null): string {
  if (!value) return '—'
  return new Intl.NumberFormat('zh-CN', {
    style: 'currency',
    currency: value.currencyCode,
    minimumFractionDigits: 2,
  }).format(Number(value.amount))
}

function percent(value: string | null): string {
  return value === null ? '—' : `${(Number(value) * 100).toFixed(2)}%`
}

function metricValue(metrics: CampaignMetrics, key: keyof CampaignMetrics): string {
  const value = metrics[key]
  if (key === 'impressions' || key === 'clicks' || key === 'orders') return number(value as number | null)
  if (key === 'spend' || key === 'sales' || key === 'totalCost' || key === 'cpc') return money(value as MoneyValue | null)
  return percent(value as string | null)
}

async function load(): Promise<void> {
  if (!context.tenantId || !context.profileId || !campaignKey.value) return
  controller?.abort()
  controller = new AbortController()
  loading.value = true
  errorMessage.value = ''
  try {
    detail.value = await fetchCampaignDetail(
      context.tenantId,
      context.profileId,
      campaignKey.value,
      {
        ...(startDate.value && endDate.value
          ? { startDate: startDate.value, endDate: endDate.value }
          : {}),
      },
      controller.signal,
    )
  } catch (error) {
    if (controller.signal.aborted) return
    errorMessage.value = normalizeApiError(error).message
    detail.value = null
  } finally {
    if (!controller.signal.aborted) loading.value = false
  }
}

watch(() => [context.tenantId, context.profileId, campaignKey.value], () => void load())

onMounted(async () => {
  if (context.status === 'idle') await context.initialize()
  await load()
})

onBeforeUnmount(() => controller?.abort())
</script>

<template>
  <main class="campaign-detail-page">
    <RouterLink class="back-link" :to="{ name: 'advertising-overview', query: route.query }">← 返回广告活动</RouterLink>

    <section v-if="loading" class="detail-state">正在读取远程数据库…</section>
    <section v-else-if="errorMessage" class="detail-state error" role="alert">
      <strong>广告活动加载失败</strong>
      <span>{{ errorMessage }}</span>
      <button type="button" @click="load">重试</button>
    </section>
    <template v-else-if="detail">
      <header class="detail-header">
        <div>
          <p>广告活动</p>
          <h1>{{ detail.item.name }}</h1>
          <span>{{ detail.item.referenceCode }}</span>
        </div>
        <span class="source-badge">远程数据库 · 只读</span>
      </header>

      <section class="detail-meta">
        <dl><dt>状态</dt><dd>{{ detail.item.enabled ? '正在投放' : '未启用' }}</dd></dl>
        <dl><dt>投放类型</dt><dd>{{ detail.item.targetingType === 'AUTO' ? '自动投放' : '手动投放' }}</dd></dl>
        <dl><dt>竞价方案</dt><dd>{{ detail.item.biddingStrategy }}</dd></dl>
        <dl><dt>日期范围</dt><dd>{{ detail.meta.startDate }} — {{ detail.meta.endDate }}</dd></dl>
      </section>

      <section class="metric-grid" aria-label="广告活动聚合指标">
        <article><span>展示量</span><strong>{{ number(detail.item.metrics.impressions) }}</strong></article>
        <article><span>点击量</span><strong>{{ number(detail.item.metrics.clicks) }}</strong></article>
        <article><span>花费</span><strong>{{ money(detail.item.metrics.spend) }}</strong></article>
        <article><span>购买量</span><strong>{{ number(detail.item.metrics.orders) }}</strong></article>
        <article><span>点击率</span><strong>{{ percent(detail.item.metrics.ctr) }}</strong></article>
        <article><span>广告销售成本比</span><strong>{{ percent(detail.item.metrics.acos) }}</strong></article>
      </section>

      <section class="trend-card">
        <div class="trend-title">
          <div><h2>每日表现</h2><p>历史报表与实时报表按同粒度去重合并</p></div>
          <span>数据截至 {{ detail.meta.dataThroughDate ?? '—' }}</span>
        </div>
        <div class="trend-scroll">
          <table>
            <thead><tr><th>日期</th><th>展示量</th><th>点击量</th><th>花费</th><th>购买量</th><th>点击率</th><th>ACoS</th></tr></thead>
            <tbody>
              <tr v-for="point in detail.trend" :key="point.date">
                <td>{{ point.date }}</td>
                <td>{{ metricValue(point.metrics, 'impressions') }}</td>
                <td>{{ metricValue(point.metrics, 'clicks') }}</td>
                <td>{{ metricValue(point.metrics, 'spend') }}</td>
                <td>{{ metricValue(point.metrics, 'orders') }}</td>
                <td>{{ metricValue(point.metrics, 'ctr') }}</td>
                <td>{{ metricValue(point.metrics, 'acos') }}</td>
              </tr>
              <tr v-if="detail.trend.length === 0"><td colspan="7">所选日期内暂无指标</td></tr>
            </tbody>
          </table>
        </div>
      </section>
    </template>
  </main>
</template>

<style scoped>
.campaign-detail-page { display: grid; gap: 16px; padding: 20px; color: #17233c; }
.back-link { color: #2468d9; font-size: 13px; text-decoration: none; }
.detail-header, .detail-meta, .metric-grid, .trend-card { border: 1px solid #dfe4ec; border-radius: 6px; background: #fff; }
.detail-header { display: flex; align-items: flex-start; justify-content: space-between; padding: 22px 24px; }
.detail-header p, .detail-header h1 { margin: 0; }
.detail-header p { color: #71809b; font-size: 12px; }
.detail-header h1 { margin-top: 5px; font-size: 22px; }
.detail-header div > span { color: #8a97ad; font-size: 12px; }
.source-badge { border-radius: 4px; padding: 6px 10px; color: #43624e; background: #e8f5ec; font-size: 12px; }
.detail-meta { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); padding: 16px 20px; }
.detail-meta dl { margin: 0; padding: 0 18px; border-right: 1px solid #edf0f5; }
.detail-meta dl:last-child { border: 0; }
.detail-meta dt { color: #8290a7; font-size: 12px; }
.detail-meta dd { margin: 5px 0 0; font-weight: 600; }
.metric-grid { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); }
.metric-grid article { min-height: 92px; display: grid; align-content: center; gap: 8px; padding: 0 18px; border-right: 1px solid #edf0f5; }
.metric-grid article:last-child { border: 0; }
.metric-grid span { color: #7a879c; font-size: 12px; }
.metric-grid strong { font-size: 20px; font-variant-numeric: tabular-nums; }
.trend-card { overflow: hidden; }
.trend-title { display: flex; align-items: center; justify-content: space-between; padding: 16px 20px; border-bottom: 1px solid #e4e8ef; }
.trend-title h2, .trend-title p { margin: 0; }
.trend-title h2 { font-size: 16px; }
.trend-title p, .trend-title > span { margin-top: 4px; color: #8490a2; font-size: 12px; }
.trend-scroll { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: 12px; }
th, td { height: 42px; padding: 0 16px; border-bottom: 1px solid #edf0f4; text-align: right; white-space: nowrap; }
th:first-child, td:first-child { text-align: left; }
th { color: #627089; background: #f7f9fc; }
.detail-state { min-height: 220px; display: grid; place-items: center; border: 1px solid #dfe4ec; background: #fff; }
.detail-state.error { align-content: center; gap: 8px; color: #a52a2a; }
.detail-state button { padding: 6px 16px; }
@media (max-width: 960px) { .detail-meta, .metric-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
</style>
