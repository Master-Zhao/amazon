import { httpClient } from '@/shared/api/httpClient'
import type { ApiEnvelope } from '@/shared/api/types'

export interface AgentRun {
  id: string
  agentCode: string
  status: 'QUEUED' | 'RUNNING' | 'SUCCEEDED' | 'FAILED' | 'CANCELLED'
  schemaVersion: string
  celeryTaskId: string
  outputResult: Record<string, unknown>
  errorCode: string
  errorMessage: string
  createdAt: string
  startedAt: string | null
  finishedAt: string | null
}

export interface RecommendationRevision {
  id: string
  revisionNumber: number
  schemaVersion: string
  actionType: string
  objectType: string
  objectId: string
  beforeValue: Record<string, string>
  afterValue: Record<string, string>
  reason: string
  evidence: Array<Record<string, unknown>>
  riskLevel: string
  createdAt: string
}

export interface Recommendation {
  id: string
  status: string
  actionType: string
  campaignName: string
  externalCampaignId: string
  agentRunId: string
  currentRevisionNumber: number
  currentRevision: RecommendationRevision
  createdAt: string
}

async function data<T>(request: Promise<{ data: ApiEnvelope<T> }>): Promise<T> {
  return (await request).data.data
}

export function fetchAgentRuns(
  tenantId: string,
  profileId: string,
): Promise<AgentRun[]> {
  return data(
    httpClient.get(
      `/api/v1/analysis/tenants/${tenantId}/profiles/${profileId}/runs`,
    ),
  )
}

export function createAgentRun(
  tenantId: string,
  profileId: string,
): Promise<AgentRun> {
  return data(
    httpClient.post(
      `/api/v1/analysis/tenants/${tenantId}/profiles/${profileId}/runs`,
    ),
  )
}

export function cancelAgentRun(
  tenantId: string,
  runId: string,
): Promise<AgentRun> {
  return data(
    httpClient.post(
      `/api/v1/analysis/tenants/${tenantId}/runs/${runId}/cancel`,
    ),
  )
}

export function fetchRecommendations(
  tenantId: string,
  profileId: string,
): Promise<Recommendation[]> {
  return data(
    httpClient.get(
      `/api/v1/recommendations/tenants/${tenantId}/profiles/${profileId}`,
    ),
  )
}

export function acceptRecommendation(
  tenantId: string,
  recommendationId: string,
): Promise<Recommendation> {
  return data(
    httpClient.post(
      `/api/v1/recommendations/tenants/${tenantId}/${recommendationId}/accept`,
    ),
  )
}

export function reviseRecommendation(
  tenantId: string,
  recommendationId: string,
  revision: {
    afterValue: Record<string, string>
    reason: string
    evidence: Array<Record<string, unknown>>
    riskLevel: 'LOW' | 'MEDIUM' | 'HIGH'
  },
): Promise<Recommendation> {
  return data(
    httpClient.post(
      `/api/v1/recommendations/tenants/${tenantId}/${recommendationId}/revisions`,
      revision,
    ),
  )
}

export function dismissRecommendation(
  tenantId: string,
  recommendationId: string,
  reason: string,
): Promise<Recommendation> {
  return data(
    httpClient.post(
      `/api/v1/recommendations/tenants/${tenantId}/${recommendationId}/dismiss`,
      { reason },
    ),
  )
}
