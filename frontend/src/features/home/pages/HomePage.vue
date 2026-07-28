<script setup lang="ts">
import { useAuthStore } from '@/features/auth/stores/auth'
import { useTenantContextStore } from '@/features/tenant-context/stores/tenantContext'

const authStore = useAuthStore()
const contextStore = useTenantContextStore()
</script>

<template>
  <section class="hero-card">
    <p class="eyebrow">AUTHENTICATED SELLER WORKSPACE</p>
    <h2>欢迎回来，{{ authStore.currentUser?.username }}</h2>
    <p>
      账号认证已接通。下一步选择由数据库授权的卖家空间、店铺、站点和广告 Profile，
      所有后续报表和优化动作都会绑定这一数据范围。
    </p>
    <RouterLink class="primary-link" to="/context">
      {{ contextStore.isComplete ? '查看当前卖家空间' : '选择卖家空间' }}
    </RouterLink>
    <p class="account-summary">
      当前账号：<strong>{{ authStore.currentUser?.email }}</strong>
      <span>用户 ID：{{ authStore.currentUser?.id }}</span>
    </p>
  </section>

  <section class="capability-grid" aria-label="当前真实能力">
    <article>
      <span>01</span>
      <h3>账号认证</h3>
      <p>登录、刷新、当前账号与退出接口均由真实后端提供。</p>
    </article>
    <article>
      <span>02</span>
      <h3>安全会话</h3>
      <p>并发 401 只触发一次刷新，失败后清空内存认证状态。</p>
    </article>
    <article>
      <span>03</span>
      <h3>数据权限</h3>
      <p>Tenant、Store、Marketplace 与 Profile 选项来自后端权限 Selector。</p>
    </article>
  </section>
</template>
