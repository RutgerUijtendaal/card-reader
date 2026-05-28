import { createApp, defineComponent, h, nextTick, ref } from 'vue';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import MetadataChecklistGroup from '@/components/filters/MetadataChecklistGroup.vue';
import type { MetadataOption } from '@/modules/card-detail/types';

const options: MetadataOption[] = [
  { id: 'keyword-1', key: 'alpha', label: 'Alpha' },
  { id: 'keyword-2', key: 'beta', label: 'Beta' },
  { id: 'keyword-3', key: 'delta', label: 'Delta' },
];

const mountChecklist = async (initialFavorites: string[] = []) => {
  const container = document.createElement('div');
  document.body.appendChild(container);

  const modelValue = ref<string[]>([]);
  const favoriteKeys = ref<string[]>([...initialFavorites]);
  const toggleFavorite = vi.fn((key: string) => {
    favoriteKeys.value = favoriteKeys.value.includes(key)
      ? favoriteKeys.value.filter((entry) => entry !== key)
      : [...favoriteKeys.value, key];
  });

  const Root = defineComponent({
    setup() {
      return () =>
        h(MetadataChecklistGroup, {
          label: 'Keywords',
          options,
          modelValue: modelValue.value,
          'onUpdate:modelValue': (value: string[]) => {
            modelValue.value = value;
          },
          matchMode: 'any',
          defaultOpen: true,
          favoriteGroup: 'keywords',
          favoriteKeys: favoriteKeys.value,
          onToggleFavorite: toggleFavorite,
        });
    },
  });

  const app = createApp(Root);
  app.mount(container);
  await nextTick();

  return {
    container,
    modelValue,
    favoriteKeys,
    toggleFavorite,
    unmount: () => {
      app.unmount();
      container.remove();
    },
  };
};

const readRenderedOrder = (container: HTMLElement): string[] =>
  Array.from(container.querySelectorAll('[data-option-key]')).map((element) => element.getAttribute('data-option-key') ?? '');

describe('MetadataChecklistGroup', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    document.body.innerHTML = '';
    vi.clearAllMocks();
  });

  test('renders favourites before non-favourites while preserving relative order within each bucket', async () => {
    const mounted = await mountChecklist(['delta', 'alpha']);

    expect(readRenderedOrder(mounted.container)).toEqual(['alpha', 'delta', 'beta']);

    mounted.unmount();
  });

  test('clicking the star toggles favourite state without selecting the checkbox row', async () => {
    const mounted = await mountChecklist();

    const favoriteButtons = mounted.container.querySelectorAll<HTMLButtonElement>('.theme-filter-favorite-button');
    favoriteButtons[1]?.click();
    await nextTick();

    expect(mounted.toggleFavorite).toHaveBeenCalledWith('beta');
    expect(mounted.favoriteKeys.value).toEqual(['beta']);
    expect(mounted.modelValue.value).toEqual([]);

    mounted.unmount();
  });

  test('mouse-activated favourite buttons release focus on fine pointer screens', async () => {
    vi.stubGlobal('matchMedia', vi.fn(() => ({ matches: true })));
    const mounted = await mountChecklist();

    const favoriteButtons = mounted.container.querySelectorAll<HTMLButtonElement>('.theme-filter-favorite-button');
    const button = favoriteButtons[1];
    if (!(button instanceof HTMLButtonElement)) {
      throw new Error('expected favorite button');
    }

    button.focus();
    expect(document.activeElement).toBe(button);

    button.click();
    await nextTick();

    expect(mounted.toggleFavorite).toHaveBeenCalledWith('beta');
    expect(document.activeElement).not.toBe(button);

    mounted.unmount();
  });

  test('favourite buttons stay layout-stable and hidden until hover or active state', async () => {
    const mounted = await mountChecklist(['alpha']);

    const favoriteButtons = mounted.container.querySelectorAll<HTMLButtonElement>('.theme-filter-favorite-button');
    expect(favoriteButtons[0]?.className).toContain('theme-filter-favorite-button-active');
    expect(favoriteButtons[1]?.className).toContain('theme-filter-favorite-button');

    mounted.unmount();
  });

  test('keyboard focus reveals favourite actions within the row', async () => {
    const mounted = await mountChecklist();

    const favoriteButtons = mounted.container.querySelectorAll<HTMLButtonElement>('.theme-filter-favorite-button');
    const button = favoriteButtons[1];
    if (!(button instanceof HTMLButtonElement)) {
      throw new Error('expected favorite button');
    }

    button.focus();
    await nextTick();

    expect(document.activeElement).toBe(button);
    expect(button.closest('.theme-checkbox-row')?.matches(':focus-within')).toBe(true);

    mounted.unmount();
  });

  test('search results keep favourites at the top of the filtered subset', async () => {
    const mounted = await mountChecklist(['delta']);

    const searchInput = mounted.container.querySelector('input');
    if (!(searchInput instanceof HTMLInputElement)) {
      throw new Error('expected search input');
    }

    searchInput.value = 'a';
    searchInput.dispatchEvent(new Event('input'));
    await nextTick();

    expect(readRenderedOrder(mounted.container)).toEqual(['delta', 'alpha', 'beta']);

    mounted.unmount();
  });
});
