import { beforeEach, describe, expect, it, vi } from 'vitest'

import { loginAccount } from '@/features/auth/api/authApi'
import { httpClient } from '@/shared/api/httpClient'

vi.mock('@/shared/api/httpClient', () => ({
  httpClient: {
    post: vi.fn(),
  },
}))

describe('auth API', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('sends an account identifier instead of mislabeling it as email', async () => {
    vi.mocked(httpClient.post).mockResolvedValue({
      data: {
        data: {
          accessToken: 'access',
          user: {
            id: '1',
            email: 'w0765@example.invalid',
            username: 'W0765',
            firstName: '',
            lastName: '',
          },
        },
      },
    })

    await loginAccount('W0765', 'hidden-test-password')

    expect(httpClient.post).toHaveBeenCalledWith('/api/v1/auth/login', {
      identifier: 'W0765',
      password: 'hidden-test-password',
    })
  })
})
