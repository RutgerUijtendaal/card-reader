import { describe, expect, test } from 'vitest';
import type { DeckRecord } from '@/domain/decks/types';
import { buildDeckUpsertRequestFromRecord } from '@/domain/decks/utils/deckPayload';

describe('deckPayload', () => {
  test('preserves Markdown-significant whitespace when cloning a record', () => {
    const deck = {
      name: 'Deck',
      description_markup: '    [[card:id|Literal]]\n',
      long_description_markup: 'Line with a hard break  \nNext',
      difficulty: null,
      visibility: 'private',
      hero_card: { id: 'hero-1' },
      tags: [],
      pending_tag_suggestions: [],
      mainboard: { entries: [] },
      sideboards: [],
    } as unknown as DeckRecord;

    expect(buildDeckUpsertRequestFromRecord(deck)).toMatchObject({
      description_markup: '    [[card:id|Literal]]\n',
      long_description_markup: 'Line with a hard break  \nNext',
    });
  });
});
