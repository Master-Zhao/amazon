<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'

import {
  decideActionPreview,
  fetchActionPreviews,
  recordManualExecution,
  submitActionPreview,
  type ActionPreview,
} from '@/features/actions/api/actionsApi'
import { useTenantContextStore } from '@/features/tenant-context/stores/tenantContext'
import { normalizeApiError } from '@/shared/api/httpClient'

const context = useTenantContextStore()
const items = ref<ActionPreview[]>([])
const loading = ref(false)
const busyPreviewId = ref<string | null>(null)
const errorMessage = ref<string | null>(null)

async function load(): Promise<void> {
  if (!context.tenantId || !context.profileId) {
    items.value = []
    return
  }
  loading.value = true
  errorMessage.value = null
  try {
    items.value = await fetchActionPreviews(context.tenantId, context.profileId)
  } catch (error) {
    errorMessage.value = normalizeApiError(error).message
  } finally {
    loading.value = false
  }
}

async function submit(preview: ActionPreview): Promise<void> {
  if (!context.tenantId) return
  busyPreviewId.value = preview.id
  errorMessage.value = null
  try {
    const updated = await submitActionPreview(context.tenantId, preview.id)
    items.value = items.value.map((item) => (item.id === updated.id ? updated : item))
  } catch (error) {
    errorMessage.value = normalizeApiError(error).message
  } finally {
    busyPreviewId.value = null
  }
}

async function decide(
  preview: ActionPreview,
  decision: 'APPROVED' | 'REJECTED' | 'RETURNED',
): Promise<void> {
  if (!context.tenantId) return
  busyPreviewId.value = preview.id
  errorMessage.value = null
  try {
    const updated = await decideActionPreview(
      context.tenantId,
      preview.id,
      decision,
      decision === 'APPROVED' ? '审批通过' : decision === 'REJECTED' ? '审批拒绝' : '退回修订',
    )
    items.value = items.value.map((item) => (item.id === updated.id ? updated : item))
  } catch (error) {
    errorMessage.value = normalizeApiError(error).message
  } finally {
    busyPreviewId.value = null
  }
}

async function recordExecution(
  preview: ActionPreview,
  outcome: 'SUCCEEDED' | 'FAILED' | 'SKIPPED',
): Promise<void> {
  if (!context.tenantId) return
  busyPreviewId.value = preview.id
  errorMessage.value = null
  try {
    const updated = await recordManualExecution(
      context.tenantId,
      preview.id,
      outcome,
      {},
      '人工在 Amazon 后台核对后回填',
    )
    items.value = items.value.map((item) => (item.id === updated.id ? updated : item))
  } catch (error) {
    errorMessage.value = normalizeApiError(error).message
  } finally {
    busyPreviewId.value = null
  }
}

watch(() => [context.tenantId, context.profileId], () => void load())
onMounted(async () => {
  if (context.status === 'idle') await context.initialize()
  await load()
})
</script>

<template>
  <section class="report-page">
    <header class="report-heading">
      <div>
        <p class="eyebrow">APPROVAL & EXECUTION</p>
        <h2>审批、版本与人工执行</h2>
        <p>Action Preview 创建后在此提交审批、审批决策和回填执行结果。</p>
      </div>
      <button class="secondary-button" type="button" @click="load">
        {{ loading ? '刷新中…' : '刷新' }}
      </button>
    </header>

    <div v-if="errorMessage" class="error-panel" role="alert">
      {{ errorMessage }}
    </div>
    <p v-if="!context.isComplete" class="empty-panel">
      请先完成演示上下文并选择 Advertising Profile。
    </p>
    <p v-else-if="!loading && items.length === 0" class="empty-panel">
      暂无动作预览，请先在智能优化页生成 Action Preview。
    </p>
    <template v-else>
      <article v-for="preview in items" :key="preview.id" class="workflow-section">
        <header>
          <div>
            <small>{{ preview.actionType }} · {{ preview.status }}</small>
            <h3>{{ preview.campaignName }} — Preview #{{ preview.id }}</h3>
          </div>
          <span>版本 {{ preview.currentVersionNumber }}</span>
        </header>

        <dl v-if="preview.currentVersion">
          <dt>Before</dt>
          <dd>{{ preview.currentVersion.actionPayload.beforeValue }}</dd>
          <dt>After</dt>
          <dd>{{ preview.currentVersion.actionPayload.afterValue }}</dd>
          <dt>Reason</dt>
          <dd>{{ preview.currentVersion.actionPayload.reason }}</dd>
        </dl>

        <div v-if="preview.approvals.length" class="preview-actions">
          <h4>审批记录</h4>
          <ul>
            <li v-for="approval in preview.approvals" :key="approval.id">
              {{ approval.decision }} · {{ approval.decidedByEmail }} · {{ approval.comment }}
            </li>
          </ul>
        </div>

        <div v-if="preview.executions.length" class="preview-actions">
          <h4>执行记录</h4>
          <ul>
            <li v-for="execution in preview.executions" :key="execution.id">
              {{ execution.outcome }} · {{ execution.recordedByEmail }} · {{ execution.note }}
            </li>
          </ul>
        </div>

        <div class="preview-actions">
          <button
            v-if="preview.status === 'DRAFT'"
            type="button"
            :disabled="busyPreviewId === preview.id"
            @click="submit(preview)"
          >
            提交审批
          </button>
          <button
            v-if="preview.status === 'PENDING_APPROVAL'"
            type="button"
            :disabled="busyPreviewId === preview.id"
            @click="decide(preview, 'APPROVED')"
          >
            审批通过
          </button>
          <button
            v-if="preview.status === 'PENDING_APPROVAL'"
            class="secondary-button"
            type="button"
            :disabled="busyPreviewId === preview.id"
            @click="decide(preview, 'REJECTED')"
          >
            审批拒绝
          </button>
          <button
            v-if="preview.status === 'PENDING_APPROVAL'"
            class="secondary-button"
            type="button"
            :disabled="busyPreviewId === preview.id"
            @click="decide(preview, 'RETURNED')"
          >
            退回修订
          </button>
          <template v-if="preview.status === 'APPROVED'">
            <button
              type="button"
              :disabled="busyPreviewId === preview.id"
              @click="recordExecution(preview, 'SUCCEEDED')"
            >
              确认成功
            </button>
            <button
              class="secondary-button"
              type="button"
              :disabled="busyPreviewId === preview.id"
              @click="recordExecution(preview, 'FAILED')"
            >
              标记失败
            </button>
            <button
              class="secondary-button"
              type="button"
              :disabled="busyPreviewId === preview.id"
              @click="recordExecution(preview, 'SKIPPED')"
            >
              跳过
            </button>
          </template>
        </div>
      </article>
    </template>
  </section>
</template>
