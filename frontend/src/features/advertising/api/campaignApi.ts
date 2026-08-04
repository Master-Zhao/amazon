import { httpClient } from '@/shared/api/httpClient'
import type { ApiEnvelope } from '@/shared/api/types'
import type {
  CampaignListFilters,
  CampaignListResponse,
} from '@/features/advertising/types/campaign'

export async function fetchCampaignOverview(
  tenantId: string,
  profileId: string,
  filters: CampaignListFilters,
  signal?: AbortSignal,
): Promise<CampaignListResponse> {
  const response = await httpClient.get<ApiEnvelope<CampaignListResponse>>(
    `/api/v1/advertising/tenants/${tenantId}/profiles/${profileId}/campaigns`,
    {
      params: filters,
      signal,
    },
  )
  return response.data.data
}

export async function exportCampaignOverview(
  tenantId: string,
  profileId: string,
  filters: CampaignListFilters,
): Promise<Blob> {
  const response = await httpClient.get<Blob>(
    `/api/v1/advertising/tenants/${tenantId}/profiles/${profileId}/campaigns/export`,
    {
      params: filters,
      responseType: 'blob',
    },
  )
  return response.data
}
