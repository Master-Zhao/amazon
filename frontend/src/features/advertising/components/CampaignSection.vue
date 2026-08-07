<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import {
  createCampaign,
  exportCampaignOverview,
  fetchCampaignOverview,
  updateCampaignEnabled,
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
    : route.query.enabled === 'true'
      ? 'true'
      : 'all',
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
const dateOpen = ref(false)
const dateCustomOpen = ref(false)
const createOpen = ref(false)
const metricFilters = ref(queryText(route.query.metricFilters))
const filterEditor = ref<'status' | 'metric' | null>(null)
const statusDraft = ref('')
const metricDraftField = ref('impressions')
const metricDraftOperator = ref<'gte' | 'lte' | 'eq' | 'between'>('gte')
const metricDraftValue = ref('')
const metricDraftValue2 = ref('')
const dateError = ref('')
const errorMessage = ref('')
const errorStatus = ref<number | null>(null)
const requestId = ref<string | null>(null)
const errorTitle = ref('广告活动加载失败')
const exporting = ref(false)
const creating = ref(false)
const updatingCampaignKeys = ref<Set<string>>(new Set())
const selectedCampaignKeys = ref<Set<string>>(new Set())
const createDraft = ref({
  name: '',
  targetingType: 'MANUAL' as 'AUTO' | 'MANUAL',
  dailyBudget: '10.00',
  biddingStrategy: 'down_only' as 'up_and_down' | 'down_only' | 'fixed_bids',
  startDate: '',
  endDate: '',
  enabled: true,
})
let requestSequence = 0
let activeController: AbortController | null = null
let searchTimer: number | null = null

const metricMenuItems = [
  { field: 'impressions', label: '展示量' },
  { field: 'clicks', label: '点击量' },
  { field: 'spend', label: '花费' },
  { field: 'orders', label: '购买量' },
  { field: 'cpc', label: '单次点击成本' },
  { field: 'acos', label: '广告销售成本比' },
  { field: 'ctr', label: '点击率' },
  { field: 'cvr', label: '转化率' },
] as const

interface MetricFilterRule {
  field: string
  operator: 'gte' | 'lte' | 'eq' | 'between'
  value: string
  value2?: string
}

const rows = computed(() => result.value?.items ?? [])
const selectedCount = computed(() => selectedCampaignKeys.value.size)
const allVisibleSelected = computed(() =>
  rows.value.length > 0 &&
  rows.value.every((item) => selectedCampaignKeys.value.has(item.campaignKey)),
)
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
  if (status.value) {
    chips.push({ key: 'status', label: status.value === 'enabled' ? '进行中' : `状态：${remoteStatusLabel(status.value)}` })
  }
  if (enabledMode.value === 'true') {
    chips.push({ key: 'enabled', label: '已启用' })
  } else if (enabledMode.value === 'false') {
    chips.push({ key: 'enabled', label: '启用状态：未启用' })
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
  decodeMetricFilters(metricFilters.value).forEach((rule) => {
    chips.push({
      key: `metric:${rule.field}`,
      label: metricFilterChipLabel(encodeMetricFilter(rule)),
    })
  })
  return chips
})

function filters(): CampaignListFilters {
  const effectiveStart = startDate.value || result.value?.meta.startDate
  const effectiveEnd = endDate.value || result.value?.meta.endDate
  return {
    ...(effectiveStart && effectiveEnd
      ? { startDate: effectiveStart, endDate: effectiveEnd }
      : {}),
    ...(enabledMode.value === 'all'
      ? {}
      : { enabled: enabledMode.value === 'true' }),
    ...(status.value ? { status: status.value } : {}),
    ...(targetingType.value ? { targetingType: targetingType.value } : {}),
    ...(appliedSearch.value ? { search: appliedSearch.value } : {}),
    ...(metricFilters.value ? { metricFilters: metricFilters.value } : {}),
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
      ...(metricFilters.value ? { metricFilters: metricFilters.value } : {}),
      ordering: ordering.value,
      page: String(page.value),
      pageSize: String(pageSize.value),
    },
  })
}

