import axios, {
  AxiosError,
  type AxiosInstance,
  type AxiosResponse,
  type InternalAxiosRequestConfig,
} from 'axios'

import type { ApiEnvelope, ApiError } from '@/shared/api/types'

type ValueProvider = () => string | null
type RefreshHandler = () => Promise<void>
type RequestIdObserver = (requestId: string) => void

interface RetriableRequestConfig extends InternalAxiosRequestConfig {
  _refreshAttempted?: boolean
}

let accessTokenProvider: ValueProvider = () => null
let tenantIdProvider: ValueProvider = () => null
let refreshHandler: RefreshHandler | null = null
let requestIdObserver: RequestIdObserver = () => undefined
let refreshPromise: Promise<void> | null = null

const AUTH_RETRY_EXCLUDED_PATHS = [
  '/api/v1/auth/login',
  '/api/v1/auth/refresh',
  '/api/v1/auth/logout',
]

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

export const httpClient: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? '',
  timeout: 10_000,
  headers: {
    Accept: 'application/json',
  },
  withCredentials: true,
})

export function setAccessTokenProvider(provider: ValueProvider): void {
  accessTokenProvider = provider
}

export function setTenantIdProvider(provider: ValueProvider): void {
  tenantIdProvider = provider
}

export function setRefreshHandler(handler: RefreshHandler | null): void {
  refreshHandler = handler
}

export function setRequestIdObserver(observer: RequestIdObserver): void {
  requestIdObserver = observer
}

export function readRequestId(response: AxiosResponse): string | null {
  const body = isRecord(response.data)
    ? (response.data as Partial<ApiEnvelope<unknown>>)
    : undefined
  const fromBody = body?.requestId
  const fromHeader = response.headers?.['x-request-id']
  const requestId = typeof fromBody === 'string' ? fromBody : fromHeader
  return typeof requestId === 'string' && requestId.length > 0 ? requestId : null
}

export function normalizeApiError(error: unknown): ApiError {
  if (
    isRecord(error) &&
    typeof error.code === 'string' &&
    typeof error.message === 'string' &&
    'status' in error &&
    'requestId' in error &&
    'fieldErrors' in error &&
    'retryable' in error
  ) {
    return error as unknown as ApiError
  }
  if (!axios.isAxiosError(error)) {
    return {
      status: null,
      code: 'CLIENT_ERROR',
      message: '客户端发生未知错误',
      requestId: null,
      fieldErrors: {},
      retryable: false,
    }
  }

  const axiosError = error as AxiosError<Partial<ApiEnvelope<{ errors?: Record<string, unknown> }>>>
  const status = axiosError.response?.status ?? null
  const rawResponseData = axiosError.response?.data
  const responseData = isRecord(rawResponseData)
    ? (rawResponseData as Partial<ApiEnvelope<{ errors?: Record<string, unknown> }>>)
    : undefined
  const requestId = axiosError.response ? readRequestId(axiosError.response) : null

  let code = typeof responseData?.code === 'string' ? responseData.code : 'NETWORK_ERROR'
  let message =
    typeof responseData?.message === 'string' ? responseData.message : '网络连接失败'
  if (axiosError.code === 'ECONNABORTED') {
    code = 'REQUEST_TIMEOUT'
    message = '请求超时'
  } else if (status === 401 && !responseData?.code) {
    code = 'AUTHENTICATION_REQUIRED'
    message = '身份验证失败或已过期'
  } else if (status === 403 && !responseData?.code) {
    code = 'PERMISSION_DENIED'
    message = '没有执行此操作的权限'
  }

  return {
    status,
    code,
    message,
    requestId,
    fieldErrors: isRecord(responseData?.data?.errors) ? responseData.data.errors : {},
    retryable: status === null || status >= 500 || status === 429,
  }
}

httpClient.interceptors.request.use((config) => {
  const accessToken = accessTokenProvider()
  const tenantId = tenantIdProvider()

  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`
    config.headers['X-Token'] = accessToken
  }
  if (tenantId) {
    config.headers['X-Tenant-ID'] = tenantId
  }
  return config
})

function canAttemptRefresh(config: RetriableRequestConfig): boolean {
  const url = config.url ?? ''
  return !AUTH_RETRY_EXCLUDED_PATHS.some((path) => url.includes(path))
}

async function runSingleRefresh(): Promise<void> {
  if (!refreshHandler) {
    throw new Error('Refresh handler is not installed')
  }
  if (!refreshPromise) {
    refreshPromise = refreshHandler().finally(() => {
      refreshPromise = null
    })
  }
  return refreshPromise
}

httpClient.interceptors.response.use(
  (response) => {
    const requestId = readRequestId(response)
    if (requestId) {
      requestIdObserver(requestId)
    }
    return response
  },
  async (error: AxiosError) => {
    const config = error.config as RetriableRequestConfig | undefined
    if (
      error.response?.status === 401 &&
      config &&
      !config._refreshAttempted &&
      canAttemptRefresh(config) &&
      refreshHandler
    ) {
      config._refreshAttempted = true
      await runSingleRefresh()
      return httpClient.request(config)
    }

    const normalized = normalizeApiError(error)
    if (normalized.requestId) {
      requestIdObserver(normalized.requestId)
    }
    return Promise.reject(normalized)
  },
)
