<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import {
  exportCampaignOverview,
  fetchCampaignOverview,
} from '@/features/advertising/api/campaignApi'
import type {
  CampaignListFilters,
  CampaignListResponse,
  CampaignOverviewItem,
  CampaignMetrics,
  MoneyValue,
} from '@/features/advertising/types/campaign'
import { useTenantContextStore } from '@/features/tenant-context/stores/tenantContext'
import { normalizeApiError } from '@/shared/api/httpClient'

const props = withDefaults(defineProps<{ globalSearch?: string }>(), {
  globalSearch: '',
})
const emit = defineEmits<{
  loaded: [value: CampaignListResponse]
}>()

const context = useTenantContextStore()
const route = useRoute()
const router = useRouter()

function queryText(value: unknown): string {
  return typeof value === 'string' ? value : ''
}

function queryPositiveInt(value: unknown, fallback: number): number {
  const parsed = Number(queryText(value))
  return Number.isInteger(parsed) && parsed > 0 ? parsed : fallback
}

const search = ref(queryText(route.query.search))
const appliedSearch = ref(search.value.trim())
const startDate = ref(queryText(route.query.startDate))
const endDate = ref(queryText(route.query.endDate))
const enabledMode = ref<'true' | 'false' | 'all'>(
  route.query.enabled === 'false'
    ? 'false'
    : route.query.enabled === 'all'
      ? 'all'
      : 'true',
)
const status = ref(queryText(route.query.status))
const targetingType = ref<'' | 'AUTO' | 'MANUAL'>(
  route.query.targetingType === 'AUTO' || route.query.targetingType === 'MANUAL'
    ? route.query.targetingType
    : '',
)
const ordering = ref(queryText(route.query.ordering) || '-spend')
const page = ref(queryPositiveInt(route.query.page, 1))
const pageSize = ref(Math.min(queryPositiveInt(route.query.pageSize, 15), 100))
const result = ref<CampaignListResponse | null>(null)
const loading = ref(false)
const refreshing = ref(false)
const filterOpen = ref(false)
const dateError = ref('')
const errorMessage = ref('')
const errorStatus = ref<number | null>(null)
const requestId = ref<string | null>(null)
const exporting = ref(false)
let requestSequence = 0
let activeController: AbortController | null = null
let searchTimer: number | null = null

const rows = computed(() => result.value?.items ?? [])
const summary = computed(() => result.value?.summary ?? null)
const pagination = computed(() => result.value?.pagination ?? {
  page: page.value,
  pageSize: pageSize.value,
  total: 0,
  totalPages: 0,
})
const isInitialLoading = computed(() => loading.value && result.value === null)
const dateLabel = computed(() => {
  const start = startDate.value || result.value?.meta.startDate
  const end = endDate.value || result.value?.meta.endDate
  if (start && end) return `${start} — ${end}`
  return '最近 30 天'
})
const activeChips = computed(() => {
  const chips: Array<{ key: string; label: string }> = []
  if (appliedSearch.value) {
    chips.push({ key: 'search', label: `搜索：${appliedSearch.value}` })
  }
  if (enabledMode.value === 'false') {
    chips.push({ key: 'enabled', label: '启用状态：未启用' })
  } else if (enabledMode.value === 'all') {
    chips.push({ key: 'enabled', label: '启用状态：全部' })
  }
  if (status.value) {
    chips.push({ key: 'status', label: `状态：${remoteStatusLabel(status.value)}` })
  }
  if (targetingType.value) {
    chips.push({
      key: 'targetingType',
      label: `投放类型：${targetingTypeLabel(targetingType.value)}`,
    })
  }
  if (startDate.value && endDate.value) {
    chips.push({ key: 'date', label: `日期：${startDate.value} — ${endDate.value}` })
  }
  return chips
})

