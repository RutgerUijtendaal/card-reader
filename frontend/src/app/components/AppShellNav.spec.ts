import { createApp, nextTick } from 'vue';
import { createPinia } from 'pinia';
import { createMemoryHistory, createRouter } from 'vue-router';
import { afterEach, describe, expect, test, vi } from 'vitest';
import AppShellNav from '@/app/components/AppShellNav.vue';
import { useCardPoolWorkspaceStore } from '@/domain/cards/cardPoolWorkspace';
import type { CardPool } from '@/domain/cards/cardPools';

const authState = {
  authenticated: true,
  canAccessStaffRoutes: false,
  logout: vi.fn(),
};
const unreadNotificationCount = { value: 3, __v_isRef: true };
const pendingAccessRequestCount = { value: 0, __v_isRef: true };

vi.mock('@/domain/session/store', () => ({
  useAuthStore: () => authState,
}));

vi.mock('@/domain/review/composables/useReviewSummary', () => ({
  useReviewSummary: () => ({
    openParseFlagItemCount: { value: 0, __v_isRef: true },
    loadReviewSummary: vi.fn(),
  }),
}));

vi.mock('@/domain/notifications/composables/useNotificationSummary', () => ({
  useNotificationSummary: () => ({
    unreadNotificationCount,
    loadNotificationSummary: vi.fn(),
  }),
}));

vi.mock('@/domain/access-requests/composables/useAccessRequestSummary', () => ({
  useAccessRequestSummary: () => ({
    pendingAccessRequestCount,
    loadAccessRequestSummary: vi.fn(),
  }),
}));

vi.mock('@/app/components/AppHotkeysPanel.vue', () => ({
  default: {
    name: 'AppHotkeysPanel',
    template: '<div data-testid="hotkeys-panel" />',
    props: ['compact'],
  },
}));

vi.mock('@/app/components/ThemeModeMenu.vue', () => ({
  default: {
    name: 'ThemeModeMenu',
    template: '<div />',
    props: ['compact'],
  },
}));

const mountNav = async (
  props: { collapsed?: boolean; mobile?: boolean } = {},
  accessiblePools: CardPool[] = ['player'],
  blockEvilNavigation = false,
) => {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/cards', component: { template: '<div />' } },
      { path: '/decks', component: { template: '<div />' } },
      { path: '/playtester', component: { template: '<div />' } },
      { path: '/my/decks', component: { template: '<div />' } },
      { path: '/my/decks/new', component: { template: '<div />' } },
      { path: '/notifications', component: { template: '<div />' } },
      { path: '/settings', component: { template: '<div />' } },
      { path: '/import-jobs', component: { template: '<div />' } },
      { path: '/review', component: { template: '<div />' } },
      { path: '/admin', component: { template: '<div />' } },
    ],
  });
  if (blockEvilNavigation) {
    router.beforeEach((to) => to.query.card_pool !== 'evil');
  }
  await router.push('/cards');
  await router.isReady();
  const pinia = createPinia();
  const workspace = useCardPoolWorkspaceStore(pinia);
  workspace.synchronizeSession(accessiblePools, 'test-user');
  const app = createApp(AppShellNav, props);
  app.use(pinia);
  app.use(router);
  app.mount(container);
  await nextTick();

  return {
    container,
    router,
    workspace,
    unmount: () => {
      app.unmount();
      container.remove();
    },
  };
};

