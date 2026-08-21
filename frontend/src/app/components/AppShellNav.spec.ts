import { createApp, nextTick } from 'vue';
import { createPinia } from 'pinia';
import { createMemoryHistory, createRouter } from 'vue-router';
import { afterEach, describe, expect, test, vi } from 'vitest';
import AppShellNav from '@/app/components/AppShellNav.vue';
import { useCardPoolWorkspaceStore } from '@/domain/cards/cardPoolWorkspace';
import {
  clearGalleryNavigationState,
  setGalleryNavigationCards,
  useGalleryCardNavigation,
} from '@/domain/cards/utils/gallery/galleryNavigation';

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
    openReviewCount: { value: 0, __v_isRef: true },
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
  blockEvilNavigation: boolean | (() => Promise<boolean>) = false,
  initialPath = '/cards',
) => {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      {
        path: '/',
        component: { template: '<div />' },
        meta: { workspaceCapability: 'global' },
      },
      {
        path: '/cards',
        component: { template: '<div />' },
        meta: { workspaceCapability: 'gallery' },
      },
      {
        path: '/cards/:id/edit',
        component: { template: '<div />' },
        meta: { workspaceCapability: 'resource' },
      },
      {
        path: '/decks',
        component: { template: '<div />' },
        meta: { workspaceCapability: 'player-only' },
      },
      {
        path: '/playtester',
        component: { template: '<div />' },
        meta: { workspaceCapability: 'player-only' },
      },
      {
        path: '/my/decks',
        component: { template: '<div />' },
        meta: { workspaceCapability: 'player-only' },
      },
      {
        path: '/my/decks/new',
        component: { template: '<div />' },
        meta: { workspaceCapability: 'player-only' },
      },
      {
        path: '/notifications',
        component: { template: '<div />' },
        meta: { workspaceCapability: 'global' },
      },
      {
        path: '/login',
        component: { template: '<div />' },
        meta: { workspaceCapability: 'global' },
      },
      {
        path: '/settings',
        component: { template: '<div />' },
        meta: { workspaceCapability: 'global' },
      },
      {
        path: '/imports',
        component: { template: '<div />' },
        meta: { workspaceCapability: 'global' },
      },
      {
        path: '/operations',
        component: { template: '<div />' },
        meta: { workspaceCapability: 'global' },
      },
      {
        path: '/review',
        component: { template: '<div />' },
        meta: { workspaceCapability: 'global' },
      },
      {
        path: '/admin',
        component: { template: '<div />' },
        meta: { workspaceCapability: 'global' },
      },
    ],
  });
  if (blockEvilNavigation) {
    router.beforeEach((to) => {
      if (to.query.card_pool !== 'evil') {
        return true;
      }
      return typeof blockEvilNavigation === 'function' ? blockEvilNavigation() : false;
    });
  }
  await router.push(initialPath);
  await router.isReady();
  const pinia = createPinia();
  const workspace = useCardPoolWorkspaceStore(pinia);
  const closeMobile = vi.fn();
  const app = createApp(AppShellNav, {
    ...props,
    onCloseMobile: closeMobile,
  });
  app.use(pinia);
  app.use(router);
  app.mount(container);
  await nextTick();

  return {
    container,
    router,
    workspace,
    closeMobile,
    unmount: () => {
      app.unmount();
      container.remove();
    },
  };
};