function filters(): CampaignListFilters {
  return {
    ...(startDate.value && endDate.value
      ? { startDate: startDate.value, endDate: endDate.value }
      : {}),
    ...(enabledMode.value === 'all'
      ? {}
      : { enabled: enabledMode.value === 'true' }),
    ...(status.value ? { status: status.value } : {}),
    ...(targetingType.value ? { targetingType: targetingType.value } : {}),
    ...(appliedSearch.value ? { search: appliedSearch.value } : {}),
    ordering: ordering.value,
    page: page.value,
    pageSize: pageSize.value,
    includeSummary: true,
  }
}

async function syncUrl(): Promise<void> {
  await router.replace({
    query: {
      ...(startDate.value && endDate.value
        ? { startDate: startDate.value, endDate: endDate.value }
        : {}),
      enabled: enabledMode.value,
      ...(status.value ? { status: status.value } : {}),
      ...(targetingType.value ? { targetingType: targetingType.value } : {}),
      ...(appliedSearch.value ? { search: appliedSearch.value } : {}),
      ordering: ordering.value,
      page: String(page.value),
      pageSize: String(pageSize.value),
    },
  })
}

async function load(): Promise<void> {
  if (!context.tenantId || !context.profileId) {
    result.value = null
    return
  }
  const currentRequest = ++requestSequence
  activeController?.abort()
  activeController = new AbortController()
  if (result.value === null) loading.value = true
  else refreshing.value = true
  errorMessage.value = ''
  errorStatus.value = null
  requestId.value = null
  try {
    const response = await fetchCampaignOverview(
      context.tenantId,
      context.profileId,
      filters(),
      activeController.signal,
    )
    if (currentRequest !== requestSequence) return
    result.value = response
    emit('loaded', response)
    if (!startDate.value && !endDate.value) {
      startDate.value = response.meta.startDate ?? ''
      endDate.value = response.meta.endDate ?? ''
    }
    if (page.value > response.pagination.totalPages && response.pagination.totalPages > 0) {
      page.value = response.pagination.totalPages
      await syncUrl()
      await load()
    }
  } catch (error) {
    if (activeController?.signal.aborted || currentRequest !== requestSequence) return
    const normalized = normalizeApiError(error)
    errorMessage.value = normalized.message
    errorStatus.value = normalized.status
    requestId.value = normalized.requestId
    result.value = null
  } finally {
    if (currentRequest === requestSequence) {
      loading.value = false
      refreshing.value = false
    }
  }
}

async function applyFilters(): Promise<void> {
  if (Boolean(startDate.value) !== Boolean(endDate.value)) {
    dateError.value = '请选择完整的开始和结束日期'
    return
  }
  if (startDate.value && endDate.value && startDate.value > endDate.value) {
    dateError.value = '结束日期不能早于开始日期'
    return
  }
  dateError.value = ''
  page.value = 1
  await syncUrl()
  await load()
}

function scheduleSearch(): void {
  if (searchTimer !== null) window.clearTimeout(searchTimer)
  searchTimer = window.setTimeout(() => {
    appliedSearch.value = search.value.trim()
    void applyFilters()
  }, 300)
}

function onStatusChange(): void {
  if (status.value && status.value !== 'enabled') enabledMode.value = 'all'
  void applyFilters()
}

function removeChip(key: string): void {
  if (key === 'search') {
    search.value = ''
    appliedSearch.value = ''
  } else if (key === 'enabled') {
    enabledMode.value = 'true'
  } else if (key === 'status') {
    status.value = ''
  } else if (key === 'targetingType') {
    targetingType.value = ''
  } else if (key === 'date') {
    startDate.value = ''
    endDate.value = ''
  }
  void applyFilters()
}

function clearChips(): void {
  search.value = ''
  appliedSearch.value = ''
  enabledMode.value = 'true'
  status.value = ''
  targetingType.value = ''
  startDate.value = ''
  endDate.value = ''
  void applyFilters()
}

function setOrdering(key: string): void {
  ordering.value = ordering.value === key ? `-${key}` : key
  void applyFilters()
}

function sortIndicator(key: string): string {
  if (ordering.value === key) return '↑'
  if (ordering.value === `-${key}`) return '↓'
  return ''
}

