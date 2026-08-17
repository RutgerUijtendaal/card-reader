import { createApp, nextTick } from 'vue';
import { createMemoryHistory, createRouter } from 'vue-router';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import AppHotkeysPanel from '@/app/components/AppHotkeysPanel.vue';

const { authState, workspaceState } = vi.hoisted(() => ({
  authState: {
    authenticated: true,
  },
  workspaceState: {
    activePool: 'player' as 'player' | 'evil' | 'neutral',
  },
}));

vi.mock('@/domain/session/store', () => ({
  useAuthStore: () => authState,
}));

vi.mock('@/domain/cards/cardPoolWorkspace', () => ({
  useCardPoolWorkspaceStore: () => workspaceState,
}));

vi.mock('@/shared/composables/useFloatingPopover', async () => {
  const { computed, ref } = await import('vue');
  return {
    useFloatingPopover: () => {
      const isOpen = ref(false);
      return {
        isOpen,
        triggerRef: ref<HTMLElement | null>(null),
        panelRef: ref<HTMLElement | null>(null),
        x: computed(() => 12),
        y: computed(() => 24),
        availableHeight: ref(480),
        toggle: () => {
          isOpen.value = !isOpen.value;
        },
        close: () => {
          isOpen.value = false;
        },
      };
    },
  };
});

const mountPanel = async (
  path: string,
  compact = false,
): Promise<{ container: HTMLElement; unmount: () => void }> => {
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
  const app = createApp(AppHotkeysPanel, { compact });
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
    workspaceState.activePool = 'player';
  });

  test('shows default hotkeys away from the active playtester route', async () => {
    const mounted = await mountPanel('/cards');

    expect(mounted.container.textContent).toContain('Search and quick actions');
    expect(mounted.container.textContent).toContain('Search');
    expect(mounted.container.textContent).toContain('New Deck');
    expect(mounted.container.textContent).not.toContain('Shuffle');
    expect(mounted.container.querySelector('[data-hotkey-count]')?.getAttribute('data-hotkey-count')).toBe('4');

    mounted.unmount();
  });

  test('shows playtester hotkeys on the playtester deck selector', async () => {
    const mounted = await mountPanel('/playtester');

    expect(mounted.container.textContent).toContain('Playtester essentials');
    expect(mounted.container.textContent).toContain('Next turn');
    expect(mounted.container.textContent).toContain('Untap all');
    expect(mounted.container.textContent).toContain('Draw');
    expect(mounted.container.textContent).toContain('View all shortcuts');
    expect(mounted.container.textContent).not.toContain('Shuffle');
    expect(mounted.container.textContent).not.toContain('Search and quick actions');
    expect(mounted.container.textContent).not.toContain('New Deck');

    mounted.unmount();
  });

  test('hides the Player-only New Deck shortcut in non-Player workspaces', async () => {
    workspaceState.activePool = 'evil';
    const mounted = await mountPanel('/cards');

    expect(mounted.container.textContent).toContain('Search');
    expect(mounted.container.textContent).not.toContain('New Deck');
    expect(mounted.container.querySelector('[data-hotkey-count]')?.getAttribute('data-hotkey-count')).toBe('3');

    mounted.unmount();
  });

  test('shows playtester hotkeys on the active playtester route', async () => {
    const mounted = await mountPanel('/playtester/deck-1');
    const trigger = mounted.container.querySelector<HTMLButtonElement>(
      'button[aria-label="Open all playtester hotkeys"]',
    );

    expect(trigger).not.toBeNull();
    expect(trigger?.getAttribute('aria-expanded')).toBe('false');
    trigger?.click();
    await nextTick();

    const popover = document.body.querySelector<HTMLElement>('[data-testid="hotkeys-popover"]');
    const popoverText = popover?.textContent ?? '';

    expect(trigger?.getAttribute('aria-expanded')).toBe('true');
    expect(popover).not.toBeNull();
    expect(popover?.style.maxHeight).toBe('480px');
    expect(popoverText).toContain('Playtester hotkeys');
    expect(popoverText).toContain('Turn');
    expect(popoverText).toContain('Cards & board');
    expect(popoverText).toContain('Stacks');
    expect(popoverText).toContain('History');
    expect(popoverText).toContain('View');
    expect(popoverText).toContain('Library');
    expect(popoverText).toContain('Tap');
    expect(popoverText).toContain('Flip');
    expect(popoverText).toContain('Group');
    expect(popoverText).toContain('Shuffle');
    expect(popoverText).toContain('Delete');
    expect(popoverText).toContain('Undo');
    expect(popoverText).toContain('Ctrl+Z');
    expect(popoverText).toContain('Redo');
    expect(popoverText).toContain('Ctrl+Shift+Z');
    expect(popoverText).toContain('Ctrl+Y');
    expect(popoverText).toContain('Copy/Paste');
    expect(popoverText).toContain('Zoom card');
    expect(popoverText).toContain('Middle Mouse');
    expect(popoverText).toContain('Scale');
    expect(popoverText).not.toContain('New Deck');

    mounted.unmount();
  });

  test('uses an icon-only compact trigger for the same complete reference', async () => {
    const mounted = await mountPanel('/playtester/deck-1', true);
    const trigger = mounted.container.querySelector<HTMLButtonElement>(
      'button[aria-label="Open all playtester hotkeys"]',
    );

    expect(trigger).not.toBeNull();
    expect(trigger?.parentElement?.classList.contains('justify-center')).toBe(true);
    expect(mounted.container.textContent?.trim()).toBe('');
    trigger?.click();
    await nextTick();

    expect(document.body.querySelector('[data-testid="hotkeys-popover"]')?.textContent).toContain('Shuffle');

    mounted.unmount();
  });
});
