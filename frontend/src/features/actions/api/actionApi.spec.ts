import { beforeEach, describe, expect, it, vi } from 'vitest'

import { recordManualExecution } from '@/features/actions/api/actionsApi'
import {
  decidePreview,
  submitExistingPreview,
} from '@/features/optimization/api/optimizationApi'
import { httpClient } from '@/shared/api/httpClient'

vi.mock('@/shared/api/httpClient', () => ({
  httpClient: {
    post: vi.fn(),
  },
}))

describe('action workflow APIs', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('submits execution evidence as multipart data', async () => {
    vi.mocked(httpClient.post).mockResolvedValue({
      data: { data: { id: 'preview-1', status: 'APPROVED' } },
    })
    const evidence = new File(['proof'], 'proof.txt', { type: 'text/plain' })

    await recordManualExecution(
      'tenant-1',
      'preview-1',
      'SUCCEEDED',
      { budget: '55.00' },
      'completed',
      evidence,
    )

    const [url, body] = vi.mocked(httpClient.post).mock.calls[0]
    expect(url).toBe('/api/v1/actions/tenants/tenant-1/previews/preview-1/executions')
    expect(body).toBeInstanceOf(FormData)
  })

  it('supports RETURNED decisions and resubmitting the current version', async () => {
    vi.mocked(httpClient.post)
      .mockResolvedValueOnce({
        data: { data: { previewId: 'preview-1', status: 'RETURNED' } },
      })
      .mockResolvedValueOnce({
        data: {
          data: { previewId: 'preview-1', status: 'PENDING_APPROVAL' },
        },
      })

    await expect(
      decidePreview('tenant-1', 'preview-1', 'RETURNED', 'revise'),
    ).resolves.toEqual({ previewId: 'preview-1', status: 'RETURNED' })
    await expect(submitExistingPreview('tenant-1', 'preview-1')).resolves.toEqual({
      previewId: 'preview-1',
      status: 'PENDING_APPROVAL',
    })

    expect(vi.mocked(httpClient.post).mock.calls[0][0]).toBe(
      '/api/v1/actions/tenants/tenant-1/previews/preview-1/decision',
    )
    expect(vi.mocked(httpClient.post).mock.calls[1][0]).toBe(
      '/api/v1/actions/tenants/tenant-1/previews/preview-1/submit',
    )
  })
})
