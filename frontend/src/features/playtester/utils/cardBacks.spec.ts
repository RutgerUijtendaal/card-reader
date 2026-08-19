import { describe, expect, it } from 'vitest';
import type { DeckCardSummary } from '@/domain/decks/types';
import type { PlaytestCardInstance } from '@/features/playtester/types';
import { resolvePlaytestCardBackUrl } from '@/features/playtester/utils/cardBacks';

const instance = (
  cardId: string,
  storedImageUrl?: string,
): PlaytestCardInstance => ({
  cardId,
  instanceId: `instance-${cardId}`,
  card: {
    id: cardId,
    effective_card_back: storedImageUrl
      ? {
          source: 'pool_default',
          asset: {
            id: 'stored-back',
            label: 'Stored back',
            width: 744,
            height: 1039,
            image_url: storedImageUrl,
            created_at: '2026-01-01T00:00:00Z',
            updated_at: '2026-01-01T00:00:00Z',
          },
        }
      : null,
  } as DeckCardSummary,
  zoneId: 'library',
  order: 0,
  tapped: false,
  face: 'back',
  setupOrigin: false,
  boardX: null,
  boardY: null,
  pileGroupId: null,
  pileOrder: null,
});

describe('resolvePlaytestCardBackUrl', () => {
  it('prefers the current deck resolution for a physical instance', () => {
    expect(
      resolvePlaytestCardBackUrl(
        instance('card-1', '/stored.webp'),
        { 'card-1': 'https://cards.example/current.webp' },
        'https://cards.example/default.webp',
      ),
    ).toBe('https://cards.example/current.webp');
  });

  it('uses a stale draft card stored resolution before the pool default', () => {
    expect(
      resolvePlaytestCardBackUrl(
        instance('stale-card', 'https://cards.example/stored.webp'),
        {},
        'https://cards.example/default.webp',
      ),
    ).toBe('https://cards.example/stored.webp');
  });

  it('does not inherit when the current deck resolution is explicitly unavailable', () => {
    expect(
      resolvePlaytestCardBackUrl(
        instance('broken-override'),
        { 'broken-override': null },
        'https://cards.example/default.webp',
      ),
    ).toBeNull();
  });

  it('falls back to the pool default when no card resolution remains', () => {
    expect(
      resolvePlaytestCardBackUrl(
        instance('unknown-card'),
        {},
        'https://cards.example/default.webp',
      ),
    ).toBe('https://cards.example/default.webp');
  });
});
