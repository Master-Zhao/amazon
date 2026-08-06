<script setup lang="ts">
import { computed, ref } from 'vue'

import CampaignSection from '@/features/advertising/components/CampaignSection.vue'
import RemotePerformanceChart from '@/features/advertising/components/RemotePerformanceChart.vue'
import type {
  CampaignListResponse,
  CampaignMetrics,
  CampaignRiskLevel,
  MoneyValue,
} from '@/features/advertising/types/campaign'

const result = ref<CampaignListResponse | null>(null)
const globalSearch = ref('')
const displayMode = ref<'all' | 'chart' | 'none'>('all')

function number(value: number | null): string {
  return value === null ? '—' : new Intl.NumberFormat('zh-CN').format(value)
}

function money(value: MoneyValue | null): string {
  if (!value) return '—'
  try {
    return new Intl.NumberFormat('zh-CN', {
      style: 'currency',
      currency: value.currencyCode,
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(Number(value.amount))
  } catch {
    return `${value.currencyCode} ${Number(value.amount).toFixed(2)}`
  }
}

function ratio(value: string | null): string {
  return value === null ? '—' : `${(Number(value) * 100).toFixed(2)}%`
}

const summary = computed<CampaignMetrics | null>(() => result.value?.summary ?? null)
const metricCards = computed(() => [
  { label: '展示量', value: summary.value ? number(summary.value.impressions) : '—', tone: 'blue' },
  { label: '点击量', value: summary.value ? number(summary.value.clicks) : '—', tone: 'orange' },
  { label: '购买量', value: summary.value ? number(summary.value.orders) : '—', tone: 'green' },
  { label: '销售额', value: summary.value ? money(summary.value.sales) : '—', tone: 'purple' },
  { label: '花费', value: summary.value ? money(summary.value.spend) : '—', tone: 'red' },
  { label: 'ACoS', value: summary.value ? ratio(summary.value.acos) : '—', tone: 'teal' },
  { label: '点击率 CTR', value: summary.value ? ratio(summary.value.ctr) : '—', tone: 'sky' },
  { label: '转化率 CVR', value: summary.value ? ratio(summary.value.cvr) : '—', tone: 'gold' },
])

const riskLabels: Record<CampaignRiskLevel, string> = {
  VERY_HIGH: '极高风险',
  HIGH: '高风险',
  MEDIUM: '中风险',
  LOW: '低风险',
  VERY_LOW: '极低风险',
}
</script>

<template>
  <section class="campaign-overview-page">
    <header class="overview-heading">
      <div>
        <h1>广告活动</h1>
        <p v-if="result?.meta.dataThroughDate">
          历史报表 + 实时报表聚合范围：{{ result.meta.startDate }} — {{ result.meta.endDate }}，数据更新至 {{ result.meta.dataThroughDate }}
        </p>
        <p v-else>正在读取当前账号的远程广告数据</p>
      </div>
      <label class="overview-search">
        <span aria-hidden="true">⌕</span>
        <input v-model="globalSearch" type="search" maxlength="100" placeholder="搜索广告活动" aria-label="全局搜索广告活动">
      </label>
    </header>

    <nav class="overview-display-tools" aria-label="看板显示选项">
      <button type="button" :class="{ active: displayMode === 'all' }" @click="displayMode = 'all'">全部显示</button>
      <button type="button" :class="{ active: displayMode === 'chart' }" @click="displayMode = 'chart'">仅显示图表</button>
      <button type="button" :class="{ active: displayMode === 'none' }" @click="displayMode = 'none'">全部隐藏</button>
    </nav>

    <div v-if="displayMode === 'all'" class="overview-kpis" aria-label="广告活动指标汇总">
      <article v-for="card in metricCards" :key="card.label" class="overview-kpi" :class="`tone-${card.tone}`">
        <span>{{ card.label }}</span>
        <strong>{{ card.value }}</strong>
      </article>
    </div>

    <div v-if="displayMode !== 'none'" class="overview-analytics">
      <article class="overview-chart-card">
        <header>
          <div>
            <h2>绩效趋势</h2>
            <p>按日聚合当前筛选范围内的远程 Campaign 数据</p>
          </div>
          <span>{{ result?.dashboard.trend.length ?? 0 }} 天</span>
        </header>
        <RemotePerformanceChart :rows="result?.dashboard.trend ?? []" />
      </article>

      <aside class="overview-risk-card">
        <header>
          <div>
            <h2>风险等级</h2>
            <p>{{ result?.dashboard.evaluatedCampaigns ?? 0 }} 个广告活动已评估</p>
          </div>
          <span class="risk-info" title="依据当前异常规则与目标 ACoS 计算">i</span>
        </header>
        <div class="risk-list">
          <div v-for="risk in result?.dashboard.riskLevels ?? []" :key="risk.level" class="risk-row" :class="risk.level.toLowerCase().replace('_', '-')">
            <i />
            <span>{{ riskLabels[risk.level] }}</span>
            <strong>{{ number(risk.count) }}</strong>
          </div>
        </div>
        <p v-if="result?.dashboard.targetAcos" class="risk-target">目标 ACoS：{{ ratio(result.dashboard.targetAcos) }}</p>
        <p v-if="result?.dashboard.unavailableRuleCodes.length" class="risk-note">预算耗尽规则缺少小时级快照，未纳入本次统计。</p>
      </aside>
    </div>

    <CampaignSection :global-search="globalSearch" @loaded="result = $event" />
  </section>
</template>

<style scoped>
.campaign-overview-page {
  width: 100%;
  min-width: 0;
  display: grid;
  gap: 14px;
  color: #202124;
  font-family: Arial, "Microsoft YaHei", sans-serif;
}

.overview-heading,
.overview-display-tools,
.overview-chart-card > header,
.overview-risk-card > header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.overview-heading h1 { margin: 0 0 5px; font-size: 24px; font-weight: 600; }
.overview-heading p,
.overview-chart-card p,
.overview-risk-card p { margin: 0; color: #687078; font-size: 12px; }

.overview-search {
  width: min(360px, 42vw);
  height: 38px;
  display: flex;
  align-items: center;
  gap: 8px;
  border: 1px solid #bfc5c8;
  border-radius: 3px;
  padding: 0 11px;
  background: #fff;
  color: #6d747a;
}
.overview-search:focus-within { border-color: #527563; box-shadow: 0 0 0 2px rgba(47, 94, 72, .12); }
.overview-search input { min-width: 0; flex: 1; border: 0; outline: 0; font: inherit; }

.overview-display-tools { justify-content: flex-end; gap: 4px; }
.overview-display-tools button {
  min-height: 28px;
  border: 0;
  border-radius: 3px;
  padding: 0 11px;
  color: #4f565c;
  background: transparent;
  font-size: 12px;
  cursor: pointer;
}
.overview-display-tools button.active { color: #fff; background: #3a5549; }

.overview-kpis { display: grid; grid-template-columns: repeat(8, minmax(120px, 1fr)); gap: 8px; }
.overview-kpi {
  position: relative;
  min-height: 92px;
  display: flex;
  justify-content: center;
  flex-direction: column;
  gap: 10px;
  overflow: hidden;
  border: 1px solid #dfe2e4;
  border-radius: 4px;
  padding: 13px 14px;
  background: #fff;
  box-shadow: 0 1px 2px rgba(31, 35, 40, .05);
}
.overview-kpi::before { content: ''; position: absolute; inset: 0 auto 0 0; width: 4px; background: var(--tone); }
.overview-kpi span { color: #676e74; font-size: 12px; }
.overview-kpi strong { overflow: hidden; text-overflow: ellipsis; color: #25292d; font-size: 20px; font-weight: 600; white-space: nowrap; }
.tone-blue { --tone: #547aa5; } .tone-orange { --tone: #d98f39; } .tone-green { --tone: #43a078; }
.tone-purple { --tone: #8b68a9; } .tone-red { --tone: #c75b59; } .tone-teal { --tone: #368b8d; }
.tone-sky { --tone: #5899c2; } .tone-gold { --tone: #b69a3b; }

.overview-analytics { display: grid; grid-template-columns: minmax(0, 1fr) 270px; gap: 12px; }
.overview-chart-card,
.overview-risk-card { border: 1px solid #d8dadd; border-radius: 4px; background: #fff; box-shadow: 0 1px 2px rgba(31,35,40,.05); }
.overview-chart-card > header,
.overview-risk-card > header { min-height: 64px; padding: 10px 16px; border-bottom: 1px solid #eceef0; }
.overview-chart-card h2,
.overview-risk-card h2 { margin: 0 0 4px; font-size: 15px; }
.overview-chart-card > header > span { color: #657069; font-size: 12px; }
.risk-info { width: 20px; height: 20px; display: grid; place-items: center; border: 1px solid #98a29d; border-radius: 50%; color: #657069; font-size: 11px; }
.risk-list { padding: 10px 16px 4px; }
.risk-row { min-height: 38px; display: grid; grid-template-columns: 12px 1fr auto; align-items: center; gap: 9px; border-bottom: 1px solid #f0f1f2; font-size: 12px; }
.risk-row i { width: 9px; height: 9px; border-radius: 50%; background: #5da66f; }
.risk-row strong { font-size: 14px; font-variant-numeric: tabular-nums; }
.risk-row.very-high i { background: #b43d36; } .risk-row.high i { background: #df6c3f; }
.risk-row.medium i { background: #d5a52e; } .risk-row.low i { background: #83a64a; }
.risk-target { padding: 7px 16px 0; }
.risk-note { padding: 8px 16px 14px; line-height: 1.5; }

@media (max-width: 1300px) {
  .overview-kpis { grid-template-columns: repeat(4, minmax(140px, 1fr)); }
}
@media (max-width: 900px) {
  .overview-heading { align-items: flex-start; flex-direction: column; gap: 12px; }
  .overview-search { width: 100%; }
  .overview-kpis { grid-template-columns: repeat(2, minmax(140px, 1fr)); }
  .overview-analytics { grid-template-columns: 1fr; }
}
</style>
