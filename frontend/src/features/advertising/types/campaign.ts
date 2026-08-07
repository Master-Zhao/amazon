export interface MoneyValue {
  amount: string
  currencyCode: string
}

export interface CampaignMetrics {
  impressions: number | null
  topOfSearchShare: string | null
  spend: MoneyValue | null
  sales: MoneyValue | null
  clicks: number | null
  ctr: string | null
  totalCost: MoneyValue | null
  orders: number | null
  cpc: MoneyValue | null
  acos: string | null
  cvr: string | null
}

export interface CampaignOverviewItem {
  campaignKey: string
  name: string
  campaignCode: string
  enabled: boolean
  targetingType: 'AUTO' | 'MANUAL' | 'UNKNOWN'
  status:
    | 'DELIVERING'
    | 'PAUSED'
    | 'ARCHIVED'
    | 'ENDED'
    | 'REVIEWING'
    | 'REJECTED'
    | 'UNKNOWN'
  biddingStrategy: string
  startDate: string | null
  endDate: string | null
  dailyBudget: MoneyValue | null
  metrics: CampaignMetrics
  metadataMatched: boolean
  hasMetrics: boolean
  partialFields: string[]
}

export interface CampaignPagination {
  page: number
  pageSize: number
  total: number
  totalPages: number
}

export interface CampaignOverviewMeta {
  source: 'REMOTE_MYSQL_COMPOSITE'
  currencyCode: string
  timezone: string
  startDate: string | null
  endDate: string | null
  dataThroughDate: string | null
  historyThroughDate: string | null
  realtimeThroughDate: string | null
  realtimeAsOf: string | null
  deduplicationVersion: string
  fieldMappings: Record<string, string>
  totalCostSemantics: 'SPEND_ALIAS'
  attributionSemantics: 'REMOTE_FIELDS_UNVERIFIED'
  statusFilterSemantics: 'SCM_CURRENT_STATE_WITH_FACT_FALLBACK'
}

export interface CampaignListResponse {
  items: CampaignOverviewItem[]
  summary: CampaignMetrics | null
  dashboard: CampaignDashboard
  pagination: CampaignPagination
  meta: CampaignOverviewMeta
}

export type CampaignRiskLevel = 'VERY_HIGH' | 'HIGH' | 'MEDIUM' | 'LOW' | 'VERY_LOW'

export interface CampaignTrendPoint {
  date: string
  metrics: CampaignMetrics
}

export interface CampaignDashboard {
  trend: CampaignTrendPoint[]
  riskLevels: Array<{ level: CampaignRiskLevel; count: number }>
  evaluatedCampaigns: number
  targetAcos: string | null
  unavailableRuleCodes: string[]
  riskSemantics: 'SYSTEM_RULES_AGGREGATED'
}

export interface CampaignListFilters {
  startDate?: string
  endDate?: string
  enabled?: boolean
  status?: string
  targetingType?: 'AUTO' | 'MANUAL'
  search?: string
  metricFilters?: string
  ordering?: string
  page: number
  pageSize: number
  includeSummary?: boolean
}

export interface CampaignDetailResponse {
  item: CampaignOverviewItem
  trend: CampaignTrendPoint[]
  meta: CampaignOverviewMeta
}

export interface CampaignEnabledUpdateResponse {
  item: CampaignOverviewItem
}

export interface CampaignCreatePayload {
  name: string
  targetingType: 'AUTO' | 'MANUAL'
  dailyBudget: string
  biddingStrategy: 'up_and_down' | 'down_only' | 'fixed_bids'
  startDate: string
  endDate?: string | null
  enabled: boolean
}

export interface CampaignCreateResponse {
  item: CampaignOverviewItem
}
