import { beforeEach, describe, expect, test } from 'vitest';
import { createMemoryHistory } from 'vue-router';
import { createPinia, setActivePinia } from 'pinia';
import { createAppRouter } from '@/app/router';
import { useAuthStore } from '@/domain/session/store';
import {
  CARD_POOL_WORKSPACE_PREFERENCE_KEY,
  useCardPoolWorkspaceStore,
} from '@/domain/cards/cardPoolWorkspace';

const setSession = (
  accessibleCardPools: ('player' | 'evil' | 'neutral')[],
): void => {
  const auth = useAuthStore();
  auth.$patch({
    initialized: true,
    user: {
      authenticated: true,
      id: 'staff-1',
      username: 'staff',
      is_staff: accessibleCardPools.length > 1,
      can_access_admin: accessibleCardPools.length > 1,
      accessible_card_pools: accessibleCardPools,
    },
  });
};

describe('card pool workspace routes', () => {
  beforeEach(() => {
    localStorage.clear();
    setActivePinia(createPinia());
  });

  test.each(['evil', 'neutral'] as const)(
    'restores a permitted %s preference when opening the Gallery root',
    async (preferredPool) => {
      localStorage.setItem(CARD_POOL_WORKSPACE_PREFERENCE_KEY, preferredPool);
      setSession(['player', 'evil', 'neutral']);
      const router = createAppRouter(createMemoryHistory());

      await router.push('/cards');

      expect(router.currentRoute.value.fullPath).toBe(`/cards?card_pool=${preferredPool}`);
      expect(useCardPoolWorkspaceStore().activePool).toBe(preferredPool);
    },
  );

  test('rejects a restricted deep link when the session cannot access its pool', async () => {
    setSession(['player']);
    const router = createAppRouter(createMemoryHistory());

    await router.push('/cards?card_pool=evil');

    expect(router.currentRoute.value.fullPath).toBe('/cards');
    expect(useCardPoolWorkspaceStore().activePool).toBe('player');
  });

  test('removes unauthorized pool context from direct card routes', async () => {
    setSession(['player']);
    const router = createAppRouter(createMemoryHistory());

    await router.push('/cards/restricted-card?card_pool=evil');

    expect(router.currentRoute.value.fullPath).toBe('/cards');
    expect(useCardPoolWorkspaceStore().activePool).toBe('player');
  });

  test('normalizes an obsolete Gallery pool to Player instead of a stored preference', async () => {
    localStorage.setItem(CARD_POOL_WORKSPACE_PREFERENCE_KEY, 'neutral');
    setSession(['player', 'evil', 'neutral']);
    const router = createAppRouter(createMemoryHistory());

    await router.push('/cards?card_pool=game_master');

    expect(router.currentRoute.value.fullPath).toBe('/cards');
    expect(useCardPoolWorkspaceStore().activePool).toBe('player');
  });

  test('makes deck and Playtester routes explicitly return to Player', async () => {
    setSession(['player', 'evil', 'neutral']);
    const router = createAppRouter(createMemoryHistory());
    await router.push('/cards?card_pool=evil');

    await router.push('/playtester');

    expect(router.currentRoute.value.path).toBe('/playtester');
    expect(useCardPoolWorkspaceStore().activePool).toBe('player');
  });
});
