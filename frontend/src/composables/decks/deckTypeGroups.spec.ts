import { describe, expect, test } from 'vitest';
import { groupDeckEntriesByType } from '@/composables/decks/deckTypeGroups';

const buildEntry = (
  id: string,
  name: string,
  types: Array<{ key: string; label: string }>,
) => ({
  quantity: 1,
  card: {
    id,
    key: id,
    label: name,
    name,
    types,
  },
});

const typeBuckets = [
  { key: 'mana', label: 'Mana', linked_card_count: 99 },
  { key: 'creature', label: 'Creature', linked_card_count: 3 },
  { key: 'spell', label: 'Spell', linked_card_count: 5 },
  { key: 'attachment', label: 'Attachment', linked_card_count: 1 },
];

describe('groupDeckEntriesByType', () => {
  test('uses the highest-priority matching type for multi-type cards', () => {
    const groups = groupDeckEntriesByType(
      [
        buildEntry('multi', 'Arcane Multi', [
          { key: 'creature', label: 'Creature' },
          { key: 'spell', label: 'Spell' },
        ]),
      ],
      typeBuckets,
    );

    expect(groups).toHaveLength(1);
    expect(groups[0]?.key).toBe('spell');
    expect(groups[0]?.entries.map((entry) => entry.card.id)).toEqual(['multi']);
  });

  test('places untyped cards before mana cards and omits empty buckets', () => {
    const groups = groupDeckEntriesByType(
      [
        buildEntry('mana-card', 'Mana Card', [{ key: 'mana', label: 'Mana' }]),
        buildEntry('unknown-card', 'Unknown Card', [{ key: 'unknown', label: 'Unknown' }]),
        buildEntry('blank-card', 'Blank Card', []),
      ],
      typeBuckets,
    );

    expect(groups.map((group) => group.label)).toEqual(['Untyped', 'Mana']);
    expect(groups.map((group) => group.entries.map((entry) => entry.card.id))).toEqual([
      ['blank-card', 'unknown-card'],
      ['mana-card'],
    ]);
  });

  test('keeps cards inside a bucket in name, label, id order', () => {
    const groups = groupDeckEntriesByType(
      [
        buildEntry('card-c', 'Beta', [{ key: 'spell', label: 'Spell' }]),
        buildEntry('card-b', 'Alpha', [{ key: 'spell', label: 'Spell' }]),
        buildEntry('card-a', 'Alpha', [{ key: 'spell', label: 'Spell' }]),
      ],
      typeBuckets,
    );

    expect(groups).toHaveLength(1);
    expect(groups[0]?.entries.map((entry) => entry.card.id)).toEqual(['card-a', 'card-b', 'card-c']);
  });

  test('uses a provided comparator only within each bucket', () => {
    const groups = groupDeckEntriesByType(
      [
        buildEntry('spell-low', 'Spell Low', [{ key: 'spell', label: 'Spell' }]),
        buildEntry('creature', 'Creature', [{ key: 'creature', label: 'Creature' }]),
        buildEntry('spell-high', 'Spell High', [{ key: 'spell', label: 'Spell' }]),
      ],
      typeBuckets,
      {
        compareEntries: (left, right) => right.card.id.localeCompare(left.card.id),
      },
    );

    expect(groups.map((group) => group.key)).toEqual(['spell', 'creature']);
    expect(groups[0]?.entries.map((entry) => entry.card.id)).toEqual(['spell-low', 'spell-high']);
  });
});
