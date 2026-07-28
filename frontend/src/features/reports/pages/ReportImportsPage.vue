<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import {
  downloadImportSource,
  fetchImportErrors,
  fetchImportTasks,
  reprocessImport,
  uploadReport,
  type ImportRowError,
  type ImportTask,
  type ReportType,
} from '@/features/reports/api/reportApi'
import { useTenantContextStore } from '@/features/tenant-context/stores/tenantContext'
import { normalizeApiError } from '@/shared/api/httpClient'

const context = useTenantContextStore()
const tasks = ref<ImportTask[]>([])
const selectedFile = ref<globalThis.File | null>(null)
const reportType = ref<ReportType>('CAMPAIGN')
const selectedTaskId = ref<string | null>(null)
const errors = ref<ImportRowError[]>([])
const loading = ref(false)
const uploading = ref(false)
const uploadProgress = ref(0)
const errorMessage = ref<string | null>(null)
let pollTimer: ReturnType<typeof globalThis.setTimeout> | null = null

const selectedTask = computed(
  () => tasks.value.find((task) => task.id === selectedTaskId.value) ?? null,
)
const canUpload = computed(() => {
  const profile = context.currentProfile
  if (!profile) return false
  const allowedByRole =
    context.membershipRole === 'OWNER' || context.membershipRole === 'ADMIN'
  const allowedByFeature = context.permissionCodes.includes('reports.upload')
  const level = ['VIEW', 'OPERATE', 'APPROVE', 'EXECUTE', 'MANAGE'].indexOf(
    profile.accessLevel,
  )
  return (allowedByRole || allowedByFeature) && level >= 1
})
const hasPendingTasks = computed(() =>
  tasks.value.some((task) => ['QUEUED', 'RUNNING'].includes(task.status)),
)

function clearPoll(): void {
  if (pollTimer) {
    globalThis.clearTimeout(pollTimer)
    pollTimer = null
  }
}

function schedulePoll(): void {
  clearPoll()
  if (hasPendingTasks.value) {
    pollTimer = globalThis.setTimeout(() => void refreshTasks(), 1500)
  }
}

async function refreshTasks(): Promise<void> {
  if (!context.tenantId || !context.profileId) {
    tasks.value = []
    return
  }
  loading.value = true
  errorMessage.value = null
  try {
    tasks.value = await fetchImportTasks(context.tenantId, context.profileId)
    if (
      selectedTaskId.value &&
      !tasks.value.some((task) => task.id === selectedTaskId.value)
    ) {
      selectedTaskId.value = null
      errors.value = []
    }
  } catch (error) {
    errorMessage.value = normalizeApiError(error).message
  } finally {
    loading.value = false
    schedulePoll()
  }
}

function chooseFile(event: globalThis.Event): void {
  selectedFile.value =
    (event.target as globalThis.HTMLInputElement).files?.item(0) ?? null
  uploadProgress.value = 0
}

async function submitUpload(): Promise<void> {
  if (!context.tenantId || !context.profileId || !selectedFile.value) return
  uploading.value = true
  errorMessage.value = null
  try {
    const task = await uploadReport(
      context.tenantId,
      context.profileId,
      reportType.value,
      selectedFile.value,
      (event) => {
        uploadProgress.value = event.total
          ? Math.round((event.loaded / event.total) * 100)
          : 0
      },
    )
    tasks.value = [task, ...tasks.value]
    selectedFile.value = null
    uploadProgress.value = 100
    schedulePoll()
  } catch (error) {
    errorMessage.value = normalizeApiError(error).message
  } finally {
    uploading.value = false
  }
}

async function showErrors(task: ImportTask): Promise<void> {
  if (!context.tenantId) return
  selectedTaskId.value = task.id
  errors.value = []
  errorMessage.value = null
  try {
    errors.value = await fetchImportErrors(context.tenantId, task.id)
  } catch (error) {
    errorMessage.value = normalizeApiError(error).message
  }
}

async function reprocess(task: ImportTask): Promise<void> {
  if (!context.tenantId) return
  errorMessage.value = null
  try {
    const next = await reprocessImport(context.tenantId, task.id)
    tasks.value = [next, ...tasks.value]
    schedulePoll()
  } catch (error) {
    errorMessage.value = normalizeApiError(error).message
  }
}

async function downloadSource(task: ImportTask): Promise<void> {
  if (!context.tenantId) return
  errorMessage.value = null
  try {
    const blob = await downloadImportSource(context.tenantId, task.id)
    const url = globalThis.URL.createObjectURL(blob)
    const anchor = globalThis.document.createElement('a')
    anchor.href = url
    anchor.download = task.upload.originalFilename
    anchor.click()
    globalThis.URL.revokeObjectURL(url)
  } catch (error) {
    errorMessage.value = normalizeApiError(error).message
  }
}

