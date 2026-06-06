import { describe, expect, test } from 'vitest';
import { buildTypeSortBuckets, buildTypeSortLookup, compareCardSort } from '@/composables/card-gallery/cardSort';

const buildCard = (
  id: string,
  name: string,
  types: Array<{ key: string; label: string }>,
) => ({
  id,
  key: id,
  label: name,
  name,
  mana_value: null,
  updated_at: '2026-05-26T12:00:00.000Z',
  types,
});

describe('cardSort type sorting', () => {
  test('builds a stable type lookup with mana last', () => {
    const types = [
      { key: 'mana', label: 'Mana', linked_card_count: 99 },
      { key: 'creature', label: 'Creature', linked_card_count: 3 },
      { key: 'spell', label: 'Spell', linked_card_count: 5 },
      { key: 'alpha', label: 'Alpha', linked_card_count: 1 },
      { key: 'zeta', label: 'Zeta', linked_card_count: 1 },
    ];
    const lookup = buildTypeSortLookup(types);

    expect(buildTypeSortBuckets(types).map((type) => type.key)).toEqual([
      'spell',
      'creature',
      'alpha',
      'zeta',
      'mana',
    ]);

    expect(compareCardSort(
      buildCard('spell-card', 'Spell Card', [{ key: 'spell', label: 'Spell' }]),
      buildCard('creature-card', 'Creature Card', [{ key: 'creature', label: 'Creature' }]),
      'types_asc',
      lookup,
    )).toBeLessThan(0);
    expect(compareCardSort(
      buildCard('alpha-card', 'Alpha Card', [{ key: 'alpha', label: 'Alpha' }]),
      buildCard('zeta-card', 'Zeta Card', [{ key: 'zeta', label: 'Zeta' }]),
      'types_asc',
      lookup,
    )).toBeLessThan(0);
    expect(compareCardSort(
      buildCard('untyped-card', 'Untyped Card', []),
      buildCard('mana-card', 'Mana Card', [{ key: 'mana', label: 'Mana' }]),
      'types_asc',
      lookup,
    )).toBeLessThan(0);
  });

  test('uses the highest priority non-mana type for multi-type cards', () => {
    const lookup = buildTypeSortLookup([
      { key: 'mana', label: 'Mana', linked_card_count: 10 },
      { key: 'creature', label: 'Creature', linked_card_count: 2 },
      { key: 'spell', label: 'Spell', linked_card_count: 4 },
    ]);

    const multiTypeCard = buildCard('multi', 'Arcane Multi', [
      { key: 'creature', label: 'Creature' },
      { key: 'spell', label: 'Spell' },
      { key: 'mana', label: 'Mana' },
    ]);
    const creatureCard = buildCard('creature', 'Creature Solo', [{ key: 'creature', label: 'Creature' }]);

    expect(compareCardSort(multiTypeCard, creatureCard, 'types_asc', lookup)).toBeLessThan(0);
  });
});
