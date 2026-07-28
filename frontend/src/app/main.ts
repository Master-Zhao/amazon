import { createPinia } from 'pinia'
import { createApp } from 'vue'

import App from '@/app/App.vue'
import { installAuthRouterGuards, router } from '@/app/router'
import { installHttpContext } from '@/app/setupHttpContext'
import '@/shared/styles/base.css'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
installHttpContext(pinia, router)
installAuthRouterGuards(router, pinia)
app.use(router)
app.mount('#app')
