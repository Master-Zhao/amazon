import { AxiosError, type AxiosAdapter, type AxiosResponse } from 'axios'
import { afterEach, vi } from 'vitest'

import {
  httpClient,
  normalizeApiError,
  readRequestId,
  setAccessTokenProvider,
  setRefreshHandler,
  setTenantIdProvider,
} from '@/shared/api/httpClient'

function response(overrides: Partial<AxiosResponse> = {}): AxiosResponse {
  return {
    data: {},
    status: 200,
    statusText: 'OK',
    headers: {},
    config: { headers: {} },
    ...overrides,
  } as AxiosResponse
}

describe('HTTP client error and requestId handling', () => {
  it('reads requestId from the response body before the header', () => {
    const value = readRequestId(
      response({
        data: { requestId: 'req_body' },
        headers: { 'x-request-id': 'req_header' },
      }),
    )

    expect(value).toBe('req_body')
  })

  it('falls back to the requestId response header', () => {
    expect(
      readRequestId(response({ headers: { 'x-request-id': 'req_header' } })),
    ).toBe('req_header')
  })

  it('normalizes structured 403 errors', () => {
    const error = {
      isAxiosError: true,
      code: 'ERR_BAD_REQUEST',
      response: response({
        status: 403,
        data: {
          code: 'PERMISSION_DENIED',
          message: '没有权限',
          data: { errors: { actionType: ['forbidden'] } },
          requestId: 'req_denied',
        },
      }),
    }

    expect(normalizeApiError(error)).toEqual({
      status: 403,
      code: 'PERMISSION_DENIED',
      message: '没有权限',
      requestId: 'req_denied',
      fieldErrors: { actionType: ['forbidden'] },
      retryable: false,
    })
  })

  it('normalizes a 401 response without a backend envelope', () => {
    const error = {
      isAxiosError: true,
      code: 'ERR_BAD_REQUEST',
      response: response({ status: 401, data: '' }),
    }

    expect(normalizeApiError(error)).toEqual({
      status: 401,
      code: 'AUTHENTICATION_REQUIRED',
      message: '身份验证失败或已过期',
      requestId: null,
      fieldErrors: {},
      retryable: false,
    })
  })

  it('normalizes a 403 response without a backend envelope', () => {
    const error = {
      isAxiosError: true,
      code: 'ERR_BAD_REQUEST',
      response: response({
        status: 403,
        data: { unexpected: 'safe fallback' },
        headers: { 'x-request-id': 'req_forbidden_header' },
      }),
    }

    expect(normalizeApiError(error)).toMatchObject({
      status: 403,
      code: 'PERMISSION_DENIED',
      requestId: 'req_forbidden_header',
      fieldErrors: {},
      retryable: false,
    })
  })

  it('normalizes a network error without an HTTP response', () => {
    const error = {
      isAxiosError: true,
      code: 'ERR_NETWORK',
      message: 'socket details must not become the user message',
    }

    expect(normalizeApiError(error)).toEqual({
      status: null,
      code: 'NETWORK_ERROR',
      message: '网络连接失败',
      requestId: null,
      fieldErrors: {},
      retryable: true,
    })
  })

  it('normalizes timeouts without inventing a requestId', () => {
    const error = {
      isAxiosError: true,
      code: 'ECONNABORTED',
    }

    expect(normalizeApiError(error)).toMatchObject({
      status: null,
      code: 'REQUEST_TIMEOUT',
      requestId: null,
      retryable: true,
    })
  })

  it('keeps a standard backend error envelope and body requestId', () => {
    const error = {
      isAxiosError: true,
      response: response({
        status: 409,
        data: {
          code: 'VERSION_CONFLICT',
          message: '版本冲突',
          data: { errors: { version: ['stale'] } },
          requestId: 'req_conflict',
        },
      }),
    }

    expect(normalizeApiError(error)).toEqual({
      status: 409,
      code: 'VERSION_CONFLICT',
      message: '版本冲突',
      requestId: 'req_conflict',
      fieldErrors: { version: ['stale'] },
      retryable: false,
    })
  })

  it('safely degrades a non-object error body', () => {
    const error = {
      isAxiosError: true,
      response: response({ status: 502, data: '<html>upstream error</html>' }),
    }

    expect(normalizeApiError(error)).toEqual({
      status: 502,
      code: 'NETWORK_ERROR',
      message: '网络连接失败',
      requestId: null,
      fieldErrors: {},
      retryable: true,
    })
  })
})

