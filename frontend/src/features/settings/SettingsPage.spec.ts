import { createApp, nextTick } from 'vue';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { createMemoryHistory, createRouter } from 'vue-router';
import SettingsPage from './SettingsPage.vue';

const { authState } = vi.hoisted(() => ({
  authState: { canDownloadDeveloperData: true },
}));

vi.mock('@/domain/session/store', () => ({
  useAuthStore: () => authState,
}));

vi.mock('./components/DeveloperDataSettingsSection.vue', () => ({
  default: { template: '<div data-testid="developer-data-section">Developer data content</div>' },
}));

const mountPage = async (path = '/settings') => {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/settings', component: { template: '<div />' } }],
  });
  await router.push(path);
  await router.isReady();
  const app = createApp(SettingsPage);
  app.use(router);
  app.mount(container);
  await nextTick();
  return {
    container,
    router,
    unmount: () => {
      app.unmount();
      container.remove();
    },
  };
};

describe('SettingsPage developer-data capability', () => {
  beforeEach(() => {
    authState.canDownloadDeveloperData = true;
  });

  afterEach(() => {
    document.body.innerHTML = '';
  });

  test('opens Developer Data from a deep link when the session capability allows it', async () => {
    const mounted = await mountPage('/settings?settings_tab=developer-data');
    expect(mounted.container.querySelector('[data-testid="developer-data-section"]')).not.toBeNull();
    mounted.unmount();
  });

  test('updates the URL when a settings tab is selected', async () => {
    const mounted = await mountPage();
    const developerLink = Array.from(mounted.container.querySelectorAll('a')).find((link) =>
      link.textContent?.includes('Developer Data'),
    );
    expect(developerLink?.getAttribute('href')).toBe('/settings?settings_tab=developer-data');

    developerLink?.click();
    await vi.waitFor(() => {
      expect(mounted.router.currentRoute.value.query.settings_tab).toBe('developer-data');
    });
    expect(developerLink?.getAttribute('aria-current')).toBe('page');
    expect(developerLink?.classList.contains('theme-selected-surface-strong')).toBe(true);
    expect(mounted.container.querySelector('[data-testid="developer-data-section"]')).not.toBeNull();
    mounted.unmount();
  });

  test('hides Developer Data when the capability is absent', async () => {
    authState.canDownloadDeveloperData = false;
    const mounted = await mountPage('/settings?settings_tab=developer-data');
    expect(mounted.container.textContent).not.toContain('Developer Data');
    expect(mounted.container.textContent).toContain('Display');
    mounted.unmount();
  });
});
