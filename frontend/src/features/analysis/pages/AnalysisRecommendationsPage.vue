<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import { createActionPreview } from '@/features/actions/api/actionsApi'
import {
  acceptRecommendation,
  cancelAgentRun,
  createAgentRun,
  dismissRecommendation,
  fetchAgentRuns,
  fetchRecommendations,
  reviseRecommendation,
  type AgentRun,
  type Recommendation,
} from '@/features/analysis/api/analysisApi'
import { useTenantContextStore } from '@/features/tenant-context/stores/tenantContext'
import { normalizeApiError } from '@/shared/api/httpClient'

const context = useTenantContextStore()
const runs = ref<AgentRun[]>([])
const recommendations = ref<Recommendation[]>([])
const loading = ref(false)
const errorMessage = ref<string | null>(null)
const createdPreviewIds = ref<Record<string, string>>({})
let pollTimer: ReturnType<typeof globalThis.setTimeout> | null = null

const canRun = computed(() => {
  const profile = context.currentProfile
  if (!profile) return false
  const roleAllows =
    context.membershipRole === 'OWNER' || context.membershipRole === 'ADMIN'
  return (
    (roleAllows || context.permissionCodes.includes('analysis.run')) &&
    profile.accessLevel !== 'VIEW'
  )
})

function schedulePoll(): void {
  if (pollTimer) globalThis.clearTimeout(pollTimer)
  if (runs.value.some((run) => ['QUEUED', 'RUNNING'].includes(run.status))) {
    pollTimer = globalThis.setTimeout(() => void refresh(), 1500)
  }
}

async function refresh(): Promise<void> {
  if (!context.tenantId || !context.profileId) {
    runs.value = []
    recommendations.value = []
    return
  }
  loading.value = true
  errorMessage.value = null
  try {
    ;[runs.value, recommendations.value] = await Promise.all([
      fetchAgentRuns(context.tenantId, context.profileId),
      fetchRecommendations(context.tenantId, context.profileId),
    ])
  } catch (error) {
    errorMessage.value = normalizeApiError(error).message
  } finally {
    loading.value = false
    schedulePoll()
  }
}

async function runAnalysis(): Promise<void> {
  if (!context.tenantId || !context.profileId) return
  errorMessage.value = null
  try {
    const run = await createAgentRun(context.tenantId, context.profileId)
    runs.value = [run, ...runs.value]
    schedulePoll()
  } catch (error) {
    errorMessage.value = normalizeApiError(error).message
  }
}

async function cancelRun(run: AgentRun): Promise<void> {
  if (!context.tenantId) return
  errorMessage.value = null
  try {
    const updated = await cancelAgentRun(context.tenantId, run.id)
    runs.value = runs.value.map((item) =>
      item.id === updated.id ? updated : item,
    )
  } catch (error) {
    errorMessage.value = normalizeApiError(error).message
  }
}

async function makePreview(recommendation: Recommendation): Promise<void> {
  if (!context.tenantId) return
  errorMessage.value = null
  try {
    const preview = await createActionPreview(
      context.tenantId,
      recommendation.id,
    )
    createdPreviewIds.value[recommendation.id] = preview.id
  } catch (error) {
    errorMessage.value = normalizeApiError(error).message
  }
}

async function updateRecommendation(
  operation: () => Promise<Recommendation>,
): Promise<void> {
  errorMessage.value = null
  try {
    const updated = await operation()
    recommendations.value = recommendations.value.map((item) =>
      item.id === updated.id ? updated : item,
    )
    await refresh()
  } catch (error) {
    errorMessage.value = normalizeApiError(error).message
  }
}

function accept(item: Recommendation): Promise<void> {
  if (!context.tenantId) return Promise.resolve()
  return updateRecommendation(() =>
    acceptRecommendation(context.tenantId!, item.id),
  )
}

function dismiss(item: Recommendation): Promise<void> {
  if (!context.tenantId) return Promise.resolve()
  return updateRecommendation(() =>
    dismissRecommendation(
      context.tenantId!,
      item.id,
      'Rejected after human review.',
    ),
  )
}