async function load(silent = false): Promise<void> {
  if (!context.tenantId || !context.profileId) {
    result.value = null
    return
  }
  const currentRequest = ++requestSequence
  activeController?.abort()
  activeController = new AbortController()
  if (result.value === null) loading.value = true
  else refreshing.value = true
  if (!silent) {
    errorMessage.value = ''
    errorStatus.value = null
    requestId.value = null
  }
  try {
    const response = await fetchCampaignOverview(
      context.tenantId,
      context.profileId,
      filters(),
      activeController.signal,
    )
    if (currentRequest !== requestSequence) return
    if (shouldRelaxMetriclessStatusFilters(response)) {
      enabledMode.value = 'all'
      status.value = ''
      page.value = 1
      await syncUrl()
      await load(silent)
      return
    }
    result.value = response
    emit('loaded', response)
    if (page.value > response.pagination.totalPages && response.pagination.totalPages > 0) {
      page.value = response.pagination.totalPages
      await syncUrl()
      await load(silent)
    }
  } catch (error) {
    if (activeController?.signal.aborted || currentRequest !== requestSequence) return
    if (silent) return
    const normalized = normalizeApiError(error)
    errorTitle.value = '广告活动加载失败'
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

function shouldRelaxMetriclessStatusFilters(response: CampaignListResponse): boolean {
  return (
    response.items.length > 0 &&
    response.items.every((item) => !item.hasMetrics) &&
    (enabledMode.value !== 'all' || Boolean(status.value))
  )
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

function removeChip(key: string): void {
  if (key === 'search') {
    search.value = ''
    appliedSearch.value = ''
  } else if (key === 'enabled') {
    enabledMode.value = 'all'
  } else if (key === 'status') {
    status.value = ''
  } else if (key === 'targetingType') {
    targetingType.value = ''
  } else if (key === 'date') {
    startDate.value = ''
    endDate.value = ''
  } else if (key.startsWith('metric:')) {
    const field = key.slice('metric:'.length)
    metricFilters.value = decodeMetricFilters(metricFilters.value)
      .filter((rule) => rule.field !== field)
      .map(encodeMetricFilter)
      .join(';')
  }
  void applyFilters()
}

function clearChips(): void {
  search.value = ''
  appliedSearch.value = ''
  enabledMode.value = 'all'
  status.value = ''
  targetingType.value = ''
  startDate.value = ''
  endDate.value = ''
  metricFilters.value = ''
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
    errorTitle.value = '广告活动导出失败'
    errorMessage.value = normalized.message
    errorStatus.value = normalized.status
    requestId.value = normalized.requestId
  } finally {
    exporting.value = false
  }
}

function openCreateCampaign(): void {
  createDraft.value = {
    name: '',
    targetingType: 'MANUAL',
    dailyBudget: '10.00',
    biddingStrategy: 'down_only',
    startDate: result.value?.meta.dataThroughDate || isoDate(new Date()),
    endDate: '',
    enabled: true,
  }
  errorMessage.value = ''
  errorStatus.value = null
  requestId.value = null
  createOpen.value = true
}

function closeCreateCampaign(): void {
  if (!creating.value) createOpen.value = false
}

async function submitCreateCampaign(): Promise<void> {
  if (!context.tenantId || !context.profileId || creating.value) return
  if (!createDraft.value.name.trim()) {
    errorTitle.value = '广告活动创建失败'
    errorMessage.value = '请输入广告活动名称'
    return
  }
  if (!createDraft.value.startDate) {
    errorTitle.value = '广告活动创建失败'
    errorMessage.value = '请选择开始日期'
    return
  }
  if (createDraft.value.endDate && createDraft.value.startDate > createDraft.value.endDate) {
    errorTitle.value = '广告活动创建失败'
    errorMessage.value = '结束日期不能早于开始日期'
    return
  }
  creating.value = true
  errorMessage.value = ''
  errorStatus.value = null
  requestId.value = null
  try {
    const parsedBudget = Number(createDraft.value.dailyBudget)
    await createCampaign(
      context.tenantId,
      context.profileId,
      {
        name: createDraft.value.name.trim(),
        targetingType: createDraft.value.targetingType,
        dailyBudget: Number.isFinite(parsedBudget)
          ? parsedBudget.toFixed(2)
          : String(createDraft.value.dailyBudget),
        biddingStrategy: createDraft.value.biddingStrategy,
        startDate: createDraft.value.startDate,
        ...(createDraft.value.endDate ? { endDate: createDraft.value.endDate } : {}),
        enabled: createDraft.value.enabled,
      },
    )
    createOpen.value = false
    page.value = 1
    await syncUrl()
    await load()
  } catch (error) {
    const normalized = normalizeApiError(error)
    errorTitle.value = '广告活动创建失败'
    errorMessage.value = normalized.message
    errorStatus.value = normalized.status
    requestId.value = normalized.requestId
  } finally {
    creating.value = false
  }
}

function currentDateWindow(): Pick<CampaignListFilters, 'startDate' | 'endDate'> {
  const start = startDate.value || result.value?.meta.startDate || undefined
  const end = endDate.value || result.value?.meta.endDate || undefined
  return start && end ? { startDate: start, endDate: end } : {}
}

function isCampaignUpdating(campaignKey: string): boolean {
  return updatingCampaignKeys.value.has(campaignKey)
}

function replaceCampaignItem(campaignKey: string, item: CampaignOverviewItem): void {
  if (!result.value) return
  result.value = {
    ...result.value,
    items: result.value.items.map((current) =>
      current.campaignKey === campaignKey ? item : current,
    ),
  }
}

function optimisticEnabledItem(
  item: CampaignOverviewItem,
  enabled: boolean,
): CampaignOverviewItem {
  return {
    ...item,
    enabled,
    status: enabled ? 'DELIVERING' : 'PAUSED',
  }
}

async function toggleCampaignEnabled(item: CampaignOverviewItem): Promise<void> {
  if (!context.tenantId || !context.profileId) return
  if (isCampaignUpdating(item.campaignKey)) return
  const nextEnabled = !item.enabled
  const previousItem = item
  replaceCampaignItem(item.campaignKey, optimisticEnabledItem(item, nextEnabled))
  updatingCampaignKeys.value = new Set([
    ...updatingCampaignKeys.value,
    item.campaignKey,
  ])
  errorMessage.value = ''
  errorStatus.value = null
  requestId.value = null
  try {
    const response = await updateCampaignEnabled(
      context.tenantId,
      context.profileId,
      item.campaignKey,
      nextEnabled,
      currentDateWindow(),
    )
    replaceCampaignItem(item.campaignKey, response.item)
    void load(true)
  } catch (error) {
    const normalized = normalizeApiError(error)
    if (normalized.status === 503) {
      replaceCampaignItem(item.campaignKey, previousItem)
      errorTitle.value = '广告活动启停失败'
      errorMessage.value = '远程广告数据库暂不可用，请稍后重试'
      errorStatus.value = 503
      requestId.value = normalized.requestId
      return
    }
    replaceCampaignItem(item.campaignKey, previousItem)
    errorTitle.value = '广告活动启停失败'
    errorMessage.value = normalized.message
    errorStatus.value = normalized.status
    requestId.value = normalized.requestId
  } finally {
    const next = new Set(updatingCampaignKeys.value)
    next.delete(item.campaignKey)
    updatingCampaignKeys.value = next
  }
}

function toggleRowSelection(campaignKey: string, checked: boolean): void {
  const next = new Set(selectedCampaignKeys.value)
  if (checked) next.add(campaignKey)
  else next.delete(campaignKey)
  selectedCampaignKeys.value = next
}

function toggleVisibleSelection(checked: boolean): void {
  const next = new Set(selectedCampaignKeys.value)
  for (const item of rows.value) {
    if (checked) next.add(item.campaignKey)
    else next.delete(item.campaignKey)
  }
  selectedCampaignKeys.value = next
}

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

function percent(value: string | null, fractionDigits = 2): string {
  return value === null ? '—' : `${(Number(value) * 100).toFixed(fractionDigits)}%`
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
    FIXED: '固定竞价',
    DOWN_ONLY: '动态竞价 - 只降低',
    UP_AND_DOWN: '动态竞价 - 提高和降低',
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
    return number(value as number | null)
  }
  if (key === 'spend' || key === 'totalCost' || key === 'cpc') {
    return money(value as MoneyValue | null)
  }
  return percent(value as string | null)
}

function metricLabel(field: string): string {
  return metricMenuItems.find((item) => item.field === field)?.label ?? field
}

function decodeMetricFilters(value: string): MetricFilterRule[] {
  if (!value) return []
  return value.split(';').flatMap((encoded) => {
    const [field, operator, first, second] = encoded.split(':')
    if (!field || !['gte', 'lte', 'eq', 'between'].includes(operator) || !first) return []
    return [{
      field,
      operator: operator as MetricFilterRule['operator'],
      value: first,
      ...(second ? { value2: second } : {}),
    }]
  })
}

function encodeMetricFilter(rule: MetricFilterRule): string {
  return [rule.field, rule.operator, rule.value, rule.value2].filter(Boolean).join(':')
}

function isRatioMetric(field: string): boolean {
  return ['acos', 'ctr', 'cvr'].includes(field)
}

function metricFilterDisplayValue(field: string, value: string): string {
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) return value
  if (isRatioMetric(field)) return `${(numeric * 100).toFixed(2)}%`
  return new Intl.NumberFormat('zh-CN', { maximumFractionDigits: 4 }).format(numeric)
}

