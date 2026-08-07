import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import {
  fetchNotifications,
  fetchUnreadCount,
  markAllNotificationsRead,
  markNotificationRead,
} from '@/features/notifications/api/notificationApi'
import NotificationCenterPage from '@/features/notifications/pages/NotificationCenterPage.vue'

vi.mock('@/features/notifications/api/notificationApi', () => ({
  fetchNotifications: vi.fn(),
  fetchUnreadCount: vi.fn(),
  markNotificationRead: vi.fn(),
  markAllNotificationsRead: vi.fn(),
}))

const notificationsMock = vi.mocked(fetchNotifications)
const unreadMock = vi.mocked(fetchUnreadCount)
const markReadMock = vi.mocked(markNotificationRead)
const markAllMock = vi.mocked(markAllNotificationsRead)

function mountPage() {
  const router = createRouter({ history: createMemoryHistory(), routes: [] })
  return mount(NotificationCenterPage, {
    global: {
      plugins: [router],
    },
  })
}

describe('Notification center page', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    setActivePinia(createPinia())
  })

  it('renders notifications sourced from sys_notification', async () => {
    notificationsMock.mockResolvedValue([
      {
        id: 1,
        notificationType: 'ANOMALY_DETECTED',
        title: 'ACOS 异常预警',
        content: 'Campaign ACOS 达到 45.2%',
        targetRoute: '/advertising/overview',
        isRead: false,
        readAt: null,
        createdAt: '2026-08-07T10:00:00Z',
      },
      {
        id: 2,
        notificationType: 'REPORT_IMPORTED',
        title: '报表导入完成',
        content: 'Campaign 报表已导入 200 行',
        targetRoute: '/reports/imports',
        isRead: true,
        readAt: '2026-08-07T09:00:00Z',
        createdAt: '2026-08-07T09:00:00Z',
      },
    ])
    unreadMock.mockResolvedValue(1)

    const wrapper = mountPage()
    await flushPromises()

    expect(wrapper.text()).toContain('ANOMALY_DETECTED')
    expect(wrapper.text()).toContain('ACOS 异常预警')
    expect(wrapper.text()).toContain('Campaign ACOS 达到 45.2%')
    expect(wrapper.text()).toContain('REPORT_IMPORTED')
    expect(wrapper.text()).toContain('报表导入完成')
    expect(wrapper.text()).toContain('全部标记已读')
  })

  it('marks a single notification as read and navigates to its target route', async () => {
    notificationsMock.mockResolvedValue([
      {
        id: 1,
        notificationType: 'ANOMALY_DETECTED',
        title: 'ACOS 异常预警',
        content: 'Campaign ACOS 达到 45.2%',
        targetRoute: '/advertising/overview',
        isRead: false,
        readAt: null,
        createdAt: '2026-08-07T10:00:00Z',
      },
    ])
    unreadMock.mockResolvedValue(1)
    markReadMock.mockResolvedValue({
      id: 1,
      notificationType: 'ANOMALY_DETECTED',
      title: 'ACOS 异常预警',
      content: 'Campaign ACOS 达到 45.2%',
      targetRoute: '/advertising/overview',
      isRead: true,
      readAt: '2026-08-07T10:05:00Z',
      createdAt: '2026-08-07T10:00:00Z',
    })

    const wrapper = mountPage()
    await flushPromises()

    await wrapper.get('.notification-item').trigger('click')
    await flushPromises()

    expect(markReadMock).toHaveBeenCalledWith(1)
  })

  it('marks all notifications as read in a single batch call', async () => {
    notificationsMock.mockResolvedValue([
      {
        id: 1,
        notificationType: 'ANOMALY_DETECTED',
        title: 'ACOS 异常预警',
        content: 'Campaign ACOS 达到 45.2%',
        targetRoute: '/advertising/overview',
        isRead: false,
        readAt: null,
        createdAt: '2026-08-07T10:00:00Z',
      },
    ])
    unreadMock.mockResolvedValue(1)
    markAllMock.mockResolvedValue(1)

    const wrapper = mountPage()
    await flushPromises()

    const markAllButton = wrapper
      .findAll('button')
      .find((button) => button.text() === '全部标记已读')
    await markAllButton?.trigger('click')
    await flushPromises()

    expect(markAllMock).toHaveBeenCalled()
  })

  it('renders an empty state when no notifications exist', async () => {
    notificationsMock.mockResolvedValue([])
    unreadMock.mockResolvedValue(0)
    const wrapper = mountPage()
    await flushPromises()
    expect(wrapper.text()).toContain('暂无通知')
  })

  it('renders an error state when the API rejects', async () => {
    notificationsMock.mockRejectedValue(new Error('unavailable'))
    unreadMock.mockRejectedValue(new Error('unavailable'))
    const wrapper = mountPage()
    await flushPromises()
    expect(wrapper.text()).toContain('加载失败')
  })
})