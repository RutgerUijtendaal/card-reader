import { createApp, defineComponent, h, nextTick, ref } from 'vue';
import { afterEach, describe, expect, test } from 'vitest';
import CardMarkupEditor from '@/domain/cards/components/CardMarkupEditor.vue';

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
  afterEach(() => {
    document.body.innerHTML = '';
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
});
