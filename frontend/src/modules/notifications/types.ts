export type NotificationStatusFilter = 'unread' | 'read' | 'all';

export const NOTIFICATION_EVENT_PARSE_FLAG_ITEM_REVIEWED = 'parse_flag_item.reviewed';
export const NOTIFICATION_EVENT_DECK_CARD_VERSION_CHANGED = 'deck.card_version_changed';

export type ParseFlagReviewStatus = 'resolved' | 'dismissed';
export type DeckCardVersionChangeCause = 'import_created' | 'version_promoted';

export type ParseFlagItemReviewedMetadata = {
  card_id: string;
  card_name: string;
  card_version_id: string;
  flag_id: string;
  property_key: string;
  property_label: string;
  status: ParseFlagReviewStatus;
  submitted_value: string;
  submission_note: string;
  reviewer_name: string;
  review_note: string;
};

export type DeckCardVersionChangedMetadata = {
  deck_id: string;
  deck_name: string;
  card_id: string;
  card_name: string;
  card_version_id: string;
  previous_card_version_id?: string;
  change_cause: DeckCardVersionChangeCause;
  import_job_id?: string;
  import_item_id?: string;
};

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
