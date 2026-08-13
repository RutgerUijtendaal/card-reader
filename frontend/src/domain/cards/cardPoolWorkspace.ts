import { defineStore } from 'pinia';
import { useLocalStorage } from '@vueuse/core';
import { computed, ref } from 'vue';
import type { LocationQueryRaw, RouteLocationRaw } from 'vue-router';
import {
  CARD_POOL_OPTIONS,
  isCardPool,
  type CardPool,
} from '@/domain/cards/cardPools';

export const CARD_POOL_WORKSPACE_PREFERENCE_KEY = 'card-reader.card-pool-workspace';

export const normalizeAccessibleCardPools = (
  cardPools: readonly CardPool[],
): CardPool[] => {
  const allowed = new Set<CardPool>(['player', ...cardPools]);
  return CARD_POOL_OPTIONS
    .map((option) => option.value)
    .filter((cardPool) => allowed.has(cardPool));
};

export const resolveCardPoolWorkspace = (
  accessibleCardPools: readonly CardPool[],
  routeCardPool: unknown,
  preferredCardPool: unknown,
): CardPool => {
  const accessible = new Set(normalizeAccessibleCardPools(accessibleCardPools));
  if (isCardPool(routeCardPool) && accessible.has(routeCardPool)) {
    return routeCardPool;
  }
  if (isCardPool(preferredCardPool) && accessible.has(preferredCardPool)) {
    return preferredCardPool;
  }
  return 'player';
};

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

export const buildWorkspaceSelectionLocation = (
  cardPool: CardPool,
): RouteLocationRaw => cardPool === 'player'
  ? { path: '/cards', query: { card_pool: 'player' } }
  : buildWorkspaceGalleryLocation(cardPool);

export const useCardPoolWorkspaceStore = defineStore('card-pool-workspace', () => {
  const activePool = ref<CardPool>('player');
  const accessiblePools = ref<CardPool[]>(['player']);
  const generation = ref(0);
  const initialized = ref(false);
  const sessionKey = ref('anonymous');
  const preferredPool = useLocalStorage<CardPool | null>(
    CARD_POOL_WORKSPACE_PREFERENCE_KEY,
    null,
    { writeDefaults: false },
  );

  const availableOptions = computed(() =>
    CARD_POOL_OPTIONS.filter((option) => accessiblePools.value.includes(option.value)),
  );

  const synchronizeSession = (
    nextAccessiblePools: readonly CardPool[],
    nextSessionKey: string,
    routeCardPool?: unknown,
  ): boolean => {
    const normalizedPools = normalizeAccessibleCardPools(nextAccessiblePools);
    const scopeChanged = normalizedPools.join(':') !== accessiblePools.value.join(':');
    const identityChanged = nextSessionKey !== sessionKey.value;
    const nextPool = initialized.value
      ? resolveCardPoolWorkspace(
          normalizedPools,
          routeCardPool,
          normalizedPools.includes(activePool.value) ? activePool.value : preferredPool.value,
        )
      : resolveCardPoolWorkspace(normalizedPools, routeCardPool, preferredPool.value);
    const poolChanged = nextPool !== activePool.value;

    accessiblePools.value = normalizedPools;
    sessionKey.value = nextSessionKey;
    activePool.value = nextPool;
    initialized.value = true;
    if (poolChanged) {
      preferredPool.value = nextPool;
    }
    if (scopeChanged || identityChanged || poolChanged) {
      generation.value += 1;
    }
    return poolChanged;
  };

  const selectPool = (cardPool: CardPool): boolean => {
    if (!accessiblePools.value.includes(cardPool) || cardPool === activePool.value) {
      return false;
    }
    activePool.value = cardPool;
    preferredPool.value = cardPool;
    generation.value += 1;
    return true;
  };

  return {
    activePool,
    accessiblePools,
    availableOptions,
    generation,
    initialized,
    synchronizeSession,
    selectPool,
  };
});
