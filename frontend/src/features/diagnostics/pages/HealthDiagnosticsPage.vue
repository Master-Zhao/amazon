<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { fetchLiveHealth, fetchReadyHealth } from '@/shared/api/healthApi'
import type { ApiError, HealthData } from '@/shared/api/types'

type CheckState = 'idle' | 'loading' | 'healthy' | 'degraded' | 'error'

const state = ref<CheckState>('idle')
const live = ref<HealthData | null>(null)
const ready = ref<HealthData | null>(null)
const error = ref<ApiError | null>(null)
const requestIds = ref<string[]>([])

async function runChecks(): Promise<void> {
  state.value = 'loading'
  error.value = null
  requestIds.value = []
  try {
    const liveResponse = await fetchLiveHealth()
    live.value = liveResponse.data
    requestIds.value.push(liveResponse.requestId)

    const readyResponse = await fetchReadyHealth()
    ready.value = readyResponse.data
    requestIds.value.push(readyResponse.requestId)
    state.value = readyResponse.data.status === 'ready' ? 'healthy' : 'degraded'
  } catch (caught) {
    const apiError = caught as ApiError
    error.value = apiError
    if (apiError.requestId) {
      requestIds.value.push(apiError.requestId)
    }
    state.value = apiError.status === 503 ? 'degraded' : 'error'
  }
}

onMounted(runChecks)
</script>

<template>
  <section class="diagnostic-card">
    <div class="diagnostic-heading">
      <div>
        <p class="eyebrow">LIVE DEPENDENCY CHECK</p>
        <h2>运行诊断</h2>
      </div>
      <button type="button" :disabled="state === 'loading'" @click="runChecks">
        {{ state === 'loading' ? '检查中…' : '重新检查' }}
      </button>
    </div>

    <p v-if="state === 'loading'" role="status">正在请求后端健康接口…</p>

    <div v-else class="status-list">
      <article>
        <span>Django</span>
        <strong>{{ live?.status ?? '不可用' }}</strong>
      </article>
      <article>
        <span>依赖就绪</span>
        <strong>{{ ready?.status ?? (state === 'degraded' ? 'not_ready' : '不可用') }}</strong>
      </article>
    </div>

    <dl v-if="ready?.dependencies" class="dependency-list">
      <template v-for="(value, key) in ready.dependencies" :key="key">
        <dt>{{ key }}</dt>
        <dd>{{ value }}</dd>
      </template>
    </dl>

    <div v-if="error" class="error-panel" role="alert">
      <strong>{{ error.code }}</strong>
      <p>{{ error.message }}</p>
      <small v-if="error.requestId">requestId: {{ error.requestId }}</small>
    </div>

    <footer v-if="requestIds.length > 0">
      requestId：{{ requestIds.join(' · ') }}
    </footer>
  </section>
</template>
