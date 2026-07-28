<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'

import {
  createEffectEvaluation,
  decideActionPreview,
  fetchActionPreviews,
  recordManualExecution,
  reviseReturnedActionPreview,
  submitActionPreview,
  withdrawActionPreview,
  type ActionPreview,
  type ExecutionRecord,
} from '@/features/actions/api/actionsApi'
import { useTenantContextStore } from '@/features/tenant-context/stores/tenantContext'
import { normalizeApiError } from '@/shared/api/httpClient'

const context = useTenantContextStore()
const previews = ref<ActionPreview[]>([])
const loading = ref(false)
const errorMessage = ref<string | null>(null)
const evidenceFiles = ref<Record<string, globalThis.File | undefined>>({})
const observedAcos = ref('')
const observedWindowDays = ref('7')
const evaluations = computed(() =>
  previews.value.flatMap((preview) =>
    preview.executions.flatMap((record) => record.effectEvaluations ?? []),
  ),
)

async function refresh(): Promise<void> {
  if (!context.tenantId || !context.profileId) {
    previews.value = []
    return
  }
  loading.value = true
  errorMessage.value = null
  try {
    previews.value = await fetchActionPreviews(
      context.tenantId,
      context.profileId,
    )
  } catch (error) {
    errorMessage.value = normalizeApiError(error).message
  } finally {
    loading.value = false
  }
}

async function transition(
  operation: () => Promise<ActionPreview>,
): Promise<void> {
  errorMessage.value = null
  try {
    const updated = await operation()
    previews.value = previews.value.map((item) =>
      item.id === updated.id ? updated : item,
    )
    await refresh()
  } catch (error) {
    errorMessage.value = normalizeApiError(error).message
  }
}

function submit(preview: ActionPreview): Promise<void> {
  if (!context.tenantId) return Promise.resolve()
  return transition(() => submitActionPreview(context.tenantId!, preview.id))
}

function decide(
  preview: ActionPreview,
  decision: 'APPROVED' | 'REJECTED' | 'RETURNED',
): Promise<void> {
  if (!context.tenantId) return Promise.resolve()
  return transition(() =>
    decideActionPreview(
      context.tenantId!,
      preview.id,
      decision,
      `${decision} after reviewing the immutable preview.`,
    ),
  )
}

function withdraw(preview: ActionPreview): Promise<void> {
  if (!context.tenantId) return Promise.resolve()
  return transition(() =>
    withdrawActionPreview(context.tenantId!, preview.id),
  )
}

function reviseReturned(preview: ActionPreview): Promise<void> {
  if (!context.tenantId) return Promise.resolve()
  const value = globalThis.prompt(
    '编辑新版本 afterValue JSON',
    JSON.stringify(preview.currentVersion.actionPayload.afterValue),
  )
  if (!value) return Promise.resolve()
  try {
    const afterValue = JSON.parse(value) as Record<string, string>
    const actionPayload = {
      ...preview.currentVersion.actionPayload,
      afterValue,
      reason: 'Revised after RETURNED decision.',
      evidence: [{ source: 'human-review' }],
    }
    return transition(() =>
      reviseReturnedActionPreview(
        context.tenantId!,
        preview.id,
        actionPayload,
      ),
    )
  } catch {
    errorMessage.value = 'afterValue 必须是合法 JSON。'
    return Promise.resolve()
  }
}

function execute(
  preview: ActionPreview,
  outcome: 'SUCCEEDED' | 'FAILED' | 'SKIPPED',
): Promise<void> {
  if (!context.tenantId) return Promise.resolve()
  return transition(() =>
    recordManualExecution(
      context.tenantId!,
      preview.id,
      outcome,
      outcome === 'SUCCEEDED'
        ? preview.currentVersion.actionPayload.afterValue
        : {},
      `${outcome} recorded after fictional manual Amazon console work.`,
      evidenceFiles.value[preview.id],
    ),
  )
}

function chooseEvidence(
  preview: ActionPreview,
  event: unknown,
): void {
  const input = (
    event as {
      target: {
        files?: ArrayLike<globalThis.File> | null
      }
    }
  ).target
  evidenceFiles.value[preview.id] = input.files?.[0]
}

async function queueEvaluation(
  preview: ActionPreview,
  record: ExecutionRecord,
): Promise<void> {
  if (!context.tenantId) return
  if (!observedAcos.value || !observedWindowDays.value) {
    errorMessage.value = '请填写观察 ACOS 和观察天数。'
    return
  }
  errorMessage.value = null
  try {
    await createEffectEvaluation(context.tenantId, preview.id, record.id, {
      acos: observedAcos.value,
      windowDays: Number(observedWindowDays.value),
    })
    await refresh()
  } catch (error) {
    errorMessage.value = normalizeApiError(error).message
  }
}

watch(
  () => [context.tenantId, context.profileId],
  () => void refresh(),
)
onMounted(async () => {
  if (context.status === 'idle') await context.initialize()
  await refresh()
})
</script>

