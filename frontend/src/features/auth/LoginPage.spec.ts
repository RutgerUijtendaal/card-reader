import { createApp, nextTick } from 'vue';
import { createMemoryHistory, createRouter } from 'vue-router';
import { afterEach, describe, expect, test, vi } from 'vitest';
import LoginPage from '@/features/auth/LoginPage.vue';

const authState = vi.hoisted(() => ({
  loading: false,
  login: vi.fn(),
}));

vi.mock('@/domain/session/store', () => ({
  useAuthStore: () => authState,
}));

vi.mock('@/domain/session/api', () => ({
  submitAccessRequest: vi.fn(),
}));

const flushPromises = async (): Promise<void> => {
  await Promise.resolve();
  await Promise.resolve();
};

const mountLogin = async (initialPath = '/login') => {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: { template: '<div />' } },
      { path: '/login', component: LoginPage },
      { path: '/my/decks/new', component: { template: '<div />' } },
    ],
  });
  await router.push(initialPath);
  await router.isReady();
  const app = createApp(LoginPage);
  app.use(router);
  app.mount(container);
  await nextTick();

  return {
    container,
    router,
    submit: async () => {
      container.querySelector('form')?.dispatchEvent(
        new Event('submit', {
          bubbles: true,
          cancelable: true,
        }),
      );
      await flushPromises();
      await nextTick();
    },
    unmount: () => {
      app.unmount();
      container.remove();
    },
  };
};

describe('LoginPage', () => {
  afterEach(() => {
    vi.clearAllMocks();
    authState.loading = false;
    document.body.innerHTML = '';
  });

  test('returns Home after a direct sign in', async () => {
    authState.login.mockResolvedValue({ authenticated: true });
    const mounted = await mountLogin();

    await mounted.submit();

    expect(authState.login).toHaveBeenCalledWith({ username: '', password: '' });
    await vi.waitFor(() => {
      expect(mounted.router.currentRoute.value.fullPath).toBe('/');
    });
    mounted.unmount();
  });

  test('preserves an explicit protected-route redirect', async () => {
    authState.login.mockResolvedValue({ authenticated: true });
    const mounted = await mountLogin('/login?redirect=%2Fmy%2Fdecks%2Fnew%3Freturn_to%3Dmy_decks');

    await mounted.submit();

    await vi.waitFor(() => {
      expect(mounted.router.currentRoute.value.fullPath).toBe('/my/decks/new?return_to=my_decks');
    });
    mounted.unmount();
  });
});
