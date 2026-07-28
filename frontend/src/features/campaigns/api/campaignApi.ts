import { httpClient } from '@/shared/api/httpClient'
import type { ApiEnvelope } from '@/shared/api/types'

export interface Campaign {
  id: string
  externalCampaignId: string
  name: string
  state: string
  dailyBudget: string | null
  currency: string
}

export async function fetchCampaigns(profileId: string): Promise<Campaign[]> {
  const response = await httpClient.get<ApiEnvelope<{ items: Campaign[] }>>(
    '/api/v1/advertising/campaigns',
    { params: { profileId } },
  )
  return response.data.data.items
}
