import { beforeEach, describe, expect, test } from 'vitest';
import { createMemoryHistory } from 'vue-router';
import { createPinia, setActivePinia } from 'pinia';
import { nextTick } from 'vue';
import { APP_ROUTES, createAppRouter } from '@/app/router';
import { useAuthStore } from '@/domain/session/store';
import {
  CARD_POOL_WORKSPACE_PREFERENCE_KEY,
  useCardPoolWorkspaceStore,
} from '@/domain/cards/cardPoolWorkspace';

const setSession = (): void => {
  const auth = useAuthStore();
  auth.$patch({
    initialized: true,
    user: {
      authenticated: true,
      id: 'staff-1',
      username: 'staff',
      is_staff: false,
      can_access_admin: false,
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
      setSession();
      const router = createAppRouter(createMemoryHistory());

      await router.push('/cards');

      expect(router.currentRoute.value.fullPath).toBe(`/cards?card_pool=${preferredPool}`);
      expect(useCardPoolWorkspaceStore().activePool).toBe(preferredPool);
    },
  );

  test.each(['evil', 'neutral'] as const)(
    'allows an anonymous %s Gallery deep link',
    async (cardPool) => {
      setAnonymousSession();
      const router = createAppRouter(createMemoryHistory());

      await router.push(`/cards?card_pool=${cardPool}`);

      expect(router.currentRoute.value.fullPath).toBe(`/cards?card_pool=${cardPool}`);
      expect(useCardPoolWorkspaceStore().activePool).toBe(cardPool);
    },
  );

  test('allows an ordinary user to open a non-Player Gallery deep link with a trailing slash', async () => {
    setSession();
    const router = createAppRouter(createMemoryHistory());

    await router.push('/cards/?card_pool=evil');

    expect(router.currentRoute.value.query.card_pool).toBe('evil');
    expect(useCardPoolWorkspaceStore().activePool).toBe('evil');
  });

  test('preserves the selected workspace across login and logout session changes', async () => {
    setAnonymousSession();
    const router = createAppRouter(createMemoryHistory());
    await router.push('/cards?card_pool=neutral');
    const workspace = useCardPoolWorkspaceStore();

    setSession();
    expect(workspace.activePool).toBe('neutral');
    setAnonymousSession();
    await nextTick();

    expect(workspace.activePool).toBe('neutral');
    expect(localStorage.getItem(CARD_POOL_WORKSPACE_PREFERENCE_KEY)).toBe('neutral');
  });

  test('does not commit route-derived workspace state when a later guard rejects navigation', async () => {
    setSession();
    const router = createAppRouter(createMemoryHistory());
    router.beforeEach((to) => to.query.card_pool !== 'evil');
    await router.push('/cards');
    const workspace = useCardPoolWorkspaceStore();
    const generation = workspace.generation;

    await router.push('/cards?card_pool=evil');

    expect(router.currentRoute.value.fullPath).toBe('/cards');
    expect(workspace.activePool).toBe('player');
    expect(workspace.generation).toBe(generation);
  });

  test('keeps public pool context on direct card routes', async () => {
    setAnonymousSession();
    const router = createAppRouter(createMemoryHistory());

    await router.push('/cards/evil-card?card_pool=evil&return_card_pool=neutral');

    expect(router.currentRoute.value.fullPath).toBe(
      '/cards/evil-card?card_pool=evil&return_card_pool=neutral',
    );
    expect(useCardPoolWorkspaceStore().activePool).toBe('neutral');
  });

  test('initializes a resource workspace from its explicit card pool', async () => {
    localStorage.setItem(CARD_POOL_WORKSPACE_PREFERENCE_KEY, 'player');
    setSession();
    const router = createAppRouter(createMemoryHistory());

    await router.push('/cards/evil-card?card_pool=evil');

    expect(router.currentRoute.value.fullPath).toBe('/cards/evil-card?card_pool=evil');
    expect(useCardPoolWorkspaceStore().activePool).toBe('evil');
  });

  test('prefers a resource return pool over the target card pool', async () => {
    localStorage.setItem(CARD_POOL_WORKSPACE_PREFERENCE_KEY, 'player');
    setSession();
    const router = createAppRouter(createMemoryHistory());

    await router.push('/cards/neutral-card?card_pool=neutral&return_card_pool=evil');

    expect(useCardPoolWorkspaceStore().activePool).toBe('evil');
  });

  test('preserves a non-Player staff-route deep link through login', async () => {
    setAnonymousSession();
    const router = createAppRouter(createMemoryHistory());

    await router.push('/cards/evil-card/edit?card_pool=evil');

    expect(router.currentRoute.value.path).toBe('/login');
    expect(router.currentRoute.value.query.redirect).toBe(
      '/cards/evil-card/edit?card_pool=evil',
    );
  });

  test('normalizes an obsolete Gallery pool to Player instead of a stored preference', async () => {
    localStorage.setItem(CARD_POOL_WORKSPACE_PREFERENCE_KEY, 'neutral');
    setSession();
    const router = createAppRouter(createMemoryHistory());

    await router.push('/cards?card_pool=unsupported');

    expect(router.currentRoute.value.fullPath).toBe('/cards');
    expect(useCardPoolWorkspaceStore().activePool).toBe('player');
  });

  test('makes deck and Playtester routes explicitly return to Player', async () => {
    setSession();
    const router = createAppRouter(createMemoryHistory());
    await router.push('/cards?card_pool=evil');

    await router.push('/playtester?card_pool=evil&preview=deck-1');

    expect(router.currentRoute.value.path).toBe('/playtester');
    expect(router.currentRoute.value.fullPath).toBe('/playtester?preview=deck-1');
    expect(useCardPoolWorkspaceStore().activePool).toBe('player');
  });

  test('strips a non-Player pool query from a Player-only route', async () => {
    setSession();
    const router = createAppRouter(createMemoryHistory());

    await router.push('/playtester?card_pool=evil');

    expect(router.currentRoute.value.fullPath).toBe('/playtester');
    expect(useCardPoolWorkspaceStore().activePool).toBe('player');
  });

  test('marks card-derived routes with their workspace capabilities', () => {
    setSession();
    const router = createAppRouter(createMemoryHistory());

    expect(router.resolve('/cards/evil-card').meta.workspaceCapability).toBe('resource');
    expect(router.resolve('/card-groups/neutral-group').meta.workspaceCapability).toBe('resource');
    expect(router.resolve('/settings').meta.workspaceCapability).toBe('global');
  });

  test('declares one workspace capability for every user-visible route', () => {
    const userVisibleRoutes = APP_ROUTES.filter((route) => !('redirect' in route));

    expect(userVisibleRoutes.length).toBeGreaterThan(0);
    expect(userVisibleRoutes.every((route) => route.meta?.workspaceCapability)).toBe(true);
  });

  test.each(['evil', 'neutral'] as const)(
    'switches from %s back to canonical Player Gallery',
    async (nonPlayerPool) => {
      setSession();
      const router = createAppRouter(createMemoryHistory());
      await router.push(`/cards?card_pool=${nonPlayerPool}`);

      await router.push({ path: '/cards', query: { card_pool: 'player' } });

      expect(router.currentRoute.value.fullPath).toBe('/cards');
      expect(useCardPoolWorkspaceStore().activePool).toBe('player');
    },
  );
});
