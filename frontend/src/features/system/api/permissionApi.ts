import { httpClient } from '@/shared/api/httpClient'
import type { ApiEnvelope } from '@/shared/api/types'

export interface Role {
  id: string
  tenantId: string | null
  code: string
  name: string
  isSystem: boolean
  permissionCodes: string[]
}

export async function fetchRoles(tenantId: string): Promise<Role[]> {
  const response = await httpClient.get<ApiEnvelope<{ items: Role[] }>>(
    '/api/v1/permissions/roles',
    { params: { tenantId } },
  )
  return response.data.data.items
}

export async function createRole(input: {
  tenantId: string
  code: string
  name: string
  permissionCodes: string[]
}): Promise<Role> {
  const response = await httpClient.post<ApiEnvelope<Role>>(
    '/api/v1/permissions/roles',
    input,
  )
  return response.data.data
}

