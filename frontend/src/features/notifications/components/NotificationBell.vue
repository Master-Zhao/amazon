<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'

import { useNotificationStore } from '@/features/notifications/stores/notifications'

const store = useNotificationStore()
const router = useRouter()
const showPanel = ref(false)
let pollTimer: ReturnType<typeof setInterval> | null = null

function togglePanel() {
  showPanel.value = !showPanel.value
  if (showPanel.value && store.status === 'idle') {
    void store.loadNotifications()
  }
}

async function handleClick(id: number, targetRoute: string) {
  await store.markRead(id)
  showPanel.value = false
  if (targetRoute) {
    await router.push(targetRoute)
  }
}

async function handleMarkAllRead() {
  await store.markAllRead()
}

function openNotificationCenter() {
  showPanel.value = false
  void router.push('/notifications')
}

onMounted(() => {
  void store.refreshUnreadCount()
  pollTimer = setInterval(() => void store.refreshUnreadCount(), 30_000)
})

onUnmounted(() => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
})
</script>

<template>
  <div class="notification-bell" @mouseleave="showPanel = false">
    <button
      class="bell-button"
      type="button"
      aria-label="通知"
      @mouseenter="togglePanel"
      @click="togglePanel"
    >
      <span class="bell-icon">&#x1F514;</span>
      <span v-if="store.unreadCount > 0" class="bell-badge">
        {{ store.unreadCount > 99 ? '99+' : store.unreadCount }}
      </span>
    </button>

    <div v-if="showPanel" class="notification-panel">
      <div class="panel-header">
        <span>通知</span>
        <button
          v-if="store.unreadCount > 0"
          class="mark-all-btn"
          type="button"
          @click="handleMarkAllRead"
        >
          全部已读
        </button>
      </div>

      <div v-if="store.status === 'loading'" class="panel-loading">
        加载中…
      </div>

      <div v-else-if="store.status === 'error'" class="panel-error">
        加载失败
      </div>

      <div v-else-if="store.notifications.length === 0" class="panel-empty">
        暂无通知
      </div>

      <ul v-else class="panel-list">
        <li
          v-for="item in store.notifications.slice(0, 5)"
          :key="item.id"
          class="panel-item"
          :class="{ unread: !item.isRead }"
          @click="handleClick(item.id, item.targetRoute)"
        >
          <span class="item-title">{{ item.title }}</span>
          <p class="item-content">{{ item.content }}</p>
          <time class="item-time">{{ item.createdAt }}</time>
        </li>
      </ul>

      <div class="panel-footer">
        <button class="view-all-btn" type="button" @click="openNotificationCenter">
          查看全部通知
        </button>
      </div>
    </div>
  </div>
</template>