import { createApp, h, nextTick, ref } from 'vue';
import { afterEach, describe, expect, test, vi } from 'vitest';
import BuilderWorkspaceLayout from './BuilderWorkspaceLayout.vue';

const cleanups: (() => void)[] = [];
afterEach(() => cleanups.splice(0).forEach((cleanup) => cleanup()));

const mountWorkspace = async (initiallyOpen = false) => {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const open = ref(initiallyOpen);
  const mountedGallery = vi.fn();
  const app = createApp({
    setup: () => () =>
      h(
        BuilderWorkspaceLayout,
        {},
        {
          default: () => h('button', { 'data-testid': 'card', onVnodeMounted: mountedGallery }, 'Add card'),
          endAside: () =>
            h('aside', {}, [
              h(
                'button',
                {
                  'data-testid': 'details',
                  onClick: () => {
                    open.value = true;
                  },
                },
                'Details',
              ),
              h(
                'button',
                {
                  'data-testid': 'cards',
                  onClick: () => {
                    open.value = false;
                  },
                },
                'Cards',
              ),
            ]),
          ...(open.value
            ? {
                overlay: () =>
                  h('section', {}, [
                    h(
                      'button',
                      {
                        'data-testid': 'close',
                        onClick: () => {
                          open.value = false;
                        },
                      },
                      'Close details',
                    ),
                    h('input', { 'aria-label': 'Name' }),
                  ]),
              }
            : {}),
        },
      ),
  });
  app.mount(container);
  cleanups.push(() => {
    app.unmount();
    container.remove();
  });
  await nextTick();
  const button = (id: string) =>
    container.querySelector<HTMLButtonElement>(`[data-testid="${id}"]`)!;
  return { container, button, mountedGallery };
};

describe('BuilderWorkspaceLayout', () => {
  test('isolates the covered gallery, focuses Details, and restores focus on close', async () => {
    const { container, button, mountedGallery } = await mountWorkspace();
    const card = button('card');
    button('details').focus();
    button('details').click();
    await nextTick();

    expect(card.closest('[inert]')).not.toBeNull();
    expect(button('cards').closest('[inert]')).toBeNull();
    expect(document.activeElement).toBe(button('close'));
    button('close').click();
    await nextTick();

    expect(container.querySelector('[inert]')).toBeNull();
    expect(document.activeElement).toBe(button('details'));
    expect(button('card')).toBe(card);
    expect(mountedGallery).toHaveBeenCalledOnce();
  });

  test('preserves focus on a collection tab when that tab closes Details', async () => {
    const { button } = await mountWorkspace(true);
    expect(document.activeElement).toBe(button('close'));
    button('cards').focus();
    button('cards').click();
    await nextTick();
    expect(document.activeElement).toBe(button('cards'));
    expect(button('card').closest('[inert]')).toBeNull();
  });
});
