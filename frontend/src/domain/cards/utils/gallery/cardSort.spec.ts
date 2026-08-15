import { describe, expect, test } from 'vitest';
import { buildTypeSortBuckets, buildTypeSortLookup, compareCardSort } from '@/domain/cards/utils/gallery/cardSort';

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
      { cardPool: 'player', typeSortLookup: lookup },
    )).toBeLessThan(0);
    expect(compareCardSort(
      buildCard('alpha-card', 'Alpha Card', [{ key: 'alpha', label: 'Alpha' }]),
      buildCard('zeta-card', 'Zeta Card', [{ key: 'zeta', label: 'Zeta' }]),
      'types_asc',
      { cardPool: 'player', typeSortLookup: lookup },
    )).toBeLessThan(0);
    expect(compareCardSort(
      buildCard('untyped-card', 'Untyped Card', []),
      buildCard('mana-card', 'Mana Card', [{ key: 'mana', label: 'Mana' }]),
      'types_asc',
      { cardPool: 'player', typeSortLookup: lookup },
    )).toBeLessThan(0);
  });

  test('uses the Type key before card identity when counts and labels tie', () => {
    const lookup = buildTypeSortLookup([
      { key: 'zeta', label: 'Shared', linked_card_count: 1 },
      { key: 'alpha', label: 'Shared', linked_card_count: 1 },
    ]);

    expect(compareCardSort(
      buildCard('alpha-type-card', 'Zulu Card', [{ key: 'alpha', label: 'Shared' }]),
      buildCard('zeta-type-card', 'Alpha Card', [{ key: 'zeta', label: 'Shared' }]),
      'types_asc',
      { cardPool: 'player', typeSortLookup: lookup },
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

    expect(compareCardSort(
      multiTypeCard,
      creatureCard,
      'types_asc',
      { cardPool: 'player', typeSortLookup: lookup },
    )).toBeLessThan(0);
  });

  test('sorts by the server-provided mana-family rank before name', () => {
    const arcane = { ...buildCard('arcane', 'Zulu', []), mana_family_sort_key: 0 };
    const dark = { ...buildCard('dark', 'Alpha', []), mana_family_sort_key: 1 };
    const noFamily = buildCard('none', 'Beta', []);

    expect(compareCardSort(arcane, dark, 'mana_type_asc', { cardPool: 'player' })).toBeLessThan(0);
    expect(compareCardSort(dark, noFamily, 'mana_type_asc', { cardPool: 'player' })).toBeLessThan(0);
  });

  test('uses backend-compatible exact text tie-breakers for mana-family sorting', () => {
    const uppercase = { ...buildCard('uppercase', 'Zoo', []), mana_family_sort_key: 0 };
    const lowercase = { ...buildCard('lowercase', 'alpha', []), mana_family_sort_key: 0 };

    expect(compareCardSort(uppercase, lowercase, 'mana_type_asc', { cardPool: 'player' })).toBeLessThan(0);
  });
});

describe('cardSort default sorting', () => {
  test('sorts Player by mana family, Hero, default role, then mana value', () => {
    const cards = [
      { ...buildCard('dark-hero', 'Dark Hero', []), mana_family_sort_key: 1, mana_value: 0, card_roles: ['hero'] as const },
      { ...buildCard('arcane-boss', 'Arcane Boss', []), mana_family_sort_key: 0, mana_value: 0, card_roles: ['boss'] as const },
      { ...buildCard('arcane-normal-high', 'Arcane Normal High', []), mana_family_sort_key: 0, mana_value: 4, card_roles: [] },
      { ...buildCard('arcane-normal-low', 'Arcane Normal Low', []), mana_family_sort_key: 0, mana_value: 1, card_roles: [] },
      { ...buildCard('arcane-normal-null', 'Arcane Normal Null', []), mana_family_sort_key: 0, mana_value: null, card_roles: [] },
      { ...buildCard('arcane-hero', 'Arcane Hero', []), mana_family_sort_key: 0, mana_value: 6, card_roles: ['hero'] as const },
    ];

    cards.sort((left, right) => compareCardSort(left, right, 'default', {
      cardPool: 'player',
    }));

    expect(cards.map((card) => card.id)).toEqual([
      'arcane-hero',
      'arcane-normal-low',
      'arcane-normal-high',
      'arcane-normal-null',
      'arcane-boss',
      'dark-hero',
    ]);
  });

  test('sorts Evil by faction, Boss, Location, default role, then mana value', () => {
    const cards = [
      { ...buildCard('none-boss', 'None Boss', []), mana_value: 0, card_factions: [], card_roles: ['boss'] as const },
      { ...buildCard('blood-boss', 'Blood Boss', []), mana_value: 0, card_factions: ['blood'] as const, card_roles: ['boss'] as const },
      { ...buildCard('order-normal-high', 'Order Normal High', []), mana_value: 5, card_factions: ['order'] as const, card_roles: [] },
      { ...buildCard('order-location', 'Order Location', []), mana_value: 0, card_factions: ['order'] as const, card_roles: ['location'] as const },
      { ...buildCard('order-normal-low', 'Order Normal Low', []), mana_value: 1, card_factions: ['order'] as const, card_roles: [] },
      { ...buildCard('order-boss', 'Order Boss', []), mana_value: 9, card_factions: ['order'] as const, card_roles: ['boss'] as const },
    ];

    cards.sort((left, right) => compareCardSort(left, right, 'default', { cardPool: 'evil' }));

    expect(cards.map((card) => card.id)).toEqual([
      'order-boss',
      'order-location',
      'order-normal-low',
      'order-normal-high',
      'blood-boss',
      'none-boss',
    ]);
  });

  test('sorts Neutral by the canonical default role order', () => {
    const cards = [
      { ...buildCard('location', 'Location', []), card_roles: ['location'] as const },
      { ...buildCard('shop', 'Shop', []), card_roles: ['shop_item'] as const },
      { ...buildCard('hero', 'Hero', []), card_roles: ['hero'] as const },
      { ...buildCard('boss', 'Boss', []), card_roles: ['boss'] as const },
      { ...buildCard('event', 'Event', []), card_roles: ['event'] as const },
      { ...buildCard('boon-event', 'Boon Event', []), card_roles: ['boon', 'event'] as const },
      { ...buildCard('boon', 'Boon', []), card_roles: ['boon'] as const },
      { ...buildCard('normal', 'Normal', []), card_roles: [] },
    ];

    cards.sort((left, right) => compareCardSort(left, right, 'default', { cardPool: 'neutral' }));

    expect(cards.map((card) => card.id)).toEqual([
      'normal',
      'hero',
      'boss',
      'location',
      'boon',
      'boon-event',
      'event',
      'shop',
    ]);
  });
});
