/* eslint-disable vue/one-component-per-file */
import { createApp, defineComponent, h, nextTick } from 'vue';
import { createMemoryHistory, createRouter } from 'vue-router';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { useDeckEditor } from '@/modules/decks/composables/useDeckEditor';

const { fetchMyDeckMock, updateDeckMock, toastErrorMock } = vi.hoisted(() => ({
  fetchMyDeckMock: vi.fn(),
  updateDeckMock: vi.fn(),
  toastErrorMock: vi.fn(),
}));

vi.mock('@/modules/decks/api', () => ({
  createDeck: vi.fn(),
  fetchMyDeck: fetchMyDeckMock,
  updateDeck: updateDeckMock,
}));

vi.mock('@/composables/decks/deckRules', () => ({
  fallbackDeckBuildingRules: () => ({
    mainboard_card_count: { min: 0, max: 60 },
    mana_type_count: { min: 0 },
  }),
  fetchDeckRulesMetadata: vi.fn(async () => ({
    default_rules: {
      mainboard_card_count: { min: 0, max: 60 },
      mana_type_count: { min: 0 },
    },
  })),
}));

vi.mock('@/modules/decks/composables/useDeckEditorFilters', () => ({
  useDeckEditorFilters: () => ({
    filtersLoaded: { value: true },
    buildSearchParams: vi.fn(() => new URLSearchParams()),
    selectionState: { value: {} },
    currentDeckOnly: { value: false },
    currentDeckCardIds: { value: [] },
    sort: { value: null },
    effectiveSort: { value: null },
    cardScale: { value: 'normal' },
    loadFilters: vi.fn(async () => undefined),
    applyHeroAffinityManaPreset: vi.fn(),
  }),
}));

vi.mock('@/modules/decks/composables/useDeckEditorGallery', () => ({
  useDeckEditorGallery: () => ({
    searchCards: vi.fn(async () => undefined),
  }),
}));

vi.mock('vue-sonner', () => ({
  toast: {
    error: toastErrorMock,
    success: vi.fn(),
  },
}));

const mountController = async () => {
  let controller!: ReturnType<typeof useDeckEditor>;
  const container = document.createElement('div');
  document.body.appendChild(container);
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      {
        path: '/my/decks/:id/edit',
        component: defineComponent({
          setup() {
            controller = useDeckEditor();
            return () => h('div');
          },
        }),
      },
      { path: '/cards', component: { template: '<div />' } },
    ],
  });
  await router.push('/my/decks/deck-1/edit');
  await router.isReady();

  const app = createApp({ template: '<RouterView />' });
  app.use(router);
  app.mount(container);
  await nextTick();
  await Promise.resolve();
  await nextTick();

  return {
    controller,
    router,
    unmount: () => {
      app.unmount();
      container.remove();
    },
  };
};

describe('useDeckEditor', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    localStorage.setItem('card-reader.deck-editor.autosync', 'true');
    fetchMyDeckMock.mockResolvedValue({
      id: 'deck-1',
      name: 'Loaded Deck',
      description: null,
      visibility: 'private',
      hero_card: {
        id: 'hero-1',
        result_type: 'card',
        key: 'hero-1',
        label: 'Hero',
        is_hero: true,
        template_id: '',
        version_id: 'hero-version',
        version_number: 1,
        previous_version_id: null,
        is_latest: true,
        name: 'Hero',
        type_line: 'Hero',
        mana_cost: '',
        mana_value: 0,
        mana_symbols: [],
        attack: null,
        health: null,
        rules_text: '',
        confidence: 1,
        created_at: '',
        updated_at: '',
        image_url: null,
        keywords: [],
        tags: [],
        symbols: [],
        types: [],
      },
      mainboard: { entries: [] },
      sideboards: [],
      status: { is_valid: true },
    });
    updateDeckMock.mockResolvedValue({
      id: 'deck-1',
      status: { is_valid: true },
    });
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
    localStorage.clear();
    document.body.innerHTML = '';
  });

  test('pauses autosync retries after failure until the draft changes again', async () => {
    updateDeckMock.mockRejectedValueOnce(new Error('offline'));
    const mounted = await mountController();
    mounted.controller.deck.form.name = 'First dirty state';
    await nextTick();

    await vi.advanceTimersByTimeAsync(900);
    await Promise.resolve();
    await nextTick();

    expect(updateDeckMock).toHaveBeenCalledTimes(1);
    expect(toastErrorMock).toHaveBeenCalledWith('Autosync failed. Changes are still unsaved.');
    expect(mounted.controller.changeStatusLabel.value).toBe('Autosync Paused');

    await vi.advanceTimersByTimeAsync(2000);
    await Promise.resolve();
    expect(updateDeckMock).toHaveBeenCalledTimes(1);

    updateDeckMock.mockResolvedValueOnce({
      id: 'deck-1',
      status: { is_valid: true },
    });
    mounted.controller.deck.form.name = 'Second dirty state';
    await nextTick();
    await vi.advanceTimersByTimeAsync(900);
    await Promise.resolve();
    await nextTick();

    expect(updateDeckMock).toHaveBeenCalledTimes(2);
    expect(mounted.controller.changeStatusLabel.value).toBe('Saved');

    mounted.unmount();
  });

  test('keeps beforeunload protection active while saving unsaved changes', async () => {
    let resolveSave!: (value: { id: string; status: { is_valid: boolean } }) => void;
    updateDeckMock.mockReturnValueOnce(
      new Promise((resolve) => {
        resolveSave = resolve;
      }),
    );
    const mounted = await mountController();
    mounted.controller.deck.form.name = 'Unsaved while saving';
    await nextTick();

    const savePromise = mounted.controller.saveDeck();
    await nextTick();

    expect(mounted.controller.hasUnsavedChanges.value).toBe(true);
    expect(mounted.controller.saving.value).toBe(true);

    const event = new Event('beforeunload', { cancelable: true });
    window.dispatchEvent(event);

    expect(event.defaultPrevented).toBe(true);

    resolveSave({
      id: 'deck-1',
      status: { is_valid: true },
    });
    await savePromise;
    mounted.unmount();
  });

  test('keeps route-leave protection active when edits change during a pending save', async () => {
    let resolveSave!: (value: { id: string; status: { is_valid: boolean } }) => void;
    updateDeckMock.mockReturnValueOnce(
      new Promise((resolve) => {
        resolveSave = resolve;
      }),
    );
    const mounted = await mountController();
    mounted.controller.deck.form.name = 'Payload being saved';
    await nextTick();

    const savePromise = mounted.controller.saveDeck();
    await nextTick();

    mounted.controller.deck.form.name = 'Unsaved after save started';
    await nextTick();

    const navigationPromise = mounted.router.push('/cards');
    await nextTick();

    expect(mounted.controller.hasUnsavedChanges.value).toBe(true);
    expect(mounted.controller.saving.value).toBe(true);
    expect(mounted.controller.discardChangesModalOpen.value).toBe(true);
    expect(mounted.router.currentRoute.value.fullPath).toBe('/my/decks/deck-1/edit');

    mounted.controller.cancelDiscardChanges();
    await navigationPromise;

    expect(mounted.router.currentRoute.value.fullPath).toBe('/my/decks/deck-1/edit');

    resolveSave({
      id: 'deck-1',
      status: { is_valid: true },
    });
    await savePromise;
    mounted.unmount();
  });
});
