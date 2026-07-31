import { defineStore } from 'pinia'

import {
  fetchCurrentUser,
  loginAccount,
  logoutAccount,
  refreshAccessToken,
} from '@/features/auth/api/authApi'
import type { AuthenticatedUser } from '@/shared/api/types'

export type AuthInitializationStatus = 'idle' | 'loading' | 'ready'

interface AuthState {
  accessToken: string | null
  currentUser: AuthenticatedUser | null
  initializationStatus: AuthInitializationStatus
}

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    accessToken: null,
    currentUser: null,
    initializationStatus: 'idle',
  }),
  getters: {
    isAuthenticated: (state) =>
      Boolean(state.accessToken && state.currentUser),
  },
  actions: {
    clearSession() {
      this.accessToken = null
      this.currentUser = null
    },
    async login(identifier: string, password: string) {
      const result = await loginAccount(identifier, password)
      this.accessToken = result.accessToken
      this.currentUser = result.user
      try {
        this.currentUser = await fetchCurrentUser()
      } catch (error) {
        this.clearSession()
        throw error
      }
    },
    async refreshSession() {
      const result = await refreshAccessToken()
      this.accessToken = result.accessToken
    },
    async initialize() {
      if (this.initializationStatus !== 'idle') {
        return
      }

      this.initializationStatus = 'loading'
      try {
        await this.refreshSession()
        this.currentUser = await fetchCurrentUser()
      } catch {
        this.clearSession()
      } finally {
        this.initializationStatus = 'ready'
      }
    },
    async logout() {
      try {
        await logoutAccount()
      } finally {
        this.clearSession()
      }
    },
  },
})
