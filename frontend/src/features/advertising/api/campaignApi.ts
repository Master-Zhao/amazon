import { httpClient } from '@/shared/api/httpClient'
import type { ApiEnvelope } from '@/shared/api/types'
import type {
  CampaignCreatePayload,
  CampaignCreateResponse,
  CampaignEnabledUpdateResponse,
  CampaignListFilters,
  CampaignListResponse,
  CampaignDetailResponse,
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

export async function createCampaign(
  tenantId: string,
  profileId: string,
  payload: CampaignCreatePayload,
): Promise<CampaignCreateResponse> {
  const response = await httpClient.post<ApiEnvelope<CampaignCreateResponse>>(
    `/api/v1/advertising/tenants/${tenantId}/profiles/${profileId}/campaigns`,
    payload,
  )
  return response.data.data
}

export async function fetchCampaignDetail(
  tenantId: string,
  profileId: string,
  campaignKey: string,
  dates: Pick<CampaignListFilters, 'startDate' | 'endDate'>,
  signal?: AbortSignal,
): Promise<CampaignDetailResponse> {
  const response = await httpClient.get<ApiEnvelope<CampaignDetailResponse>>(
    `/api/v1/advertising/tenants/${tenantId}/profiles/${profileId}/campaigns/${encodeURIComponent(campaignKey)}`,
    { params: dates, signal },
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

export async function updateCampaignEnabled(
  tenantId: string,
  profileId: string,
  campaignKey: string,
  enabled: boolean,
  dates: Pick<CampaignListFilters, 'startDate' | 'endDate'> = {},
): Promise<CampaignEnabledUpdateResponse> {
  const response = await httpClient.patch<ApiEnvelope<CampaignEnabledUpdateResponse>>(
    `/api/v1/advertising/tenants/${tenantId}/profiles/${profileId}/campaigns/${encodeURIComponent(campaignKey)}/enabled`,
    {
      enabled,
      ...dates,
    },
  )
  return response.data.data
}
