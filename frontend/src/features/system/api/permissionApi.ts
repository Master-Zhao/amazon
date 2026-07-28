import { httpClient } from '@/shared/api/httpClient'
import type { ApiEnvelope } from '@/shared/api/types'

export interface Role {
  id: string
  code: string
  name: string
  isSystem: boolean
  permissionCodes: string[]
}

export async function fetchRoles(tenantId: string): Promise<Role[]> {
  const response = await httpClient.get<ApiEnvelope<Role[]>>(
    `/api/v1/permissions/tenants/${tenantId}/roles`,
  )
  return response.data.data
}

export async function createRole(input: {
  tenantId: string
  code: string
  name: string
  permissionCodes: string[]
}): Promise<void> {
  await httpClient.post<ApiEnvelope<Pick<Role, 'id' | 'code' | 'name'>>>(
    `/api/v1/permissions/tenants/${input.tenantId}/roles`,
    {
      code: input.code,
      name: input.name,
      permissionCodes: input.permissionCodes,
    },
  )
}
