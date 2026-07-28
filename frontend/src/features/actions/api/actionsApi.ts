import { httpClient } from '@/shared/api/httpClient'
import type { ApiEnvelope } from '@/shared/api/types'

export interface ActionPreviewVersion {
  id: string
  versionNumber: number
  actionPayload: {
    schemaVersion: string
    actionType: string
    objectType: string
    objectId: string
    beforeValue: Record<string, string>
    afterValue: Record<string, string>
    reason: string
    evidence: Array<Record<string, unknown>>
    riskLevel: string
  }
  objectStateVersion: string
  createdAt: string
}

export interface ApprovalRecord {
  id: string
  decision: 'APPROVED' | 'REJECTED' | 'RETURNED'
  comment: string
  decidedByEmail: string
  createdAt: string
}

export interface ExecutionRecord {
  id: string
  outcome: 'SUCCEEDED' | 'SUCCESS' | 'FAILED' | 'SKIPPED'
  actualValue: Record<string, string>
  executedAt: string
  note: string
  evidenceMetadata: Record<string, unknown>
  effectEvaluations: EffectEvaluation[]
  recordedByEmail: string
  createdAt: string
}

export interface EffectEvaluation {
  id: string
  status: string
  baselineStart: string
  baselineEnd: string
  observationStart: string
  observationEnd: string
  result: Record<string, unknown>
  reasonCode: string
  errorMessage: string
  createdAt: string
}

export interface ActionPreview {
  id: string
  status:
    | 'DRAFT'
    | 'PENDING_APPROVAL'
    | 'APPROVED'
    | 'REJECTED'
    | 'RETURNED'
    | 'WITHDRAWN'
  campaignName: string
  actionType: string
  currentVersionNumber: number
  currentVersion: ActionPreviewVersion
  approvals: ApprovalRecord[]
  executions: ExecutionRecord[]
  createdAt: string
  updatedAt: string
}

async function data<T>(request: Promise<{ data: ApiEnvelope<T> }>): Promise<T> {
  return (await request).data.data
}

export function fetchActionPreviews(
  tenantId: string,
  profileId: string,
): Promise<ActionPreview[]> {
  return data(
    httpClient.get(
      `/api/v1/actions/tenants/${tenantId}/profiles/${profileId}/previews`,
    ),
  )
}

export function createActionPreview(
  tenantId: string,
  recommendationId: string,
): Promise<ActionPreview> {
  return data(
    httpClient.post(
      `/api/v1/actions/tenants/${tenantId}/recommendations/${recommendationId}/previews`,
    ),
  )
}

export function submitActionPreview(
  tenantId: string,
  previewId: string,
): Promise<ActionPreview> {
  return data(
    httpClient.post(
      `/api/v1/actions/tenants/${tenantId}/previews/${previewId}/submit`,
    ),
  )
}

export function decideActionPreview(
  tenantId: string,
  previewId: string,
  decision: 'APPROVED' | 'REJECTED' | 'RETURNED',
  comment: string,
): Promise<ActionPreview> {
  return data(
    httpClient.post(
      `/api/v1/actions/tenants/${tenantId}/previews/${previewId}/decision`,
      {
        decision,
        comment,
        idempotencyKey: crypto.randomUUID(),
      },
    ),
  )
}

export function recordManualExecution(
  tenantId: string,
  previewId: string,
  outcome: 'SUCCEEDED' | 'FAILED' | 'SKIPPED',
  actualValue: Record<string, string>,
  note: string,
  evidenceFile?: File,
): Promise<ActionPreview> {
  const form = new FormData()
  form.append('outcome', outcome)
  form.append('actualValue', JSON.stringify(actualValue))
  form.append('executedAt', new Date().toISOString())
  form.append('note', note)
  form.append('evidenceMetadata', JSON.stringify({}))
  form.append('idempotencyKey', crypto.randomUUID())
  if (evidenceFile) form.append('evidenceFile', evidenceFile)
  return data(
    httpClient.post(
      `/api/v1/actions/tenants/${tenantId}/previews/${previewId}/executions`,
      form,
    ),
  )
}

export function withdrawActionPreview(
  tenantId: string,
  previewId: string,
): Promise<ActionPreview> {
  return data(
    httpClient.post(
      `/api/v1/actions/tenants/${tenantId}/previews/${previewId}/withdraw`,
    ),
  )
}

export function reviseReturnedActionPreview(
  tenantId: string,
  previewId: string,
  actionPayload: ActionPreviewVersion['actionPayload'],
): Promise<ActionPreview> {
  return data(
    httpClient.post(
      `/api/v1/actions/tenants/${tenantId}/previews/${previewId}/versions`,
      { actionPayload },
    ),
  )
}

export function createEffectEvaluation(
  tenantId: string,
  previewId: string,
  executionRecordId: string,
  observed: Record<string, unknown>,
): Promise<EffectEvaluation> {
  return data(
    httpClient.post(
      `/api/v1/actions/tenants/${tenantId}/previews/${previewId}/evaluations`,
      {
        executionRecordId,
        observed,
        evaluationKey: crypto.randomUUID(),
      },
    ),
  )
}
