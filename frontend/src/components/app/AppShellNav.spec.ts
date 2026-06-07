import { createApp, nextTick } from 'vue';
import { createMemoryHistory, createRouter } from 'vue-router';
import { afterEach, describe, expect, test, vi } from 'vitest';
import AppShellNav from '@/components/app/AppShellNav.vue';

const authState = {
  authEnabled: true,
  authenticated: true,
  canAccessStaffRoutes: false,
  logout: vi.fn(),
};
const unreadNotificationCount = { value: 3, __v_isRef: true };

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

const mountNav = async () => {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/cards', component: { template: '<div />' } },
      { path: '/decks', component: { template: '<div />' } },
      { path: '/my/decks', component: { template: '<div />' } },
      { path: '/notifications', component: { template: '<div />' } },
      { path: '/settings', component: { template: '<div />' } },
    ],
  });
  await router.push('/cards');
  await router.isReady();
  const app = createApp(AppShellNav);
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
    authState.authEnabled = true;
    authState.authenticated = true;
    unreadNotificationCount.value = 3;
    document.body.innerHTML = '';
  });

  test('shows notification link with unread badge for authenticated users', async () => {
    const mounted = await mountNav();

    expect(mounted.container.textContent).toContain('Notifications');
    expect(mounted.container.textContent).toContain('3');
    expect(mounted.container.querySelector('a[href="/notifications"]')).not.toBeNull();
    mounted.unmount();
  });

  test('hides notification link when there is no real authenticated user', async () => {
    authState.authEnabled = false;
    authState.authenticated = false;

    const mounted = await mountNav();

    expect(mounted.container.textContent).not.toContain('Notifications');
    mounted.unmount();
  });
});
