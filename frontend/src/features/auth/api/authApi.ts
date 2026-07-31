import { httpClient } from '@/shared/api/httpClient'
import type {
  AccessTokenData,
  ApiEnvelope,
  AuthenticatedUser,
  LoginData,
} from '@/shared/api/types'

export interface RemoteAccount {
  source: 'SCM_MERCHANT_ADMIN'
  externalUserId: string
  merchantId: string
  identifier: string
  isActive: boolean
}

export async function loginAccount(
  identifier: string,
  password: string,
): Promise<LoginData> {
  const response = await httpClient.post<ApiEnvelope<LoginData>>(
    '/api/v1/auth/login',
    { identifier, password },
  )
  return response.data.data
}

export async function refreshAccessToken(): Promise<AccessTokenData> {
  const response = await httpClient.post<ApiEnvelope<AccessTokenData>>(
    '/api/v1/auth/refresh',
  )
  return response.data.data
}

export async function fetchCurrentUser(): Promise<AuthenticatedUser> {
  const response = await httpClient.get<ApiEnvelope<AuthenticatedUser>>(
    '/api/v1/auth/me',
  )
  return response.data.data
}

export async function fetchRemoteAccount(): Promise<RemoteAccount> {
  const response = await httpClient.get<ApiEnvelope<RemoteAccount>>(
    '/api/v1/auth/remote-account',
  )
  return response.data.data
}

export async function logoutAccount(): Promise<void> {
  await httpClient.post('/api/v1/auth/logout')
}