function metricFilterChipLabel(value: string): string {
  const [field, operator, first, second] = value.split(':')
  const operatorLabel = { gte: '≥', lte: '≤', eq: '=', between: '介于' }[operator] ?? operator
  const firstLabel = metricFilterDisplayValue(field, first)
  const secondLabel = second ? metricFilterDisplayValue(field, second) : ''
  return `${metricLabel(field)} ${operatorLabel} ${firstLabel}${secondLabel ? ` — ${secondLabel}` : ''}`
}

function openStatusFilter(): void {
  statusDraft.value = status.value
  filterOpen.value = false
  filterEditor.value = 'status'
}

function openMetricFilter(field: string): void {
  const existing = decodeMetricFilters(metricFilters.value).find((rule) => rule.field === field)
  metricDraftField.value = field
  metricDraftOperator.value = existing?.operator ?? 'gte'
  metricDraftValue.value = existing?.value ?? ''
  metricDraftValue2.value = existing?.value2 ?? ''
  filterOpen.value = false
  filterEditor.value = 'metric'
}

function closeFilterDialog(): void {
  filterEditor.value = null
}

function applyStatusFilter(): void {
  status.value = statusDraft.value
  if (status.value && status.value !== 'enabled') enabledMode.value = 'all'
  if (status.value === 'enabled') enabledMode.value = 'true'
  if (!status.value) enabledMode.value = 'all'
  closeFilterDialog()
  void applyFilters()
}

