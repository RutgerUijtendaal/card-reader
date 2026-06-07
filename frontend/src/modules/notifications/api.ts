import { api } from '@/api/client';
import type {
  MarkAllNotificationsReadResponse,
  NotificationPage,
  NotificationStatusFilter,
  NotificationSummary,
  UserNotification,
} from '@/modules/notifications/types';

export const fetchNotificationSummary = async (): Promise<NotificationSummary> => {
  const response = await api.get<NotificationSummary>('/notifications/summary');
  return response.data;
};

export const fetchNotifications = async (params?: URLSearchParams): Promise<NotificationPage> => {
  const response = await api.get<NotificationPage>('/notifications', { params });
  return response.data;
};

export const buildNotificationSearchParams = (
  status: NotificationStatusFilter,
  page: number,
  pageSize: number,
): URLSearchParams => {
  const params = new URLSearchParams();
  params.set('status', status);
  params.set('page', String(page));
  params.set('page_size', String(pageSize));
  return params;
};

export const setNotificationReadState = async (notificationId: string, read: boolean): Promise<UserNotification> => {
  const response = await api.patch<UserNotification>(`/notifications/${notificationId}`, { read });
  return response.data;
};

export const markAllNotificationsRead = async (): Promise<MarkAllNotificationsReadResponse> => {
  const response = await api.post<MarkAllNotificationsReadResponse>('/notifications/mark-all-read');
  return response.data;
};