<template>
  <section class="report-page">
    <header class="report-heading">
      <div>
        <p class="eyebrow">HUMAN-IN-THE-LOOP</p>
        <h2>Action Preview、审批与执行回填</h2>
        <p>
          提交后的版本不可修改；审批和人工执行记录只追加。系统不会调用真实 Amazon
          Ads API，也不会自动修改广告。
        </p>
      </div>
      <button class="secondary-button" type="button" @click="refresh">
        {{ loading ? '刷新中…' : '刷新' }}
      </button>
    </header>

    <div v-if="errorMessage" class="error-panel" role="alert">
      {{ errorMessage }}
    </div>
    <p v-if="previews.length === 0" class="empty-panel">
      暂无 Action Preview。请从 Recommendation 页面创建。
    </p>
    <div v-else class="preview-list">
      <article v-for="preview in previews" :key="preview.id">
        <header>
          <div>
            <small>Preview #{{ preview.id }} · v{{ preview.currentVersionNumber }}</small>
            <h3>{{ preview.campaignName }}</h3>
          </div>
          <span :class="['task-status', `status-${preview.status.toLowerCase()}`]">
            {{ preview.status }}
          </span>
        </header>
        <p>{{ preview.currentVersion.actionPayload.reason }}</p>
        <div class="action-values">
          <code>{{ preview.currentVersion.actionPayload.beforeValue }}</code>
          <span>→</span>
          <code>{{ preview.currentVersion.actionPayload.afterValue }}</code>
        </div>
        <div class="preview-actions">
          <label
            v-if="preview.status === 'APPROVED' && preview.executions.length === 0"
          >
            执行证据（可选：PDF/PNG/JPEG/TXT）
            <input
              type="file"
              accept=".pdf,.png,.jpg,.jpeg,.txt"
              @change="chooseEvidence(preview, $event)"
            >
          </label>
          <button
            v-if="preview.status === 'DRAFT'"
            type="button"
            @click="submit(preview)"
          >
            提交审批
          </button>
          <button
            v-if="['DRAFT', 'PENDING_APPROVAL'].includes(preview.status)"
            class="secondary-button"
            type="button"
            @click="withdraw(preview)"
          >
            撤回
          </button>
          <button
            v-if="preview.status === 'PENDING_APPROVAL'"
            type="button"
            @click="decide(preview, 'APPROVED')"
          >
            批准
          </button>
          <button
            v-if="preview.status === 'PENDING_APPROVAL'"
            class="secondary-button"
            type="button"
            @click="decide(preview, 'REJECTED')"
          >
            拒绝
          </button>
          <button
            v-if="preview.status === 'PENDING_APPROVAL'"
            class="secondary-button"
            type="button"
            @click="decide(preview, 'RETURNED')"
          >
            退回
          </button>
          <button
            v-if="preview.status === 'RETURNED'"
            type="button"
            @click="reviseReturned(preview)"
          >
            创建修订版本
          </button>
          <button
            v-if="preview.status === 'APPROVED' && preview.executions.length === 0"
            type="button"
            @click="execute(preview, 'SUCCEEDED')"
          >
            回填人工执行成功
          </button>
          <button
            v-if="preview.status === 'APPROVED' && preview.executions.length === 0"
            class="secondary-button"
            type="button"
            @click="execute(preview, 'FAILED')"
          >
            回填失败
          </button>
          <button
            v-if="preview.status === 'APPROVED' && preview.executions.length === 0"
            class="secondary-button"
            type="button"
            @click="execute(preview, 'SKIPPED')"
          >
            回填跳过
          </button>
        </div>
        <div v-if="preview.approvals.length" class="record-list">
          <strong>审批记录</strong>
          <span v-for="record in preview.approvals" :key="record.id">
            {{ record.decision }} · {{ record.decidedByEmail }} · {{ record.comment }}
          </span>
        </div>
        <div v-if="preview.executions.length" class="record-list">
          <strong>执行记录</strong>
          <div v-for="record in preview.executions" :key="record.id">
            <span>
              {{ record.outcome }} · {{ record.recordedByEmail }} · {{ record.note }}
            </span>
            <small v-if="record.evidenceMetadata.originalFilename">
              {{ record.evidenceMetadata.originalFilename }} ·
              {{ record.evidenceMetadata.sha256 }}
            </small>
            <button
              v-if="['SUCCEEDED', 'SUCCESS'].includes(record.outcome)"
              class="secondary-button"
              type="button"
              @click="queueEvaluation(preview, record)"
            >
              创建效果评估
            </button>
          </div>
        </div>
      </article>
    </div>

    <section class="workflow-section">
      <h3>效果评估窗口</h3>
      <p>
        后端按执行日期生成固定基线和观察窗口；此处只回填已观察结果，
        不做因果归因或收益承诺。
      </p>
      <div class="action-values">
        <label>观察 ACOS <input v-model="observedAcos" inputmode="decimal"></label>
        <label>观察天数 <input v-model="observedWindowDays" type="number" min="1"></label>
      </div>
      <p v-if="evaluations.length === 0" class="empty-panel">暂无效果评估。</p>
      <div v-else class="record-list">
        <span v-for="evaluation in evaluations" :key="evaluation.id">
          #{{ evaluation.id }} · {{ evaluation.status }} ·
          {{ evaluation.baselineStart }}—{{ evaluation.baselineEnd }} /
          {{ evaluation.observationStart }}—{{ evaluation.observationEnd }}
          <code>{{ evaluation.result }}</code>
        </span>
      </div>
    </section>
  </section>
</template>