function applyMetricFilter(): void {
  if (!metricDraftValue.value) return
  const nextRule: MetricFilterRule = {
    field: metricDraftField.value,
    operator: metricDraftOperator.value,
    value: metricDraftValue.value,
    ...(metricDraftOperator.value === 'between' && metricDraftValue2.value
      ? { value2: metricDraftValue2.value }
      : {}),
  }
  const existing = decodeMetricFilters(metricFilters.value)
    .filter((rule) => rule.field !== metricDraftField.value)
  metricFilters.value = [...existing, nextRule].map(encodeMetricFilter).join(';')
  closeFilterDialog()
  void applyFilters()
}

function toggleFilterMenu(): void {
  filterOpen.value = !filterOpen.value
  if (filterOpen.value) filterEditor.value = null
}

function handleKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape' && filterEditor.value) closeFilterDialog()
}

function isoDate(value: Date): string {
  return value.toISOString().slice(0, 10)
}

function setDatePreset(days: number): void {
  const end = new Date(`${result.value?.meta.dataThroughDate ?? isoDate(new Date())}T00:00:00`)
  const start = new Date(end)
  start.setDate(end.getDate() - days + 1)
  startDate.value = isoDate(start)
  endDate.value = isoDate(end)
  dateOpen.value = false
  dateCustomOpen.value = false
  void applyFilters()
}

