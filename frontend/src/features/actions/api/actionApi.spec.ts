import { beforeEach, describe, expect, it, vi } from 'vitest'

import { recordExecution } from '@/features/actions/api/actionApi'
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
      data: { data: { recordId: 'record-1' } },
    })
    const evidence = new File(['proof'], 'proof.txt', { type: 'text/plain' })

    await expect(
      recordExecution({
        itemId: 'item-1',
        result: 'SUCCEEDED',
        actualValue: { budget: '55.00' },
        note: 'completed',
        evidence,
      }),
    ).resolves.toBe('record-1')

    const [url, body] = vi.mocked(httpClient.post).mock.calls[0]
    expect(url).toBe('/api/v1/actions/execution-items/item-1/records')
    expect(body).toBeInstanceOf(FormData)
    expect((body as FormData).get('actualValue')).toBe('{"budget":"55.00"}')
    expect((body as FormData).get('evidence')).toBe(evidence)
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
      decidePreview('preview-1', 'RETURNED', 'revise'),
    ).resolves.toEqual({ previewId: 'preview-1', status: 'RETURNED' })
    await expect(submitExistingPreview('preview-1')).resolves.toEqual({
      previewId: 'preview-1',
      status: 'PENDING_APPROVAL',
    })

    expect(vi.mocked(httpClient.post).mock.calls[0][0]).toBe(
      '/api/v1/actions/previews/preview-1/decisions',
    )
    expect(vi.mocked(httpClient.post).mock.calls[1][0]).toBe(
      '/api/v1/actions/previews/preview-1/submit',
    )
  })
})
