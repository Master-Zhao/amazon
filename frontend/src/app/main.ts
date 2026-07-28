import { createPinia } from 'pinia'
import { createApp } from 'vue'

import App from '@/app/App.vue'
import { router } from '@/app/router'
import { installHttpContext } from '@/app/setupHttpContext'
import '@/shared/styles/base.css'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)
installHttpContext(pinia)
app.mount('#app')
