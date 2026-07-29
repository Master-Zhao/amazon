<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import {
  fetchKnowledgeArticle,
  type KnowledgeArticle,
} from '@/features/knowledge/api/knowledgeApi'
import { useTenantContextStore } from '@/features/tenant-context/stores/tenantContext'
import { normalizeApiError } from '@/shared/api/httpClient'
import type { ApiError } from '@/shared/api/types'

const route = useRoute()
const context = useTenantContextStore()
const article = ref<KnowledgeArticle | null>(null)
const loading = ref(false)
const notFound = ref(false)
const errorMessage = ref<string | null>(null)
let initialized = false

function slugFromRoute(): string {
  const value = route.params.slug
  return Array.isArray(value) ? (value[0] ?? '') : (value ?? '')
}

function apiError(error: unknown): ApiError {
  if (
    typeof error === 'object' &&
    error !== null &&
    'status' in error &&
    'message' in error
  ) {
    return error as ApiError
  }
  return normalizeApiError(error)
}

function setBrowserTitle(title: string): void {
  document.title = `${title} · 帮助中心 · Amazon Ads Optimizer`
}

async function loadArticle(): Promise<void> {
  const slug = slugFromRoute()
  article.value = null
  notFound.value = false
  errorMessage.value = null

  if (!context.tenantId || !slug) return

  loading.value = true
  try {
    article.value = await fetchKnowledgeArticle(context.tenantId, slug)
    setBrowserTitle(article.value.title)
  } catch (error) {
    const normalized = apiError(error)
    if (normalized.status === 404) {
      notFound.value = true
      setBrowserTitle('帮助内容不存在')
    } else {
      errorMessage.value = normalized.message
    }
  } finally {
    loading.value = false
  }
}

watch(
  [() => context.tenantId, () => route.params.slug],
  () => {
    if (initialized) void loadArticle()
  },
)

onMounted(async () => {
  if (context.status === 'idle') await context.initialize()
  initialized = true
  await loadArticle()
})
</script>

<template>
  <section class="help-center help-faq-detail">
    <nav class="help-detail-breadcrumb" aria-label="帮助中心路径">
      <RouterLink :to="{ name: 'help-center' }">帮助中心</RouterLink>
      <span aria-hidden="true">/</span>
      <span>常见问题</span>
      <template v-if="article">
        <span aria-hidden="true">/</span>
        <span aria-current="page">{{ article.title }}</span>
      </template>
    </nav>

    <p v-if="!context.tenantId" class="empty-panel">
      请先选择卖家空间后查看帮助内容。
    </p>
    <p v-else-if="loading" class="empty-panel">正在加载完整解答…</p>
    <div v-else-if="errorMessage" class="error-panel" role="alert">
      {{ errorMessage }}
    </div>
    <article v-else-if="notFound" class="help-not-found">
      <p class="eyebrow">HELP CONTENT NOT FOUND</p>
      <h2>未找到该帮助内容</h2>
      <p>链接可能已失效，或该内容当前不可用。</p>
      <RouterLink class="primary-link" :to="{ name: 'help-center' }">
        返回帮助中心
      </RouterLink>
    </article>
    <article v-else-if="article" class="help-answer">
      <p class="eyebrow">{{ article.categoryName }}</p>
      <h2>{{ article.title }}</h2>
      <p class="help-answer-body">{{ article.body }}</p>
      <RouterLink class="primary-link" :to="{ name: 'help-center' }">
        返回帮助中心
      </RouterLink>
    </article>
  </section>
</template>
