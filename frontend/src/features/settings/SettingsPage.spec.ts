import { createApp, nextTick } from 'vue';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
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

const mountPage = async () => {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const app = createApp(SettingsPage);
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

describe('SettingsPage developer-data capability', () => {
  beforeEach(() => {
    authState.canDownloadDeveloperData = true;
  });

  afterEach(() => {
    document.body.innerHTML = '';
  });

  test('shows and opens Developer Data when the session capability allows it', async () => {
    const mounted = await mountPage();
    const developerButton = Array.from(mounted.container.querySelectorAll('button')).find((button) =>
      button.textContent?.includes('Developer Data'),
    );
    expect(developerButton).toBeDefined();

    developerButton?.click();
    await nextTick();
    expect(mounted.container.querySelector('[data-testid="developer-data-section"]')).not.toBeNull();
    mounted.unmount();
  });

  test('hides Developer Data when the capability is absent', async () => {
    authState.canDownloadDeveloperData = false;
    const mounted = await mountPage();
    expect(mounted.container.textContent).not.toContain('Developer Data');
    mounted.unmount();
  });
});
