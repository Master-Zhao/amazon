import { httpClient } from '@/shared/api/httpClient'
import type { ApiEnvelope } from '@/shared/api/types'

export interface DashboardData {
  currency: string
  totals: {
    impressions: number
    clicks: number
    spend: string
    orders: number
    sales: string
    ctr: string | null
    cpc: string | null
    cvr: string | null
    acos: string | null
    roas: string | null
  }
  series: Array<{
    date: string
    campaignId: string
    campaignName: string
    spend: string
    sales: string
    acos: string | null
    budgetSnapshot: string | null
    stateSnapshot: string
    anomalies: Array<{ status: string; riskLevel: string }>
  }>
}

export async function fetchDashboard(profileId: string): Promise<DashboardData> {
  const response = await httpClient.get<ApiEnvelope<DashboardData>>(
    '/api/v1/analytics/dashboard',
    { params: { profileId } },
  )
  return response.data.data
}

export async function fetchAnalyticsList(
  path: string,
  profileId: string,
): Promise<{ currency: string; items: Array<Record<string, unknown>> }> {
  const response = await httpClient.get<
    ApiEnvelope<{ currency: string; items: Array<Record<string, unknown>> }>
  >(path, { params: { profileId } })
  return response.data.data
}

