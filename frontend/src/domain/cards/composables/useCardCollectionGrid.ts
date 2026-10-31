import { computed, type Ref } from 'vue';
import type { CardListItem, CardFiltersResponse } from '@/domain/cards/types';
import type { CardPool } from '@/domain/cards/cardPools';
import {
  buildTypeSortLookup,
  compareCardSort,
  type CardSort,
} from '@/domain/cards/utils/gallery/cardSort';
import { groupCardEntriesByType } from '@/domain/cards/utils/cardTypeGroups';

export const useCardCollectionGrid = (
  entries: Ref<Array<{ card: CardListItem; quantity: number }>>,
  types: Ref<CardFiltersResponse['types']>,
  pool: CardPool,
  sort: Ref<CardSort>,
  cardScale: Ref<number>,
) => {
  const cardHeightRem = computed(() => Number((24 * cardScale.value).toFixed(2)));
  const cardWidthRem = computed(() => Number(((cardHeightRem.value * 63) / 88).toFixed(2)));
  const gridStyle = computed(() => ({
    gridTemplateColumns: `repeat(auto-fill, minmax(min(100%, ${Math.round((cardWidthRem.value + 1) * 16)}px), 1fr))`,
  }));
  const cardStyle = computed(() => ({ width: '100%', maxWidth: `${cardWidthRem.value}rem` }));
  const typeSortLookup = computed(() => buildTypeSortLookup(types.value));
  const compare = (left: { card: CardListItem }, right: { card: CardListItem }) =>
    compareCardSort(left.card, right.card, sort.value, {
      cardPool: pool,
      typeSortLookup: typeSortLookup.value,
    });
  const sortedEntries = computed(() => [...entries.value].sort(compare));
  const groupedEntries = computed(() =>
    groupCardEntriesByType(entries.value, types.value, {
      compareEntries: sort.value === 'types_asc' ? undefined : compare,
    }),
  );
  return { cardHeightRem, cardStyle, gridStyle, sortedEntries, groupedEntries };
};