describe('AppShellNav', () => {
  afterEach(() => {
    authState.authenticated = true;
    unreadNotificationCount.value = 3;
    pendingAccessRequestCount.value = 0;
    authState.canAccessStaffRoutes = false;
    localStorage.clear();
    document.body.innerHTML = '';
  });

  test('shows notification link with unread badge for authenticated users', async () => {
    const mounted = await mountNav();

    expect(mounted.container.textContent).toContain('Notifications');
    expect(mounted.container.textContent).toContain('3');
    expect(mounted.container.querySelector('a[href="/notifications"]')).not.toBeNull();
    expect(mounted.container.querySelector('a[href="/notifications"] .nav-badge')?.textContent).toContain('3');
    mounted.unmount();
  });

  test('shows Player as the only workspace when restricted pools are unavailable', async () => {
    const mounted = await mountNav();

    expect(mounted.container.querySelector('[aria-label="Player workspace"]')).not.toBeNull();
    expect(mounted.container.querySelector('[aria-label="Evil workspace"]')).toBeNull();
    expect(mounted.container.querySelector('[aria-label="Neutral workspace"]')).toBeNull();
    mounted.unmount();
  });

  test('places the workspace picker immediately before the hotkeys area', async () => {
    const mounted = await mountNav({}, ['player', 'evil', 'neutral']);
    const pickerSection = mounted.container.querySelector('[data-testid="card-pool-workspace-switcher"]')?.parentElement;
    const hotkeysSection = mounted.container.querySelector('[data-testid="hotkeys-panel"]')?.parentElement?.parentElement;
    const poolButtons = Array.from(mounted.container.querySelectorAll<HTMLButtonElement>(
      '[data-testid="card-pool-workspace-switcher"] button',
    ));

    expect(pickerSection?.nextElementSibling).toBe(hotkeysSection);
    expect(poolButtons.every((button) => button.parentElement?.classList.contains('flex-1'))).toBe(true);
    mounted.unmount();
  });

  test('shows notification indicator dot when collapsed', async () => {
    const mounted = await mountNav({ collapsed: true });
    const notificationLink = mounted.container.querySelector('a[href="/notifications"]');

    expect(notificationLink).not.toBeNull();
    expect(notificationLink?.querySelector('.nav-badge')).toBeNull();
    expect(notificationLink?.querySelector('.nav-indicator-dot')).not.toBeNull();
    mounted.unmount();
  });

  test('hides notification link when there is no real authenticated user', async () => {
    authState.authenticated = false;

    const mounted = await mountNav();

    expect(mounted.container.textContent).not.toContain('Notifications');
    mounted.unmount();
  });

  test('shows admin pending access request badge for staff users', async () => {
    authState.canAccessStaffRoutes = true;
    pendingAccessRequestCount.value = 2;

    const mounted = await mountNav();
    const adminLink = mounted.container.querySelector('a[href="/admin"]');

    expect(adminLink).not.toBeNull();
    expect(adminLink?.querySelector('.nav-badge')?.textContent).toContain('2');
    mounted.unmount();
  });

  test('shows permitted workspaces and removes Player-only navigation in Evil', async () => {
    const mounted = await mountNav({}, ['player', 'evil', 'neutral']);
    const evilButton = mounted.container.querySelector<HTMLButtonElement>('[aria-label="Evil workspace"]');
    expect(evilButton).toBeInstanceOf(HTMLButtonElement);

    evilButton?.click();
    await new Promise((resolve) => setTimeout(resolve, 0));
    await nextTick();

    expect(mounted.container.textContent).not.toContain('Playtester');
    expect(mounted.container.textContent).not.toContain('Build a deck');
    expect(mounted.container.querySelector('a[href="/cards?card_pool=evil"]')).not.toBeNull();
    mounted.unmount();
  });

  test('treats the active workspace button as a no-op', async () => {
    const mounted = await mountNav({}, ['player', 'evil', 'neutral']);
    const generation = mounted.workspace.generation;
    const playerButton = mounted.container.querySelector<HTMLButtonElement>('[aria-label="Player workspace"]');

    playerButton?.click();
    await nextTick();

    expect(mounted.router.currentRoute.value.fullPath).toBe('/cards');
    expect(mounted.workspace.activePool).toBe('player');
    expect(mounted.workspace.generation).toBe(generation);
    mounted.unmount();
  });

  test('keeps the current workspace mounted when guarded navigation is rejected', async () => {
    const mounted = await mountNav({}, ['player', 'evil', 'neutral'], true);
    const generation = mounted.workspace.generation;
    const evilButton = mounted.container.querySelector<HTMLButtonElement>('[aria-label="Evil workspace"]');

    evilButton?.click();
    await new Promise((resolve) => setTimeout(resolve, 0));
    await nextTick();

    expect(mounted.workspace.activePool).toBe('player');
    expect(mounted.workspace.generation).toBe(generation);
    expect(mounted.container.textContent).toContain('Playtester');
    mounted.unmount();
  });

  test('exposes all compact workspace icons with accessible names when collapsed', async () => {
    const mounted = await mountNav({ collapsed: true }, ['player', 'evil', 'neutral']);
    const buttons = Array.from(mounted.container.querySelectorAll<HTMLButtonElement>(
      '[data-testid="card-pool-workspace-switcher"] button',
    ));

    expect(buttons.map((button) => button.getAttribute('aria-label'))).toEqual([
      'Player workspace',
      'Evil workspace',
      'Neutral workspace',
    ]);
    expect(buttons.every((button) => button.querySelector('svg'))).toBe(true);
    mounted.unmount();
  });

  test('shows pool names in tooltips on hover', async () => {
    const mounted = await mountNav({}, ['player', 'evil', 'neutral']);
    const evilButton = mounted.container.querySelector<HTMLButtonElement>('[aria-label="Evil workspace"]');

    evilButton?.dispatchEvent(new MouseEvent('mouseenter', { bubbles: true }));
    await nextTick();

    expect(document.body.querySelector('[role="tooltip"]')?.textContent).toBe('Evil');
    mounted.unmount();
  });
});