function showCustomDate(): void {
  dateCustomOpen.value = true
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
  window.addEventListener('keydown', handleKeydown)
  if (context.status === 'idle') await context.initialize()
  await load()
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleKeydown)
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
    <div v-if="selectedCount" class="campaign-selection-bar" role="status">
      已选择 {{ selectedCount }} 个广告活动
      <button type="button" @click="selectedCampaignKeys = new Set()">取消选择</button>
    </div>

    <div class="campaign-toolbar">
      <div class="campaign-toolbar-left">
        <button class="campaign-title-button" type="button" aria-label="广告活动视图">
          广告活动 <span aria-hidden="true">⌄</span>
        </button>
        <button class="campaign-create-button" type="button" @click="openCreateCampaign">
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
          class="campaign-filter-trigger"
          :class="{ active: filterOpen }"
          type="button"
          aria-controls="campaign-filter-panel"
          :aria-expanded="filterOpen"
          @click="toggleFilterMenu"
        >
          <span aria-hidden="true">⊟</span>
          <span class="sr-only">筛选广告活动</span>
        </button>
        <div v-if="filterOpen" id="campaign-filter-panel" class="campaign-filter-menu" role="menu">
          <button type="button" role="menuitem" @click="openStatusFilter">状态 <span>›</span></button>
          <button v-for="item in metricMenuItems" :key="item.field" type="button" role="menuitem" @click="openMetricFilter(item.field)">
            {{ item.label }} <span>›</span>
          </button>
        </div>
      </div>
      <div class="campaign-toolbar-right">
        <div class="campaign-date-control">
          <button class="campaign-date-label" type="button" :aria-expanded="dateOpen" @click="dateOpen = !dateOpen">
            <span aria-hidden="true">▦</span> {{ dateLabel }} <span aria-hidden="true">⌄</span>
          </button>
          <div v-if="dateOpen" class="campaign-date-menu">
            <button type="button" @click="setDatePreset(7)">最近 7 天</button>
            <button type="button" @click="setDatePreset(14)">最近 14 天</button>
            <button type="button" @click="setDatePreset(30)">最近 30 天</button>
            <button type="button" @click="showCustomDate">自定义日期</button>
            <div v-if="dateCustomOpen" class="campaign-date-custom">
              <label>开始日期<input v-model="startDate" type="date"></label>
              <label>结束日期<input v-model="endDate" type="date"></label>
              <button type="button" @click="dateOpen = false; applyFilters()">应用</button>
            </div>
          </div>
        </div>
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

    <div
      v-if="filterEditor"
      class="campaign-filter-backdrop"
      @click.self="closeFilterDialog"
    >
      <section
        class="campaign-filter-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="campaign-filter-dialog-title"
      >
        <header>
          <h2 id="campaign-filter-dialog-title">
            {{ filterEditor === 'status' ? '状态' : metricLabel(metricDraftField) }} — 筛选条件
          </h2>
          <button type="button" aria-label="关闭筛选条件" @click="closeFilterDialog">×</button>
        </header>

        <div class="campaign-filter-dialog-body">
          <template v-if="filterEditor === 'status'">
            <label>
              <span>状态</span>
              <select v-model="statusDraft" aria-label="状态筛选">
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
          </template>
          <template v-else>
            <label>
              <span>条件</span>
              <select v-model="metricDraftOperator" aria-label="筛选条件">
                <option value="gte">大于等于 (&gt;=)</option>
                <option value="lte">小于等于 (&lt;=)</option>
                <option value="eq">等于 (=)</option>
                <option value="between">介于</option>
              </select>
            </label>
            <label>
              <span>值</span>
              <input v-model="metricDraftValue" type="number" step="any" placeholder="请输入数值" aria-label="筛选数值">
            </label>
            <label v-if="metricDraftOperator === 'between'">
              <span>结束值</span>
              <input v-model="metricDraftValue2" type="number" step="any" placeholder="请输入结束数值" aria-label="筛选结束数值">
            </label>
            <p v-if="isRatioMetric(metricDraftField)" class="campaign-filter-hint">
              比例按小数输入，例如 25% 输入 0.25；服务端会在汇总后按公式重新计算。
            </p>
          </template>
        </div>

        <footer>
          <button class="campaign-dialog-cancel" type="button" @click="closeFilterDialog"><span style="color: #111a2e; font-size: 16px; font-family: Arial, 'Microsoft YaHei', sans-serif; line-height: 1.4;">取消</span></button>
          <button
            class="campaign-dialog-confirm"
            type="button"
            :disabled="filterEditor === 'metric' && (!metricDraftValue || (metricDraftOperator === 'between' && !metricDraftValue2))"
            @click="filterEditor === 'status' ? applyStatusFilter() : applyMetricFilter()"
          >
            确定
          </button>
        </footer>
      </section>
    </div>

    <div
      v-if="createOpen"
      class="campaign-filter-backdrop"
      @click.self="closeCreateCampaign"
    >
      <section
        class="campaign-filter-dialog campaign-create-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="campaign-create-dialog-title"
      >
        <header>
          <h2 id="campaign-create-dialog-title">创建广告活动</h2>
          <button type="button" aria-label="关闭创建广告活动" @click="closeCreateCampaign">×</button>
        </header>

        <div class="campaign-filter-dialog-body campaign-create-body">
          <label>
            <span>广告活动名称</span>
            <input v-model="createDraft.name" type="text" maxlength="255" aria-label="广告活动名称">
          </label>
          <label>
            <span>投放类型</span>
            <select v-model="createDraft.targetingType" aria-label="投放类型">
              <option value="MANUAL">手动投放</option>
              <option value="AUTO">自动投放</option>
            </select>
          </label>
          <label>
            <span>每日预算</span>
            <input v-model="createDraft.dailyBudget" type="number" min="0.01" step="0.01" aria-label="每日预算">
          </label>
          <label>
            <span>竞价策略</span>
            <select v-model="createDraft.biddingStrategy" aria-label="竞价策略">
              <option value="down_only">动态竞价 - 只降低</option>
              <option value="up_and_down">动态竞价 - 提高和降低</option>
              <option value="fixed_bids">固定竞价</option>
            </select>
          </label>
          <label>
            <span>开始日期</span>
            <input v-model="createDraft.startDate" type="date" aria-label="创建开始日期">
          </label>
          <label>
            <span>结束日期</span>
            <input v-model="createDraft.endDate" type="date" aria-label="创建结束日期">
          </label>
          <label class="campaign-create-toggle">
            <input v-model="createDraft.enabled" type="checkbox">
            <span>创建后启用</span>
          </label>
        </div>

        <footer>
          <button class="campaign-dialog-cancel" type="button" :disabled="creating" @click="closeCreateCampaign"><span style="color: #111a2e; font-size: 16px; font-family: Arial, 'Microsoft YaHei', sans-serif; line-height: 1.4;">取消</span></button>
          <button
            class="campaign-dialog-confirm"
            type="button"
            :disabled="creating || !createDraft.name.trim() || !createDraft.startDate || Number(createDraft.dailyBudget) <= 0"
            @click="submitCreateCampaign"
          >
            {{ creating ? '创建中…' : '创建' }}
          </button>
        </footer>
      </section>
    </div>

    <p v-if="dateError" class="campaign-date-error" role="alert">{{ dateError }}</p>

    <div v-if="!context.isComplete" class="campaign-state campaign-context-state">
      <strong>请先选择广告数据范围</strong>
      <span>需要完成 Tenant、AmazonStore、Marketplace 和 AdvertisingProfile 选择。</span>
      <RouterLink to="/context">前往卖家空间</RouterLink>
    </div>

    <div v-else class="campaign-table-shell" :aria-busy="loading || refreshing">
      <div v-if="refreshing" class="campaign-refresh-mask" role="status">正在刷新…</div>
      <div class="campaign-table" role="table" aria-label="广告活动表现">
        <div class="campaign-grid campaign-header" role="row">
          <div role="columnheader">
            <input
              type="checkbox"
              aria-label="选择全部广告活动"
              :checked="allVisibleSelected"
              @change="toggleVisibleSelection(($event.target as HTMLInputElement).checked)"
            >
          </div>
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
          <strong>{{ errorStatus === 403 ? '没有查看此数据的权限' : errorTitle }}</strong>
          <span>{{ errorMessage }}</span>
          <small v-if="requestId">requestId：{{ requestId }}</small>
          <button type="button" @click="load">重试</button>
        </div>

        <div v-else-if="rows.length === 0" class="campaign-state campaign-empty-state">
          暂无数据
        </div>

        <template v-else>
          <div v-for="item in rows" :key="item.campaignKey" class="campaign-grid campaign-row" role="row">
            <div role="cell">
              <input
                type="checkbox"
                :checked="selectedCampaignKeys.has(item.campaignKey)"
                :aria-label="`选择 ${item.name}`"
                @change="toggleRowSelection(item.campaignKey, ($event.target as HTMLInputElement).checked)"
              >
            </div>
            <div role="cell">
              <button
                class="campaign-switch"
                :class="{ on: item.enabled, updating: isCampaignUpdating(item.campaignKey) }"
                type="button"
                role="switch"
                :aria-checked="item.enabled"
                :aria-disabled="isCampaignUpdating(item.campaignKey)"
                :title="item.enabled ? '暂停广告活动' : '启用广告活动'"
                :aria-label="`${item.name}：${item.enabled ? '暂停' : '启用'}`"
                @click="toggleCampaignEnabled(item)"
              >
                <i />
              </button>
            </div>
            <div class="campaign-name-cell" role="cell">
              <RouterLink
                :to="{
                  name: 'advertising-campaign-detail',
                  params: { campaignKey: item.campaignKey },
                  query: {
                    startDate: startDate || result?.meta.startDate,
                    endDate: endDate || result?.meta.endDate,
                  },
                }"
              >
                <b aria-hidden="true">⌄</b>{{ item.name || '—' }}
              </RouterLink>
              <small>{{ item.campaignCode || '—' }}</small>
            </div>
            <div role="cell">{{ targetingTypeLabel(item.targetingType) }}</div>
            <div role="cell"><span class="campaign-status" :class="item.status.toLowerCase()">{{ statusLabel(item.status) }}</span></div>
            <div role="cell">{{ biddingLabel(item.biddingStrategy) }}</div>
            <div role="cell">{{ dateValue(item.startDate) }}</div>
            <div role="cell">{{ dateValue(item.endDate, '无结束日期') }}</div>
            <div class="numeric" role="cell">{{ money(item.dailyBudget) }}</div>
            <div class="numeric" role="cell">{{ number(item.metrics.impressions) }}</div>
            <div class="numeric" role="cell">{{ percent(item.metrics.topOfSearchShare, 0) }}</div>
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
.campaign-selection-bar,
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

