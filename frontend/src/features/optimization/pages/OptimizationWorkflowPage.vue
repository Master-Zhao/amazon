<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'

import {
  createAndSubmitPreview,
  decidePreview,
  fetchAnalysisTasks,
  fetchRecommendations,
  runAnalysis,
  type AnalysisTask,
  type AnalysisTaskSummary,
  type Recommendation,
} from '@/features/optimization/api/optimizationApi'
import { useTenantContextStore } from '@/features/tenant-context/stores/context'

const context = useTenantContextStore()
const analysis = ref<AnalysisTask | null>(null)
const recommendations = ref<Recommendation[]>([])
const selectedIds = ref<string[]>([])
const preview = ref<{ previewId: string; status: string } | null>(null)
const busy = ref(false)
const error = ref<string | null>(null)
const history = ref<AnalysisTaskSummary[]>([])

async function load(): Promise<void> {
  if (!context.selectedProfileId) return
  error.value = null
  try {
    const [recommendationItems, taskItems] = await Promise.all([
      fetchRecommendations(context.selectedProfileId),
      fetchAnalysisTasks(context.selectedProfileId),
    ])
    recommendations.value = recommendationItems
    history.value = taskItems
  } catch {
    error.value = '智能优化数据加载失败或当前账号无权限。'
  }
}

onMounted(load)
watch(() => context.selectedProfileId, load)

async function analyze(): Promise<void> {
  if (!context.selectedTenantId || !context.selectedProfileId) return
  busy.value = true
  error.value = null
  try {
    analysis.value = await runAnalysis(
      context.selectedTenantId,
      context.selectedProfileId,
    )
    recommendations.value = await fetchRecommendations(context.selectedProfileId)
    history.value = await fetchAnalysisTasks(context.selectedProfileId)
  } catch {
    error.value = '分析任务执行失败，请核对报表数据与权限。'
  } finally {
    busy.value = false
  }
}

async function submitPreview(): Promise<void> {
  if (
    !context.selectedTenantId ||
    !context.selectedProfileId ||
    selectedIds.value.length === 0
  ) return
  busy.value = true
  error.value = null
  try {
    preview.value = await createAndSubmitPreview({
      tenantId: context.selectedTenantId,
      profileId: context.selectedProfileId,
      recommendationIds: selectedIds.value,
    })
  } catch {
    error.value = '动作预览创建或提交失败。'
  } finally {
    busy.value = false
  }
}

async function approve(): Promise<void> {
  if (!preview.value) return
  busy.value = true
  error.value = null
  try {
    preview.value = await decidePreview(
      preview.value.previewId,
      'APPROVED',
      '在界面确认动作预览',
    )
  } catch {
    error.value = '审批失败；团队/企业空间不允许提交人自审批。'
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <section class="panel">
    <p class="eyebrow">OPTIMIZATION WORKFLOW</p>
    <h2>分析、建议与人工执行闭环</h2>
    <p v-if="!context.selectedProfileId" class="empty-state">
      请先在卖家空间选择 Advertising Profile。
    </p>
    <template v-else>
      <button class="primary-button" type="button" :disabled="busy" @click="analyze">
        {{ busy ? '处理中…' : '运行四 Agent 分析' }}
      </button>
      <p v-if="analysis">分析状态：{{ analysis.status }}；Agent 数：{{ analysis.runs.length }}</p>
      <p v-if="error" class="error-banner">{{ error }}</p>
      <div v-if="recommendations.length" class="card-list">
        <label v-for="item in recommendations" :key="item.id" class="selection-card">
          <input v-model="selectedIds" type="checkbox" :value="item.id">
          <span>
            <strong>{{ item.actionType }} · {{ item.riskLevel }}</strong>
            <small>{{ item.reason }}</small>
            <code>{{ item.beforeValue }} → {{ item.afterValue }}</code>
          </span>
        </label>
        <button type="button" :disabled="busy || selectedIds.length === 0" @click="submitPreview">
          冻结版本并提交审批
        </button>
      </div>
      <article v-if="preview" class="hero-card compact-card">
        <h3>动作预览 {{ preview.previewId }}</h3>
        <p>状态：{{ preview.status }}</p>
        <button
          v-if="preview.status === 'PENDING_APPROVAL'"
          type="button"
          :disabled="busy"
          @click="approve"
        >
          审批通过
        </button>
        <p v-if="preview.status === 'APPROVED'">
          已创建人工执行任务；系统不会调用真实 Amazon Ads API。
        </p>
      </article>
      <section v-if="history.length" class="table-scroll">
        <h3>分析任务</h3>
        <table>
          <thead><tr><th>时间</th><th>状态</th><th>错误</th></tr></thead>
          <tbody>
            <tr v-for="item in history" :key="item.taskId">
              <td>{{ new Date(item.createdAt).toLocaleString() }}</td>
              <td>{{ item.status }}</td>
              <td>{{ item.error || '—' }}</td>
            </tr>
          </tbody>
        </table>
      </section>
    </template>
  </section>
</template>
