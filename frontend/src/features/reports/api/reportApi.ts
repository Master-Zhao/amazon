import { httpClient } from '@/shared/api/httpClient'
import type { ApiEnvelope } from '@/shared/api/types'

export type ReportType = 'CAMPAIGN' | 'TARGETING' | 'SEARCH_TERM'

export interface ImportTask {
  taskId: string
  reportType: ReportType
  status: 'QUEUED' | 'RUNNING' | 'SUCCEEDED' | 'PARTIAL_SUCCEEDED' | 'FAILED'
  isDuplicate: boolean
  batch: null | {
    id: string
    totalRows: number
    succeededRows: number
    failedRows: number
    errors: Array<{
      rowNumber: number
      code: string
      field: string
      message: string
    }>
  }
}

export async function uploadReport(input: {
  tenantId: string
  profileId: string
  reportType: ReportType
  file: File
}): Promise<{ taskId: string; status: string; isDuplicate: boolean }> {
  const body = new FormData()
  body.append('tenantId', input.tenantId)
  body.append('profileId', input.profileId)
  body.append('reportType', input.reportType)
  body.append('file', input.file)
  const response = await httpClient.post<
    ApiEnvelope<{ taskId: string; status: string; isDuplicate: boolean }>
  >('/api/v1/reports/uploads', body)
  return response.data.data
}

export async function fetchImportTask(taskId: string): Promise<ImportTask> {
  const response = await httpClient.get<ApiEnvelope<ImportTask>>(
    `/api/v1/reports/tasks/${taskId}`,
  )
  return response.data.data
}

