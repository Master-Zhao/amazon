<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'

import {
  fetchKnowledgeArticles,
  type KnowledgeArticle,
} from '@/features/knowledge/api/knowledgeApi'
import { useTenantContextStore } from '@/features/tenant-context/stores/tenantContext'
import { normalizeApiError } from '@/shared/api/httpClient'

const context = useTenantContextStore()
const faqs = ref<KnowledgeArticle[]>([])
const loading = ref(false)
const errorMessage = ref<string | null>(null)
let initialized = false

async function refresh(): Promise<void> {
  if (!context.tenantId) {
    faqs.value = []
    return
  }

  loading.value = true
  errorMessage.value = null
  try {
    faqs.value = await fetchKnowledgeArticles(context.tenantId)
  } catch (error) {
    errorMessage.value = normalizeApiError(error).message
  } finally {
    loading.value = false
  }
}

watch(
  () => context.tenantId,
  () => {
    if (initialized) void refresh()
  },
)

onMounted(async () => {
  if (context.status === 'idle') await context.initialize()
  initialized = true
  await refresh()
})
</script>

<template>
  <section class="help-center">
    <p class="eyebrow">HELP CENTER</p>
    <h2>帮助中心</h2>
    <p class="page-desc">平台使用指南与常见问题解答。</p>
    <p class="help-topics">
      涵盖快速入门、报表导入指南、广告分析说明、AI
      优化工作流与权限角色相关说明。
    </p>

    <header class="help-section-heading">
      <div>
        <h3>常见问题</h3>
        <p>选择一个问题，前往可独立访问的完整解答页面。</p>
      </div>
      <button
        class="secondary-button"
        type="button"
        :disabled="loading"
        @click="refresh"
      >
        {{ loading ? '加载中…' : '刷新' }}
      </button>
    </header>

    <div v-if="errorMessage" class="error-panel" role="alert">
      {{ errorMessage }}
    </div>
    <p v-else-if="!context.tenantId" class="empty-panel">
      请先选择卖家空间后查看帮助内容。
    </p>
    <p v-else-if="loading && faqs.length === 0" class="empty-panel">
      正在加载常见问题…
    </p>
    <p v-else-if="faqs.length === 0" class="empty-panel">
      当前没有可用的帮助内容。
    </p>
    <nav v-else class="help-nav" aria-label="常见问题">
      <ul>
        <li v-for="faq in faqs" :key="faq.slug">
          <RouterLink
            class="help-faq-link"
            :to="{ name: 'help-faq-detail', params: { slug: faq.slug } }"
          >
            <span>
              <small>{{ faq.categoryName }}</small>
              <strong>{{ faq.title }}</strong>
            </span>
            <span class="help-faq-arrow" aria-hidden="true">→</span>
          </RouterLink>
        </li>
      </ul>
    </nav>
  </section>
</template>
