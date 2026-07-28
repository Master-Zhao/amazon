<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'

import { fetchAuditLogs, type AuditLog } from '@/features/audit/api/auditApi'
import { useTenantContextStore } from '@/features/tenant-context/stores/tenantContext'
import { normalizeApiError } from '@/shared/api/httpClient'

const context = useTenantContextStore()
const logs = ref<AuditLog[]>([])
const loading = ref(false)
const errorMessage = ref<string | null>(null)

async function refresh(): Promise<void> {
  if (!context.tenantId) {
    logs.value = []
    return
  }
  loading.value = true
  errorMessage.value = null
  try {
    logs.value = await fetchAuditLogs(context.tenantId)
  } catch (error) {
    errorMessage.value = normalizeApiError(error).message
  } finally {
    loading.value = false
  }
}

watch(() => context.tenantId, () => void refresh())
onMounted(async () => {
  if (context.status === 'idle') await context.initialize()
  await refresh()
})
</script>

<template>
  <section class="report-page">
    <header class="report-heading">
      <div>
        <p class="eyebrow">APPEND-ONLY BUSINESS EVIDENCE</p>
        <h2>审计日志</h2>
        <p>
          登录、上传、导入、AI、Action Preview、审批和执行均记录 requestId/taskId
          及脱敏 before/after；普通业务接口不能修改或删除这些记录。
        </p>
      </div>
      <button class="secondary-button" type="button" @click="refresh">
        {{ loading ? '刷新中…' : '刷新' }}
      </button>
    </header>

    <div v-if="errorMessage" class="error-panel" role="alert">
      {{ errorMessage }}
    </div>
    <p v-if="logs.length === 0" class="empty-panel">当前 Tenant 暂无可见审计事件。</p>
    <div v-else class="audit-list">
      <article v-for="log in logs" :key="log.id">
        <header>
          <strong>{{ log.event }}</strong>
          <time>{{ new Date(log.createdAt).toLocaleString() }}</time>
        </header>
        <p>
          {{ log.objectType }} #{{ log.objectId }} · {{ log.actorEmail ?? 'system' }}
        </p>
        <code>requestId={{ log.requestId }} taskId={{ log.taskId || '—' }}</code>
        <details>
          <summary>查看 before / after</summary>
          <pre>{{ JSON.stringify({ before: log.beforeData, after: log.afterData }, null, 2) }}</pre>
        </details>
      </article>
    </div>
  </section>
</template>
