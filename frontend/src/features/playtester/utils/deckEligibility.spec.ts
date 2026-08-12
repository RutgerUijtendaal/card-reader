import { describe, expect, test } from 'vitest';
import type { DeckRecord, DeckSummaryRecord } from '@/domain/decks/types';
import {
  isPlaytestDeckEligible,
  isPlaytestDeckSummaryEligible,
} from '@/features/playtester/utils/deckEligibility';

const buildSummary = (): DeckSummaryRecord => ({
  id: 'deck-1',
  name: 'Player deck',
  description: null,
  difficulty: null,
  visibility: 'public',
  owner: { id: 'user-1', username: 'player' },
  hero_card: {
    id: 'hero-1',
    key: 'hero-1',
    label: 'Hero',
    name: 'Hero',
    image_url: null,
    symbols: [],
    card_pool: 'player',
    card_roles: ['hero'],
  },
  mainboard: { total_cards: 1, unique_cards: 1 },
  sideboard_count: 0,
  status: { is_valid: true, label: 'Ready', deprecated_card_count: 0 },
  has_restricted_cards: false,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
});

const buildDeck = (): DeckRecord => {
  const card = {
    id: 'card-1',
    card_pool: 'player',
    restricted: false,
    lifecycle_status: 'active',
  };
  return {
    ...buildSummary(),
    long_description: null,
    hero_card: { ...card, id: 'hero-1', card_roles: ['hero'] },
    mainboard: { total_cards: 1, unique_cards: 1, entries: [{ quantity: 1, card }] },
    sideboards: [],
    totals: {
      overall_total_cards: 1,
      overall_unique_cards: 1,
      mainboard_total_cards: 1,
      mainboard_unique_cards: 1,
    },
    status: { is_valid: true, label: 'Ready', issues: [] },
  } as unknown as DeckRecord;
};

describe('playtester deck eligibility', () => {
  test('accepts invalid Player deck summaries and rejects restricted ones', () => {
    const summary = buildSummary();
    expect(isPlaytestDeckSummaryEligible(summary)).toBe(true);
    expect(isPlaytestDeckSummaryEligible({
      ...summary,
      status: { ...summary.status, is_valid: false },
    })).toBe(true);
    expect(isPlaytestDeckSummaryEligible({
      ...summary,
      status: { ...summary.status, is_valid: false, deprecated_card_count: 1 },
    })).toBe(false);
    expect(isPlaytestDeckSummaryEligible({
      ...summary,
      has_restricted_cards: true,
      hero_card: { ...summary.hero_card, card_pool: 'evil', restricted: true },
    })).toBe(false);
  });

  test('rejects a full deck when any referenced card is not a visible Player card', () => {
    const deck = buildDeck();
    expect(isPlaytestDeckEligible(deck)).toBe(true);
    expect(isPlaytestDeckEligible({
      ...deck,
      status: { ...deck.status, is_valid: false, issues: ['Under construction'] },
    })).toBe(true);
    expect(isPlaytestDeckEligible({
      ...deck,
      status: {
        ...deck.status,
        is_valid: false,
        issues: ['Deck references deprecated cards.'],
        deprecated_card_count: 1,
      },
    })).toBe(false);
    expect(isPlaytestDeckEligible({
      ...deck,
      mainboard: {
        ...deck.mainboard,
        entries: [{
          ...deck.mainboard.entries[0],
          card: { ...deck.mainboard.entries[0]!.card, restricted: true },
        }],
      },
    })).toBe(false);
    expect(isPlaytestDeckEligible({
      ...deck,
      hero_card: { ...deck.hero_card, card_pool: 'evil' },
    })).toBe(false);
    expect(isPlaytestDeckEligible({
      ...deck,
      hero_card: { ...deck.hero_card, lifecycle_status: 'deprecated' },
    })).toBe(false);
  });
});
