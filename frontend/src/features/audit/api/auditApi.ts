import { httpClient } from '@/shared/api/httpClient'
import type { ApiEnvelope } from '@/shared/api/types'

export interface AuditEntry {
  id: string
  event: string
  object_type: string
  object_id: string
  actor_id: string | null
  request_id: string
  created_at: string
}

export async function fetchAuditLog(): Promise<AuditEntry[]> {
  const response = await httpClient.get<ApiEnvelope<{ items: AuditEntry[] }>>(
    '/api/v1/audit/',
  )
  return response.data.data.items
}
