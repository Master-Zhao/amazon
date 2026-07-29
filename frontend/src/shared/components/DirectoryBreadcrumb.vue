<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

interface DirectorySegment {
  label: string
  route: string
}

const route = useRoute()
const router = useRouter()

const directoryPath = computed<DirectorySegment[]>(() => {
  const path = route.meta.directoryPath as DirectorySegment[] | undefined
  if (path) return path

  const segments = route.path.split('/').filter(Boolean)
  const result: DirectorySegment[] = []
  let accumulated = ''
  for (const segment of segments) {
    accumulated += `/${segment}`
    result.push({ label: segment, route: accumulated })
  }
  return result
})

async function navigateTo(routePath: string) {
  await router.push(routePath)
}
</script>

<template>
  <nav class="directory-breadcrumb" aria-label="目录路径">
    <button
      class="breadcrumb-home"
      type="button"
      title="首页"
      @click="navigateTo('/')"
    >
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
        <polyline points="9 22 9 12 15 12 15 22" />
      </svg>
    </button>
    <template v-for="(segment, index) in directoryPath" :key="index">
      <span class="breadcrumb-separator">›</span>
      <button
        class="breadcrumb-segment"
        :class="{ active: index === directoryPath.length - 1 }"
        type="button"
        @click="navigateTo(segment.route)"
      >
        {{ segment.label }}
      </button>
    </template>
  </nav>
</template>
