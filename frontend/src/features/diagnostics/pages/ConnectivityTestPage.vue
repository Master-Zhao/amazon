<script setup lang="ts">
import { onMounted, ref } from 'vue'

import {
  fetchConnectivityTenants,
  type TenantItem,
} from '@/shared/api/connectivityApi'
import {
  fetchRemoteAccount,
  type RemoteAccount,
} from '@/features/auth/api/authApi'
import type { ApiError } from '@/shared/api/types'

type PageState = 'idle' | 'loading' | 'success' | 'error'

const state = ref<PageState>('idle')
const total = ref(0)
const tenants = ref<TenantItem[]>([])
const error = ref<ApiError | null>(null)
const requestId = ref<string | null>(null)
const fetchedAt = ref<string | null>(null)
const remoteState = ref<PageState>('idle')
const remoteAccount = ref<RemoteAccount | null>(null)
const remoteError = ref<ApiError | null>(null)

async function loadTenants(): Promise<void> {
  state.value = 'loading'
  error.value = null
  try {
    const data = await fetchConnectivityTenants()
    total.value = data.total
    tenants.value = data.tenants
    fetchedAt.value = new Date().toISOString()
    state.value = 'success'
  } catch (caught) {
    error.value = caught as ApiError
    requestId.value = error.value?.requestId ?? null
    state.value = 'error'
  }
}

async function loadRemoteAccount(): Promise<void> {
  remoteState.value = 'loading'
  remoteAccount.value = null
  remoteError.value = null
  try {
    remoteAccount.value = await fetchRemoteAccount()
    remoteState.value = 'success'
  } catch (caught) {
    remoteError.value = caught as ApiError
    remoteState.value = 'error'
  }
}

onMounted(() => {
  void loadTenants()
  void loadRemoteAccount()
})
</script>

<template>
  <section class="diagnostic-card">
    <div class="diagnostic-heading">
      <div>
        <p class="eyebrow">END-TO-END CONNECTIVITY TEST</p>
        <h2>前后端连通性验证</h2>
      </div>
      <button type="button" :disabled="state === 'loading'" @click="loadTenants">
        {{ state === 'loading' ? '请求中…' : '重新测试' }}
      </button>
    </div>

    <p class="page-desc">
      此页面直接调用后端 <code>/api/v1/connectivity/</code> 接口，从数据库读取
      <strong>Tenant</strong> 表记录并渲染。验证链路：前端 → Axios → Vite Proxy → Django → MySQL → 返回 → 渲染。
    </p>

    <p v-if="state === 'loading'" role="status">正在请求后端连通性接口…</p>

    <div v-if="state === 'success'" class="connectivity-result">
      <div class="result-summary">
        <span class="success-badge">连通成功</span>
        <span>数据库 Tenant 记录数：<strong>{{ total }}</strong></span>
        <span v-if="fetchedAt">获取时间：{{ fetchedAt }}</span>
      </div>

      <table class="tenant-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>名称</th>
            <th>类型</th>
            <th>目标 ACOS</th>
            <th>状态</th>
            <th>创建时间</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="tenant in tenants" :key="tenant.id">
            <td>{{ tenant.id }}</td>
            <td>{{ tenant.name }}</td>
            <td>{{ tenant.tenantType }}</td>
            <td>{{ tenant.targetAcos ?? '—' }}</td>
            <td>
              <span :class="tenant.isActive ? 'status-succeeded' : 'status-failed'" class="task-status">
                {{ tenant.isActive ? '活跃' : '停用' }}
              </span>
            </td>
            <td>{{ tenant.createdAt }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="state === 'error'" class="error-panel" role="alert">
      <strong>{{ error?.code }}</strong>
      <p>{{ error?.message }}</p>
      <small v-if="requestId">requestId: {{ requestId }}</small>
    </div>

    <div class="diagnostic-heading">
      <div>
        <p class="eyebrow">AUTHENTICATED REMOTE SCM TEST</p>
        <h2>远程数据库账号数据</h2>
      </div>
      <button
        type="button"
        :disabled="remoteState === 'loading'"
        @click="loadRemoteAccount"
      >
        {{ remoteState === 'loading' ? '读取中…' : '重新读取远程数据' }}
      </button>
    </div>

    <p class="page-desc">
      此区域调用受保护的 <code>/api/v1/auth/remote-account</code>，
      请求由统一 Axios 客户端自动携带 <code>Authorization</code> 和
      <code>X-Token</code>，后端再从
      <code>scm_remote.eb_merchant_admin</code> 读取当前账号的白名单字段。
    </p>

    <p v-if="remoteState === 'loading'" role="status">
      正在读取远程 SCM 账号数据…
    </p>

    <div v-if="remoteState === 'success' && remoteAccount" class="connectivity-result">
      <div class="result-summary">
        <span class="success-badge">远程读取成功</span>
        <span>数据源：<strong>{{ remoteAccount.source }}</strong></span>
      </div>
      <table class="tenant-table">
        <thead>
          <tr>
            <th>远程用户 ID</th>
            <th>商户 ID</th>
            <th>账号</th>
            <th>状态</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>{{ remoteAccount.externalUserId }}</td>
            <td>{{ remoteAccount.merchantId }}</td>
            <td>{{ remoteAccount.identifier }}</td>
            <td>
              <span
                :class="remoteAccount.isActive ? 'status-succeeded' : 'status-failed'"
                class="task-status"
              >
                {{ remoteAccount.isActive ? '活跃' : '停用' }}
              </span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="remoteState === 'error'" class="error-panel" role="alert">
      <strong>{{ remoteError?.code }}</strong>
      <p>{{ remoteError?.message }}</p>
      <small v-if="remoteError?.requestId">
        requestId: {{ remoteError.requestId }}
      </small>
    </div>
  </section>
</template>
