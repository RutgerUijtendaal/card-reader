import { defineStore } from 'pinia';
import { useLocalStorage } from '@vueuse/core';
import { ref } from 'vue';
import type { LocationQueryRaw, RouteLocationRaw } from 'vue-router';
import {
  CARD_POOL_OPTIONS,
  isCardPool,
  type CardPool,
} from '@/domain/cards/cardPools';

export const CARD_POOL_WORKSPACE_PREFERENCE_KEY = 'card-reader.card-pool-workspace';

export const resolveCardPoolWorkspace = (preferredCardPool: unknown): CardPool =>
  isCardPool(preferredCardPool) ? preferredCardPool : 'player';

export const buildWorkspaceGalleryLocation = (
  cardPool: CardPool,
  query: LocationQueryRaw = {},
): RouteLocationRaw => {
  const nextQuery: LocationQueryRaw = { ...query };
  if (cardPool === 'player') {
    delete nextQuery.card_pool;
  } else {
    nextQuery.card_pool = cardPool;
  }
  return Object.keys(nextQuery).length > 0
    ? { path: '/cards', query: nextQuery }
    : '/cards';
};

export const buildWorkspaceGallerySelectionLocation = (
  cardPool: CardPool,
): RouteLocationRaw => ({
  path: '/cards',
  query: { card_pool: cardPool },
});

export const useCardPoolWorkspaceStore = defineStore('card-pool-workspace', () => {
  const preferredPool = useLocalStorage<CardPool | null>(
    CARD_POOL_WORKSPACE_PREFERENCE_KEY,
    null,
    { writeDefaults: false },
  );
  const activePool = ref<CardPool>(resolveCardPoolWorkspace(preferredPool.value));
  const generation = ref(0);

  const selectPool = (cardPool: CardPool): boolean => {
    if (cardPool === activePool.value) {
      return false;
    }
    activePool.value = cardPool;
    preferredPool.value = cardPool;
    generation.value += 1;
    return true;
  };

  return {
    activePool,
    availableOptions: CARD_POOL_OPTIONS,
    generation,
    selectPool,
  };
});
