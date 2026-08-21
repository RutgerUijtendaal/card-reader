import { createApp, nextTick } from 'vue';
import { createPinia, setActivePinia } from 'pinia';
import { createMemoryHistory, createRouter } from 'vue-router';
import { afterEach, describe, expect, test } from 'vitest';
import HomePage from '@/features/home/HomePage.vue';
import { useCardPoolWorkspaceStore } from '@/domain/cards/cardPoolWorkspace';
import { useAuthStore } from '@/domain/session/store';
import type { CurrentUser } from '@/domain/session/types';

const mountHome = async (user: CurrentUser = { authenticated: false }) => {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const pinia = createPinia();
  setActivePinia(pinia);
  const auth = useAuthStore(pinia);
  auth.$patch({ initialized: true, user });
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: HomePage },
      { path: '/cards', component: { template: '<div />' } },
      { path: '/decks', component: { template: '<div />' } },
      { path: '/playtester', component: { template: '<div />' } },
      { path: '/my/decks/new', component: { template: '<div />' } },
      { path: '/login', component: { template: '<div />' } },
    ],
  });
  await router.push('/');
  await router.isReady();
  const app = createApp(HomePage);
  app.use(pinia);
  app.use(router);
  app.mount(container);
  await nextTick();

  return {
    auth,
    container,
    router,
    workspace: useCardPoolWorkspaceStore(pinia),
    unmount: () => {
      app.unmount();
      container.remove();
    },
  };
};

describe('HomePage', () => {
  afterEach(() => {
    localStorage.clear();
    document.body.innerHTML = '';
  });

  test('orients anonymous visitors around the full collection and keeps Player workflows public', async () => {
    const mounted = await mountHome();

    expect(mounted.container.textContent).toContain('Explore every side of the game.');
    expect(mounted.container.textContent).toContain('Choose a collection');
    expect(
      mounted.container
        .querySelector('[data-card-pool-link="player"]')
        ?.getAttribute('href'),
    ).toBe('/cards');
    expect(
      mounted.container
        .querySelector('[data-card-pool-link="evil"]')
        ?.getAttribute('href'),
    ).toBe('/cards?card_pool=evil');
    expect(mounted.container.querySelectorAll('[data-card-pool-link]')).toHaveLength(3);
    expect(
      mounted.container.querySelector('[data-testid="home-decks-action"]')?.getAttribute('href'),
    ).toBe('/decks');
    expect(
      mounted.container.querySelector('[data-testid="home-playtester-action"]')?.getAttribute('href'),
    ).toBe('/playtester');
    expect(mounted.container.querySelector('[data-testid="home-build-deck-link"]')).toBeNull();

    const signInHref = mounted.container
      .querySelector('[data-testid="home-build-sign-in-link"]')
      ?.getAttribute('href');
    expect(signInHref).toBeTruthy();
    expect(mounted.router.resolve(signInHref ?? '/').query.redirect).toBe(
      '/my/decks/new?return_to=my_decks',
    );
    expect(mounted.container.querySelector('[data-testid="home-build-sign-in-link"]')?.textContent).toContain(
      'Log in to build',
    );
    mounted.unmount();
  });

  test('shows deck creation to an authenticated user', async () => {
    const mounted = await mountHome({
      authenticated: true,
      id: 'user-1',
      username: 'player',
      can_access_admin: false,
    });

    expect(
      mounted.container.querySelector('[data-testid="home-build-deck-link"]')?.getAttribute('href'),
    ).toBe('/my/decks/new?return_to=my_decks');
    expect(mounted.container.querySelector('[data-testid="home-build-sign-in-link"]')).toBeNull();
    mounted.unmount();
  });

  test('keeps the overarching presentation in place while the workspace context changes', async () => {
    const mounted = await mountHome({ authenticated: true, id: 'user-1', username: 'player' });

    mounted.workspace.selectPool('evil');
    await nextTick();

    expect(mounted.router.currentRoute.value.fullPath).toBe('/');
    expect(mounted.container.textContent).toContain('Explore every side of the game.');
    expect(
      mounted.container
        .querySelector('[data-card-pool-link="evil"]')
        ?.getAttribute('href'),
    ).toBe('/cards?card_pool=evil');
    expect(
      mounted.container.querySelector('[data-card-pool-link="evil"] [data-current-workspace]'),
    ).not.toBeNull();
    expect(
      mounted.container.querySelector('[data-card-pool-link="player"] [data-current-workspace]'),
    ).toBeNull();
    expect(mounted.container.querySelector('[data-testid="home-decks-action"]')).not.toBeNull();
    expect(mounted.container.querySelector('[data-testid="home-playtester-action"]')).not.toBeNull();
    expect(mounted.container.querySelector('[data-testid="home-build-deck-link"]')).not.toBeNull();
    expect(mounted.container.querySelectorAll('[data-card-pool-link]')).toHaveLength(3);
    expect(
      mounted.container.querySelector('[data-card-pool-link="neutral"]')?.getAttribute('href'),
    ).toBe('/cards?card_pool=neutral');
    mounted.unmount();
  });
});
