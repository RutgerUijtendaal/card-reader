import { createApp, defineComponent, h, nextTick } from 'vue';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { api } from '@/api/client';
import CardSearchSelect from '@/components/cards/CardSearchSelect.vue';
import type { CardListItem } from '@/modules/card-detail/types';

vi.mock('@/api/client', () => ({
  api: {
    get: vi.fn(),
  },
  toAbsoluteApiUrl: (url: string) => url,
}));

const mockedGet = vi.mocked(api.get);

const buildCard = (overrides: Partial<CardListItem> = {}): CardListItem => ({
  id: 'card-1',
  key: 'card-1',
  result_type: 'card',
  image_url: '/card.png',
  label: 'Card 1',
  is_hero: false,
  template_id: 'template-1',
  version_id: 'version-1',
  version_number: 1,
  previous_version_id: null,
  is_latest: true,
  name: 'Card 1',
  mana_cost: '1',
  mana_symbols: [],
  mana_value: 1,
  attack: null,
  health: null,
  type_line: 'Item',
  rules_text: '',
  confidence: 1,
  created_at: '2025-01-01T00:00:00Z',
  updated_at: '2025-01-01T00:00:00Z',
  keywords: [],
  tags: [],
  symbols: [],
  types: [],
  ...overrides,
});

const mountSearch = async (props: Record<string, unknown> = {}) => {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const select = vi.fn();
  const app = createApp(
    defineComponent({
      setup() {
        return () =>
          h(CardSearchSelect, {
            label: 'Search card',
            placeholder: 'Search cards',
            onSelect: select,
            ...props,
          });
      },
    }),
  );
  app.mount(container);
  await nextTick();

  return {
    container,
    select,
    input: () => {
      const input = container.querySelector('input');
      if (!(input instanceof HTMLInputElement)) {
        throw new Error('expected search input');
      }
      return input;
    },
    unmount: () => {
      app.unmount();
      container.remove();
    },
  };
};

const typeSearch = async (input: HTMLInputElement, value: string): Promise<void> => {
  input.focus();
  input.value = value;
  input.dispatchEvent(new Event('input'));
  await nextTick();
  await vi.advanceTimersByTimeAsync(250);
  await nextTick();
};

describe('CardSearchSelect', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    mockedGet.mockResolvedValue({
      data: {
        results: [buildCard()],
      },
    });
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
    document.body.innerHTML = '';
  });

  test('closes results after selecting in single mode', async () => {
    const mounted = await mountSearch({ selectionMode: 'single' });

    await typeSearch(mounted.input(), 'Card');
    const row = document.body.querySelector('button[aria-label="Select Card 1"]');
    if (!(row instanceof HTMLButtonElement)) {
      throw new Error('expected search result row');
    }

    row.click();
    await nextTick();

    expect(mounted.select).toHaveBeenCalledWith(expect.objectContaining({ id: 'card-1' }));
    expect(document.body.querySelector('button[aria-label="Select Card 1"]')).toBeNull();

    mounted.unmount();
  });

  test('keeps results open after selecting in multi mode', async () => {
    const mounted = await mountSearch({ selectionMode: 'multi' });

    await typeSearch(mounted.input(), 'Card');
    const row = document.body.querySelector('button[aria-label="Select Card 1"]');
    if (!(row instanceof HTMLButtonElement)) {
      throw new Error('expected search result row');
    }

    row.click();
    await nextTick();

    expect(mounted.select).toHaveBeenCalledWith(expect.objectContaining({ id: 'card-1' }));
    expect(document.body.querySelector('button[aria-label="Select Card 1"]')).not.toBeNull();

    mounted.unmount();
  });
});
