import type { AxiosResponse } from 'axios'

import { normalizeApiError, readRequestId } from '@/shared/api/httpClient'

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
