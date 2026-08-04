export interface MoneyValue {
  amount: string
  currencyCode: string
}

export interface CampaignMetrics {
  impressions: number
  topOfSearchShare: string | null
  spend: MoneyValue
  sales: MoneyValue
  clicks: number
  ctr: string | null
  totalCost: MoneyValue
  orders: number
  cpc: MoneyValue | null
  acos: string | null
  cvr: string | null
}

export interface CampaignOverviewItem {
  campaignKey: string
  name: string
  referenceCode: string
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
  partialFields: string[]
}

export interface CampaignPagination {
  page: number
  pageSize: number
  total: number
  totalPages: number
}

export interface CampaignOverviewMeta {
  source: 'REMOTE_MYSQL'
  currencyCode: string
  timezone: string
  startDate: string | null
  endDate: string | null
  dataThroughDate: string | null
  totalCostSemantics: 'SPEND_ALIAS'
  attributionSemantics: 'REMOTE_FIELDS_UNVERIFIED'
  statusFilterSemantics: 'ANALYSIS_FILTER_SCM_DISPLAY'
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
  ordering?: string
  page: number
  pageSize: number
  includeSummary?: boolean
}
