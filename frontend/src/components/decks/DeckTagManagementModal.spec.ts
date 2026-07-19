/* eslint-disable vue/one-component-per-file */
import { createApp, h, nextTick } from 'vue';
import { afterEach, describe, expect, test, vi } from 'vitest';
import DeckTagManagementModal from '@/components/decks/DeckTagManagementModal.vue';

const catalog = {
  roles: [{ id: 'role-damage', kind: 'role' as const, key: 'damage', label: 'Damage' }],
  types: [{ id: 'type-armor', kind: 'type' as const, key: 'armor', label: 'Armor' }],
};

afterEach(() => {
  document.body.innerHTML = '';
});

describe('DeckTagManagementModal', () => {
  test('edits tags and submits the modal', async () => {
    const updateTags = vi.fn();
    const save = vi.fn();
    const app = createApp({
      render: () => h(DeckTagManagementModal, {
        open: true,
        deckName: 'Azure Tempo',
        catalog,
        modelValue: [],
        suggestedTypeLabels: [],
        loading: false,
        saving: false,
        'onUpdate:modelValue': updateTags,
        onSave: save,
      }),
    });
    const container = document.createElement('div');
    document.body.appendChild(container);
    app.mount(container);
    await nextTick();

    const damageButton = Array.from(document.body.querySelectorAll('button')).find(
      (button) => button.textContent?.trim() === 'Damage',
    );
    damageButton?.click();
    document.body.querySelector<HTMLButtonElement>('button.btn-primary')?.click();

    expect(updateTags).toHaveBeenCalledWith(['role-damage']);
    expect(save).toHaveBeenCalledTimes(1);

    app.unmount();
  });

  test('shows retry state and prevents saving after a load failure', async () => {
    const retry = vi.fn();
    const save = vi.fn();
    const app = createApp({
      render: () => h(DeckTagManagementModal, {
        open: true,
        deckName: 'Azure Tempo',
        catalog,
        modelValue: [],
        suggestedTypeLabels: [],
        loading: false,
        saving: false,
        errorMessage: 'Unable to load deck tags.',
        onRetry: retry,
        onSave: save,
      }),
    });
    const container = document.createElement('div');
    document.body.appendChild(container);
    app.mount(container);
    await nextTick();

    const retryButton = Array.from(document.body.querySelectorAll('button')).find(
      (button) => button.textContent?.trim() === 'Retry',
    );
    retryButton?.click();
    const saveButton = Array.from(document.body.querySelectorAll<HTMLButtonElement>('button')).find(
      (button) => button.textContent?.trim() === 'Save Tags',
    );

    expect(retry).toHaveBeenCalledTimes(1);
    expect(saveButton?.disabled).toBe(true);
    expect(save).not.toHaveBeenCalled();

    app.unmount();
  });

  test('keeps the modal open when interacting with the teleported picker search', async () => {
    const cancel = vi.fn();
    const app = createApp({
      render: () => h(DeckTagManagementModal, {
        open: true,
        deckName: 'Azure Tempo',
        catalog,
        modelValue: [],
        suggestedTypeLabels: [],
        loading: false,
        saving: false,
        onCancel: cancel,
      }),
    });
    const container = document.createElement('div');
    document.body.appendChild(container);
    app.mount(container);
    await nextTick();

    document.body.querySelector<HTMLButtonElement>('button[aria-label="Add deck tags"]')?.click();
    await nextTick();
    const searchInput = document.body.querySelector<HTMLInputElement>(
      'input[placeholder="Search or suggest a type..."]',
    );
    searchInput?.click();
    await nextTick();

    expect(searchInput).not.toBeNull();
    expect(document.body.textContent).toContain('Manage Tags');
    expect(cancel).not.toHaveBeenCalled();

    app.unmount();
  });
});
