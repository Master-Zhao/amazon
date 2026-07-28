import { httpClient } from '@/shared/api/httpClient'
import type { ApiEnvelope } from '@/shared/api/types'

export interface ActionPreview {
  id: string
  status: string
  currentVersion: number
  versionLock: number
  createdAt: string
  version: null | {
    version: number
    items: Array<Record<string, unknown>>
    contentHash: string
    frozenAt: string | null
  }
  approvals: Array<{
    id: string
    decision: string
    comment: string
    createdAt: string
  }>
  execution: null | {
    id: string
    status: string
    items: Array<{
      id: string
      status: string
      action: Record<string, unknown>
      records: Array<Record<string, unknown>>
    }>
    evaluations: Array<Record<string, unknown>>
  }
}

export async function fetchActionPreviews(
  profileId: string,
): Promise<ActionPreview[]> {
  const response = await httpClient.get<
    ApiEnvelope<{ items: ActionPreview[] }>
  >('/api/v1/actions/previews', { params: { profileId } })
  return response.data.data.items
}

export async function recordExecution(input: {
  itemId: string
  result: 'SUCCEEDED' | 'FAILED' | 'SKIPPED'
  actualValue?: Record<string, unknown>
  note: string
}): Promise<string> {
  const response = await httpClient.post<ApiEnvelope<{ recordId: string }>>(
    `/api/v1/actions/execution-items/${input.itemId}/records`,
    {
      result: input.result,
      actualValue: input.actualValue ?? {},
      executedAt: new Date().toISOString(),
      note: input.note,
    },
    { headers: { 'Idempotency-Key': crypto.randomUUID() } },
  )
  return response.data.data.recordId
}
