import { defineStore } from 'pinia'

import {
  fetchNotifications,
  fetchUnreadCount,
  markAllNotificationsRead,
  markNotificationRead,
  type Notification,
} from '@/features/notifications/api/notificationApi'

interface NotificationState {
  notifications: Notification[]
  unreadCount: number
  status: 'idle' | 'loading' | 'ready' | 'error'
}

export const useNotificationStore = defineStore('notifications', {
  state: (): NotificationState => ({
    notifications: [],
    unreadCount: 0,
    status: 'idle',
  }),
  getters: {
    recentUnread(state): Notification[] {
      return state.notifications
        .filter((n) => !n.isRead)
        .slice(0, 5)
    },
  },
  actions: {
    async loadNotifications() {
      this.status = 'loading'
      try {
        const [notifications, count] = await Promise.all([
          fetchNotifications(),
          fetchUnreadCount(),
        ])
        this.notifications = notifications
        this.unreadCount = count
        this.status = 'ready'
      } catch {
        this.status = 'error'
      }
    },
    async refreshUnreadCount() {
      try {
        this.unreadCount = await fetchUnreadCount()
      } catch {
        // silent
      }
    },
    async markRead(id: number) {
      try {
        const updated = await markNotificationRead(id)
        const index = this.notifications.findIndex((n) => n.id === id)
        if (index !== -1) {
          this.notifications[index] = updated
        }
        if (!updated.isRead || this.unreadCount > 0) {
          this.unreadCount = Math.max(0, this.unreadCount - 1)
        }
      } catch {
        // silent
      }
    },
    async markAllRead() {
      try {
        await markAllNotificationsRead()
        this.notifications.forEach((n) => {
          n.isRead = true
        })
        this.unreadCount = 0
      } catch {
        // silent
      }
    },
  },
})