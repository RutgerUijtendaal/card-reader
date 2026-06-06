import { createApp, defineComponent, h, nextTick } from 'vue';
import { afterEach, describe, expect, test } from 'vitest';
import { usePrimarySearchHotkeys } from '@/composables/useHotkeys';
import GalleryFilterSidebar from '@/components/filters/GalleryFilterSidebar.vue';

const mountSidebar = async () => {
  const container = document.createElement('div');
  document.body.appendChild(container);

  const Harness = defineComponent({
    setup() {
      usePrimarySearchHotkeys();

      return () =>
        h(
          GalleryFilterSidebar,
          {
            title: 'Gallery',
            query: '',
            onUpdateQuery: () => undefined,
            searchPlaceholder: 'Search cards...',
            totalCount: 12,
            onReset: () => undefined,
          },
          {
            default: () => h('div', 'Filters'),
          },
        );
    },
  });

  const app = createApp(Harness);
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

describe('GalleryFilterSidebar', () => {
  afterEach(() => {
    document.body.innerHTML = '';
  });

  test('renders search shortcut hints', async () => {
    const mounted = await mountSidebar();
    const text = mounted.container.textContent ?? '';

    expect(text).toContain('/');
    expect(text).not.toMatch(/Ctrl\+K|Cmd\+K/);

    mounted.unmount();
  });

  test('focuses the search input from the slash hotkey', async () => {
    const mounted = await mountSidebar();
    const input = mounted.container.querySelector('input');
    if (!(input instanceof HTMLInputElement)) {
      throw new Error('expected search input');
    }

    const event = new KeyboardEvent('keydown', {
      key: '/',
      bubbles: true,
      cancelable: true,
    });
    window.dispatchEvent(event);

    expect(document.activeElement).toBe(input);
    expect(event.defaultPrevented).toBe(true);

    mounted.unmount();
  });
});
