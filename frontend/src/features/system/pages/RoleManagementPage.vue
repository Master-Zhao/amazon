<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import { useTenantContextStore } from '@/features/tenant-context/stores/context'
import {
  createRole,
  fetchRoles,
  type Role,
} from '@/features/system/api/permissionApi'

const context = useTenantContextStore()
const canManage = computed(() => context.permissionCodes.includes('roles.manage'))
const roles = ref<Role[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const code = ref('')
const name = ref('')

async function loadRoles(): Promise<void> {
  if (!context.selectedTenantId) return
  loading.value = true
  error.value = null
  try {
    roles.value = await fetchRoles(context.selectedTenantId)
  } catch {
    error.value = '角色列表加载失败'
  } finally {
    loading.value = false
  }
}

async function submit(): Promise<void> {
  if (!context.selectedTenantId) return
  const role = await createRole({
    tenantId: context.selectedTenantId,
    code: code.value,
    name: name.value,
    permissionCodes: ['context.view'],
  })
  roles.value.push(role)
  code.value = ''
  name.value = ''
}

watch(() => context.selectedTenantId, loadRoles, { immediate: true })
</script>

<template>
  <section class="panel">
    <p class="eyebrow">SYSTEM MANAGEMENT</p>
    <h2>角色与权限</h2>
    <p v-if="!context.selectedTenantId">请先选择卖家空间。</p>
    <p v-else-if="!canManage" class="error-banner">当前卖家空间内无角色管理权限。</p>
    <p v-else-if="loading" role="status">正在加载角色…</p>
    <p v-else-if="error" class="error-banner">{{ error }}</p>
    <div v-else>
      <p>系统角色不可删除；Tenant 自定义角色只能组合固定权限编码。</p>
      <ul v-if="roles.length">
        <li v-for="role in roles" :key="role.id">
          {{ role.name }}（{{ role.code }}）
          <span>{{ role.isSystem ? '系统角色' : '自定义角色' }}</span>
        </li>
      </ul>
      <p v-else class="empty-state">当前没有可见角色。</p>
      <form class="context-grid" @submit.prevent="submit">
        <label>
          角色编码
          <input v-model.trim="code" required pattern="[a-z][a-z0-9_.-]+">
        </label>
        <label>
          角色名称
          <input v-model.trim="name" required>
        </label>
        <button class="primary-button" type="submit">创建只读角色</button>
      </form>
    </div>
  </section>
</template>
