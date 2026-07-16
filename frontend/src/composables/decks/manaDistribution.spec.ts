import { describe, expect, test } from 'vitest';
import {
  buildManaDistribution,
  buildManaDistributionFromEntryGroups,
  type ManaDistributionSymbolLike,
} from '@/composables/decks/manaDistribution';

const symbols: ManaDistributionSymbolLike[] = [
  { key: 'blue-mana', label: 'Blue Mana', symbol_type: 'mana', text_token: '{B}', asset_url: '/blue.webp' },
  { key: 'white-mana', label: 'White Mana', symbol_type: 'mana', text_token: '{W}', asset_url: '/white.webp' },
  { key: 'colorless-mana-2', label: 'Colorless 2', symbol_type: 'mana', text_token: '{2}' },
  { key: 'blue-affinity', label: 'Blue Affinity', symbol_type: 'affinity', text_token: '{BA}' },
];

describe('buildManaDistribution', () => {
  test('weights totals and colored-card averages by quantity while keeping per-card maxima', () => {
    const summary = buildManaDistribution([
      {
        quantity: 4,
        card: { mana_symbols: ['blue-mana', 'blue-mana', 'white-mana'], types: [{ key: 'spell' }] },
      },
      {
        quantity: 2,
        card: { mana_symbols: ['white-mana', 'white-mana', 'white-mana'], types: [{ key: 'follower' }] },
      },
      {
        quantity: 3,
        card: { mana_symbols: ['white-mana'], types: [{ key: 'attachment' }] },
      },
    ], symbols);

    expect(summary.totalCards).toBe(9);
    expect(summary.colors).toEqual([
      expect.objectContaining({ key: 'blue-mana', total: 8, average: 2, highest: 2, matchingCards: 4 }),
      expect.objectContaining({
        key: 'white-mana',
        total: 13,
        average: 13 / 9,
        highest: 3,
        matchingCards: 9,
      }),
    ]);
  });

  test('excludes mana-type cards and ignores colorless, X, and non-mana catalog symbols', () => {
    const summary = buildManaDistribution([
      {
        quantity: 2,
        card: { mana_symbols: ['blue-mana', 'colorless-mana-2', 'x'], types: [{ key: 'spell' }] },
      },
      {
        quantity: 20,
        card: { mana_symbols: ['white-mana'], types: [{ key: ' Mana ' }] },
      },
    ], symbols);

    expect(summary.totalCards).toBe(2);
    expect(summary.colors.map((color) => color.key)).toEqual(['blue-mana']);
    expect(summary.colors[0]).toEqual(expect.objectContaining({ total: 2, average: 1, highest: 1 }));
  });

  test('matches any selected type once and allows groups to overlap', () => {
    const summary = buildManaDistribution([
      {
        quantity: 3,
        card: {
          mana_symbols: ['blue-mana', 'white-mana'],
          types: [{ key: 'spell' }, { key: 'follower' }],
        },
      },
      {
        quantity: 2,
        card: { mana_symbols: ['white-mana', 'white-mana'], types: [{ key: 'attachment' }] },
      },
    ], symbols, [
      {
        id: 'actions',
        name: 'Actions',
        typeKeys: ['spell', 'attachment'],
        excludedTypeKeys: [],
        isVisible: true,
      },
      {
        id: 'units',
        name: 'Units',
        typeKeys: ['follower', 'creature'],
        excludedTypeKeys: [],
        isVisible: true,
      },
    ]);

    expect(summary.groups[0]?.totalCards).toBe(5);
    expect(summary.groups[0]?.colors).toEqual([
      expect.objectContaining({ key: 'blue-mana', total: 3, average: 1, highest: 1 }),
      expect.objectContaining({ key: 'white-mana', total: 7, average: 7 / 5, highest: 2 }),
    ]);
    expect(summary.groups[1]?.totalCards).toBe(3);
    expect(summary.groups[1]?.colors).toEqual([
      expect.objectContaining({ key: 'blue-mana', total: 3 }),
      expect.objectContaining({ key: 'white-mana', total: 3 }),
    ]);
  });

  test('keeps the active board color rows with zero values in unmatched groups', () => {
    const summary = buildManaDistribution([
      {
        quantity: 1,
        card: { mana_symbols: ['blue-mana'], types: [{ key: 'spell' }] },
      },
    ], symbols, [{
      id: 'followers',
      name: 'Followers',
      typeKeys: ['follower', 'creature'],
      excludedTypeKeys: [],
      isVisible: true,
    }]);

    expect(summary.groups[0]).toEqual({
      group: {
        id: 'followers',
        name: 'Followers',
        typeKeys: ['follower', 'creature'],
        excludedTypeKeys: [],
        isVisible: true,
      },
      totalCards: 0,
      colors: [expect.objectContaining({ key: 'blue-mana', total: 0, average: 0, highest: 0, matchingCards: 0 })],
    });
  });

  test('calculates exact pre-grouped entry subsets without matching secondary types', () => {
    const entries = [
      {
        quantity: 3,
        card: {
          mana_symbols: ['blue-mana'],
          types: [{ key: 'spell' }, { key: 'follower' }],
        },
      },
      {
        quantity: 2,
        card: { mana_symbols: ['white-mana'], types: [{ key: 'follower' }] },
      },
    ];
    const summary = buildManaDistributionFromEntryGroups(entries, symbols, [
      {
        group: {
          id: 'base-type:spell',
          name: 'Spell',
          typeKeys: ['spell'],
          excludedTypeKeys: [],
          isVisible: true,
        },
        entries: [entries[0]!],
      },
      {
        group: {
          id: 'base-type:follower',
          name: 'Follower',
          typeKeys: ['follower'],
          excludedTypeKeys: [],
          isVisible: true,
        },
        entries: [entries[1]!],
      },
    ]);

    expect(summary.groups[0]?.totalCards).toBe(3);
    expect(summary.groups[1]?.totalCards).toBe(2);
    expect(summary.groups[1]?.colors).toEqual([
      expect.objectContaining({ key: 'blue-mana', total: 0 }),
      expect.objectContaining({ key: 'white-mana', total: 2 }),
    ]);
  });

  test('rejects cards containing an excluded type after matching an included type', () => {
    const summary = buildManaDistribution([
      {
        quantity: 3,
        card: { mana_symbols: ['blue-mana'], types: [{ key: 'spell' }] },
      },
      {
        quantity: 4,
        card: {
          mana_symbols: ['white-mana'],
          types: [{ key: 'spell' }, { key: 'follower' }],
        },
      },
    ], symbols, [{
      id: 'actions',
      name: 'Actions',
      typeKeys: ['spell', 'attachment'],
      excludedTypeKeys: ['follower'],
      isVisible: true,
    }]);

    expect(summary.groups[0]?.totalCards).toBe(3);
    expect(summary.groups[0]?.colors).toEqual([
      expect.objectContaining({ key: 'blue-mana', total: 3 }),
      expect.objectContaining({ key: 'white-mana', total: 0 }),
    ]);
  });

  test('treats all eligible cards as candidates for exclusion-only groups', () => {
    const summary = buildManaDistribution([
      {
        quantity: 2,
        card: { mana_symbols: ['blue-mana'], types: [{ key: 'spell' }] },
      },
      {
        quantity: 3,
        card: { mana_symbols: ['white-mana'], types: [{ key: 'follower' }] },
      },
      {
        quantity: 4,
        card: { mana_symbols: ['blue-mana'], types: [{ key: 'attachment' }] },
      },
    ], symbols, [{
      id: 'not-units',
      name: 'Not units',
      typeKeys: [],
      excludedTypeKeys: ['follower', 'creature'],
      isVisible: true,
    }]);

    expect(summary.groups[0]?.totalCards).toBe(6);
    expect(summary.groups[0]?.colors).toEqual([
      expect.objectContaining({ key: 'blue-mana', total: 6 }),
      expect.objectContaining({ key: 'white-mana', total: 0 }),
    ]);
  });
});
