<script setup lang="ts">
import { onMounted, ref } from 'vue'

import {
  fetchConnectivityTenants,
  type TenantItem,
} from '@/shared/api/connectivityApi'
import type { ApiError } from '@/shared/api/types'

type PageState = 'idle' | 'loading' | 'success' | 'error'

const state = ref<PageState>('idle')
const total = ref(0)
const tenants = ref<TenantItem[]>([])
const error = ref<ApiError | null>(null)
const requestId = ref<string | null>(null)
const fetchedAt = ref<string | null>(null)

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

onMounted(loadTenants)
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
  </section>
</template>