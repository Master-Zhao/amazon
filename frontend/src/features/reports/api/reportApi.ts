import type { AxiosProgressEvent } from 'axios'

import { httpClient } from '@/shared/api/httpClient'
import type { ApiEnvelope } from '@/shared/api/types'

export type ImportTaskStatus =
  | 'QUEUED'
  | 'RUNNING'
  | 'SUCCEEDED'
  | 'PARTIAL_SUCCEEDED'
  | 'FAILED'

export type ReportType = 'CAMPAIGN' | 'TARGETING' | 'SEARCH_TERM'

export interface ReportUploadSummary {
  id: string
  reportType: ReportType
  originalFilename: string
  contentType: string
  sizeBytes: number
  sha256: string
  duplicateOfId: string | null
  createdAt: string
}

export interface ImportTask {
  id: string
  status: ImportTaskStatus
  celeryTaskId: string
  totalRows: number
  successRows: number
  errorRows: number
  errorCode: string
  errorMessage: string
  reprocessedFromId: string | null
  createdAt: string
  startedAt: string | null
  finishedAt: string | null
  upload: ReportUploadSummary
}

export interface ImportRowError {
  id: string
  rowNumber: number
  errorCode: string
  message: string
  fieldName: string
  rejectedValue: string
  createdAt: string
}

async function data<T>(request: Promise<{ data: ApiEnvelope<T> }>): Promise<T> {
  return (await request).data.data
}

export function uploadReport(
  tenantId: string,
  profileId: string,
  reportType: ReportType,
  file: File,
  onUploadProgress?: (event: AxiosProgressEvent) => void,
): Promise<ImportTask> {
  const form = new FormData()
  form.append('reportType', reportType)
  form.append('file', file)
  return data(
    httpClient.post(
      `/api/v1/reports/tenants/${tenantId}/profiles/${profileId}/uploads`,
      form,
      { onUploadProgress },
    ),
  )
}

export function fetchImportTasks(
  tenantId: string,
  profileId: string,
): Promise<ImportTask[]> {
  return data(
    httpClient.get(
      `/api/v1/reports/tenants/${tenantId}/profiles/${profileId}/tasks`,
    ),
  )
}

export function fetchImportErrors(
  tenantId: string,
  taskId: string,
): Promise<ImportRowError[]> {
  return data(
    httpClient.get(
      `/api/v1/reports/tenants/${tenantId}/tasks/${taskId}/errors`,
    ),
  )
}

export function reprocessImport(
  tenantId: string,
  taskId: string,
): Promise<ImportTask> {
  return data(
    httpClient.post(
      `/api/v1/reports/tenants/${tenantId}/tasks/${taskId}/reprocess`,
    ),
  )
}

export async function downloadImportSource(
  tenantId: string,
  taskId: string,
): Promise<Blob> {
  const response = await httpClient.get(
    `/api/v1/reports/tenants/${tenantId}/tasks/${taskId}/source`,
    { responseType: 'blob' },
  )
  return response.data as Blob
}
