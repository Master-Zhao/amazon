<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'

import {
  fetchActionPreviews,
  recordExecution,
  type ActionPreview,
} from '@/features/actions/api/actionApi'
import { useTenantContextStore } from '@/features/tenant-context/stores/context'

const context = useTenantContextStore()
const items = ref<ActionPreview[]>([])
const loading = ref(false)
const busyItem = ref<string | null>(null)
const error = ref<string | null>(null)
type EvidenceFile = NonNullable<
  Parameters<typeof recordExecution>[0]['evidence']
>
const evidenceFiles = ref<Record<string, EvidenceFile | undefined>>({})

async function load(): Promise<void> {
  if (!context.selectedProfileId) return
  loading.value = true
  error.value = null
  try {
    items.value = await fetchActionPreviews(context.selectedProfileId)
  } catch {
    error.value = '审批执行数据加载失败或当前账号无权限。'
  } finally {
    loading.value = false
  }
}

async function confirm(itemId: string, result: 'SUCCEEDED' | 'FAILED' | 'SKIPPED') {
  busyItem.value = itemId
  error.value = null
  try {
    await recordExecution({
      itemId,
      result,
      note: '人工在 Amazon 后台核对后回填',
      evidence: evidenceFiles.value[itemId],
    })
    await load()
  } catch {
    error.value = '执行回填失败；请检查状态、权限和幂等冲突。'
  } finally {
    busyItem.value = null
  }
}

function selectEvidence(itemId: string, event: unknown): void {
  const target = (
    event as { target?: { files?: ArrayLike<EvidenceFile> | null } }
  ).target
  evidenceFiles.value[itemId] = target?.files?.[0]
}

onMounted(load)
watch(() => context.selectedProfileId, load)
</script>

<template>
  <section class="panel">
    <p class="eyebrow">APPROVAL & EXECUTION</p>
    <h2>审批、版本与人工执行</h2>
    <p v-if="!context.selectedProfileId" class="empty-state">请先选择 Advertising Profile。</p>
    <p v-else-if="loading">正在加载动作预览…</p>
    <p v-if="error" class="error-banner">{{ error }}</p>
    <p v-else-if="!loading && items.length === 0" class="empty-state">
      暂无动作预览，请先在智能优化页选择建议。
    </p>
    <article v-for="preview in items" :key="preview.id" class="hero-card compact-card">
      <h3>Preview {{ preview.id }}</h3>
      <p>
        {{ preview.status }} · 版本 {{ preview.currentVersion }} ·
        {{ preview.version?.frozenAt ? '已冻结' : '可编辑' }}
      </p>
      <details>
        <summary>版本内容与审批记录</summary>
        <pre>{{ preview.version?.items }}</pre>
        <ul>
          <li v-for="approval in preview.approvals" :key="approval.id">
            {{ approval.decision }} · {{ approval.comment }}
          </li>
        </ul>
      </details>
      <div v-if="preview.execution" class="card-list">
        <h4>人工执行清单 · {{ preview.execution.status }}</h4>
        <section
          v-for="executionItem in preview.execution.items"
          :key="executionItem.id"
          class="selection-card"
        >
          <span>
            <strong>{{ executionItem.action.actionType }} · {{ executionItem.status }}</strong>
            <code>{{ executionItem.action }}</code>
          </span>
          <div v-if="executionItem.status === 'PENDING'" class="button-row">
            <label>
              执行证据（可选）
              <input
                type="file"
                accept=".jpg,.jpeg,.png,.pdf,.txt"
                @change="selectEvidence(executionItem.id, $event)"
              >
            </label>
            <button :disabled="busyItem === executionItem.id" @click="confirm(executionItem.id, 'SUCCEEDED')">
              确认成功
            </button>
            <button class="secondary-button" :disabled="busyItem === executionItem.id" @click="confirm(executionItem.id, 'FAILED')">
              标记失败
            </button>
            <button class="secondary-button" :disabled="busyItem === executionItem.id" @click="confirm(executionItem.id, 'SKIPPED')">
              跳过
            </button>
          </div>
        </section>
      </div>
    </article>
  </section>
</template>