describe('HTTP client authentication flow', () => {
  const originalAdapter = httpClient.defaults.adapter

  afterEach(() => {
    httpClient.defaults.adapter = originalAdapter
    setAccessTokenProvider(() => null)
    setTenantIdProvider(() => null)
    setRefreshHandler(null)
  })

  it('injects the in-memory access token as Bearer authorization', async () => {
    setAccessTokenProvider(() => 'memory-access')
    httpClient.defaults.adapter = (async (config) => ({
      data: { code: 'SUCCESS', message: 'ok', data: {}, requestId: 'req_auth' },
      status: 200,
      statusText: 'OK',
      headers: {},
      config,
    })) as AxiosAdapter

    const result = await httpClient.get('/protected')

    expect(result.config.headers.Authorization).toBe('Bearer memory-access')
  })

  it('injects the selected tenant scope header', async () => {
    setTenantIdProvider(() => 'tenant-42')
    httpClient.defaults.adapter = (async (config) => ({
      data: { code: 'SUCCESS', message: 'ok', data: {}, requestId: 'req_scope' },
      status: 200,
      statusText: 'OK',
      headers: {},
      config,
    })) as AxiosAdapter

    const result = await httpClient.get('/protected')

    expect(result.config.headers['X-Tenant-ID']).toBe('tenant-42')
  })

  it('merges concurrent 401 responses into one refresh then replays both', async () => {
    let token = 'expired-access'
    let protectedCalls = 0
    const refresh = vi.fn(async () => {
      await Promise.resolve()
      token = 'fresh-access'
    })
    setAccessTokenProvider(() => token)
    setRefreshHandler(refresh)
    httpClient.defaults.adapter = (async (config) => {
      protectedCalls += 1
      if (config.headers.Authorization === 'Bearer expired-access') {
        throw new AxiosError(
          'unauthorized',
          'ERR_BAD_REQUEST',
          config,
          undefined,
          {
            data: {},
            status: 401,
            statusText: 'Unauthorized',
            headers: {},
            config,
          },
        )
      }
      return {
        data: { code: 'SUCCESS', message: 'ok', data: {}, requestId: 'req_ok' },
        status: 200,
        statusText: 'OK',
        headers: {},
        config,
      }
    }) as AxiosAdapter

    const results = await Promise.all([
      httpClient.get('/protected/one'),
      httpClient.get('/protected/two'),
    ])

    expect(refresh).toHaveBeenCalledOnce()
    expect(protectedCalls).toBe(4)
    expect(results.every((item) => item.status === 200)).toBe(true)
  })

  it('does not recurse when the refresh endpoint itself returns 401', async () => {
    const refresh = vi.fn(async () => undefined)
    setRefreshHandler(refresh)
    httpClient.defaults.adapter = (async (config) => {
      throw new AxiosError(
        'unauthorized',
        'ERR_BAD_REQUEST',
        config,
        undefined,
        {
          data: {
            code: 'AUTH_TOKEN_REVOKED',
            message: 'revoked',
            data: { errors: {} },
            requestId: 'req_revoked',
          },
          status: 401,
          statusText: 'Unauthorized',
          headers: {},
          config,
        },
      )
    }) as AxiosAdapter

    await expect(httpClient.post('/api/v1/auth/refresh')).rejects.toMatchObject({
      code: 'AUTH_TOKEN_REVOKED',
    })
    expect(refresh).not.toHaveBeenCalled()
  })
})
