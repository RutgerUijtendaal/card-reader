export type NotificationStatusFilter = 'unread' | 'read' | 'all';

export type NotificationActor = {
  id: string;
  username: string;
};

export type UserNotification = {
  id: string;
  event_type: string;
  subject_type: string;
  subject_id: string;
  target_url: string;
  title: string;
  message: string;
  metadata: Record<string, unknown>;
  event_count: number;
  read_at: string | null;
  created_at: string;
  updated_at: string;
  last_event_at: string;
  actor: NotificationActor | null;
};

export type NotificationPage = {
  count: number;
  next_page: number | null;
  previous_page: number | null;
  page: number;
  page_size: number;
  results: UserNotification[];
};

export type NotificationSummary = {
  unread_count: number;
};

export type MarkAllNotificationsReadResponse = {
  updated_count: number;
  unread_count: number;
};
