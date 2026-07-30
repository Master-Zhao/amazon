import { httpClient } from '@/shared/api/httpClient'
import type { ApiEnvelope } from '@/shared/api/types'

export interface FormulaValue {
  value: string | null
  reason: string | null
}

export interface CampaignAnomaly {
  id: string
  ruleCode: string
  ruleVersion: number
  status: 'NORMAL' | 'ANOMALY' | 'INSUFFICIENT_DATA'
  riskLevel: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL' | null
  observedValue: string | null
  thresholdValue: string | null
  reasonCode: string
  explanation: string
}

export interface CampaignMetricRow {
  id: string
  campaignId: string
  externalCampaignId: string
  campaignName: string
  reportDate: string
  currencyCode: string
  impressions: number
  clicks: number
  spend: string
  orders: number
  sales: string
  calculationReasons: Record<string, string>
  dailyBudgetSnapshot: string | null
  snapshotHourLocal: number | null
  stateSnapshot: string
  targetAcos: string | null
  ctr: FormulaValue
  cpc: FormulaValue
  cvr: FormulaValue
  acos: FormulaValue
  roas: FormulaValue
  sourceBatchId: string
  anomalies: CampaignAnomaly[]
}

export interface RemoteCampaignMetricRow {
  id: string
  externalCampaignId: string
  campaignName: string
  reportDate: string
  currencyCode: string
  impressions: number
  clicks: number
  spend: string
  orders: number
  sales: string
  dailyBudget: string | null
  state: string
  ctr: FormulaValue
  cpc: FormulaValue
  cvr: FormulaValue
  acos: FormulaValue
  roas: FormulaValue
  scmMatched: boolean
  sourceSystem: 'REMOTE_MYSQL'
}

export interface CampaignDetail {
  campaignId: string
  externalCampaignId: string
  campaignName: string
  state: string
  targetAcos: string | null
  metrics: CampaignMetricRow[]
}

export interface CampaignTargetAcos {
  campaignId: string
  campaignName: string
  targetAcos: string | null
  effectiveTargetAcos: string | null
}

export interface AnomalyRuleVersion {
  id: string
  code: string
  version: number
  scopeKey: string
  configuration: Record<string, string | number>
  createdAt: string
}

export interface AnalyticsConfiguration {
  tenantTargetAcos: string | null
  profileTargetAcos: string | null
  campaigns: CampaignTargetAcos[]
  rules: AnomalyRuleVersion[]
}

export interface TargetingMetricRow {
  id: string
  campaignId: string
  campaignName: string
  adGroupId: string
  adGroupName: string
  targetType: 'KEYWORD' | 'PRODUCT_TARGET'
  targetId: string
  targetText: string
  matchType: 'BROAD' | 'PHRASE' | 'EXACT' | null
  reportDate: string
  currencyCode: string
  impressions: number
  clicks: number
  spend: string
  orders: number
  sales: string
  calculationReasons: Record<string, string>
  bidSnapshot: string | null
  stateSnapshot: string
  ctr: FormulaValue
  cpc: FormulaValue
  cvr: FormulaValue
  acos: FormulaValue
  roas: FormulaValue
  sourceBatchId: string
}

export interface SearchTermMetricRow {
  id: string
  campaignId: string
  campaignName: string
  adGroupId: string
  adGroupName: string
  searchTermId: string
  searchTerm: string
  targetingExpression: string
  reportDate: string
  currencyCode: string
  impressions: number
  clicks: number
  spend: string
  orders: number
  sales: string
  calculationReasons: Record<string, string>
  ctr: FormulaValue
  cpc: FormulaValue
  cvr: FormulaValue
  acos: FormulaValue
  roas: FormulaValue
  sourceBatchId: string
}

