<script setup lang="ts">
import { useAuthStore } from '@/features/auth/stores/auth'

const authStore = useAuthStore()
</script>

<template>
  <section class="hero-card">
    <p class="eyebrow">PHASE 2A AUTHENTICATED</p>
    <h2>欢迎回来，{{ authStore.currentUser?.username }}</h2>
    <p>
      账号认证纵向链路已接通：短期访问令牌只驻留内存，刷新令牌由 HttpOnly Cookie
      管理，并支持轮换、撤销和会话恢复。
    </p>
    <p class="account-summary">
      当前账号：<strong>{{ authStore.currentUser?.email }}</strong>
      <span>用户 ID：{{ authStore.currentUser?.id }}</span>
    </p>
  </section>

  <section class="capability-grid" aria-label="Phase 2A 能力边界">
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
      <h3>范围边界</h3>
      <p>Tenant、Store、权限和广告业务仍未实现，不以静态数据冒充。</p>
    </article>
  </section>
</template>
