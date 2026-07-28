import { httpClient } from '@/shared/api/httpClient'
import type { ApiEnvelope, HealthData } from '@/shared/api/types'

export async function fetchLiveHealth(): Promise<ApiEnvelope<HealthData>> {
  const response = await httpClient.get<ApiEnvelope<HealthData>>('/health/live')
  return response.data
}

export async function fetchReadyHealth(): Promise<ApiEnvelope<HealthData>> {
  const response = await httpClient.get<ApiEnvelope<HealthData>>('/health/ready')
  return response.data
}
