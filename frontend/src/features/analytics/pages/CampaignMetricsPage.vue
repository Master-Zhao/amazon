<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'

import {
  fetchCampaignMetrics,
  type CampaignMetricRow,
  type FormulaValue,
} from '@/features/analytics/api/analyticsApi'
import { useTenantContextStore } from '@/features/tenant-context/stores/tenantContext'
import { normalizeApiError } from '@/shared/api/httpClient'

const context = useTenantContextStore()
const rows = ref<CampaignMetricRow[]>([])
const startDate = ref('')
const endDate = ref('')
const loading = ref(false)
const errorMessage = ref<string | null>(null)

const anomalyCount = computed(() =>
  rows.value.reduce(
    (count, row) =>
      count + row.anomalies.filter((item) => item.status === 'ANOMALY').length,
    0,
  ),
)

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

function number(metric: FormulaValue): string {
  return metric.value === null
    ? `— (${metric.reason ?? 'UNAVAILABLE'})`
    : Number(metric.value).toFixed(2)
}

async function refresh(): Promise<void> {
  if (!context.tenantId || !context.profileId) {
    rows.value = []
    return
  }
  loading.value = true
  errorMessage.value = null
  try {
    rows.value = await fetchCampaignMetrics(
      context.tenantId,
      context.profileId,
      {
        ...(startDate.value ? { startDate: startDate.value } : {}),
        ...(endDate.value ? { endDate: endDate.value } : {}),
      },
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
        <p class="eyebrow">DETERMINISTIC ANALYTICS</p>
        <h2>Campaign 指标与异常</h2>
        <p>
          指标来自 Campaign Daily Metric。CTR、CPC、CVR、ACOS 和 ROAS
          由 Python 确定性计算，异常可追溯到规则版本和来源批次。
        </p>
      </div>
      <div class="metric-summary">
        <span>{{ rows.length }} 条每日事实</span>
        <strong>{{ anomalyCount }} 个异常</strong>
      </div>
    </header>

    <div v-if="!context.isComplete" class="empty-panel">
      请先完成演示上下文选择。
      <RouterLink to="/context">前往上下文</RouterLink>
    </div>

    <template v-else>
      <form class="filter-bar" @submit.prevent="refresh">
        <label>
          开始日期
          <input v-model="startDate" type="date">
        </label>
        <label>
          结束日期
          <input v-model="endDate" type="date">
        </label>
        <button type="submit" :disabled="loading">
          {{ loading ? '加载中…' : '查询' }}
        </button>
        <RouterLink class="secondary-link" to="/reports/imports">
          导入新报表
        </RouterLink>
      </form>

      <div v-if="errorMessage" class="error-panel" role="alert">
        {{ errorMessage }}
      </div>
      <p v-if="loading && rows.length === 0" role="status">正在加载指标…</p>
      <p v-else-if="rows.length === 0" class="empty-panel">
        当前 Profile 和日期范围没有 Campaign 每日事实。
      </p>

      <div v-else class="metric-cards">
        <article v-for="row in rows" :key="row.id" class="metric-card">
          <header>
            <div>
              <small>
                {{ row.reportDate }} · {{ row.stateSnapshot }}
                <template v-if="row.snapshotHourLocal !== null">
                  · {{ row.snapshotHourLocal }}:00 local snapshot
                </template>
              </small>
              <h3>{{ row.campaignName }}</h3>
              <code>{{ row.externalCampaignId }}</code>
              <RouterLink
                class="secondary-link"
                :to="`/campaigns/${row.campaignId}`"
              >
                查看详情与趋势
              </RouterLink>
            </div>
            <span>Batch #{{ row.sourceBatchId }}</span>
          </header>

          <dl class="metric-grid">
            <div><dt>曝光</dt><dd>{{ row.impressions }}</dd></div>
            <div><dt>点击</dt><dd>{{ row.clicks }}</dd></div>
            <div><dt>花费</dt><dd>{{ money(row.spend, row.currencyCode) }}</dd></div>
            <div><dt>订单</dt><dd>{{ row.orders }}</dd></div>
            <div><dt>销售额</dt><dd>{{ money(row.sales, row.currencyCode) }}</dd></div>
            <div><dt>CTR</dt><dd>{{ ratio(row.ctr) }}</dd></div>
            <div><dt>CPC</dt><dd>{{ number(row.cpc) }}</dd></div>
            <div><dt>CVR</dt><dd>{{ ratio(row.cvr) }}</dd></div>
            <div class="metric-highlight">
              <dt>ACOS / 目标</dt>
              <dd>
                {{ ratio(row.acos) }} /
                {{ row.targetAcos ? `${(Number(row.targetAcos) * 100).toFixed(2)}%` : '—' }}
              </dd>
            </div>
            <div><dt>ROAS</dt><dd>{{ number(row.roas) }}</dd></div>
          </dl>

          <div class="anomaly-list">
            <article
              v-for="anomaly in row.anomalies"
              :key="anomaly.id"
              :class="['anomaly-item', `anomaly-${anomaly.status.toLowerCase()}`]"
            >
              <strong>
                {{ anomaly.ruleCode }} · v{{ anomaly.ruleVersion }}
              </strong>
              <span>{{ anomaly.status }} {{ anomaly.riskLevel ?? '' }}</span>
              <p>{{ anomaly.explanation }}</p>
            </article>
          </div>
        </article>
      </div>
    </template>
  </section>
</template>
