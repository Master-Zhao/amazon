export interface ApiEnvelope<T> {
  code: string
  message: string
  data: T
  requestId: string
}

export interface ApiError {
  status: number | null
  code: string
  message: string
  requestId: string | null
  fieldErrors: Record<string, unknown>
  retryable: boolean
}

export interface HealthData {
  status: 'alive' | 'ready' | 'not_ready'
  dependencies?: Record<string, string>
}
