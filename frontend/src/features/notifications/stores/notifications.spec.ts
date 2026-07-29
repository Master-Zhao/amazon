import { describe, it, expect, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('@/features/notifications/api/notificationApi', () => ({
  fetchNotifications: vi.fn().mockResolvedValue([
    {
      id: 1,
      notificationType: 'ANOMALY_DETECTED',
      title: 'ACOS 异常预警',
      content: 'Campaign ACOS 达到 45.2%',
      targetRoute: '/advertising/overview',
      isRead: false,
      readAt: null,
      createdAt: '2026-07-29T00:00:00Z',
    },
    {
      id: 2,
      notificationType: 'REPORT_IMPORTED',
      title: '报表导入完成',
      content: 'Campaign 报表已导入',
      targetRoute: '/reports/imports',
      isRead: true,
      readAt: '2026-07-28T12:00:00Z',
      createdAt: '2026-07-28T11:00:00Z',
    },
  ]),
  fetchUnreadCount: vi.fn().mockResolvedValue(1),
  markNotificationRead: vi.fn().mockImplementation((id: number) =>
    Promise.resolve({
      id,
      notificationType: 'ANOMALY_DETECTED',
      title: 'ACOS 异常预警',
      content: 'Campaign ACOS 达到 45.2%',
      targetRoute: '/advertising/overview',
      isRead: true,
      readAt: '2026-07-29T01:00:00Z',
      createdAt: '2026-07-29T00:00:00Z',
    }),
  ),
  markAllNotificationsRead: vi.fn().mockResolvedValue(1),
}))

import { useNotificationStore } from '@/features/notifications/stores/notifications'

describe('notificationStore', () => {
  it('loads notifications and unread count', async () => {
    setActivePinia(createPinia())
    const store = useNotificationStore()
    await store.loadNotifications()
    expect(store.notifications).toHaveLength(2)
    expect(store.unreadCount).toBe(1)
    expect(store.status).toBe('ready')
  })

  it('computes recentUnread', async () => {
    setActivePinia(createPinia())
    const store = useNotificationStore()
    await store.loadNotifications()
    expect(store.recentUnread).toHaveLength(1)
    expect(store.recentUnread[0].id).toBe(1)
  })

  it('marks a notification as read', async () => {
    setActivePinia(createPinia())
    const store = useNotificationStore()
    await store.loadNotifications()
    await store.markRead(1)
    expect(store.notifications[0].isRead).toBe(true)
    expect(store.unreadCount).toBe(0)
  })

  it('marks all as read', async () => {
    setActivePinia(createPinia())
    const store = useNotificationStore()
    await store.loadNotifications()
    await store.markAllRead()
    expect(store.unreadCount).toBe(0)
    store.notifications.forEach((n) => {
      expect(n.isRead).toBe(true)
    })
  })
})