export interface DashboardRow {
  marketplaceCode: string
  marketplaceName: string
  currencyCode: string
  campaignCount: number
  impressions: number
  clicks: number
  spend: string
  orders: number
  sales: string
  ctr: FormulaValue
  cpc: FormulaValue
  cvr: FormulaValue
  acos: FormulaValue
  roas: FormulaValue
  anomalyCount: number
  authoritativeGrain: 'CAMPAIGN_DAILY_METRIC'
}

async function data<T>(request: Promise<{ data: ApiEnvelope<T> }>): Promise<T> {
  return (await request).data.data
}

export function fetchCampaignMetrics(
  tenantId: string,
  profileId: string,
  filters: { startDate?: string; endDate?: string } = {},
): Promise<CampaignMetricRow[]> {
  return data(
    httpClient.get(
      `/api/v1/analytics/tenants/${tenantId}/profiles/${profileId}/campaigns`,
      { params: filters },
    ),
  )
}

export function fetchRemoteCampaignMetrics(
  tenantId: string,
  profileId: string,
  filters: { startDate?: string; endDate?: string } = {},
): Promise<RemoteCampaignMetricRow[]> {
  return data(
    httpClient.get(
      `/api/v1/analytics/tenants/${tenantId}/profiles/${profileId}/remote-campaigns`,
      { params: filters },
    ),
  )
}

export function fetchCampaignDetail(
  tenantId: string,
  profileId: string,
  campaignId: string,
  filters: { startDate?: string; endDate?: string } = {},
): Promise<CampaignDetail> {
  return data(
    httpClient.get(
      `/api/v1/analytics/tenants/${tenantId}/profiles/${profileId}/campaigns/${campaignId}`,
      { params: filters },
    ),
  )
}

export function fetchAnalyticsConfiguration(
  tenantId: string,
  profileId: string,
): Promise<AnalyticsConfiguration> {
  return data(
    httpClient.get(
      `/api/v1/analytics/tenants/${tenantId}/profiles/${profileId}/configuration`,
    ),
  )
}

export function updateTargetAcos(
  tenantId: string,
  profileId: string,
  payload: {
    scopeType: 'TENANT' | 'PROFILE' | 'CAMPAIGN'
    campaignId?: string
    targetAcos: string | null
  },
): Promise<AnalyticsConfiguration> {
  return data(
    httpClient.put(
      `/api/v1/analytics/tenants/${tenantId}/profiles/${profileId}/configuration/target-acos`,
      payload,
    ),
  )
}

export function createAnomalyRuleVersion(
  tenantId: string,
  profileId: string,
  payload: {
    code: string
    scopeType: 'TENANT' | 'PROFILE' | 'CAMPAIGN'
    campaignId?: string
    configuration: Record<string, string | number>
  },
): Promise<AnomalyRuleVersion> {
  return data(
    httpClient.post(
      `/api/v1/analytics/tenants/${tenantId}/profiles/${profileId}/configuration/rules`,
      payload,
    ),
  )
}

export function fetchDashboard(
  tenantId: string,
  profileId: string,
  filters: { startDate?: string; endDate?: string } = {},
): Promise<DashboardRow[]> {
  return data(
    httpClient.get(
      `/api/v1/analytics/tenants/${tenantId}/profiles/${profileId}/dashboard`,
      { params: filters },
    ),
  )
}

export function fetchTargetingMetrics(
  tenantId: string,
  profileId: string,
  filters: { startDate?: string; endDate?: string } = {},
): Promise<TargetingMetricRow[]> {
  return data(
    httpClient.get(
      `/api/v1/analytics/tenants/${tenantId}/profiles/${profileId}/targeting`,
      { params: filters },
    ),
  )
}

export function fetchSearchTermMetrics(
  tenantId: string,
  profileId: string,
  filters: { startDate?: string; endDate?: string } = {},
): Promise<SearchTermMetricRow[]> {
  return data(
    httpClient.get(
      `/api/v1/analytics/tenants/${tenantId}/profiles/${profileId}/search-terms`,
      { params: filters },
    ),
  )
}