function revise(item: Recommendation): Promise<void> {
  if (!context.tenantId) return Promise.resolve()
  const value = globalThis.prompt(
    '编辑 afterValue JSON',
    JSON.stringify(item.currentRevision.afterValue),
  )
  if (!value) return Promise.resolve()
  try {
    const afterValue = JSON.parse(value) as Record<string, string>
    return updateRecommendation(() =>
      reviseRecommendation(context.tenantId!, item.id, {
        afterValue,
        reason: 'Revised after human review.',
        evidence: [{ source: 'human-review' }],
        riskLevel: item.currentRevision.riskLevel as 'LOW' | 'MEDIUM' | 'HIGH',
      }),
    )
  } catch {
    errorMessage.value = 'afterValue 必须是合法 JSON。'
    return Promise.resolve()
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
onBeforeUnmount(() => {
  if (pollTimer) globalThis.clearTimeout(pollTimer)
})
</script>

<template>
  <section class="report-page">
    <header class="report-heading">
      <div>
        <p class="eyebrow">MOCK LLM · STRUCTURED OUTPUT</p>
        <h2>AI 分析与 Recommendation</h2>
        <p>
          四类 Agent 只接收当前授权 Profile 的最小数据，由 Orchestrator
          调用 MockLLMProvider。后端 Schema、归属、金额和当前值校验通过后才保存建议。
        </p>
      </div>
      <button type="button" :disabled="!canRun || loading" @click="runAnalysis">
        运行 Mock 智能分析
      </button>
    </header>

    <p v-if="!context.isComplete" class="empty-panel">
      请先完成演示上下文并导入 Campaign 报表。
    </p>
    <template v-else>
      <div v-if="errorMessage" class="error-panel" role="alert">
        {{ errorMessage }}
      </div>

      <section class="workflow-section">
        <div class="task-toolbar">
          <h3>AgentRun</h3>
          <button class="secondary-button" type="button" @click="refresh">刷新</button>
        </div>
        <p v-if="runs.length === 0" class="empty-panel">尚无分析任务。</p>
        <div v-else class="run-list">
          <article v-for="run in runs" :key="run.id">
            <strong>Run #{{ run.id }}</strong>
            <span :class="['task-status', `status-${run.status.toLowerCase()}`]">
              {{ run.status }}
            </span>
            <small>{{ run.schemaVersion }} · Task {{ run.celeryTaskId }}</small>
            <p v-if="run.errorMessage">{{ run.errorCode }} · {{ run.errorMessage }}</p>
            <button
              v-if="['QUEUED', 'RUNNING'].includes(run.status)"
              class="secondary-button"
              type="button"
              @click="cancelRun(run)"
            >
              取消分析
            </button>
          </article>
        </div>
      </section>

      <section class="workflow-section">
        <h3>结构化 Recommendation</h3>
        <p v-if="recommendations.length === 0" class="empty-panel">
          暂无已验证建议。请先运行分析并等待 SUCCEEDED。
        </p>
        <div v-else class="recommendation-grid">
          <article v-for="item in recommendations" :key="item.id">
            <header>
              <div>
                <small>{{ item.actionType }} · {{ item.currentRevision.riskLevel }}</small>
                <h4>{{ item.campaignName }}</h4>
              </div>
              <span>{{ item.status }} · v{{ item.currentRevision.revisionNumber }}</span>
            </header>
            <p>{{ item.currentRevision.reason }}</p>
            <dl>
              <dt>Before</dt>
              <dd>{{ item.currentRevision.beforeValue }}</dd>
              <dt>After</dt>
              <dd>{{ item.currentRevision.afterValue }}</dd>
            </dl>
            <div class="preview-actions">
              <button
                v-if="item.status === 'ACTIVE'"
                type="button"
                @click="accept(item)"
              >
                接受建议
              </button>
              <button
                v-if="['ACTIVE', 'ACCEPTED'].includes(item.status)"
                class="secondary-button"
                type="button"
                @click="revise(item)"
              >
                修订
              </button>
              <button
                v-if="['ACTIVE', 'ACCEPTED'].includes(item.status)"
                class="secondary-button"
                type="button"
                @click="dismiss(item)"
              >
                拒绝
              </button>
              <button
                v-if="item.status !== 'DISMISSED'"
                type="button"
                :disabled="Boolean(createdPreviewIds[item.id])"
                @click="makePreview(item)"
              >
                {{
                  createdPreviewIds[item.id]
                    ? `已创建 Preview #${createdPreviewIds[item.id]}`
                    : '生成 Action Preview'
                }}
              </button>
            </div>
          </article>
        </div>
      </section>
    </template>
  </section>
</template>
