<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '@/features/auth/stores/auth'
import type { ApiError } from '@/shared/api/types'

const authStore = useAuthStore()
const route = useRoute()
const router = useRouter()

const identifier = ref('')
const password = ref('')
const submitting = ref(false)
const error = ref<ApiError | null>(null)
const showPassword = ref(false)

const identifierError = computed(() => {
  if (!identifier.value) return ''
  if (!identifier.value.trim()) return '请输入账号或邮箱'
  return identifier.value.trim().length <= 254
    ? ''
    : '账号或邮箱不能超过 254 个字符'
})

const passwordError = computed(() => {
  if (!password.value) return ''
  return password.value.length < 1 ? '密码不能为空' : ''
})

const canSubmit = computed(() => {
  return (
    identifier.value.trim().length > 0 &&
    identifier.value.trim().length <= 254 &&
    password.value.length > 0 &&
    !identifierError.value &&
    !passwordError.value &&
    !submitting.value
  )
})

async function submit(): Promise<void> {
  if (!canSubmit.value) return
  submitting.value = true
  error.value = null
  try {
    await authStore.login(identifier.value, password.value)
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
  <section class="login-experience" aria-labelledby="login-brand-title">
    <div class="login-brand-panel">
      <div class="login-brand-lockup">
        <span class="login-brand-mark" aria-hidden="true">
          <svg viewBox="0 0 48 48" role="img">
            <path d="M13 31.5 22.2 12h6.2L38 31.5h-7.2l-1.7-4.2H20.9l-1.7 4.2H13Z" />
            <path d="M16 35.5c5.3 2.4 10.6 2.4 16 0" />
          </svg>
        </span>
        <span>
          <strong>Amazon Ads Optimizer</strong>
          <small>智能广告优化系统</small>
        </span>
      </div>

      <div class="login-brand-copy">
        <p class="login-kicker">DATA · INSIGHT · ACTION</p>
        <h1 id="login-brand-title">让广告数据转化为可执行的优化决策</h1>
        <p>
          从数据导入到建议审批，用一条可追溯的工作流连接分析、决策与执行。
        </p>
      </div>

      <ul class="login-capabilities" aria-label="平台能力">
        <li>
          <span aria-hidden="true">01</span>
          <div>
            <strong>数据分析与异常识别</strong>
            <small>统一指标口径，快速定位需要关注的广告表现。</small>
          </div>
        </li>
        <li>
          <span aria-hidden="true">02</span>
          <div>
            <strong>可解释的优化建议</strong>
            <small>保留依据与影响范围，让每项建议都可复核。</small>
          </div>
        </li>
        <li>
          <span aria-hidden="true">03</span>
          <div>
            <strong>审批、执行和审计追踪</strong>
            <small>关键动作经过状态守卫，并留下完整操作证据。</small>
          </div>
        </li>
      </ul>

      <div class="login-signal-card" aria-hidden="true">
        <div class="login-signal-heading">
          <span>WORKFLOW SIGNAL</span>
          <span class="login-signal-status">建议待审批</span>
        </div>
        <div class="login-signal-body">
          <div>
            <small>优化流程</small>
            <strong>分析完成</strong>
          </div>
          <div class="login-signal-bars">
            <i />
            <i />
            <i />
            <i />
            <i />
            <i />
          </div>
        </div>
      </div>
    </div>

    <div class="login-form-region">
      <div class="login-form-card">
        <div class="login-mobile-brand" aria-hidden="true">
          <span class="login-brand-mark">
            <svg viewBox="0 0 48 48">
              <path d="M13 31.5 22.2 12h6.2L38 31.5h-7.2l-1.7-4.2H20.9l-1.7 4.2H13Z" />
              <path d="M16 35.5c5.3 2.4 10.6 2.4 16 0" />
            </svg>
          </span>
          <strong>Amazon Ads Optimizer</strong>
        </div>

        <header class="login-form-heading">
          <p class="login-kicker">SECURE WORKSPACE</p>
          <h2>欢迎回来</h2>
          <p>登录并继续管理你的广告优化工作流。</p>
        </header>

        <form
          aria-label="账号登录"
          :aria-busy="submitting"
          novalidate
          @submit.prevent="submit"
        >
          <div class="login-field">
            <label for="identifier">账号或邮箱</label>
            <input
              id="identifier"
              v-model="identifier"
              name="identifier"
              type="text"
              autocomplete="username"
              autocapitalize="none"
              spellcheck="false"
              maxlength="254"
              placeholder="请输入账号或邮箱"
              required
              :aria-invalid="Boolean(identifierError)"
              :aria-describedby="identifierError ? 'identifier-error' : undefined"
              :disabled="submitting"
            >
            <span
              v-if="identifierError"
              id="identifier-error"
              class="field-error"
            >
              {{ identifierError }}
            </span>
          </div>

          <div class="login-field">
            <label for="password">密码</label>
            <div class="login-password-control">
              <input
                id="password"
                v-model="password"
                name="password"
                :type="showPassword ? 'text' : 'password'"
                autocomplete="current-password"
                placeholder="请输入密码"
                required
                :aria-invalid="Boolean(passwordError)"
                :aria-describedby="passwordError ? 'password-error' : undefined"
                :disabled="submitting"
              >
              <button
                class="login-password-toggle"
                type="button"
                :aria-label="showPassword ? '隐藏密码' : '显示密码'"
                :aria-pressed="showPassword"
                :disabled="submitting"
                @click="showPassword = !showPassword"
              >
                <svg v-if="showPassword" viewBox="0 0 24 24" aria-hidden="true">
                  <path d="m3 3 18 18M10.6 10.6a2 2 0 0 0 2.8 2.8M9.9 4.3A10.8 10.8 0 0 1 12 4c5.5 0 9 5.2 9 5.2a14.7 14.7 0 0 1-2.2 2.6M6.2 6.2C4.3 7.5 3 9.2 3 9.2s3.5 5.2 9 5.2c.8 0 1.6-.1 2.3-.3" />
                </svg>
                <svg v-else viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M3 12s3.5-5.2 9-5.2 9 5.2 9 5.2-3.5 5.2-9 5.2S3 12 3 12Z" />
                  <circle cx="12" cy="12" r="2.5" />
                </svg>
              </button>
            </div>
            <span v-if="passwordError" id="password-error" class="field-error">
              {{ passwordError }}
            </span>
          </div>

          <button class="login-submit" type="submit" :disabled="!canSubmit">
            <span v-if="submitting" class="login-spinner" aria-hidden="true" />
            {{ submitting ? '正在登录…' : '登录工作台' }}
          </button>

          <div v-if="error" class="login-error-panel" role="alert">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <circle cx="12" cy="12" r="9" />
              <path d="M12 7.5v5M12 16.5h.01" />
            </svg>
            <div>
              <strong>{{ error.message }}</strong>
              <small>
                {{ error.code }}
                <template v-if="error.requestId"> · requestId: {{ error.requestId }}</template>
              </small>
            </div>
          </div>
        </form>

        <footer class="login-security-note">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M7.5 10V7a4.5 4.5 0 0 1 9 0v3M6 10h12v10H6z" />
          </svg>
          <span>
            <strong>受控演示环境</strong>
            <small>仅限已授权账号访问，刷新令牌由安全 Cookie 管理。</small>
          </span>
        </footer>
      </div>
    </div>
  </section>
</template>
