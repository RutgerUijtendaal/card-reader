/* eslint-disable vue/one-component-per-file */
import { createApp, h, nextTick, ref } from 'vue';
import { afterEach, describe, expect, test, vi } from 'vitest';
import DeckTagPicker from '@/components/decks/DeckTagPicker.vue';
import DeckTagPills from '@/components/decks/DeckTagPills.vue';
import type { DeckTagCatalog, PendingDeckTagSuggestion } from '@/modules/decks/types';

vi.mock('@/composables/useFloatingPopover', async () => {
  const { computed, ref: vueRef } = await import('vue');
  return {
    useFloatingPopover: () => {
      const isOpen = vueRef(false);
      return {
        isOpen,
        triggerRef: vueRef<HTMLElement | null>(null),
        panelRef: vueRef<HTMLElement | null>(null),
        x: computed(() => 0),
        y: computed(() => 0),
        availableHeight: computed(() => 240),
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

const catalog: DeckTagCatalog = {
  roles: [
    { id: 'role-damage', kind: 'role', key: 'damage', label: 'Damage' },
    { id: 'role-control', kind: 'role', key: 'control', label: 'Control' },
  ],
  types: [{ id: 'type-armor', kind: 'type', key: 'armor', label: 'Armor' }],
};

afterEach(() => {
  document.body.innerHTML = '';
});

describe('DeckTagPicker', () => {
  test('uses role quick-picks, grouped selection, and typed type suggestions', async () => {
    const container = document.createElement('div');
    document.body.appendChild(container);
    const selectedIds = ref<string[]>([]);
    const suggestions = ref<string[]>([]);
    const app = createApp({
      render: () =>
        h(DeckTagPicker, {
          catalog,
          modelValue: selectedIds.value,
          suggestedTypeLabels: suggestions.value,
          'onUpdate:modelValue': (value: string[]) => {
            selectedIds.value = value;
          },
          'onUpdate:suggestedTypeLabels': (value: string[]) => {
            suggestions.value = value;
          },
        }),
    });
    app.mount(container);
    await nextTick();

    const damageQuickPick = [...container.querySelectorAll('button')].find(
      (button) => button.textContent?.trim() === 'Damage',
    );
    damageQuickPick?.click();
    await nextTick();
    expect(selectedIds.value).toEqual(['role-damage']);
    expect(container.textContent).not.toContain('Control');

    container.querySelector<HTMLButtonElement>('button[aria-label="Add deck tags"]')?.click();
    await nextTick();
    const popover = document.body.querySelector<HTMLElement>('[data-testid="deck-tag-picker-popover"]');
    const options = document.body.querySelector<HTMLElement>('[data-testid="deck-tag-picker-options"]');
    expect(popover?.style.maxHeight).toBe('240px');
    expect(popover?.classList.contains('overflow-hidden')).toBe(true);
    expect(options?.classList.contains('overflow-y-auto')).toBe(true);
    expect(options?.classList.contains('app-scrollbar')).toBe(true);
    expect(document.body.textContent).toContain('Roles');
    expect(document.body.textContent).toContain('Types');
    const armorOption = [...document.body.querySelectorAll('button')].find(
      (button) => button.textContent?.trim() === 'Armor',
    );
    armorOption?.click();
    await nextTick();
    expect(selectedIds.value).toEqual(['role-damage', 'type-armor']);

    const input = document.body.querySelector<HTMLInputElement>(
      'input[placeholder="Search or suggest a type..."]',
    );
    expect(input).not.toBeNull();
    if (input) {
      input.value = '  Tempo   Burst  ';
      input.dispatchEvent(new Event('input', { bubbles: true }));
    }
    await nextTick();
    const suggestionAction = [...document.body.querySelectorAll('button')].find((button) =>
      button.textContent?.includes('Suggest type'),
    );
    suggestionAction?.click();
    await nextTick();
    expect(suggestions.value).toEqual(['Tempo Burst']);

    app.unmount();
  });
});

describe('DeckTagPills', () => {
  test('renders active and pending tags with distinct treatments', async () => {
    const container = document.createElement('div');
    document.body.appendChild(container);
    const pendingSuggestions: PendingDeckTagSuggestion[] = [
      {
        id: 'suggestion-1',
        label: 'Tempo Burst',
        normalized_value: 'tempo burst',
        kind: 'type',
        status: 'pending',
      },
    ];
    const app = createApp({
      render: () =>
        h(DeckTagPills, {
          tags: [catalog.roles[0], catalog.types[0]],
          pendingSuggestions,
        }),
    });
    app.mount(container);
    await nextTick();

    expect(container.textContent).toContain('Damage');
    expect(container.textContent).toContain('Armor');
    expect(container.textContent).toContain('Tempo Burst');
    expect(container.textContent).toContain('Pending');
    expect(container.querySelector('.border-dashed')).not.toBeNull();

    app.unmount();
  });
});
