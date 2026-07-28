<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'

import {
  fetchKnowledgeArticle,
  fetchKnowledgeArticles,
  fetchKnowledgeCategories,
  type KnowledgeArticle,
  type KnowledgeCategory,
} from '@/features/knowledge/api/knowledgeApi'
import { useTenantContextStore } from '@/features/tenant-context/stores/tenantContext'
import { normalizeApiError } from '@/shared/api/httpClient'

const context = useTenantContextStore()
const categories = ref<KnowledgeCategory[]>([])
const articles = ref<KnowledgeArticle[]>([])
const selectedCategory = ref('')
const selectedArticle = ref<KnowledgeArticle | null>(null)
const loading = ref(false)
const errorMessage = ref<string | null>(null)

async function refresh(): Promise<void> {
  if (!context.tenantId) {
    categories.value = []
    articles.value = []
    return
  }
  loading.value = true
  errorMessage.value = null
  try {
    ;[categories.value, articles.value] = await Promise.all([
      fetchKnowledgeCategories(context.tenantId),
      fetchKnowledgeArticles(
        context.tenantId,
        selectedCategory.value || undefined,
      ),
    ])
    selectedArticle.value = null
  } catch (error) {
    errorMessage.value = normalizeApiError(error).message
  } finally {
    loading.value = false
  }
}

async function openArticle(article: KnowledgeArticle): Promise<void> {
  if (!context.tenantId) return
  errorMessage.value = null
  try {
    selectedArticle.value = await fetchKnowledgeArticle(
      context.tenantId,
      article.slug,
    )
  } catch (error) {
    errorMessage.value = normalizeApiError(error).message
  }
}

watch(() => context.tenantId, () => void refresh())
watch(selectedCategory, () => void refresh())
onMounted(async () => {
  if (context.status === 'idle') await context.initialize()
  await refresh()
})
</script>

<template>
  <section class="report-page">
    <header class="report-heading">
      <div>
        <p class="eyebrow">READ-ONLY KNOWLEDGE</p>
        <h2>知识中心</h2>
        <p>内容来自版本受控的本地 seed，不使用网络采集、RAG、知识图谱或向量检索。</p>
      </div>
      <button class="secondary-button" type="button" @click="refresh">
        {{ loading ? '刷新中…' : '刷新' }}
      </button>
    </header>

    <div v-if="errorMessage" class="error-panel" role="alert">
      {{ errorMessage }}
    </div>
    <p v-if="!context.tenantId" class="empty-panel">请先选择卖家空间。</p>
    <template v-else>
      <label>
        分类
        <select v-model="selectedCategory">
          <option value="">全部分类</option>
          <option
            v-for="category in categories"
            :key="category.code"
            :value="category.code"
          >
            {{ category.name }}
          </option>
        </select>
      </label>
      <p v-if="!loading && articles.length === 0" class="empty-panel">
        当前分类暂无文章。
      </p>
      <div v-else class="recommendation-grid">
        <article v-for="article in articles" :key="article.slug">
          <small>{{ article.categoryName }}</small>
          <h3>{{ article.title }}</h3>
          <p>{{ article.summary }}</p>
          <button type="button" @click="openArticle(article)">查看详情</button>
        </article>
      </div>
      <article v-if="selectedArticle" class="workflow-section">
        <small>{{ selectedArticle.categoryName }}</small>
        <h3>{{ selectedArticle.title }}</h3>
        <p>{{ selectedArticle.body }}</p>
        <small>内容哈希：{{ selectedArticle.contentHash }}</small>
      </article>
    </template>
  </section>
</template>
