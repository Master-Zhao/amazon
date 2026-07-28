import { httpClient } from '@/shared/api/httpClient'
import type { ApiEnvelope } from '@/shared/api/types'

export interface Recommendation {
  id: string
  action_type: string
  object_type: string
  object_id: string
  before_value: Record<string, unknown>
  after_value: Record<string, unknown>
  reason: string
  evidence: Array<Record<string, unknown>>
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH'
}

export interface AnalysisTask {
  task_id: string
  status: 'QUEUED' | 'RUNNING' | 'SUCCEEDED' | 'FAILED'
  result: Record<string, unknown>
  error: string
  runs: Array<{
    agent_code: string
    status: string
    output: Record<string, unknown>
  }>
}

export async function runAnalysis(
  tenantId: string,
  profileId: string,
): Promise<AnalysisTask> {
  const created = await httpClient.post<
    ApiEnvelope<{ task_id: string; status: string }>
  >(
    '/api/v1/analysis/tasks',
    { tenantId, profileId },
    { headers: { 'Idempotency-Key': crypto.randomUUID() } },
  )
  const response = await httpClient.get<ApiEnvelope<AnalysisTask>>(
    `/api/v1/analysis/tasks/${created.data.data.task_id}`,
  )
  return response.data.data
}

export async function fetchRecommendations(
  profileId: string,
): Promise<Recommendation[]> {
  const response = await httpClient.get<
    ApiEnvelope<{ items: Recommendation[] }>
  >('/api/v1/recommendations/', { params: { profileId } })
  return response.data.data.items
}

export async function createAndSubmitPreview(input: {
  tenantId: string
  profileId: string
  recommendationIds: string[]
}): Promise<{ previewId: string; status: string }> {
  const created = await httpClient.post<
    ApiEnvelope<{ preview_id: string; status: string }>
  >('/api/v1/actions/previews', {
    tenantId: input.tenantId,
    profileId: input.profileId,
    recommendationIds: input.recommendationIds,
  })
  const submitted = await httpClient.post<
    ApiEnvelope<{ preview_id: string; status: string }>
  >(`/api/v1/actions/previews/${created.data.data.preview_id}/submit`)
  return {
    previewId: submitted.data.data.preview_id,
    status: submitted.data.data.status,
  }
}

export async function decidePreview(
  previewId: string,
  decision: 'APPROVED' | 'REJECTED' | 'RETURNED',
  comment: string,
): Promise<{ previewId: string; status: string }> {
  const response = await httpClient.post<
    ApiEnvelope<{ preview_id: string; status: string }>
  >(
    `/api/v1/actions/previews/${previewId}/decisions`,
    { decision, comment },
    { headers: { 'Idempotency-Key': crypto.randomUUID() } },
  )
  return {
    previewId: response.data.data.preview_id,
    status: response.data.data.status,
  }
}
