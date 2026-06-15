import { createApp, nextTick } from 'vue';
import { createMemoryHistory, createRouter } from 'vue-router';
import { afterEach, describe, expect, test, vi } from 'vitest';
import AppShellNav from '@/components/app/AppShellNav.vue';

const authState = {
  authenticated: true,
  canAccessStaffRoutes: false,
  logout: vi.fn(),
};
const unreadNotificationCount = { value: 3, __v_isRef: true };
const pendingAccessRequestCount = { value: 0, __v_isRef: true };

vi.mock('@/modules/auth/authStore', () => ({
  useAuthStore: () => authState,
}));

vi.mock('@/composables/useReviewSummary', () => ({
  useReviewSummary: () => ({
    openParseFlagItemCount: { value: 0, __v_isRef: true },
    loadReviewSummary: vi.fn(),
  }),
}));

vi.mock('@/composables/useNotificationSummary', () => ({
  useNotificationSummary: () => ({
    unreadNotificationCount,
    loadNotificationSummary: vi.fn(),
  }),
}));

vi.mock('@/composables/useAccessRequestSummary', () => ({
  useAccessRequestSummary: () => ({
    pendingAccessRequestCount,
    loadAccessRequestSummary: vi.fn(),
  }),
}));

vi.mock('@/components/app/AppHotkeysPanel.vue', () => ({
  default: {
    name: 'AppHotkeysPanel',
    template: '<div />',
    props: ['compact'],
  },
}));

vi.mock('@/components/app/ThemeModeMenu.vue', () => ({
  default: {
    name: 'ThemeModeMenu',
    template: '<div />',
    props: ['compact'],
  },
}));

const mountNav = async (props: { collapsed?: boolean } = {}) => {
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
  await router.push('/cards');
  await router.isReady();
  const app = createApp(AppShellNav, props);
  app.use(router);
  app.mount(container);
  await nextTick();

  return {
    container,
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
});
