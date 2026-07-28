<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { fetchAuditLog, type AuditEntry } from '@/features/audit/api/auditApi'
import { useTenantContextStore } from '@/features/tenant-context/stores/context'

const context = useTenantContextStore()
const items = ref<AuditEntry[]>([])
const loading = ref(true)
const error = ref(false)

onMounted(async () => {
  if (!context.selectedTenantId) {
    loading.value = false
    return
  }
  try {
    items.value = await fetchAuditLog()
  } catch {
    error.value = true
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <section class="panel">
    <p class="eyebrow">AUDIT TRAIL</p>
    <h2>只追加审计日志</h2>
    <p v-if="!context.selectedTenantId" class="empty-state">请先选择 Tenant。</p>
    <p v-else-if="loading">正在加载…</p>
    <p v-else-if="error" class="error-banner">审计日志加载失败或当前账号无权限。</p>
    <p v-else-if="items.length === 0" class="empty-state">当前没有审计记录。</p>
    <div v-else class="table-scroll">
      <table>
        <thead><tr><th>时间</th><th>事件</th><th>对象</th><th>Request ID</th></tr></thead>
        <tbody>
          <tr v-for="item in items" :key="item.id">
            <td>{{ new Date(item.created_at).toLocaleString() }}</td>
            <td>{{ item.event }}</td>
            <td>{{ item.object_type }} / {{ item.object_id }}</td>
            <td><code>{{ item.request_id }}</code></td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