async function goToPage(target: number): Promise<void> {
  if (target < 1 || target > pagination.value.totalPages || target === page.value) return
  page.value = target
  await syncUrl()
  await load()
}

async function exportCampaigns(): Promise<void> {
  if (!context.tenantId || !context.profileId || rows.value.length === 0) return
  exporting.value = true
  errorMessage.value = ''
  try {
    const blob = await exportCampaignOverview(
      context.tenantId,
      context.profileId,
      filters(),
    )
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `campaigns-${startDate.value || 'latest'}-${endDate.value || 'latest'}.csv`
    document.body.appendChild(anchor)
    anchor.click()
    anchor.remove()
    URL.revokeObjectURL(url)
  } catch (error) {
    const normalized = normalizeApiError(error)
    errorMessage.value = normalized.message
    errorStatus.value = normalized.status
    requestId.value = normalized.requestId
  } finally {
    exporting.value = false
  }
}

function number(value: number): string {
  return new Intl.NumberFormat('zh-CN').format(value)
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

function percent(value: string | null): string {
  return value === null ? '—' : `${(Number(value) * 100).toFixed(2)}%`
}

function targetingTypeLabel(value: string): string {
  return { AUTO: '自动投放', MANUAL: '手动投放', UNKNOWN: '—' }[value] ?? '—'
}

function statusLabel(value: CampaignOverviewItem['status']): string {
  return {
    DELIVERING: '正在投放',
    PAUSED: '已暂停',
    ARCHIVED: '已归档',
    ENDED: '已结束',
    REVIEWING: '审核中',
    REJECTED: '已拒绝',
    UNKNOWN: '未知',
  }[value]
}

function remoteStatusLabel(value: string): string {
  return {
    enabled: '正在投放',
    paused: '已暂停',
    archived: '已归档',
    ended: '已结束',
    applying: '审核中',
    refuse: '已拒绝',
    nothing: '未知/未开始',
  }[value] ?? value
}

function biddingLabel(value: string): string {
  const normalized = value.toUpperCase()
  return {
    FIXED_BIDS: '固定竞价',
    DYNAMIC_BIDS_DOWN_ONLY: '动态竞价 - 只降低',
    DYNAMIC_BIDS_UP_AND_DOWN: '动态竞价 - 提高和降低',
    LEGACY_FOR_SALES: '动态竞价',
    UNKNOWN: '—',
  }[normalized] ?? value
}

function dateValue(value: string | null, empty = '—'): string {
  return value || empty
}

function summaryCell(metric: CampaignMetrics | null, key: keyof CampaignMetrics): string {
  if (!metric) return '—'
  const value = metric[key]
  if (key === 'impressions' || key === 'clicks' || key === 'orders') {
    return number(value as number)
  }
  if (key === 'spend' || key === 'totalCost' || key === 'cpc') {
    return money(value as MoneyValue | null)
  }
  return percent(value as string | null)
}

watch(
  () => [context.tenantId, context.profileId],
  () => {
    result.value = null
    page.value = 1
    void load()
  },
)

watch(
  () => props.globalSearch,
  (value) => {
    if (value === search.value) return
    search.value = value
    scheduleSearch()
  },
)

onMounted(async () => {
  if (context.status === 'idle') await context.initialize()
  await load()
})

onBeforeUnmount(() => {
  activeController?.abort()
  if (searchTimer !== null) window.clearTimeout(searchTimer)
})
</script>

<template>
  <section class="campaign-section" aria-label="广告活动列表">
    <div v-if="activeChips.length" class="campaign-filter-chips" aria-label="当前筛选">
      <span v-for="chip in activeChips" :key="chip.key" class="campaign-chip">
        {{ chip.label }}
        <button type="button" :aria-label="`删除筛选 ${chip.label}`" @click="removeChip(chip.key)">×</button>
      </span>
      <button class="campaign-clear-filters" type="button" @click="clearChips">删除所有</button>
    </div>

    <div class="campaign-toolbar">
      <div class="campaign-toolbar-left">
        <button class="campaign-title-button" type="button" aria-label="广告活动视图">
          广告活动 <span aria-hidden="true">⌄</span>
        </button>
        <button class="campaign-create-button" type="button" disabled title="当前为只读远程数据">
          ＋ 创建广告活动
        </button>
        <label class="campaign-search">
          <span aria-hidden="true">⌕</span>
          <input
            v-model="search"
            type="search"
            maxlength="100"
            placeholder="查找广告活动"
            aria-label="查找广告活动"
            @input="scheduleSearch"
          >
        </label>
        <button
          class="campaign-ghost-button"
          :class="{ active: filterOpen }"
          type="button"
          aria-controls="campaign-filter-panel"
          :aria-expanded="filterOpen"
          @click="filterOpen = !filterOpen"
        >
          筛选
        </button>
      </div>
      <div class="campaign-toolbar-right">
        <span class="campaign-date-label">{{ dateLabel }}</span>
        <button
          class="campaign-ghost-button"
          type="button"
          :disabled="exporting || rows.length === 0"
          @click="exportCampaigns"
        >
          {{ exporting ? '导出中…' : '导出' }}
        </button>
      </div>
    </div>

    <div v-if="filterOpen" id="campaign-filter-panel" class="campaign-filter-panel">
      <label>
        启用状态
        <select v-model="enabledMode" @change="applyFilters">
          <option value="true">已启用</option>
          <option value="false">未启用</option>
          <option value="all">全部</option>
        </select>
      </label>
      <label>
        状态
        <select v-model="status" @change="onStatusChange">
          <option value="">全部状态</option>
          <option value="enabled">正在投放</option>
          <option value="paused">已暂停</option>
          <option value="archived">已归档</option>
          <option value="ended">已结束</option>
          <option value="applying">审核中</option>
          <option value="refuse">已拒绝</option>
          <option value="nothing">未知/未开始</option>
        </select>
      </label>
      <label>
        投放类型
        <select v-model="targetingType" @change="applyFilters">
          <option value="">全部类型</option>
          <option value="AUTO">自动投放</option>
          <option value="MANUAL">手动投放</option>
        </select>
      </label>
      <label>
        开始日期
        <input v-model="startDate" type="date" @change="applyFilters">
      </label>
      <label>
        结束日期
        <input v-model="endDate" type="date" @change="applyFilters">
      </label>
      <p v-if="dateError" class="campaign-date-error" role="alert">{{ dateError }}</p>
    </div>

    <div v-if="!context.isComplete" class="campaign-state campaign-context-state">
      <strong>请先选择广告数据范围</strong>
      <span>需要完成 Tenant、AmazonStore、Marketplace 和 AdvertisingProfile 选择。</span>
      <RouterLink to="/context">前往卖家空间</RouterLink>
    </div>

    <div v-else class="campaign-table-shell" :aria-busy="loading || refreshing">
      <div v-if="refreshing" class="campaign-refresh-mask" role="status">正在刷新…</div>
      <div class="campaign-table" role="table" aria-label="广告活动表现">
        <div class="campaign-grid campaign-header" role="row">
          <div role="columnheader"><input type="checkbox" disabled aria-label="选择全部广告活动"></div>
          <div role="columnheader">启用</div>
          <button role="columnheader" type="button" @click="setOrdering('name')">广告活动名称 {{ sortIndicator('name') }}</button>
          <button role="columnheader" type="button" @click="setOrdering('targetingType')">投放类型 {{ sortIndicator('targetingType') }}</button>
          <button role="columnheader" type="button" @click="setOrdering('status')">状态 {{ sortIndicator('status') }}</button>
          <button role="columnheader" type="button" @click="setOrdering('biddingStrategy')">竞价方案 {{ sortIndicator('biddingStrategy') }}</button>
          <div role="columnheader">开始日期</div>
          <div role="columnheader">结束日期</div>
          <button role="columnheader" type="button" @click="setOrdering('dailyBudget')">预算金额 {{ sortIndicator('dailyBudget') }}</button>
          <button role="columnheader" type="button" @click="setOrdering('impressions')">展示量 {{ sortIndicator('impressions') }}</button>
          <div role="columnheader">搜索结果首页位置</div>
          <button role="columnheader" type="button" @click="setOrdering('spend')">花费 {{ sortIndicator('spend') }}</button>
          <button role="columnheader" type="button" @click="setOrdering('clicks')">点击量 {{ sortIndicator('clicks') }}</button>
          <button role="columnheader" type="button" @click="setOrdering('ctr')">点击率 {{ sortIndicator('ctr') }}</button>
          <button role="columnheader" type="button" @click="setOrdering('totalCost')">总成本 {{ sortIndicator('totalCost') }}</button>
          <button role="columnheader" type="button" @click="setOrdering('orders')">购买量 {{ sortIndicator('orders') }}</button>
          <button role="columnheader" type="button" @click="setOrdering('cpc')">单次点击成本 {{ sortIndicator('cpc') }}</button>
          <button role="columnheader" type="button" @click="setOrdering('acos')">广告销售成本 ACoS {{ sortIndicator('acos') }}</button>
          <button role="columnheader" type="button" @click="setOrdering('cvr')">转化率 CVR {{ sortIndicator('cvr') }}</button>
        </div>

        <template v-if="isInitialLoading">
          <div v-for="index in 10" :key="index" class="campaign-grid campaign-skeleton" role="row" aria-hidden="true">
            <span v-for="cell in 19" :key="cell"><i /></span>
          </div>
        </template>

        <div v-else-if="errorMessage" class="campaign-state campaign-error-state" role="alert">
          <strong>{{ errorStatus === 403 ? '没有查看此数据的权限' : '广告活动加载失败' }}</strong>
          <span>{{ errorMessage }}</span>
          <small v-if="requestId">requestId：{{ requestId }}</small>
          <button type="button" @click="load">重试</button>
        </div>

        <div v-else-if="rows.length === 0" class="campaign-state campaign-empty-state">
          暂无数据
        </div>

        <template v-else>
          <div v-for="item in rows" :key="item.campaignKey" class="campaign-grid campaign-row" role="row">
            <div role="cell"><input type="checkbox" disabled :aria-label="`选择 ${item.name}`"></div>
            <div role="cell">
              <span class="campaign-switch" :class="{ on: item.enabled }" role="switch" :aria-checked="item.enabled" aria-readonly="true"><i /></span>
            </div>
            <div class="campaign-name-cell" role="cell">
              <span><b aria-hidden="true">›</b>{{ item.name || '—' }}</span>
              <small>{{ item.referenceCode || '—' }}</small>
            </div>
            <div role="cell">{{ targetingTypeLabel(item.targetingType) }}</div>
            <div role="cell"><span class="campaign-status" :class="item.status.toLowerCase()">{{ statusLabel(item.status) }}</span></div>
            <div role="cell">{{ biddingLabel(item.biddingStrategy) }}</div>
            <div role="cell">{{ dateValue(item.startDate) }}</div>
            <div role="cell">{{ dateValue(item.endDate, '无结束日期') }}</div>
            <div class="numeric" role="cell">{{ money(item.dailyBudget) }}</div>
            <div class="numeric" role="cell">{{ number(item.metrics.impressions) }}</div>
            <div class="numeric" role="cell">{{ percent(item.metrics.topOfSearchShare) }}</div>
            <div class="numeric" role="cell">{{ money(item.metrics.spend) }}</div>
            <div class="numeric" role="cell">{{ number(item.metrics.clicks) }}</div>
            <div class="numeric" role="cell">{{ percent(item.metrics.ctr) }}</div>
            <div class="numeric" role="cell">{{ money(item.metrics.totalCost) }}</div>
            <div class="numeric" role="cell">{{ number(item.metrics.orders) }}</div>
            <div class="numeric" role="cell">{{ money(item.metrics.cpc) }}</div>
            <div class="numeric" role="cell">{{ percent(item.metrics.acos) }}</div>
            <div class="numeric" role="cell">{{ percent(item.metrics.cvr) }}</div>
          </div>

          <div class="campaign-grid campaign-summary" role="row">
            <div role="cell" />
            <div role="cell" />
            <div role="cell"><strong>合计</strong><small>{{ pagination.total }} 个广告活动</small></div>
            <div role="cell">—</div>
            <div role="cell">—</div>
            <div role="cell">—</div>
            <div role="cell">—</div>
            <div role="cell">—</div>
            <div role="cell">—</div>
            <div class="numeric" role="cell">{{ summaryCell(summary, 'impressions') }}</div>
            <div class="numeric" role="cell">—</div>
            <div class="numeric" role="cell">{{ summaryCell(summary, 'spend') }}</div>
            <div class="numeric" role="cell">{{ summaryCell(summary, 'clicks') }}</div>
            <div class="numeric" role="cell">{{ summaryCell(summary, 'ctr') }}</div>
            <div class="numeric" role="cell">{{ summaryCell(summary, 'totalCost') }}</div>
            <div class="numeric" role="cell">{{ summaryCell(summary, 'orders') }}</div>
            <div class="numeric" role="cell">{{ summaryCell(summary, 'cpc') }}</div>
            <div class="numeric" role="cell">{{ summaryCell(summary, 'acos') }}</div>
            <div class="numeric" role="cell">{{ summaryCell(summary, 'cvr') }}</div>
          </div>
        </template>
      </div>
    </div>

    <div v-if="context.isComplete" class="campaign-pagination" aria-label="广告活动分页">
      <span>共 {{ pagination.total }} 条</span>
      <label>
        每页
        <select v-model.number="pageSize" @change="applyFilters">
          <option :value="15">15</option>
          <option :value="30">30</option>
          <option :value="50">50</option>
          <option :value="100">100</option>
        </select>
      </label>
      <button type="button" :disabled="page <= 1 || loading" aria-label="上一页" @click="goToPage(page - 1)">‹</button>
      <strong>{{ pagination.totalPages ? page : 0 }} / {{ pagination.totalPages }}</strong>
      <button type="button" :disabled="page >= pagination.totalPages || loading" aria-label="下一页" @click="goToPage(page + 1)">›</button>
    </div>
  </section>
</template>

<style scoped>
.campaign-section {
  width: 100%;
  overflow: hidden;
  border: 1px solid #d8dadd;
  border-radius: 4px;
  background: #fff;
  color: #202124;
  box-shadow: 0 1px 2px rgba(31, 35, 40, 0.06);
  font-family: Arial, "Microsoft YaHei", sans-serif;
  font-size: 12px;
}

.campaign-toolbar,
.campaign-toolbar-left,
.campaign-toolbar-right,
.campaign-filter-chips,
.campaign-filter-panel,
.campaign-pagination {
  display: flex;
  align-items: center;
}

.campaign-toolbar {
  min-height: 52px;
  justify-content: space-between;
  gap: 16px;
  padding: 8px 12px;
  border-bottom: 1px solid #e0e2e5;
}

.campaign-toolbar-left,
.campaign-toolbar-right {
  gap: 8px;
}

.campaign-title-button,
.campaign-create-button,
.campaign-ghost-button,
.campaign-clear-filters,
.campaign-pagination button,
.campaign-error-state button {
  min-height: 32px;
  border: 1px solid #c8ccd0;
  border-radius: 3px;
  padding: 0 12px;
  color: #24272b;
  background: #fff;
  font: inherit;
  font-weight: 600;
  cursor: pointer;
}

.campaign-title-button {
  border-color: transparent;
  padding-left: 4px;
  font-size: 14px;
}

.campaign-create-button {
  border-color: #223b31;
  color: #fff;
  background: #223b31;
}

.campaign-create-button:disabled,
.campaign-ghost-button:disabled,
.campaign-pagination button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.campaign-ghost-button.active,
.campaign-ghost-button:hover:not(:disabled) {
  border-color: #6d747a;
  background: #f4f5f6;
}

.campaign-search {
  display: flex;
  width: 184px;
  height: 32px;
  align-items: center;
  gap: 6px;
  border: 1px solid #c8ccd0;
  border-radius: 3px;
  padding: 0 8px;
  color: #697078;
  background: #fff;
}

.campaign-search:focus-within {
  border-color: #6a8b7d;
  box-shadow: 0 0 0 2px rgba(76, 112, 96, 0.12);
}

.campaign-search input {
  min-width: 0;
  flex: 1;
  border: 0;
  padding: 0;
  outline: 0;
  font: inherit;
}

.campaign-date-label {
  min-height: 32px;
  display: inline-flex;
  align-items: center;
  border: 1px solid #c8ccd0;
  border-radius: 3px;
  padding: 0 10px;
  color: #4e555c;
  white-space: nowrap;
}

.campaign-filter-chips {
  min-height: 42px;
  flex-wrap: wrap;
  gap: 6px;
  padding: 6px 12px;
  border-bottom: 1px solid #e0e2e5;
  background: #fafbfb;
}

.campaign-chip {
  display: inline-flex;
  min-height: 26px;
  align-items: center;
  gap: 6px;
  border: 1px solid #cfd5d1;
  border-radius: 14px;
  padding: 2px 5px 2px 10px;
  color: #38453f;
  background: #fff;
}

.campaign-chip button {
  width: 20px;
  height: 20px;
  border: 0;
  border-radius: 50%;
  padding: 0;
  color: #68716c;
  background: transparent;
  line-height: 18px;
}

.campaign-clear-filters {
  min-height: 26px;
  border: 0;
  padding: 0 6px;
  color: #38634f;
  background: transparent;
}

.campaign-filter-panel {
  position: relative;
  flex-wrap: wrap;
  gap: 10px 16px;
  padding: 10px 12px;
  border-bottom: 1px solid #e0e2e5;
  background: #f7f8f8;
}

.campaign-filter-panel label {
  display: grid;
  gap: 4px;
  color: #555d63;
  font-weight: 600;
}

.campaign-filter-panel select,
.campaign-filter-panel input,
.campaign-pagination select {
  min-height: 30px;
  border: 1px solid #c8ccd0;
  border-radius: 3px;
  padding: 3px 8px;
  color: #202124;
  background: #fff;
  font: inherit;
}

.campaign-date-error {
  width: 100%;
  margin: 0;
  color: #a22922;
}

.campaign-table-shell {
  position: relative;
  max-width: 100%;
  overflow-x: auto;
  scrollbar-color: #aeb4b8 #f0f1f2;
  scrollbar-width: thin;
}

.campaign-table {
  width: 1895px;
  min-width: 1895px;
}

.campaign-grid {
  display: grid;
  grid-template-columns: 42px 48px 220px 90px 100px 130px 105px 110px 110px 100px 120px 105px 90px 90px 105px 90px 115px 110px 100px;
  align-items: stretch;
}

.campaign-grid > * {
  min-width: 0;
  display: flex;
  align-items: center;
  border-right: 1px solid #eceef0;
  padding: 0 9px;
  overflow: hidden;
}

.campaign-header {
  height: 40px;
  border-bottom: 1px solid #d4d7da;
  color: #4f555a;
  background: #f2f3f4;
  font-weight: 700;
}

.campaign-header > button {
  border: 0;
  border-right: 1px solid #e3e5e7;
  border-radius: 0;
  padding: 0 9px;
  color: inherit;
  background: transparent;
  font: inherit;
  text-align: left;
  cursor: pointer;
}

.campaign-header > button:hover {
  background: #e9ebed;
}

.campaign-row {
  min-height: 50px;
  border-bottom: 1px solid #e5e7e9;
  background: #fff;
}

.campaign-row:hover {
  background: #f6f7f7;
}

.campaign-row .numeric,
.campaign-summary .numeric {
  justify-content: flex-end;
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.campaign-name-cell {
  align-items: flex-start;
  justify-content: center;
  flex-direction: column;
  gap: 3px;
}

.campaign-name-cell span,
.campaign-name-cell small {
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.campaign-name-cell span {
  color: #245d88;
  font-weight: 600;
}

.campaign-name-cell b {
  margin-right: 7px;
  color: #6d747a;
  font-size: 16px;
}

.campaign-name-cell small,
.campaign-summary small {
  color: #7a8086;
  font-size: 10px;
}

.campaign-status {
  display: inline-flex;
  min-height: 22px;
  align-items: center;
  border-radius: 11px;
  padding: 0 8px;
  color: #23633f;
  background: #e4f4e9;
  font-size: 11px;
  white-space: nowrap;
}

.campaign-status.paused,
.campaign-status.archived,
.campaign-status.ended,
.campaign-status.unknown {
  color: #626970;
  background: #eceeef;
}

.campaign-status.reviewing {
  color: #8a5b10;
  background: #fff1cf;
}

.campaign-status.rejected {
  color: #9a2d28;
  background: #fde5e3;
}

.campaign-switch {
  position: relative;
  display: inline-block;
  width: 34px;
  height: 18px;
  border-radius: 9px;
  background: #bfc4c7;
}

.campaign-switch i {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
}

.campaign-switch.on {
  background: #3f8b62;
}

.campaign-switch.on i {
  left: 18px;
}

.campaign-summary {
  min-height: 50px;
  border-top: 2px solid #b8bdc1;
  border-bottom: 1px solid #d8dadd;
  background: #f3f4f5;
  font-weight: 700;
}

.campaign-summary > div:nth-child(3) {
  align-items: flex-start;
  justify-content: center;
  flex-direction: column;
  gap: 3px;
}

.campaign-skeleton {
  height: 50px;
  border-bottom: 1px solid #eceef0;
}

.campaign-skeleton i {
  width: 100%;
  height: 10px;
  border-radius: 4px;
  background: linear-gradient(90deg, #edf0f1 25%, #f7f8f8 50%, #edf0f1 75%);
  background-size: 200% 100%;
  animation: campaign-shimmer 1.25s infinite linear;
}

@keyframes campaign-shimmer {
  to { background-position: -200% 0; }
}

.campaign-refresh-mask {
  position: absolute;
  inset: 40px 0 0;
  z-index: 3;
  display: grid;
  place-items: start center;
  padding-top: 12px;
  color: #3e554a;
  background: rgba(255, 255, 255, 0.58);
  font-weight: 700;
  pointer-events: none;
}

.campaign-state {
  min-height: 190px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  gap: 8px;
  padding: 24px;
  color: #697078;
  text-align: center;
}

.campaign-state strong {
  color: #2f353a;
  font-size: 14px;
}

.campaign-state a {
  color: #245d88;
  font-weight: 700;
}

.campaign-error-state small {
  color: #7c8389;
}

.campaign-error-state button {
  margin-top: 4px;
  border-color: #223b31;
  color: #fff;
  background: #223b31;
}

.campaign-pagination {
  min-height: 48px;
  justify-content: flex-end;
  gap: 10px;
  padding: 8px 12px;
  border-top: 1px solid #e0e2e5;
  color: #5b6268;
}

.campaign-pagination label {
  display: flex;
  align-items: center;
  gap: 6px;
}

.campaign-pagination button {
  width: 32px;
  min-height: 30px;
  padding: 0;
  font-size: 18px;
}

@media (max-width: 920px) {
  .campaign-toolbar {
    align-items: flex-start;
    flex-direction: column;
  }

  .campaign-toolbar-left,
  .campaign-toolbar-right {
    width: 100%;
    flex-wrap: wrap;
  }

  .campaign-toolbar-right {
    justify-content: flex-end;
  }
}
</style>
