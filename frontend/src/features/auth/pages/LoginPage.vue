<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '@/features/auth/stores/auth'
import type { ApiError } from '@/shared/api/types'

const authStore = useAuthStore()
const route = useRoute()
const router = useRouter()

const email = ref('')
const password = ref('')
const submitting = ref(false)
const error = ref<ApiError | null>(null)

async function submit(): Promise<void> {
  submitting.value = true
  error.value = null
  try {
    await authStore.login(email.value, password.value)
    const redirect =
      typeof route.query.redirect === 'string' ? route.query.redirect : '/'
    await router.replace(redirect)
  } catch (caught) {
    error.value = caught as ApiError
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <section class="login-card">
    <div>
      <p class="eyebrow">SECURE ACCOUNT ACCESS</p>
      <h2>登录广告优化工作台</h2>
      <p>访问令牌仅保存在页面内存中，刷新令牌由浏览器的 HttpOnly Cookie 管理。</p>
    </div>

    <form aria-label="账号登录" @submit.prevent="submit">
      <label for="email">邮箱</label>
      <input
        id="email"
        v-model="email"
        name="email"
        type="email"
        autocomplete="username"
        required
      >

      <label for="password">密码</label>
      <input
        id="password"
        v-model="password"
        name="password"
        type="password"
        autocomplete="current-password"
        required
      >

      <button type="submit" :disabled="submitting">
        {{ submitting ? '正在登录…' : '登录' }}
      </button>

      <div v-if="error" class="error-panel" role="alert">
        <strong>{{ error.code }}</strong>
        <p>{{ error.message }}</p>
        <small v-if="error.requestId">requestId: {{ error.requestId }}</small>
      </div>
    </form>
  </section>
</template>