.campaign-toolbar-left {
  position: relative;
}

.campaign-title-button,
.campaign-create-button,
.campaign-ghost-button,
.campaign-filter-trigger,
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

.campaign-filter-trigger {
  width: 32px;
  padding: 0;
  border-color: #14233c;
  color: #18365f;
  font-size: 18px;
  line-height: 1;
}

.campaign-filter-trigger.active {
  color: #fff;
  background: #17345c;
}

.campaign-filter-menu,
.campaign-date-menu {
  position: absolute;
  z-index: 12;
  border: 1px solid #dfe3eb;
  border-radius: 5px;
  background: #fff;
  box-shadow: 0 12px 28px rgba(22, 34, 56, 0.18);
}

.campaign-filter-menu {
  top: 38px;
  left: 251px;
  width: 178px;
  padding: 7px 0;
}

.campaign-filter-menu button {
  width: 100%;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border: 0;
  padding: 0 17px;
  color: #0d203d;
  background: #fff;
  font: inherit;
  font-size: 13px;
  text-align: left;
  cursor: pointer;
}

.campaign-filter-menu button:hover {
  background: #f4f7fc;
}

.campaign-filter-menu button span {
  color: #7390be;
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
  background: #fff;
  white-space: nowrap;
  font: inherit;
  cursor: pointer;
}

