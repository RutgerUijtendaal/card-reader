import { describe, expect, test } from 'vitest';
import type { UserNotification } from '@/domain/notifications/types';
import { presentNotification } from '@/features/notifications/utils/notificationPresentation';

const notification = (overrides: Partial<UserNotification> = {}): UserNotification => ({
  id: 'notification-1',
  event_type: 'test.event',
  subject_type: 'test',
  subject_id: 'subject-1',
  target_url: '/fallback',
  title: 'Stored title',
  message: 'Stored message',
  metadata: {},
  event_count: 1,
  read_at: null,
  created_at: '2026-06-07T10:00:00Z',
  updated_at: '2026-06-07T10:00:00Z',
  last_event_at: '2026-06-07T10:00:00Z',
  actor: null,
  ...overrides,
});

describe('notification presentation', () => {
  test('presents a reviewed flag with an exact-version action and expandable details', () => {
    const presentation = presentNotification(
      notification({
        event_type: 'parse_flag_item.reviewed',
        actor: { id: 'reviewer-1', username: 'reviewer' },
        metadata: {
          card_id: 'card-1',
          card_name: 'Flagged Card',
          card_version_id: 'version/2',
          property_key: 'rules_text',
          property_label: 'rules text flag',
          status: 'dismissed',
          submitted_value: 'Suggested rules',
          submission_note: 'The last line appears incorrect.\nPlease compare the image.',
          review_note: 'The original parse is correct.',
        },
      }),
    );

    expect(presentation.kind).toBe('flag-review');
    expect(presentation.title).toBe('Your rules text flag for Flagged Card was dismissed');
    expect(presentation.summary).toBe('Reviewed by reviewer.');
    expect(presentation.details).toEqual([
      { label: 'Your suggestion', value: 'Suggested rules' },
      { label: 'Your note', value: 'The last line appears incorrect.\nPlease compare the image.' },
      { label: 'Reviewer response', value: 'The original parse is correct.' },
    ]);
    expect(presentation.actions).toEqual([
      {
        icon: 'card',
        label: 'View card',
        to: {
          path: '/cards/card-1',
          query: {
            version_id: 'version/2',
            return_to: 'notifications',
          },
        },
      },
    ]);
  });

  test('presents a coalesced deck card update with both destinations', () => {
    const presentation = presentNotification(
      notification({
        event_type: 'deck.card_version_changed',
        event_count: 3,
        metadata: {
          deck_id: 'deck-1',
          deck_name: 'Control Deck',
          card_id: 'card-1',
          card_name: 'Updated Card',
          card_version_id: 'version-3',
          previous_card_version_id: 'version-2',
          change_cause: 'import_created',
        },
      }),
    );

    expect(presentation.kind).toBe('deck-card-update');
    expect(presentation.title).toBe('Updated Card changed in Control Deck');
    expect(presentation.summary).toBe('A newly imported version became the current card version.');
    expect(presentation.occurrenceLabel).toBe('3 updates while unread');
    expect(presentation.detailsLabel).toBe('Compare versions');
    expect(presentation.cardVersionComparison).toEqual({
      cardId: 'card-1',
      beforeVersionId: 'version-2',
      afterVersionId: 'version-3',
    });
    expect(presentation.actions).toEqual([
      {
        icon: 'deck',
        label: 'View deck',
        to: {
          path: '/my/decks/deck-1',
          query: { return_to: 'notifications' },
        },
      },
      {
        icon: 'card',
        label: 'View card',
        to: {
          path: '/cards/card-1',
          query: {
            version_id: 'version-3',
            return_to: 'notifications',
          },
        },
      },
    ]);
  });

  test('uses legacy metadata where possible and stored snapshots as the generic fallback', () => {
    const legacy = presentNotification(
      notification({
        event_type: 'deck.card_version_changed',
        metadata: {
          deck_id: 'deck-1',
          deck_name: 'Legacy Deck',
          card_id: 'card-1',
          card_name: 'Legacy Card',
          change_label: 'promoted',
        },
      }),
    );
    const unknown = presentNotification(notification());
    const incompleteKnown = presentNotification(
      notification({ event_type: 'parse_flag_item.reviewed' }),
    );

    expect(legacy.summary).toBe('A different version was promoted to current.');
    expect(unknown.kind).toBe('generic');
    expect(unknown.title).toBe('Stored title');
    expect(incompleteKnown.kind).toBe('generic');
    expect(incompleteKnown.summary).toBe('Stored message');
  });
});
