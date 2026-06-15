import { createApp } from 'vue';
import { createMemoryHistory, createRouter } from 'vue-router';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import AppHotkeysPanel from '@/components/app/AppHotkeysPanel.vue';

const { authState } = vi.hoisted(() => ({
  authState: {
    authenticated: true,
  },
}));

vi.mock('@/modules/auth/authStore', () => ({
  useAuthStore: () => authState,
}));

const mountPanel = async (path: string): Promise<{ container: HTMLElement; unmount: () => void }> => {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/cards', component: { template: '<div />' } },
      { path: '/playtester', component: { template: '<div />' } },
      { path: '/playtester/:deckId', component: { template: '<div />' } },
    ],
  });
  await router.push(path);
  await router.isReady();
  const app = createApp(AppHotkeysPanel);
  app.use(router);
  app.mount(container);
  return {
    container,
    unmount: () => {
      app.unmount();
      container.remove();
    },
  };
};

describe('AppHotkeysPanel', () => {
  beforeEach(() => {
    document.body.innerHTML = '';
    authState.authenticated = true;
  });

  test('shows default hotkeys away from the active playtester route', async () => {
    const mounted = await mountPanel('/cards');

    expect(mounted.container.textContent).toContain('Search and quick actions');
    expect(mounted.container.textContent).toContain('Search');
    expect(mounted.container.textContent).toContain('New Deck');
    expect(mounted.container.textContent).not.toContain('Shuffle');

    mounted.unmount();
  });

  test('shows playtester hotkeys on the playtester deck selector', async () => {
    const mounted = await mountPanel('/playtester');

    expect(mounted.container.textContent).toContain('Playtester actions');
    expect(mounted.container.textContent).toContain('Next turn');
    expect(mounted.container.textContent).toContain('Untap all');
    expect(mounted.container.textContent).toContain('Draw');
    expect(mounted.container.textContent).toContain('Shuffle');
    expect(mounted.container.textContent).not.toContain('Search and quick actions');
    expect(mounted.container.textContent).not.toContain('New Deck');

    mounted.unmount();
  });

  test('shows playtester hotkeys on the active playtester route', async () => {
    const mounted = await mountPanel('/playtester/deck-1');

    expect(mounted.container.textContent).toContain('Playtester actions');
    expect(mounted.container.textContent).toContain('Next turn');
    expect(mounted.container.textContent).toContain('Untap all');
    expect(mounted.container.textContent).toContain('Draw');
    expect(mounted.container.textContent).toContain('N');
    expect(mounted.container.textContent).toContain('U');
    expect(mounted.container.textContent).toContain('D');
    expect(mounted.container.textContent).toContain('Tap');
    expect(mounted.container.textContent).toContain('Flip');
    expect(mounted.container.textContent).toContain('Shuffle');
    expect(mounted.container.textContent).toContain('Delete');
    expect(mounted.container.textContent).toContain('Undo');
    expect(mounted.container.textContent).toContain('Ctrl+Z');
    expect(mounted.container.textContent).toContain('Redo');
    expect(mounted.container.textContent).toContain('Ctrl+Shift+Z');
    expect(mounted.container.textContent).toContain('Ctrl+Y');
    expect(mounted.container.textContent).toContain('Copy/Paste');
    expect(mounted.container.textContent).toContain('Zoom card');
    expect(mounted.container.textContent).toContain('Middle Mouse');
    expect(mounted.container.textContent).toContain('Scale');
    expect(mounted.container.textContent).not.toContain('untap + draw');
    expect(mounted.container.textContent).not.toContain('Draw a card');
    expect(mounted.container.textContent).not.toContain('Tap Card');
    expect(mounted.container.textContent).not.toContain('Card Size');
    expect(mounted.container.textContent).not.toContain('New Deck');

    mounted.unmount();
  });
});
