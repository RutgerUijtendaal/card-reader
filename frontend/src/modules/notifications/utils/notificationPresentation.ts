import type {
  DeckCardVersionChangeCause,
  ParseFlagReviewStatus,
  UserNotification,
} from '@/modules/notifications/types';
import type { RouteLocationRaw } from 'vue-router';
import {
  NOTIFICATION_EVENT_DECK_CARD_VERSION_CHANGED,
  NOTIFICATION_EVENT_PARSE_FLAG_ITEM_REVIEWED,
} from '@/modules/notifications/types';
import { buildNotificationTargetLocation } from '@/composables/notifications/notificationRouteState';

export type NotificationAction = {
  icon: 'card' | 'deck' | 'open';
  label: string;
  to: RouteLocationRaw;
};

export type NotificationDetail = {
  label: string;
  value: string;
};

export type NotificationCardVersionComparison = {
  cardId: string;
  beforeVersionId: string;
  afterVersionId: string;
};

type NotificationPresentationKind = 'flag-review' | 'deck-card-update' | 'generic';

export type NotificationPresentation = {
  kind: NotificationPresentationKind;
  category: string;
  title: string;
  summary: string;
  status: ParseFlagReviewStatus | null;
  occurrenceLabel: string;
  detailsLabel: string;
  details: NotificationDetail[];
  cardVersionComparison: NotificationCardVersionComparison | null;
  actions: NotificationAction[];
};

const stringValue = (metadata: Record<string, unknown>, key: string): string => {
  const value = metadata[key];
  return typeof value === 'string' ? value : '';
};

const flagStatus = (metadata: Record<string, unknown>): ParseFlagReviewStatus | null => {
  const status = stringValue(metadata, 'status');
  return status === 'resolved' || status === 'dismissed' ? status : null;
};

const changeCause = (metadata: Record<string, unknown>): DeckCardVersionChangeCause | null => {
  const cause = stringValue(metadata, 'change_cause');
  if (cause === 'import_created' || cause === 'version_promoted') {
    return cause;
  }

  const legacyLabel = stringValue(metadata, 'change_label');
  if (legacyLabel === 'replaced by an import') {
    return 'import_created';
  }
  if (legacyLabel === 'promoted') {
    return 'version_promoted';
  }
  return null;
};

const propertyLabel = (metadata: Record<string, unknown>): string => {
  const snapshot = stringValue(metadata, 'property_label');
  if (snapshot) {
    return snapshot;
  }
  const propertyKey = stringValue(metadata, 'property_key');
  if (!propertyKey) {
    return 'suggestion';
  }
  return propertyKey === 'overall' ? 'overall suggestion' : `${propertyKey.replaceAll('_', ' ')} flag`;
};

const compactDetails = (details: Array<NotificationDetail | null>): NotificationDetail[] =>
  details.filter((detail): detail is NotificationDetail => detail !== null && detail.value.trim().length > 0);

const occurrenceLabel = (eventCount: number): string =>
  eventCount > 1 ? `${eventCount} updates while unread` : '';

const flagPresentation = (notification: UserNotification): NotificationPresentation | null => {
  const metadata = notification.metadata;
  const cardId = stringValue(metadata, 'card_id');
  const cardName = stringValue(metadata, 'card_name');
  if (!cardId || !cardName) {
    return null;
  }

  const cardVersionId = stringValue(metadata, 'card_version_id');
  const status = flagStatus(metadata);
  const reviewerName = stringValue(metadata, 'reviewer_name') || notification.actor?.username || '';
  const reviewedField = propertyLabel(metadata);
  const statusText = status ?? 'reviewed';
  const cardTarget = buildNotificationTargetLocation(
    `/cards/${cardId}`,
    cardVersionId ? { version_id: cardVersionId } : {},
  );

  return {
    kind: 'flag-review',
    category: 'Flag review',
    title: `Your ${reviewedField} for ${cardName} was ${statusText}`,
    summary: reviewerName ? `Reviewed by ${reviewerName}.` : notification.message,
    status,
    occurrenceLabel: occurrenceLabel(notification.event_count),
    detailsLabel: 'Review details',
    details: compactDetails([
      { label: 'Your suggestion', value: stringValue(metadata, 'submitted_value') },
      { label: 'Your note', value: stringValue(metadata, 'submission_note') },
      { label: 'Reviewer response', value: stringValue(metadata, 'review_note') },
    ]),
    cardVersionComparison: null,
    actions: [{ icon: 'card', label: 'View card', to: cardTarget }],
  };
};

const deckChangeSummary = (
  cause: DeckCardVersionChangeCause | null,
  actorName: string,
  fallback: string,
): string => {
  if (cause === 'import_created') {
    return 'A newly imported version became the current card version.';
  }
  if (cause === 'version_promoted') {
    return actorName
      ? `${actorName} promoted a different version to current.`
      : 'A different version was promoted to current.';
  }
  return fallback;
};

const deckCardPresentation = (notification: UserNotification): NotificationPresentation | null => {
  const metadata = notification.metadata;
  const deckId = stringValue(metadata, 'deck_id');
  const deckName = stringValue(metadata, 'deck_name');
  const cardId = stringValue(metadata, 'card_id');
  const cardName = stringValue(metadata, 'card_name');
  if (!deckId || !deckName || !cardId || !cardName) {
    return null;
  }

  const previousCardVersionId = stringValue(metadata, 'previous_card_version_id');
  const cardVersionId = stringValue(metadata, 'card_version_id');
  const comparison = previousCardVersionId && cardVersionId && previousCardVersionId !== cardVersionId
    ? {
        cardId,
        beforeVersionId: previousCardVersionId,
        afterVersionId: cardVersionId,
      }
    : null;

  return {
    kind: 'deck-card-update',
    category: 'Deck card update',
    title: `${cardName} changed in ${deckName}`,
    summary: deckChangeSummary(changeCause(metadata), notification.actor?.username ?? '', notification.message),
    status: null,
    occurrenceLabel: occurrenceLabel(notification.event_count),
    detailsLabel: comparison ? 'Compare versions' : '',
    details: [],
    cardVersionComparison: comparison,
    actions: [
      {
        icon: 'deck',
        label: 'View deck',
        to: buildNotificationTargetLocation(`/my/decks/${deckId}`),
      },
      {
        icon: 'card',
        label: 'View card',
        to: buildNotificationTargetLocation(
          `/cards/${cardId}`,
          cardVersionId ? { version_id: cardVersionId } : {},
        ),
      },
    ],
  };
};

const genericPresentation = (notification: UserNotification): NotificationPresentation => ({
  kind: 'generic',
  category: 'Notification',
  title: notification.title,
  summary: notification.message,
  status: null,
  occurrenceLabel: occurrenceLabel(notification.event_count),
  detailsLabel: '',
  details: [],
  cardVersionComparison: null,
  actions: notification.target_url
    ? [{ icon: 'open', label: 'Open', to: notification.target_url }]
    : [],
});

export const presentNotification = (notification: UserNotification): NotificationPresentation => {
  if (notification.event_type === NOTIFICATION_EVENT_PARSE_FLAG_ITEM_REVIEWED) {
    return flagPresentation(notification) ?? genericPresentation(notification);
  }
  if (notification.event_type === NOTIFICATION_EVENT_DECK_CARD_VERSION_CHANGED) {
    return deckCardPresentation(notification) ?? genericPresentation(notification);
  }
  return genericPresentation(notification);
};
