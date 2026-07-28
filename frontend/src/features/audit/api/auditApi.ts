import { httpClient } from '@/shared/api/httpClient'
import type { ApiEnvelope } from '@/shared/api/types'

export interface AuditLog {
  id: string
  event: string
  objectType: string
  objectId: string
  requestId: string
  taskId: string
  actorEmail: string | null
  beforeData: Record<string, unknown>
  afterData: Record<string, unknown>
  metadata: Record<string, unknown>
  createdAt: string
}

export async function fetchAuditLogs(tenantId: string): Promise<AuditLog[]> {
  const response = await httpClient.get<ApiEnvelope<AuditLog[]>>(
    `/api/v1/audit/tenants/${tenantId}`,
  )
  return response.data.data
}
