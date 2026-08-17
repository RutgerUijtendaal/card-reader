import { createApp, defineComponent, h, nextTick, ref } from 'vue';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import CardMarkupEditor from '@/domain/cards/components/CardMarkupEditor.vue';
import { fetchCards } from '@/domain/cards/api';
import type { CardListItem } from '@/domain/cards/types';

vi.mock('@/domain/cards/api', () => ({
  fetchCards: vi.fn(),
}));

const fetchCardsMock = vi.mocked(fetchCards);

const card: CardListItem = {
  id: 'card-1',
  key: 'card-1',
  result_type: 'card',
  image_url: null,
  label: 'Card One',
  card_pool: 'player',
  card_roles: [],
  template_id: 'template-1',
  version_id: 'version-1',
  version_number: 1,
  previous_version_id: null,
  is_latest: true,
  name: 'Card One',
  mana_cost: '',
  mana_symbols: [],
  mana_value: 0,
  attack: null,
  health: null,
  type_line: 'Spell',
  rules_text: '',
  confidence: 1,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
  keywords: [],
  tags: [],
  symbols: [],
  types: [],
};

const symbols = [
  {
    id: 'symbol-fire',
    key: 'fire',
    label: 'Fire',
    symbol_type: 'mana',
    text_token: '{F}',
    asset_url: null,
  },
  {
    id: 'symbol-frost',
    key: 'frost',
    label: 'Frost',
    symbol_type: 'mana',
    text_token: '{I}',
    asset_url: null,
  },
];

const mountEditor = async (initialValue: string, allowSymbols = false) => {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const value = ref(initialValue);
  const app = createApp(
    defineComponent({
      setup: () => () =>
        h(CardMarkupEditor, {
          modelValue: value.value,
          label: 'Rules text',
          symbols,
          allowSymbols,
          'onUpdate:modelValue': (next: string) => {
            value.value = next;
          },
        }),
    }),
  );
  app.mount(container);
  await nextTick();
  return { app, container, value };
};

describe('CardMarkupEditor', () => {
  beforeEach(() => {
    fetchCardsMock.mockResolvedValue({
      count: 0,
      next_page: null,
      previous_page: null,
      page: 1,
      page_size: 8,
      results: [],
    });
  });
  afterEach(() => {
    document.body.innerHTML = '';
    vi.clearAllMocks();
    vi.useRealTimers();
  });

  test('switches between Write and a rendered unsaved Preview', async () => {
    const mounted = await mountEditor('Use **bold** text.');
    const previewButton = [...mounted.container.querySelectorAll('button')].find(
      (button) => button.textContent?.trim() === 'Preview',
    );

    previewButton?.click();
    await nextTick();

    expect(mounted.container.querySelector('textarea')).toBeNull();
    expect(mounted.container.querySelector('strong')?.textContent).toBe('bold');
    mounted.app.unmount();
  });

  test('labels the authoring textarea for assistive technology', async () => {
    const mounted = await mountEditor('');

    expect(mounted.container.querySelector('textarea')?.getAttribute('aria-label'))
      .toBe('Rules text');
    mounted.app.unmount();
  });

  test('inserts the selected symbol with Tab and restores the authored value', async () => {
    const mounted = await mountEditor('[[symbol:fi', true);
    const textarea = mounted.container.querySelector('textarea');
    if (!(textarea instanceof HTMLTextAreaElement)) throw new Error('Expected textarea.');
    textarea.focus();
    textarea.setSelectionRange(textarea.value.length, textarea.value.length);
    textarea.dispatchEvent(new KeyboardEvent('keyup', { key: 'i', bubbles: true }));
    await nextTick();

    textarea.dispatchEvent(new KeyboardEvent('keydown', { key: 'Tab', bubbles: true }));
    await nextTick();

    expect(mounted.value.value).toBe('[[symbol:fire]]');
    mounted.app.unmount();
  });

  test('keeps arrow-key selection through keyup before inserting', async () => {
    const mounted = await mountEditor('[[symbol:f', true);
    const textarea = mounted.container.querySelector('textarea');
    if (!(textarea instanceof HTMLTextAreaElement)) throw new Error('Expected textarea.');
    textarea.focus();
    textarea.setSelectionRange(textarea.value.length, textarea.value.length);
    textarea.dispatchEvent(new KeyboardEvent('keyup', { key: 'f', bubbles: true }));
    await nextTick();

    textarea.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowDown', bubbles: true }));
    textarea.dispatchEvent(new KeyboardEvent('keyup', { key: 'ArrowDown', bubbles: true }));
    textarea.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
    textarea.dispatchEvent(new KeyboardEvent('keyup', { key: 'Enter', bubbles: true }));
    await nextTick();

    expect(mounted.value.value).toBe('[[symbol:frost]]');
    mounted.app.unmount();
  });

  test('does not select a stale hidden card after narrowing to symbols', async () => {
    vi.useFakeTimers();
    fetchCardsMock.mockResolvedValue({
      count: 1,
      next_page: null,
      previous_page: null,
      page: 1,
      page_size: 8,
      results: [card],
    });
    const mounted = await mountEditor('[[card:one', true);
    const textarea = mounted.container.querySelector('textarea');
    if (!(textarea instanceof HTMLTextAreaElement)) throw new Error('Expected textarea.');
    textarea.focus();
    textarea.setSelectionRange(textarea.value.length, textarea.value.length);
    textarea.dispatchEvent(new KeyboardEvent('keyup', { key: 'e', bubbles: true }));
    await vi.advanceTimersByTimeAsync(200);
    await nextTick();

    textarea.value = '[[symbol:fi';
    textarea.setSelectionRange(textarea.value.length, textarea.value.length);
    textarea.dispatchEvent(new Event('input', { bubbles: true }));
    textarea.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
    await nextTick();

    expect(mounted.value.value).toBe('[[symbol:fire]]');
    mounted.app.unmount();
  });
});
