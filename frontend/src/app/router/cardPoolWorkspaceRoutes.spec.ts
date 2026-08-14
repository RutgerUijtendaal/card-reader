import { beforeEach, describe, expect, test } from 'vitest';
import { createMemoryHistory } from 'vue-router';
import { createPinia, setActivePinia } from 'pinia';
import { createAppRouter } from '@/app/router';
import { useAuthStore } from '@/domain/session/store';
import {
  buildWorkspaceSelectionLocation,
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

const setAnonymousSession = (): void => {
  const auth = useAuthStore();
  auth.$patch({
    initialized: true,
    user: null,
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

  test('initializes a resource workspace from its explicit card pool', async () => {
    localStorage.setItem(CARD_POOL_WORKSPACE_PREFERENCE_KEY, 'player');
    setSession(['player', 'evil', 'neutral']);
    const router = createAppRouter(createMemoryHistory());

    await router.push('/cards/evil-card?card_pool=evil');

    expect(router.currentRoute.value.fullPath).toBe('/cards/evil-card?card_pool=evil');
    expect(useCardPoolWorkspaceStore().activePool).toBe('evil');
  });

  test('prefers a resource return pool over the target card pool', async () => {
    localStorage.setItem(CARD_POOL_WORKSPACE_PREFERENCE_KEY, 'player');
    setSession(['player', 'evil', 'neutral']);
    const router = createAppRouter(createMemoryHistory());

    await router.push('/cards/neutral-card?card_pool=neutral&return_card_pool=evil');

    expect(useCardPoolWorkspaceStore().activePool).toBe('evil');
  });

  test('preserves a restricted staff-route deep link through login', async () => {
    setAnonymousSession();
    const router = createAppRouter(createMemoryHistory());

    await router.push('/cards/restricted-card/edit?card_pool=evil');

    expect(router.currentRoute.value.path).toBe('/login');
    expect(router.currentRoute.value.query.redirect).toBe(
      '/cards/restricted-card/edit?card_pool=evil',
    );
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

    await router.push('/playtester?card_pool=evil&preview=deck-1');

    expect(router.currentRoute.value.path).toBe('/playtester');
    expect(router.currentRoute.value.fullPath).toBe('/playtester?preview=deck-1');
    expect(useCardPoolWorkspaceStore().activePool).toBe('player');
  });

  test('strips an inaccessible pool query instead of rejecting a Player-only route', async () => {
    setSession(['player']);
    const router = createAppRouter(createMemoryHistory());

    await router.push('/playtester?card_pool=evil');

    expect(router.currentRoute.value.fullPath).toBe('/playtester');
    expect(useCardPoolWorkspaceStore().activePool).toBe('player');
  });

  test('marks card-derived routes for safe fallback after workspace access loss', () => {
    setSession(['player', 'evil', 'neutral']);
    const router = createAppRouter(createMemoryHistory());

    expect(router.resolve('/cards/restricted-card').meta.cardPoolWorkspace).toBe(true);
    expect(router.resolve('/card-groups/restricted-group').meta.cardPoolWorkspace).toBe(true);
    expect(router.resolve('/settings').meta.cardPoolWorkspace).toBeUndefined();
  });

  test.each(['evil', 'neutral'] as const)(
    'switches from %s back to canonical Player Gallery',
    async (restrictedPool) => {
      setSession(['player', 'evil', 'neutral']);
      const router = createAppRouter(createMemoryHistory());
      await router.push(`/cards?card_pool=${restrictedPool}`);

      await router.push(buildWorkspaceSelectionLocation('player'));

      expect(router.currentRoute.value.fullPath).toBe('/cards');
      expect(useCardPoolWorkspaceStore().activePool).toBe('player');
    },
  );
});
