import { httpClient } from '@/shared/api/httpClient'
import type { ApiEnvelope } from '@/shared/api/types'

export interface Recommendation {
  id: string
  actionType: string
  objectType: string
  objectId: string
  beforeValue: Record<string, unknown>
  afterValue: Record<string, unknown>
  reason: string
  evidence: Array<Record<string, unknown>>
  riskLevel: 'LOW' | 'MEDIUM' | 'HIGH'
}

export interface AnalysisTask {
  taskId: string
  status: 'QUEUED' | 'RUNNING' | 'SUCCEEDED' | 'FAILED'
  result: Record<string, unknown>
  error: string
  runs: Array<{
    agentCode: string
    status: string
    output: Record<string, unknown>
  }>
}

export interface AnalysisTaskSummary {
  taskId: string
  status: AnalysisTask['status']
  error: string
  createdAt: string
  completedAt: string | null
}

async function fetchAnalysis(taskId: string): Promise<AnalysisTask> {
  const response = await httpClient.get<ApiEnvelope<AnalysisTask>>(
    `/api/v1/analysis/tasks/${taskId}`,
  )
  return response.data.data
}

export async function runAnalysis(
  tenantId: string,
  profileId: string,
): Promise<AnalysisTask> {
  const created = await httpClient.post<
    ApiEnvelope<{ taskId: string; status: string }>
  >(
    '/api/v1/analysis/tasks',
    { tenantId, profileId },
    { headers: { 'Idempotency-Key': crypto.randomUUID() } },
  )
  let task = await fetchAnalysis(created.data.data.taskId)
  for (let attempt = 0; attempt < 15 && ['QUEUED', 'RUNNING'].includes(task.status); attempt += 1) {
    await new Promise((resolve) => globalThis.setTimeout(resolve, 500))
    task = await fetchAnalysis(created.data.data.taskId)
  }
  return task
}

export async function fetchAnalysisTasks(
  profileId: string,
): Promise<AnalysisTaskSummary[]> {
  const response = await httpClient.get<
    ApiEnvelope<{ items: AnalysisTaskSummary[] }>
  >('/api/v1/analysis/tasks', { params: { profileId } })
  return response.data.data.items
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
    ApiEnvelope<{ previewId: string; status: string }>
  >(
    `/api/v1/actions/tenants/${input.tenantId}/profiles/${input.profileId}/previews`,
    {
      recommendationIds: input.recommendationIds,
    },
    { headers: { 'Idempotency-Key': crypto.randomUUID() } },
  )
  const submitted = await submitExistingPreview(input.tenantId, created.data.data.previewId)
  return submitted
}

export async function submitExistingPreview(
  tenantId: string,
  previewId: string,
): Promise<{ previewId: string; status: string }> {
  const submitted = await httpClient.post<
    ApiEnvelope<{ previewId: string; status: string }>
  >(`/api/v1/actions/tenants/${tenantId}/previews/${previewId}/submit`)
  return {
    previewId: submitted.data.data.previewId,
    status: submitted.data.data.status,
  }
}

export async function decidePreview(
  tenantId: string,
  previewId: string,
  decision: 'APPROVED' | 'REJECTED' | 'RETURNED',
  comment: string,
): Promise<{ previewId: string; status: string }> {
  const response = await httpClient.post<
    ApiEnvelope<{ previewId: string; status: string }>
  >(
    `/api/v1/actions/tenants/${tenantId}/previews/${previewId}/decision`,
    { decision, comment, idempotencyKey: crypto.randomUUID() },
  )
  return {
    previewId: response.data.data.previewId,
    status: response.data.data.status,
  }
}
