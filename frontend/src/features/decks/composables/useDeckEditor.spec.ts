/* eslint-disable vue/one-component-per-file */
import { createApp, defineComponent, h, nextTick } from 'vue';
import { createMemoryHistory, createRouter } from 'vue-router';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { useDeckEditor } from '@/features/decks/composables/useDeckEditor';

const {
  createDeckMock,
  fetchMyDeckMock,
  updateDeckMock,
  toastErrorMock,
  toastInfoMock,
  resetFiltersMock,
  applyHeroAffinityManaPresetMock,
  searchCardsMock,
} = vi.hoisted(() => ({
  createDeckMock: vi.fn(),
  fetchMyDeckMock: vi.fn(),
  updateDeckMock: vi.fn(),
  toastErrorMock: vi.fn(),
  toastInfoMock: vi.fn(),
  resetFiltersMock: vi.fn(),
  applyHeroAffinityManaPresetMock: vi.fn(),
  searchCardsMock: vi.fn(async () => undefined),
}));

vi.mock('@/domain/decks/api', () => ({
  createDeck: createDeckMock,
  fetchMyDeck: fetchMyDeckMock,
  updateDeck: updateDeckMock,
}));

vi.mock('@/domain/decks/utils/deckRules', () => ({
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

vi.mock('@/features/decks/composables/useDeckEditorFilters', () => ({
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
    resetFilters: resetFiltersMock,
    applyHeroAffinityManaPreset: applyHeroAffinityManaPresetMock,
  }),
}));

vi.mock('@/features/decks/composables/useDeckEditorGallery', () => ({
  useDeckEditorGallery: () => ({
    searchCards: searchCardsMock,
  }),
}));

vi.mock('vue-sonner', () => ({
  toast: {
    error: toastErrorMock,
    info: toastInfoMock,
    success: vi.fn(),
  },
}));

const buildHero = (id: string, name: string) => ({
  id,
  result_type: 'card' as const,
  key: id,
  label: name,
  is_hero: true,
  template_id: '',
  version_id: `${id}-version`,
  version_number: 1,
  previous_version_id: null,
  is_latest: true,
  name,
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
});

const mountController = async (path = '/my/decks/deck-1/edit') => {
  let controller!: ReturnType<typeof useDeckEditor>;
  const container = document.createElement('div');
  document.body.appendChild(container);
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      {
        path: '/my/decks/new',
        component: defineComponent({
          setup() {
            controller = useDeckEditor();
            return () => h('div');
          },
        }),
      },
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
  await router.push(path);
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
    createDeckMock.mockResolvedValue({
      id: 'deck-new',
      status: { is_valid: true },
    });
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
    localStorage.clear();
    document.body.innerHTML = '';
  });

  test('opens existing decks in Details without querying the hidden gallery', async () => {
    const mounted = await mountController();

    expect(mounted.controller.editorMode.value).toBe('details');
    expect(mounted.controller.canAutosync.value).toBe(false);
    expect(searchCardsMock).not.toHaveBeenCalled();

    mounted.unmount();
  });

  test('opens and keeps Edit-button Cards mode in the linkable URL', async () => {
    const mounted = await mountController(
      '/my/decks/deck-1/edit?editor_mode=cards&return_to=my_decks',
    );
    await Promise.resolve();
    await nextTick();

    expect(mounted.controller.editorMode.value).toBe('cards');
    expect(mounted.controller.canAutosync.value).toBe(true);
    expect(mounted.router.currentRoute.value.query).toEqual({
      editor_mode: 'cards',
      return_to: 'my_decks',
    });

    await mounted.router.replace(
      '/my/decks/deck-1/edit?editor_mode=details&return_to=my_decks',
    );
    await nextTick();
    expect(mounted.controller.editorMode.value).toBe('details');

    mounted.unmount();
  });

  test('creates a named hero draft before opening Details for a new deck', async () => {
    const mounted = await mountController('/my/decks/new');

    expect(mounted.controller.editorMode.value).toBe('hero');
    expect(searchCardsMock).toHaveBeenCalledTimes(1);

    mounted.controller.deck.handleGalleryAction(buildHero('hero-new', 'New Hero'));
    mounted.controller.deck.setDeckName('New Deck');
    await mounted.controller.completeInitialHeroSelection();

    expect(createDeckMock).toHaveBeenCalledWith(expect.objectContaining({
      name: 'New Deck',
      hero_card_id: 'hero-new',
    }));
    expect(mounted.router.currentRoute.value.fullPath).toBe(
      '/my/decks/deck-new/edit?editor_mode=details',
    );
    expect(mounted.controller.editorMode.value).toBe('details');

    mounted.unmount();
  });

  test('switches Details and Cards without saving or losing draft metadata', async () => {
    const mounted = await mountController();
    mounted.controller.deck.setDeckLongDescription('Keep this strategy note.');

    mounted.controller.openCards();
    expect(mounted.controller.editorMode.value).toBe('cards');
    expect(mounted.controller.canAutosync.value).toBe(true);
    expect(applyHeroAffinityManaPresetMock).toHaveBeenCalledTimes(1);
    await vi.waitFor(() => {
      expect(mounted.router.currentRoute.value.query.editor_mode).toBe('cards');
    });

    mounted.controller.openDetails();
    expect(mounted.controller.editorMode.value).toBe('details');
    expect(mounted.controller.deck.form.long_description).toBe('Keep this strategy note.');
    expect(updateDeckMock).not.toHaveBeenCalled();
    await vi.waitFor(() => {
      expect(mounted.router.currentRoute.value.query.editor_mode).toBe('details');
    });

    mounted.unmount();
  });

  test('applies a replacement hero without saving and refreshes its card preset on Cards', async () => {
    const mounted = await mountController();
    mounted.controller.deck.setDeckDescription('Preserved summary');

    mounted.controller.beginHeroChange();
    expect(mounted.controller.editorMode.value).toBe('hero');
    expect(mounted.controller.isChangingHero.value).toBe(true);
    expect(resetFiltersMock).toHaveBeenCalledTimes(1);

    mounted.controller.deck.handleGalleryAction(buildHero('hero-2', 'Replacement Hero'));
    expect(mounted.controller.canApplyHeroChange.value).toBe(true);
    mounted.controller.applyHeroChange();

    expect(mounted.controller.editorMode.value).toBe('details');
    expect(mounted.controller.deck.form.hero_card_id).toBe('hero-2');
    expect(mounted.controller.deck.form.description).toBe('Preserved summary');
    expect(updateDeckMock).not.toHaveBeenCalled();

    mounted.controller.openCards();
    expect(applyHeroAffinityManaPresetMock).toHaveBeenLastCalledWith(
      expect.objectContaining({ id: 'hero-2' }),
    );

    mounted.unmount();
  });

  test('cancels hero replacement while preserving all other draft edits', async () => {
    const mounted = await mountController();
    mounted.controller.deck.setDeckLongDescription('Preserved notes');

    mounted.controller.beginHeroChange();
    mounted.controller.deck.handleGalleryAction(buildHero('hero-2', 'Replacement Hero'));
    mounted.controller.cancelHeroChange();

    expect(mounted.controller.editorMode.value).toBe('details');
    expect(mounted.controller.deck.form.hero_card_id).toBe('hero-1');
    expect(mounted.controller.deck.form.long_description).toBe('Preserved notes');
    expect(updateDeckMock).not.toHaveBeenCalled();

    mounted.unmount();
  });

  test('keeps autosync paused in Details and resumes it in Cards', async () => {
    const mounted = await mountController();
    mounted.controller.deck.setDeckName('Dirty details');
    await nextTick();
    await vi.advanceTimersByTimeAsync(1000);

    expect(updateDeckMock).not.toHaveBeenCalled();

    mounted.controller.openCards();
    await nextTick();
    await vi.advanceTimersByTimeAsync(900);

    expect(updateDeckMock).toHaveBeenCalledTimes(1);
    mounted.unmount();
  });

  test('pauses autosync retries after failure until the draft changes again', async () => {
    updateDeckMock.mockRejectedValueOnce(new Error('offline'));
    const mounted = await mountController();
    mounted.controller.openCards();
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

  test('reconciles rejected tag suggestions after a successful save', async () => {
    const mounted = await mountController();
    mounted.controller.deck.setSuggestedTypeLabels(['Rejected Deck Type']);
    updateDeckMock.mockResolvedValueOnce({
      id: 'deck-1',
      tags: [],
      pending_tag_suggestions: [],
      tag_suggestion_results: [
        {
          label: 'Rejected Deck Type',
          normalized_value: 'rejected deck type',
          status: 'rejected',
          message: 'This tag was previously declined. Try a more specific suggestion.',
          suggestion_id: 'suggestion-1',
          tag: null,
        },
      ],
      status: { is_valid: true },
    });

    await mounted.controller.saveDeck();

    expect(mounted.controller.deck.form.suggested_type_labels).toEqual([]);
    expect(toastInfoMock).toHaveBeenCalledWith(
      'This tag was previously declined. Try a more specific suggestion.',
    );
    expect(mounted.controller.hasUnsavedChanges.value).toBe(false);

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