watch(
  () => [context.tenantId, context.profileId],
  () => void refreshTasks(),
)

onMounted(async () => {
  if (context.status === 'idle') await context.initialize()
  await refreshTasks()
})
onBeforeUnmount(clearPoll)
</script>

<template>
  <section class="report-page">
    <header class="report-heading">
      <div>
        <p class="eyebrow">ASYNCHRONOUS DATA INTAKE</p>
        <h2>Campaign、Targeting 与 Search Term 报表导入</h2>
        <p>
          文件经 Django 权限检查后保存，由 Redis/Celery 异步解析并通过 Service
          发布到 MySQL。页面不会用静态结果模拟导入状态。
        </p>
      </div>
      <RouterLink class="secondary-link" to="/context">切换演示上下文</RouterLink>
    </header>

    <div v-if="!context.isComplete" class="empty-panel">
      请先选择 Tenant、Store、Marketplace 和 AdvertisingProfile。
      <RouterLink to="/context">前往上下文选择</RouterLink>
    </div>

    <template v-else>
      <div class="context-strip">
        <strong>{{ context.currentTenant?.name }}</strong>
        <span>{{ context.currentStore?.name }}</span>
        <span>{{ context.currentMarketplace?.marketplace.code }}</span>
        <span>{{ context.currentProfile?.name }}</span>
      </div>

      <form class="upload-panel" @submit.prevent="submitUpload">
        <div>
          <strong>上传 CSV 或 XLSX</strong>
          <p>请选择与文件一致的报表类型；三类报表分别发布到独立权威事实表。</p>
        </div>
        <label>
          报表类型
          <select v-model="reportType">
            <option value="CAMPAIGN">Campaign</option>
            <option value="TARGETING">Targeting</option>
            <option value="SEARCH_TERM">Search Term</option>
          </select>
        </label>
        <input
          aria-label="Campaign report file"
          type="file"
          accept=".csv,.xlsx"
          :disabled="uploading || !canUpload"
          @change="chooseFile"
        >
        <button
          type="submit"
          :disabled="uploading || !selectedFile || !canUpload"
        >
          {{ uploading ? `上传中 ${uploadProgress}%` : '上传并异步导入' }}
        </button>
        <p v-if="!canUpload" class="permission-note">
          当前 Profile 缺少 reports.upload 或 OPERATE 权限。
        </p>
      </form>

      <div v-if="errorMessage" class="error-panel" role="alert">
        {{ errorMessage }}
      </div>

      <div class="task-toolbar">
        <h3>导入任务</h3>
        <button class="secondary-button" type="button" @click="refreshTasks">
          {{ loading ? '刷新中…' : '刷新' }}
        </button>
      </div>

      <p v-if="loading && tasks.length === 0" role="status">正在加载任务…</p>
      <p v-else-if="tasks.length === 0" class="empty-panel">
        当前 Profile 尚无导入任务。
      </p>
      <div v-else class="task-table-wrap">
        <table class="task-table">
          <thead>
            <tr>
              <th>文件</th>
              <th>状态</th>
              <th>成功 / 总计</th>
              <th>错误</th>
              <th>创建时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="task in tasks" :key="task.id">
              <td>
                {{ task.upload.reportType }} · {{ task.upload.originalFilename }}
                <small v-if="task.upload.duplicateOfId">重复文件</small>
              </td>
              <td>
                <span :class="['task-status', `status-${task.status.toLowerCase()}`]">
                  {{ task.status }}
                </span>
              </td>
              <td>{{ task.successRows }} / {{ task.totalRows }}</td>
              <td>{{ task.errorRows }}</td>
              <td>{{ new Date(task.createdAt).toLocaleString() }}</td>
              <td class="task-actions">
                <button type="button" @click="downloadSource(task)">
                  下载原文件
                </button>
                <button
                  v-if="task.errorRows"
                  class="secondary-button"
                  type="button"
                  @click="showErrors(task)"
                >
                  错误明细
                </button>
                <button
                  v-if="task.status === 'FAILED'"
                  class="secondary-button"
                  type="button"
                  :disabled="!canUpload"
                  @click="reprocess(task)"
                >
                  重新处理
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <section v-if="selectedTask" class="error-detail">
        <h3>任务 #{{ selectedTask.id }} 错误明细</h3>
        <p v-if="errors.length === 0">该任务没有可显示的行错误。</p>
        <table v-else class="task-table">
          <thead>
            <tr>
              <th>行号</th>
              <th>错误码</th>
              <th>字段</th>
              <th>说明</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in errors" :key="item.id">
              <td>{{ item.rowNumber }}</td>
              <td>{{ item.errorCode }}</td>
              <td>{{ item.fieldName || '—' }}</td>
              <td>{{ item.message }}</td>
            </tr>
          </tbody>
        </table>
      </section>
    </template>
  </section>
</template>
