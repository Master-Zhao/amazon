import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, vi } from 'vitest'

import {
  fetchCurrentUser,
  loginAccount,
  logoutAccount,
  refreshAccessToken,
} from '@/features/auth/api/authApi'
import { useAuthStore } from '@/features/auth/stores/auth'

vi.mock('@/features/auth/api/authApi', () => ({
  fetchCurrentUser: vi.fn(),
  loginAccount: vi.fn(),
  logoutAccount: vi.fn(),
  refreshAccessToken: vi.fn(),
}))

const user = {
  id: '42',
  email: 'demo@example.invalid',
  username: 'demo',
  firstName: '',
  lastName: '',
}

describe('auth store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.resetAllMocks()
    localStorage.clear()
  })

  it('keeps only access token, current user and initialization state', () => {
    const store = useAuthStore()

    expect(store.$state).toEqual({
      accessToken: null,
      currentUser: null,
      initializationStatus: 'idle',
    })
    expect(JSON.stringify(store.$state)).not.toContain('refresh')
  })

  it('stores a successful login in memory', async () => {
    vi.mocked(loginAccount).mockResolvedValue({
      accessToken: 'access-login',
      user,
    })
    vi.mocked(fetchCurrentUser).mockResolvedValue(user)
    const store = useAuthStore()

    await store.login(user.email, 'password')

    expect(store.accessToken).toBe('access-login')
    expect(store.currentUser).toEqual(user)
    expect(fetchCurrentUser).toHaveBeenCalledOnce()
    expect(localStorage.length).toBe(0)
  })

  it('does not invent state after login failure', async () => {
    vi.mocked(loginAccount).mockRejectedValue({ code: 'AUTH_INVALID_CREDENTIALS' })
    const store = useAuthStore()

    await expect(store.login(user.email, 'wrong')).rejects.toMatchObject({
      code: 'AUTH_INVALID_CREDENTIALS',
    })
    expect(store.isAuthenticated).toBe(false)
  })

  it('clears the new token when the post-login authenticated request fails', async () => {
    vi.mocked(loginAccount).mockResolvedValue({
      accessToken: 'access-login',
      user,
    })
    vi.mocked(fetchCurrentUser).mockRejectedValue({
      code: 'AUTH_TOKEN_INVALID',
    })
    const store = useAuthStore()

    await expect(store.login(user.email, 'password')).rejects.toMatchObject({
      code: 'AUTH_TOKEN_INVALID',
    })

    expect(store.accessToken).toBeNull()
    expect(store.currentUser).toBeNull()
  })

  it('restores a session with refresh then me', async () => {
    vi.mocked(refreshAccessToken).mockResolvedValue({
      accessToken: 'access-restored',
    })
    vi.mocked(fetchCurrentUser).mockResolvedValue(user)
    const store = useAuthStore()

    await store.initialize()

    expect(store.accessToken).toBe('access-restored')
    expect(store.currentUser).toEqual(user)
    expect(store.initializationStatus).toBe('ready')
  })

  it('clears session when initialization refresh fails', async () => {
    vi.mocked(refreshAccessToken).mockRejectedValue({
      code: 'AUTH_TOKEN_MISSING',
    })
    const store = useAuthStore()
    store.accessToken = 'stale'
    store.currentUser = user

    await store.initialize()

    expect(store.accessToken).toBeNull()
    expect(store.currentUser).toBeNull()
    expect(store.initializationStatus).toBe('ready')
    expect(fetchCurrentUser).not.toHaveBeenCalled()
  })

  it('logs out through the backend and clears memory state', async () => {
    vi.mocked(logoutAccount).mockResolvedValue()
    const store = useAuthStore()
    store.accessToken = 'access'
    store.currentUser = user

    await store.logout()

    expect(logoutAccount).toHaveBeenCalledOnce()
    expect(store.isAuthenticated).toBe(false)
  })
})
