import { createPinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'

import { installAuthRouterGuards, routes } from '@/app/router'
import { useAuthStore } from '@/features/auth/stores/auth'

function createGuardedRouter() {
  const pinia = createPinia()
  const targetRouter = createRouter({
    history: createMemoryHistory(),
    routes,
  })
  installAuthRouterGuards(targetRouter, pinia)
  return { pinia, targetRouter }
}

describe('authentication route guard', () => {
  it('redirects anonymous users from protected routes to login', async () => {
    const { pinia, targetRouter } = createGuardedRouter()
    const authStore = useAuthStore(pinia)
    authStore.initializationStatus = 'ready'

    await targetRouter.push('/')

    expect(targetRouter.currentRoute.value.name).toBe('login')
    expect(targetRouter.currentRoute.value.query.redirect).toBe('/')
  })

  it('redirects authenticated users away from the login page', async () => {
    const { pinia, targetRouter } = createGuardedRouter()
    const authStore = useAuthStore(pinia)
    authStore.initializationStatus = 'ready'
    authStore.accessToken = 'access'
    authStore.currentUser = {
      id: '1',
      email: 'demo@example.invalid',
      username: 'demo',
      firstName: '',
      lastName: '',
    }

    await targetRouter.push('/login')

    expect(targetRouter.currentRoute.value.name).toBe('home')
  })
})