.campaign-toolbar .campaign-date-label {
  color: #17345c;
  background: #fff;
}

.campaign-date-control {
  position: relative;
}

.campaign-date-menu {
  top: 38px;
  right: 0;
  width: 238px;
  padding: 7px;
}

.campaign-date-menu > button {
  width: 100%;
  height: 34px;
  border: 0;
  border-radius: 3px;
  padding: 0 10px;
  color: #172945;
  background: #fff;
  font: inherit;
  text-align: left;
}

.campaign-date-menu > button:hover {
  background: #f3f6fb;
}

.campaign-date-custom {
  display: grid;
  gap: 8px;
  padding: 10px;
  border-top: 1px solid #e6eaf0;
}

.campaign-date-custom label {
  display: grid;
  gap: 4px;
  color: #637089;
}

.campaign-date-custom input,
.campaign-date-custom button {
  height: 31px;
  border: 1px solid #cbd3df;
  border-radius: 3px;
  padding: 0 7px;
  font: inherit;
}

.campaign-date-custom button {
  color: #fff;
  background: #17345c;
}

.campaign-filter-chips {
  min-height: 42px;
  flex-wrap: wrap;
  gap: 6px;
  padding: 6px 12px;
  border-bottom: 1px solid #e0e2e5;
  background: #fafbfb;
}

