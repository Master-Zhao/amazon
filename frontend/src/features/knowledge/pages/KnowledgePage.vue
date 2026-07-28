<script setup lang="ts">
import { onMounted, ref } from 'vue'

import {
  fetchKnowledge,
  type KnowledgeCategory,
} from '@/features/knowledge/api/knowledgeApi'

const categories = ref<KnowledgeCategory[]>([])
const loading = ref(true)
const error = ref(false)

onMounted(async () => {
  try {
    categories.value = await fetchKnowledge()
  } catch {
    error.value = true
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <section class="panel">
    <p class="eyebrow">KNOWLEDGE BASE</p>
    <h2>Amazon 广告知识库</h2>
    <p v-if="loading">正在加载…</p>
    <p v-else-if="error" class="error-banner">知识库加载失败。</p>
    <p v-else-if="categories.length === 0" class="empty-state">暂无已发布文章。</p>
    <div v-else class="card-list">
      <section v-for="category in categories" :key="category.code" class="hero-card compact-card">
        <h3>{{ category.name }}</h3>
        <article v-for="article in category.articles" :key="article.id">
          <h4>{{ article.title }}</h4>
          <p>{{ article.body }}</p>
        </article>
      </section>
    </div>
  </section>
</template>
