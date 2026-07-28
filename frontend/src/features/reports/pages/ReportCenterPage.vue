<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'

import {
  fetchImportTask,
  fetchImportTasks,
  uploadReport,
  type ImportTask,
  type ImportTaskSummary,
  type ReportType,
} from '@/features/reports/api/reportApi'
import { useTenantContextStore } from '@/features/tenant-context/stores/context'

const context = useTenantContextStore()
const reportType = ref<ReportType>('CAMPAIGN')
const selectedFile = ref<globalThis.File | null>(null)
const task = ref<ImportTask | null>(null)
const submitting = ref(false)
const error = ref<string | null>(null)
const history = ref<ImportTaskSummary[]>([])

async function loadHistory(): Promise<void> {
  if (!context.selectedProfileId) return
  try {
    history.value = await fetchImportTasks(context.selectedProfileId)
  } catch {
    error.value = '导入任务列表加载失败或当前账号无权限'
  }
}

onMounted(loadHistory)
watch(() => context.selectedProfileId, loadHistory)

function chooseFile(event: globalThis.Event): void {
  selectedFile.value = (event.target as globalThis.HTMLInputElement).files?.[0] ?? null
}

async function submit(): Promise<void> {
  if (!context.selectedTenantId || !context.selectedProfileId || !selectedFile.value) return
  submitting.value = true
  error.value = null
  try {
    const created = await uploadReport({
      tenantId: context.selectedTenantId,
      profileId: context.selectedProfileId,
      reportType: reportType.value,
      file: selectedFile.value,
    })
    task.value = await fetchImportTask(created.taskId)
    await loadHistory()
  } catch {
    error.value = '报表上传或任务查询失败'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <section class="panel">
    <p class="eyebrow">DATA CENTER</p>
    <h2>报表上传与导入任务</h2>
    <p v-if="!context.selectedProfileId" class="empty-state">
      请先在卖家空间页选择 Advertising Profile。
    </p>
    <form v-else class="context-grid" @submit.prevent="submit">
      <label>
        报表类型
        <select v-model="reportType">
          <option value="CAMPAIGN">Campaign Report</option>
          <option value="TARGETING">Targeting Report</option>
          <option value="SEARCH_TERM">Search Term Report</option>
        </select>
      </label>
      <label>
        CSV / XLSX 文件
        <input type="file" accept=".csv,.xlsx" required @change="chooseFile">
      </label>
      <button class="primary-button" type="submit" :disabled="submitting">
        {{ submitting ? '正在创建任务…' : '上传并异步导入' }}
      </button>
    </form>
    <p v-if="error" class="error-banner">{{ error }}</p>
    <article v-if="task" class="hero-card">
      <h3>任务 {{ task.taskId }}</h3>
      <p>状态：{{ task.status }}；重复文件：{{ task.isDuplicate ? '是' : '否' }}</p>
      <p v-if="task.batch">
        总行 {{ task.batch.totalRows }}，成功 {{ task.batch.succeededRows }}，失败
        {{ task.batch.failedRows }}
      </p>
      <ul v-if="task.batch?.errors.length">
        <li v-for="item in task.batch.errors" :key="`${item.rowNumber}-${item.code}`">
          第 {{ item.rowNumber }} 行 · {{ item.field }} · {{ item.code }}
        </li>
      </ul>
    </article>
    <section v-if="history.length" class="table-scroll">
      <h3>历史导入任务</h3>
      <table>
        <thead><tr><th>文件</th><th>类型</th><th>状态</th><th>失败行</th></tr></thead>
        <tbody>
          <tr v-for="item in history" :key="item.taskId">
            <td>{{ item.originalName }}</td>
            <td>{{ item.reportType }}</td>
            <td>{{ item.status }}</td>
            <td>{{ item.failedRows ?? '—' }}</td>
          </tr>
        </tbody>
      </table>
    </section>
  </section>
</template>
