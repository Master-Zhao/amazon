import { httpClient } from '@/shared/api/httpClient'
import type { ApiEnvelope } from '@/shared/api/types'

export interface Notification {
  id: number
  notificationType: string
  title: string
  content: string
  targetRoute: string
  isRead: boolean
  readAt: string | null
  createdAt: string
}

export async function fetchNotifications(): Promise<Notification[]> {
  const response = await httpClient.get<ApiEnvelope<Notification[]>>(
    '/api/v1/notifications',
  )
  return response.data.data
}

export async function fetchUnreadCount(): Promise<number> {
  const response = await httpClient.get<ApiEnvelope<{ unreadCount: number }>>(
    '/api/v1/notifications/unread-count',
  )
  return response.data.data.unreadCount
}

export async function markNotificationRead(id: number): Promise<Notification> {
  const response = await httpClient.post<ApiEnvelope<Notification>>(
    `/api/v1/notifications/${id}/read`,
  )
  return response.data.data
}

export async function markAllNotificationsRead(): Promise<number> {
  const response = await httpClient.post<ApiEnvelope<{ markedCount: number }>>(
    '/api/v1/notifications/read-all',
  )
  return response.data.data.markedCount
}