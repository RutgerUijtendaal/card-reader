import { ref } from 'vue';
import { expect, test } from 'vitest';
import type { CardListItem } from '@/domain/cards/types';
import type { CardSort } from '@/domain/cards/utils/gallery/cardSort';
import { useCardCollectionGrid } from './useCardCollectionGrid';

test('Evil detail sorting follows factions and preserves saved quantities and entry order', () => {
  const card = (id: string, faction: string, roles: string[] = []) =>
    ({
      id,
      name: id,
      card_pool: 'evil',
      card_factions: [faction],
      card_roles: roles,
      card_mana_families: [],
      mana_value: 0,
      types: [],
      symbols: [],
    }) as unknown as CardListItem;
  const entries = ref([
    { card: card('fire-boss', 'fire', ['boss']), quantity: 2 },
    { card: card('order-normal', 'order'), quantity: 19 },
    { card: card('order-boss', 'order', ['boss']), quantity: 1 },
  ]);
  const grid = useCardCollectionGrid(entries, ref([]), 'evil', ref<CardSort>('default'), ref(1));
  expect(grid.sortedEntries.value.map((entry) => entry.card.id)).toEqual([
    'order-boss',
    'order-normal',
    'fire-boss',
  ]);
  expect(grid.sortedEntries.value.map((entry) => entry.quantity)).toEqual([1, 19, 2]);
  expect(entries.value.map((entry) => entry.card.id)).toEqual([
    'fire-boss',
    'order-normal',
    'order-boss',
  ]);
});