.campaign-selection-bar {
  min-height: 34px;
  justify-content: space-between;
  gap: 12px;
  padding: 6px 12px;
  border-bottom: 1px solid #d5eadf;
  color: #1f5137;
  background: #f0faf5;
  font-weight: 600;
}

.campaign-selection-bar button {
  border: 1px solid #9dc9b2;
  border-radius: 3px;
  padding: 4px 8px;
  color: #1f5137;
  background: #fff;
  font: inherit;
  font-weight: 600;
  cursor: pointer;
}

.campaign-filter-backdrop {
  position: fixed;
  inset: 0;
  z-index: 100;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgba(20, 28, 43, 0.44);
}

.campaign-filter-dialog {
  width: min(630px, calc(100vw - 48px));
  overflow: hidden;
  border-radius: 16px;
  color: #111a2e;
  background: #fff;
  box-shadow: 0 24px 64px rgba(15, 23, 42, 0.28);
  font-size: 16px;
}

.campaign-filter-dialog header {
  min-height: 84px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px 0 36px;
  border-bottom: 1px solid #d9dee7;
}

.campaign-filter-dialog h2 {
  margin: 0;
  font-size: 26px;
  line-height: 1.25;
}

.campaign-filter-dialog header button {
  width: 44px;
  height: 44px;
  border: 0;
  color: #91a0b7;
  background: transparent;
  font: inherit;
  font-size: 42px;
  font-weight: 200;
  line-height: 38px;
  cursor: pointer;
}

.campaign-filter-dialog-body {
  display: grid;
  gap: 18px;
  padding: 24px;
}

.campaign-filter-dialog-body label {
  display: grid;
  gap: 8px;
  color: #536078;
}

.campaign-filter-dialog-body select,
.campaign-filter-dialog-body input {
  width: 100%;
  height: 50px;
  border: 1px solid #d4dae4;
  border-radius: 9px;
  padding: 0 16px;
  color: #111827;
  background: #fff;
  font: inherit;
}

.campaign-filter-dialog-body select:focus,
.campaign-filter-dialog-body input:focus {
  border-color: #496c9d;
  outline: 0;
  box-shadow: 0 0 0 3px rgba(48, 86, 139, 0.12);
}

.campaign-filter-hint {
  margin: -4px 0 0;
  color: #6b7587;
  font-size: 13px;
}

.campaign-filter-dialog footer {
  min-height: 82px;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  padding: 0 36px;
  border-top: 1px solid #d9dee7;
}

.campaign-filter-dialog footer button {
  min-width: 86px;
  height: 48px;
  border: 1px solid #d5dae3;
  border-radius: 9px;
  padding: 0 20px;
  color: #111a2e !important;
  background: #fff;
  font-size: 16px !important;
  font-family: Arial, "Microsoft YaHei", sans-serif !important;
  line-height: 1.4 !important;
  cursor: pointer;
}

.campaign-filter-dialog footer .campaign-dialog-confirm {
  border-color: #111a2e;
  color: #fff;
  background: #111a2e;
}

.campaign-filter-dialog footer .campaign-dialog-confirm:disabled {
  cursor: not-allowed;
  opacity: 0.48;
}

.campaign-chip {
  display: inline-flex;
  min-height: 26px;
  align-items: center;
  gap: 6px;
  border: 1px solid #cfd5d1;
  border-radius: 3px;
  padding: 2px 4px 2px 9px;
  border-color: #b9d1f5;
  color: #1260d7;
  background: #e7f1ff;
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
  padding: 8px 12px;
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

.campaign-row > div:nth-child(2) {
  position: relative;
  z-index: 4;
  justify-content: center;
  overflow: visible;
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

.campaign-name-cell a,
.campaign-name-cell small {
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.campaign-name-cell a {
  color: #1465f5;
  font-weight: 600;
  text-decoration: none;
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
  z-index: 5;
  display: inline-block;
  width: 34px;
  height: 18px;
  border-radius: 9px;
  border: 0;
  padding: 0;
  background: #bfc4c7;
  opacity: 1;
  cursor: pointer;
  pointer-events: auto;
  touch-action: manipulation;
  user-select: none;
}

.campaign-switch.updating {
  cursor: progress;
  opacity: 0.72;
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
  pointer-events: none;
}

.campaign-switch.on {
  background: #2671f5;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
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
