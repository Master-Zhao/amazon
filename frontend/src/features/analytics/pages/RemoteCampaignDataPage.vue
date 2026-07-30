<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'

import {
  fetchRemoteCampaignMetrics,
  type FormulaValue,
  type RemoteCampaignMetricRow,
} from '@/features/analytics/api/analyticsApi'
import { useTenantContextStore } from '@/features/tenant-context/stores/tenantContext'
import { normalizeApiError } from '@/shared/api/httpClient'

const context = useTenantContextStore()
const rows = ref<RemoteCampaignMetricRow[]>([])
const startDate = ref('')
const endDate = ref('')
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
    rows.value = await fetchRemoteCampaignMetrics(
      context.tenantId,
      context.profileId,
      {
        ...(startDate.value ? { startDate: startDate.value } : {}),
        ...(endDate.value ? { endDate: endDate.value } : {}),
      },
    )
  } catch (error) {
    rows.value = []
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
        <p class="eyebrow">READ-ONLY REMOTE DATA</p>
        <h2>远程 Campaign 数据</h2>
        <p>
          从只读 SCM 与广告分析数据库实时查询。数据范围由当前
          Tenant、Store、Profile 权限及 Profile 商户映射共同限制。
        </p>
      </div>
      <div class="metric-summary">
        <span>{{ rows.length }} 条聚合记录</span>
        <strong>只读连接</strong>
      </div>
    </header>

    <div v-if="!context.isComplete" class="empty-panel">
      请先完成 Tenant、Store、Marketplace 和 Profile 选择。
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
          {{ loading ? '加载中…' : '查询远程数据' }}
        </button>
      </form>

      <div v-if="errorMessage" class="error-panel" role="alert">
        {{ errorMessage }}
      </div>
      <p v-if="loading" role="status">正在读取两个远程数据库…</p>
      <p v-else-if="!errorMessage && rows.length === 0" class="empty-panel">
        当前 Profile 映射和日期范围没有远程 Campaign 数据。
      </p>

      <div v-else-if="rows.length > 0" class="metric-cards">
        <article v-for="row in rows" :key="row.id" class="metric-card">
          <header>
            <div>
              <small>{{ row.reportDate }} · {{ row.state }}</small>
              <h3>{{ row.campaignName }}</h3>
              <code>{{ row.externalCampaignId }}</code>
            </div>
            <span>
              {{ row.scmMatched ? 'SCM 已匹配' : '仅分析库' }}
            </span>
          </header>

          <dl class="metric-grid">
            <div><dt>曝光</dt><dd>{{ row.impressions }}</dd></div>
            <div><dt>点击</dt><dd>{{ row.clicks }}</dd></div>
            <div><dt>花费</dt><dd>{{ money(row.spend, row.currencyCode) }}</dd></div>
            <div><dt>订单</dt><dd>{{ row.orders }}</dd></div>
            <div><dt>销售额</dt><dd>{{ money(row.sales, row.currencyCode) }}</dd></div>
            <div><dt>日预算</dt><dd>{{ row.dailyBudget ? money(row.dailyBudget, row.currencyCode) : '—' }}</dd></div>
            <div><dt>CTR</dt><dd>{{ ratio(row.ctr) }}</dd></div>
            <div><dt>CPC</dt><dd>{{ number(row.cpc) }}</dd></div>
            <div><dt>CVR</dt><dd>{{ ratio(row.cvr) }}</dd></div>
            <div class="metric-highlight"><dt>ACOS</dt><dd>{{ ratio(row.acos) }}</dd></div>
            <div><dt>ROAS</dt><dd>{{ number(row.roas) }}</dd></div>
          </dl>
        </article>
      </div>
    </template>
  </section>
</template>
