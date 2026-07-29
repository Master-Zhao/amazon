<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'

import { useNotificationStore } from '@/features/notifications/stores/notifications'

const store = useNotificationStore()
const router = useRouter()

onMounted(() => {
  if (store.status === 'idle') {
    void store.loadNotifications()
  }
})

async function handleClick(id: number, targetRoute: string) {
  await store.markRead(id)
  if (targetRoute) {
    await router.push(targetRoute)
  }
}
</script>

<template>
  <section class="notification-center">
    <header class="center-header">
      <h2>通知中心</h2>
      <button
        v-if="store.unreadCount > 0"
        class="secondary-button"
        type="button"
        @click="store.markAllRead()"
      >
        全部标记已读
      </button>
    </header>

    <div v-if="store.status === 'loading'" class="empty-panel">加载中…</div>
    <div v-else-if="store.status === 'error'" class="empty-panel">加载失败</div>
    <div v-else-if="store.notifications.length === 0" class="empty-panel">暂无通知</div>

    <ul v-else class="notification-list">
      <li
        v-for="item in store.notifications"
        :key="item.id"
        class="notification-item"
        :class="{ unread: !item.isRead }"
        @click="handleClick(item.id, item.targetRoute)"
      >
        <span class="item-type">{{ item.notificationType }}</span>
        <span class="item-title">{{ item.title }}</span>
        <p class="item-content">{{ item.content }}</p>
        <time class="item-time">{{ item.createdAt }}</time>
      </li>
    </ul>
  </section>
</template>