describe('AppShellNav', () => {
  afterEach(() => {
    vi.clearAllMocks();
    authState.authenticated = true;
    unreadNotificationCount.value = 3;
    pendingAccessRequestCount.value = 0;
    authState.canAccessStaffRoutes = false;
    localStorage.clear();
    clearGalleryNavigationState();
    document.body.innerHTML = '';
  });

  test('shows notification link with unread badge for authenticated users', async () => {
    const mounted = await mountNav();

    expect(mounted.container.textContent).toContain('Notifications');
    expect(mounted.container.textContent).toContain('3');
    expect(mounted.container.querySelector('a[href="/notifications"]')).not.toBeNull();
    expect(
      mounted.container.querySelector('a[href="/notifications"] .nav-badge')?.textContent,
    ).toContain('3');
    mounted.unmount();
  });

  test('keeps Home separate from the workspace-aware Gallery link', async () => {
    const mounted = await mountNav();

    expect(mounted.container.querySelector('a[href="/"] .lucide-house')).not.toBeNull();
    expect(mounted.container.querySelector('a[href="/cards"]')).not.toBeNull();
    const brandLink = mounted.container.querySelector<HTMLAnchorElement>('a.flex.min-w-0');
    expect(brandLink?.getAttribute('href')).toBe('/');
    mounted.unmount();
  });

  test('shows every workspace without depending on authentication', async () => {
    const mounted = await mountNav();

    expect(mounted.container.querySelector('[aria-label="Player workspace"]')).not.toBeNull();
    expect(mounted.container.querySelector('[aria-label="Evil workspace"]')).not.toBeNull();
    expect(mounted.container.querySelector('[aria-label="Neutral workspace"]')).not.toBeNull();
    mounted.unmount();
  });

  test('places the workspace picker immediately before the hotkeys area', async () => {
    const mounted = await mountNav();
    const pickerSection = mounted.container.querySelector(
      '[data-testid="card-pool-workspace-switcher"]',
    )?.parentElement;
    const hotkeysSection = mounted.container.querySelector('[data-testid="hotkeys-panel"]')
      ?.parentElement?.parentElement;
    const poolButtons = Array.from(
      mounted.container.querySelectorAll<HTMLButtonElement>(
        '[data-testid="card-pool-workspace-switcher"] button',
      ),
    );

    expect(pickerSection?.nextElementSibling).toBe(hotkeysSection);
    expect(poolButtons.every((button) => button.parentElement?.classList.contains('flex-1'))).toBe(
      true,
    );
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
    expect(
      mounted.container.querySelector('a[href="/operations"] .lucide-activity'),
    ).not.toBeNull();
    mounted.unmount();
  });

  test('shows permitted workspaces and removes Player-only navigation in Evil', async () => {
    const mounted = await mountNav();
    const evilButton = mounted.container.querySelector<HTMLButtonElement>(
      '[aria-label="Evil workspace"]',
    );
    expect(evilButton).toBeInstanceOf(HTMLButtonElement);

    evilButton?.click();
    await new Promise((resolve) => setTimeout(resolve, 0));
    await nextTick();

    expect(mounted.container.textContent).not.toContain('Playtester');
    expect(mounted.container.textContent).not.toContain('Build a deck');
    expect(mounted.container.querySelector('a[href="/cards?card_pool=evil"]')).not.toBeNull();
    mounted.unmount();
  });

  test('uses the active pool icon for the Gallery link in every workspace', async () => {
    const mounted = await mountNav();

    expect(
      mounted.container.querySelector('a[href="/cards"] [data-card-pool-icon="player"]'),
    ).not.toBeNull();

    mounted.container.querySelector<HTMLButtonElement>('[aria-label="Evil workspace"]')?.click();
    await new Promise((resolve) => setTimeout(resolve, 0));
    await nextTick();
    expect(
      mounted.container.querySelector(
        'a[href="/cards?card_pool=evil"] [data-card-pool-icon="evil"]',
      ),
    ).not.toBeNull();

    mounted.container.querySelector<HTMLButtonElement>('[aria-label="Neutral workspace"]')?.click();
    await new Promise((resolve) => setTimeout(resolve, 0));
    await nextTick();
    expect(
      mounted.container.querySelector(
        'a[href="/cards?card_pool=neutral"] [data-card-pool-icon="neutral"]',
      ),
    ).not.toBeNull();

    mounted.unmount();
  });

  test('treats the active workspace button as a no-op', async () => {
    const mounted = await mountNav();
    const generation = mounted.workspace.generation;
    const playerButton = mounted.container.querySelector<HTMLButtonElement>(
      '[aria-label="Player workspace"]',
    );

    playerButton?.click();
    await nextTick();

    expect(mounted.router.currentRoute.value.fullPath).toBe('/cards');
    expect(mounted.workspace.activePool).toBe('player');
    expect(mounted.workspace.generation).toBe(generation);
    mounted.unmount();
  });

  test.each([
    '/',
    '/settings?section=appearance',
    '/notifications',
    '/imports',
    '/operations',
    '/review?view=flags',
    '/admin?tab=catalog',
  ])('switches context without leaving the global route %s', async (initialPath) => {
    const mounted = await mountNav({}, false, initialPath);
    const evilButton = mounted.container.querySelector<HTMLButtonElement>(
      '[aria-label="Evil workspace"]',
    );

    evilButton?.click();
    await new Promise((resolve) => setTimeout(resolve, 0));
    await nextTick();

    expect(mounted.router.currentRoute.value.fullPath).toBe(initialPath);
    expect(mounted.workspace.activePool).toBe('evil');
    mounted.unmount();
  });

  test('returns Home after signing out', async () => {
    const mounted = await mountNav({}, false, '/settings');
    const signOutButton = Array.from(mounted.container.querySelectorAll('button')).find(
      (button) => button.textContent?.includes('Sign out'),
    );

    signOutButton?.click();
    await new Promise((resolve) => setTimeout(resolve, 0));
    await nextTick();

    expect(authState.logout).toHaveBeenCalled();
    expect(mounted.router.currentRoute.value.fullPath).toBe('/');
    mounted.unmount();
  });

  test('keeps a resource open and updates only its workspace return context', async () => {
    const mounted = await mountNav(
      {},
      false,
      '/cards/card-1/edit?card_pool=evil&return_card_pool=player&tab=card-version',
    );
    const neutralButton = mounted.container.querySelector<HTMLButtonElement>(
      '[aria-label="Neutral workspace"]',
    );

    neutralButton?.click();
    await new Promise((resolve) => setTimeout(resolve, 0));
    await nextTick();

    expect(mounted.router.currentRoute.value.path).toBe('/cards/card-1/edit');
    expect(mounted.router.currentRoute.value.query).toEqual({
      card_pool: 'evil',
      return_card_pool: 'neutral',
      tab: 'card-version',
    });
    expect(mounted.workspace.activePool).toBe('neutral');
    mounted.unmount();
  });

  test('clears stale Gallery paging when a resource return workspace changes', async () => {
    const mounted = await mountNav(
      {},
      false,
      '/cards/card-1/edit?return_card_pool=player',
    );
    setGalleryNavigationCards(
      [
        { id: 'card-1', result_type: 'card' },
        { id: 'card-2', result_type: 'card' },
      ],
      2,
      null,
      50,
      'card_pool=player',
    );
    const galleryNavigation = useGalleryCardNavigation(
      mounted.router.currentRoute.value,
      mounted.router,
      'edit',
    );
    expect(galleryNavigation.nextCardId.value).toBe('card-2');

    mounted.container.querySelector<HTMLButtonElement>('[aria-label="Evil workspace"]')?.click();
    await new Promise((resolve) => setTimeout(resolve, 0));
    await nextTick();

    expect(galleryNavigation.hasGalleryContext.value).toBe(false);
    expect(galleryNavigation.nextCardId.value).toBeNull();
    mounted.unmount();
  });

  test('falls back from a Player-only route only after navigation is accepted', async () => {
    const mounted = await mountNav({}, false, '/my/decks/new');
    const evilButton = mounted.container.querySelector<HTMLButtonElement>(
      '[aria-label="Evil workspace"]',
    );

    evilButton?.click();
    await new Promise((resolve) => setTimeout(resolve, 0));
    await nextTick();

    expect(mounted.router.currentRoute.value.fullPath).toBe('/cards?card_pool=evil');
    expect(mounted.workspace.activePool).toBe('evil');
    mounted.unmount();
  });

  test('closes the mobile drawer after a context-only selection succeeds', async () => {
    const mounted = await mountNav(
      { mobile: true },
      false,
      '/settings',
    );
    const evilButton = mounted.container.querySelector<HTMLButtonElement>(
      '[aria-label="Evil workspace"]',
    );

    evilButton?.click();
    await new Promise((resolve) => setTimeout(resolve, 0));
    await nextTick();

    expect(mounted.closeMobile).toHaveBeenCalledOnce();
    mounted.unmount();
  });

  test('commits only the latest rapid workspace selection', async () => {
    const mounted = await mountNav();
    const evilButton = mounted.container.querySelector<HTMLButtonElement>(
      '[aria-label="Evil workspace"]',
    );
    const neutralButton = mounted.container.querySelector<HTMLButtonElement>(
      '[aria-label="Neutral workspace"]',
    );

    evilButton?.click();
    neutralButton?.click();
    await new Promise((resolve) => setTimeout(resolve, 0));
    await nextTick();

    expect(mounted.router.currentRoute.value.fullPath).toBe('/cards?card_pool=neutral');
    expect(mounted.workspace.activePool).toBe('neutral');
    mounted.unmount();
  });

  test('counter-navigates a pending non-Player selection when Player is reselected', async () => {
    let releaseNavigation!: (accepted: boolean) => void;
    const navigationGate = new Promise<boolean>((resolve) => {
      releaseNavigation = resolve;
    });
    const mounted = await mountNav({}, () => navigationGate);
    const evilButton = mounted.container.querySelector<HTMLButtonElement>(
      '[aria-label="Evil workspace"]',
    );
    const playerButton = mounted.container.querySelector<HTMLButtonElement>(
      '[aria-label="Player workspace"]',
    );

    evilButton?.click();
    playerButton?.click();
    releaseNavigation(true);
    await new Promise((resolve) => setTimeout(resolve, 0));
    await nextTick();

    expect(mounted.router.currentRoute.value.fullPath).toBe('/cards?card_pool=player');
    expect(mounted.workspace.activePool).toBe('player');
    mounted.unmount();
  });

  test('keeps the current workspace mounted when guarded navigation is rejected', async () => {
    const mounted = await mountNav({}, true, '/my/decks/new');
    const generation = mounted.workspace.generation;
    const evilButton = mounted.container.querySelector<HTMLButtonElement>(
      '[aria-label="Evil workspace"]',
    );

    evilButton?.click();
    await new Promise((resolve) => setTimeout(resolve, 0));
    await nextTick();

    expect(mounted.workspace.activePool).toBe('player');
    expect(mounted.workspace.generation).toBe(generation);
    expect(mounted.router.currentRoute.value.path).toBe('/my/decks/new');
    expect(mounted.container.textContent).toContain('Playtester');
    mounted.unmount();
  });

  test('exposes all compact workspace icons with accessible names when collapsed', async () => {
    const mounted = await mountNav({ collapsed: true });
    const buttons = Array.from(
      mounted.container.querySelectorAll<HTMLButtonElement>(
        '[data-testid="card-pool-workspace-switcher"] button',
      ),
    );

    expect(buttons.map((button) => button.getAttribute('aria-label'))).toEqual([
      'Player workspace',
      'Evil workspace',
      'Neutral workspace',
    ]);
    expect(buttons.every((button) => button.querySelector('svg'))).toBe(true);
    mounted.unmount();
  });

  test('shows pool names in tooltips on hover', async () => {
    const mounted = await mountNav();
    const evilButton = mounted.container.querySelector<HTMLButtonElement>(
      '[aria-label="Evil workspace"]',
    );

    evilButton?.dispatchEvent(new MouseEvent('mouseenter', { bubbles: true }));
    await nextTick();

    expect(document.body.querySelector('[role="tooltip"]')?.textContent).toBe('Evil');
    mounted.unmount();
  });
});
