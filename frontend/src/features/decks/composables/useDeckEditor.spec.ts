/* eslint-disable vue/one-component-per-file */
import { createApp, defineComponent, h, nextTick } from 'vue';
import { createPinia } from 'pinia';
import { createMemoryHistory, createRouter } from 'vue-router';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import type { CardListItem } from '@/domain/cards/types';
import type { DeckCardSummary } from '@/domain/decks/types';
import { useDeckEditor } from '@/features/decks/composables/useDeckEditor';
import { createEmptyDeckForm } from '@/features/decks/composables/deckEditorDraftModel';
import type { DeckForm } from '@/features/decks/composables/deckEditorDraftTypes';
import {
  buildStoredDeckEditorDraft,
  createDeckEditorLocalDraftStorage,
  deckEditorDraftSlotToken,
  type DeckEditorDraftLockManager,
  type StoredCreateAttempt,
  type StoredDeckEditorDraft,
} from '@/features/decks/utils/deckEditorLocalDraftStorage';

const createTestLockManager = (): DeckEditorDraftLockManager => {
  let queue = Promise.resolve();
  return {
    async request<Result>(
      _name: string,
      _options: { mode: 'exclusive' },
      callback: () => Result | PromiseLike<Result>,
    ): Promise<Result> {
      const previous = queue;
      let release!: () => void;
      queue = new Promise<void>((resolve) => {
        release = resolve;
      });
      await previous;
      try {
        return await callback();
      } finally {
        release();
      }
    },
  };
};

const {
  createDeckMock,
  fetchDeckRulesMetadataMock,
  fetchMyDeckMock,
  updateDeckMock,
  toastErrorMock,
  toastInfoMock,
  resetFiltersMock,
  applyHeroAffinityManaPresetMock,
  loadFiltersMock,
  searchCardsMock,
  fetchCardMock,
  fetchCardsMock,
  fetchDeckTagsMock,
  fetchMyDeckByCreationKeyMock,
} = vi.hoisted(() => ({
  createDeckMock: vi.fn(),
  fetchDeckRulesMetadataMock: vi.fn(async () => ({
    default_rules: {
      mainboard_card_count: { min: 0, max: 60 },
      mana_type_count: { min: 0 },
    },
  })),
  fetchMyDeckMock: vi.fn(),
  updateDeckMock: vi.fn(),
  toastErrorMock: vi.fn(),
  toastInfoMock: vi.fn(),
  resetFiltersMock: vi.fn(),
  applyHeroAffinityManaPresetMock: vi.fn(),
  loadFiltersMock: vi.fn(async (): Promise<void> => undefined),
  searchCardsMock: vi.fn(async () => undefined),
  fetchCardMock: vi.fn(),
  fetchCardsMock: vi.fn(async () => ({
    count: 0,
    next_page: null,
    previous_page: null,
    page: 1,
    page_size: 100,
    results: [] as CardListItem[],
  })),
  fetchDeckTagsMock: vi.fn(),
  fetchMyDeckByCreationKeyMock: vi.fn(),
}));

vi.mock('@/domain/cards/api', () => ({
  fetchCard: fetchCardMock,
  fetchCards: fetchCardsMock,
}));

vi.mock('@/domain/decks/api', () => ({
  createDeck: createDeckMock,
  fetchDeckRulesMetadata: fetchDeckRulesMetadataMock,
  fetchDeckTags: fetchDeckTagsMock,
  fetchMyDeck: fetchMyDeckMock,
  fetchMyDeckByCreationKey: fetchMyDeckByCreationKeyMock,
  updateDeck: updateDeckMock,
}));

vi.mock('@/domain/decks/utils/deckRules', () => ({
  fallbackDeckBuildingRules: () => ({
    mainboard_card_count: { min: 0, max: 60 },
    mana_type_count: { min: 0 },
  }),
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
    loadFilters: loadFiltersMock,
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

const saveLocalDraft = async (
  ownerId: string,
  form: DeckForm,
  cards: Record<string, DeckCardSummary>,
  pendingCreateAttempt: StoredCreateAttempt | null = null,
): Promise<StoredDeckEditorDraft> => {
  const storage = createDeckEditorLocalDraftStorage();
  const current = storage.read(ownerId);
  const expected = current.status === 'loaded'
    ? deckEditorDraftSlotToken(current.slot)
    : { kind: 'empty' as const };
  const draft = buildStoredDeckEditorDraft(
    ownerId,
    `draft-${ownerId}`,
    form,
    cards,
    pendingCreateAttempt,
  );
  const result = await storage.save(draft, expected);
  if (result.status !== 'saved') throw new Error(`Could not save test draft: ${result.status}`);
  return result.draft;
};

const loadLocalDraft = (ownerId: string): StoredDeckEditorDraft | null => {
  const result = createDeckEditorLocalDraftStorage().read(ownerId);
  return result.status === 'loaded' && result.slot.kind === 'draft' ? result.slot.draft : null;
};

const dispatchDraftStorageEvent = (ownerId: string): void => {
  const key = `card-reader.deck-editor.new-draft.${ownerId}`;
  window.dispatchEvent(new StorageEvent('storage', {
    key,
    newValue: localStorage.getItem(key),
  }));
};

const flushAsyncEditorWork = async (): Promise<void> => {
  await nextTick();
  await vi.advanceTimersByTimeAsync(0);
  await Promise.resolve();
};

const buildCard = (id: string, name: string) => ({
  ...buildHero(id, name),
  is_hero: false,
  type_line: 'Unit',
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
      { path: '/my/decks', component: { template: '<div />' } },
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
  const pinia = createPinia();
  pinia.state.value.auth = {
    user: { authenticated: true, id: 'user-1', username: 'deck-builder' },
    initialized: true,
    loading: false,
  };
  app.use(pinia);
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
    Object.defineProperty(navigator, 'locks', {
      configurable: true,
      value: createTestLockManager(),
    });
    fetchCardMock.mockRejectedValue(new Error('Card not found'));
    fetchDeckTagsMock.mockResolvedValue({ roles: [], types: [] });
    fetchMyDeckByCreationKeyMock.mockResolvedValue({ status: 'missing' });
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
      record: { id: 'deck-new', status: { is_valid: true } },
      replayed: false,
    });
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
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

  test('keeps a new deck local across all three screens until Create is clicked', async () => {
    const mounted = await mountController('/my/decks/new');

    expect(mounted.controller.editorMode.value).toBe('cards');
    expect(mounted.controller.isPublished.value).toBe(false);
    expect(mounted.controller.canAutosync.value).toBe(false);
    expect(searchCardsMock).toHaveBeenCalledTimes(1);

    mounted.controller.openHero();
    mounted.controller.deck.handleGalleryAction(buildHero('hero-new', 'New Hero'));
    mounted.controller.openDetails();
    mounted.controller.deck.setDeckName('New Deck');
    mounted.controller.openCards();
    await nextTick();

    expect(createDeckMock).not.toHaveBeenCalled();
    expect(mounted.controller.editorMode.value).toBe('cards');
    expect(mounted.controller.deck.form.hero_card_id).toBe('hero-new');
    expect(mounted.controller.deck.form.name).toBe('New Deck');
    expect(mounted.controller.changeStatusLabel.value).toBe('Local Draft');
    await vi.advanceTimersByTimeAsync(1000);
    expect(createDeckMock).not.toHaveBeenCalled();

    const storedDraft = loadLocalDraft('user-1');
    expect(storedDraft?.form.name).toBe('New Deck');
    expect(storedDraft?.form.hero_card_id).toBe('hero-new');

    await mounted.controller.saveDeck();

    expect(createDeckMock).toHaveBeenCalledWith(
      expect.objectContaining({
        name: 'New Deck',
        hero_card_id: 'hero-new',
      }),
      expect.any(String),
    );
    expect(mounted.router.currentRoute.value.fullPath).toBe(
      '/my/decks/deck-new/edit?editor_mode=cards',
    );
    expect(mounted.controller.editorMode.value).toBe('cards');
    expect(mounted.controller.isPublished.value).toBe(true);
    expect(loadLocalDraft('user-1')).toBeNull();

    mounted.unmount();
  });

  test('guides Create to missing hero and name without writing to the API', async () => {
    const mounted = await mountController('/my/decks/new');

    await mounted.controller.saveDeck();

    expect(createDeckMock).not.toHaveBeenCalled();
    expect(mounted.controller.editorMode.value).toBe('hero');
    expect(toastErrorMock).toHaveBeenLastCalledWith(
      'Choose a hero and name your deck before creating it.',
    );

    mounted.controller.deck.handleGalleryAction(buildHero('hero-new', 'New Hero'));
    await mounted.controller.saveDeck();

    expect(createDeckMock).not.toHaveBeenCalled();
    expect(mounted.controller.editorMode.value).toBe('details');
    expect(mounted.controller.focusDeckNameRequest.value).toBe(1);
    expect(toastErrorMock).toHaveBeenLastCalledWith('Name your deck before creating it.');

    mounted.unmount();
  });

  test('prompts to resume a user-scoped local draft and restores referenced cards', async () => {
    const form = createEmptyDeckForm();
    form.name = 'Recovered Deck';
    form.hero_card_id = 'hero-recovered';
    form.entries = [{ card_id: 'card-recovered', quantity: 3 }];
    await saveLocalDraft('user-1', form, {
      'hero-recovered': buildHero('hero-recovered', 'Recovered Hero'),
      'card-recovered': buildCard('card-recovered', 'Recovered Card'),
    });
    const mounted = await mountController('/my/decks/new');

    expect(mounted.controller.localDraftRecoveryModalOpen.value).toBe(true);
    expect(mounted.controller.deck.form.name).toBe('');

    await mounted.controller.resumeLocalDraft();

    expect(mounted.controller.localDraftRecoveryModalOpen.value).toBe(false);
    expect(mounted.controller.deck.form.name).toBe('Recovered Deck');
    expect(mounted.controller.deck.form.hero_card_id).toBe('hero-recovered');
    expect(mounted.controller.deck.form.entries).toEqual([
      { card_id: 'card-recovered', quantity: 3 },
    ]);
    expect(mounted.controller.deck.selectedHero.value?.name).toBe('Recovered Hero');
    expect(fetchCardsMock).toHaveBeenCalledTimes(1);

    mounted.unmount();
  });

  test('waits for refreshed recovery inputs before applying the hero card preset', async () => {
    let resolveFilters!: () => void;
    loadFiltersMock.mockReturnValueOnce(new Promise<void>((resolve) => {
      resolveFilters = resolve;
    }));
    const form = createEmptyDeckForm();
    form.name = 'Recovered Deck';
    form.hero_card_id = 'hero-recovered';
    await saveLocalDraft('user-1', form, {
      'hero-recovered': buildHero('hero-recovered', 'Stored Hero'),
    });
    fetchCardsMock.mockResolvedValueOnce({
      count: 1,
      next_page: null,
      previous_page: null,
      page: 1,
      page_size: 100,
      results: [buildHero('hero-recovered', 'Refreshed Hero')],
    });
    const mounted = await mountController('/my/decks/new');

    const resumePromise = mounted.controller.resumeLocalDraft();
    await nextTick();

    expect(applyHeroAffinityManaPresetMock).not.toHaveBeenCalled();

    resolveFilters();
    await resumePromise;

    expect(applyHeroAffinityManaPresetMock).toHaveBeenCalledTimes(1);
    expect(applyHeroAffinityManaPresetMock).toHaveBeenCalledWith(
      expect.objectContaining({ name: 'Refreshed Hero' }),
    );

    mounted.unmount();
  });

  test('blocks route changes while a recovered Create attempt is still hydrating', async () => {
    let resolveFilters!: () => void;
    loadFiltersMock.mockReturnValueOnce(new Promise<void>((resolve) => {
      resolveFilters = resolve;
    }));
    const form = {
      ...createEmptyDeckForm(),
      name: 'Recovered Pending Create',
      hero_card_id: 'hero-recovered',
    };
    await saveLocalDraft('user-1', form, {
      'hero-recovered': buildHero('hero-recovered', 'Recovered Hero'),
    }, {
      payload: {
        name: form.name,
        description: null,
        long_description: null,
        difficulty: null,
        visibility: 'private',
        hero_card_id: form.hero_card_id,
        entries: [],
        sideboards: [],
        tag_ids: [],
        suggested_type_labels: [],
      },
      signature: 'recovered-pending-signature',
      startedAt: '2026-08-09T04:00:00Z',
    });
    fetchMyDeckByCreationKeyMock.mockResolvedValueOnce({
      status: 'found',
      record: { id: 'deck-recovered', status: { is_valid: true } },
    });
    const mounted = await mountController('/my/decks/new');

    const resumePromise = mounted.controller.resumeLocalDraft();
    await nextTick();

    await mounted.router.push('/cards');
    expect(mounted.router.currentRoute.value.fullPath).toBe('/my/decks/new');
    expect(mounted.controller.discardChangesModalOpen.value).toBe(false);

    resolveFilters();
    await resumePromise;

    expect(mounted.router.currentRoute.value.fullPath).toBe(
      '/my/decks/deck-recovered/edit?editor_mode=cards',
    );
    mounted.unmount();
  });

  test('removes recovered tag IDs that are no longer in the current catalog', async () => {
    fetchDeckTagsMock.mockResolvedValueOnce({
      roles: [{ id: 'role-current', key: 'current', label: 'Current', kind: 'role' }],
      types: [],
    });
    const form = createEmptyDeckForm();
    form.name = 'Recovered Deck';
    form.tag_ids = ['role-current', 'role-deleted'];
    await saveLocalDraft('user-1', form, {});
    const mounted = await mountController('/my/decks/new');

    await mounted.controller.resumeLocalDraft();
    await nextTick();

    expect(mounted.controller.deck.form.tag_ids).toEqual(['role-current']);
    expect(loadLocalDraft('user-1')?.form.tag_ids).toEqual([
      'role-current',
    ]);

    mounted.unmount();
  });

  test('resolves merged card IDs and coalesces recovered entries', async () => {
    const form = createEmptyDeckForm();
    form.name = 'Recovered Deck';
    form.hero_card_id = 'hero-merged';
    form.entries = [
      { card_id: 'card-merged', quantity: 2 },
      { card_id: 'card-target', quantity: 1 },
    ];
    form.sideboards = [{
      id: 'sideboard-1',
      name: 'Maybeboard',
      entries: [{ card_id: 'card-merged', quantity: 4 }],
    }];
    await saveLocalDraft('user-1', form, {
      'hero-merged': buildHero('hero-merged', 'Stored Hero'),
      'card-merged': buildCard('card-merged', 'Stored Card'),
      'card-target': buildCard('card-target', 'Target Card'),
    });
    fetchCardsMock.mockResolvedValueOnce({
      count: 1,
      next_page: null,
      previous_page: null,
      page: 1,
      page_size: 100,
      results: [buildCard('card-target', 'Target Card')],
    });
    fetchCardMock.mockImplementation(async (cardId: string) => {
      if (cardId === 'hero-merged') {
        return buildHero('hero-target', 'Target Hero');
      }
      if (cardId === 'card-merged') {
        return buildCard('card-target', 'Target Card');
      }
      throw new Error('Card not found');
    });
    const mounted = await mountController('/my/decks/new');

    await mounted.controller.resumeLocalDraft();

    expect(mounted.controller.deck.form.hero_card_id).toBe('hero-target');
    expect(mounted.controller.deck.form.entries).toEqual([
      { card_id: 'card-target', quantity: 3 },
    ]);
    expect(mounted.controller.deck.form.sideboards[0]?.entries).toEqual([
      { card_id: 'card-target', quantity: 4 },
    ]);
    expect(mounted.controller.deck.selectedHero.value?.name).toBe('Target Hero');

    mounted.unmount();
  });

  test('discards a pending local draft and starts with an empty Cards screen', async () => {
    await saveLocalDraft(
      'user-1',
      { ...createEmptyDeckForm(), name: 'Discard Me' },
      {},
    );
    const mounted = await mountController('/my/decks/new');

    await mounted.controller.discardPendingLocalDraft();

    expect(mounted.controller.localDraftRecoveryModalOpen.value).toBe(false);
    expect(mounted.controller.editorMode.value).toBe('cards');
    expect(mounted.controller.deck.form.name).toBe('');
    expect(loadLocalDraft('user-1')).toBeNull();

    mounted.unmount();
  });

  test('reconciles a pending Create before discarding recovered state', async () => {
    const form = {
      ...createEmptyDeckForm(),
      name: 'Already Created',
      hero_card_id: 'hero-created',
    };
    await saveLocalDraft('user-1', form, {}, {
      payload: {
        name: form.name,
        description: null,
        long_description: null,
        difficulty: null,
        visibility: 'private',
        hero_card_id: form.hero_card_id,
        entries: [],
        sideboards: [],
        tag_ids: [],
        suggested_type_labels: [],
      },
      signature: 'created-signature',
      startedAt: '2026-08-09T04:00:00Z',
    });
    fetchMyDeckByCreationKeyMock.mockResolvedValueOnce({
      status: 'found',
      record: {
        id: 'deck-created-before-reload',
        status: { is_valid: true },
      },
    });
    const mounted = await mountController('/my/decks/new');

    await mounted.controller.discardPendingLocalDraft();

    expect(fetchMyDeckByCreationKeyMock).toHaveBeenCalledWith('draft-user-1');
    expect(mounted.router.currentRoute.value.fullPath).toBe(
      '/my/decks/deck-created-before-reload/edit?editor_mode=cards',
    );
    mounted.unmount();
  });

  test('retains and resumes pending creation when discard reconciliation is unavailable', async () => {
    const form = {
      ...createEmptyDeckForm(),
      name: 'Unconfirmed Create',
      hero_card_id: 'hero-unconfirmed',
    };
    await saveLocalDraft('user-1', form, {}, {
      payload: {
        name: form.name,
        description: null,
        long_description: null,
        difficulty: null,
        visibility: 'private',
        hero_card_id: form.hero_card_id,
        entries: [],
        sideboards: [],
        tag_ids: [],
        suggested_type_labels: [],
      },
      signature: 'unknown-signature',
      startedAt: '2026-08-09T04:00:00Z',
    });
    fetchMyDeckByCreationKeyMock.mockRejectedValue(new Error('Lookup unavailable'));
    const mounted = await mountController('/my/decks/new');

    const discardPromise = mounted.controller.discardPendingLocalDraft();
    await vi.runAllTimersAsync();
    await discardPromise;

    expect(mounted.controller.localDraftRecoveryModalOpen.value).toBe(false);
    expect(mounted.controller.deck.form.name).toBe('Unconfirmed Create');
    expect(mounted.controller.creationState.value.status).toBe('unknown');
    expect(loadLocalDraft('user-1')?.pendingCreateAttempt?.signature).toBe('unknown-signature');
    mounted.unmount();
  });

  test('keeps a pending attempt locked when auxiliary recovery hydration fails', async () => {
    const form = {
      ...createEmptyDeckForm(),
      name: 'Pending Through Hydration Failure',
      hero_card_id: 'hero-pending',
    };
    await saveLocalDraft('user-1', form, {}, {
      payload: {
        name: form.name,
        description: null,
        long_description: null,
        difficulty: null,
        visibility: 'private',
        hero_card_id: form.hero_card_id,
        entries: [],
        sideboards: [],
        tag_ids: [],
        suggested_type_labels: [],
      },
      signature: 'pending-hydration-signature',
      startedAt: '2026-08-09T04:00:00Z',
    });
    loadFiltersMock.mockRejectedValueOnce(new Error('Filters unavailable'));
    let resolveLookup!: (result: { status: 'missing' }) => void;
    fetchMyDeckByCreationKeyMock.mockReturnValueOnce(new Promise((resolve) => {
      resolveLookup = resolve;
    }));
    const mounted = await mountController('/my/decks/new');

    const resumePromise = mounted.controller.resumeLocalDraft();
    await flushAsyncEditorWork();

    expect(mounted.controller.creationState.value).toEqual({
      status: 'unknown',
      reconciliation: 'checking',
    });
    expect(mounted.controller.isMutationLocked.value).toBe(true);

    resolveLookup({ status: 'missing' });
    await vi.runAllTimersAsync();
    await resumePromise;

    expect(mounted.controller.creationState.value).toEqual({
      status: 'unknown',
      reconciliation: 'awaiting-retry',
    });
    expect(mounted.controller.isMutationLocked.value).toBe(true);
    expect(loadLocalDraft('user-1')?.pendingCreateAttempt?.signature)
      .toBe('pending-hydration-signature');
    mounted.unmount();
  });

  test('retires a pending local attempt when its created deck was deleted', async () => {
    const form = {
      ...createEmptyDeckForm(),
      name: 'Deleted After Create',
      hero_card_id: 'hero-deleted',
    };
    await saveLocalDraft('user-1', form, {}, {
      payload: {
        name: form.name,
        description: null,
        long_description: null,
        difficulty: null,
        visibility: 'private',
        hero_card_id: form.hero_card_id,
        entries: [],
        sideboards: [],
        tag_ids: [],
        suggested_type_labels: [],
      },
      signature: 'deleted-signature',
      startedAt: '2026-08-09T04:00:00Z',
    });
    fetchMyDeckByCreationKeyMock.mockResolvedValueOnce({ status: 'deleted' });
    const mounted = await mountController('/my/decks/new');

    await mounted.controller.discardPendingLocalDraft();
    await flushAsyncEditorWork();

    expect(mounted.router.currentRoute.value.fullPath).toBe('/my/decks');
    expect(loadLocalDraft('user-1')).toBeNull();
    expect(toastInfoMock).toHaveBeenCalledWith(
      'This deck was already created and has since been deleted.',
    );
    mounted.unmount();
  });

  test('explicitly discards an active local draft and resets the editor', async () => {
    const mounted = await mountController('/my/decks/new');
    mounted.controller.deck.setDeckName('Discard Active Draft');
    await nextTick();

    mounted.controller.requestDiscardLocalDraft();
    expect(mounted.controller.discardLocalDraftModalOpen.value).toBe(true);

    await mounted.controller.confirmDiscardLocalDraft();

    expect(mounted.controller.discardLocalDraftModalOpen.value).toBe(false);
    expect(mounted.controller.deck.form.name).toBe('');
    expect(mounted.controller.editorMode.value).toBe('cards');
    expect(mounted.controller.hasLocalDraft.value).toBe(false);
    expect(loadLocalDraft('user-1')).toBeNull();

    mounted.unmount();
  });

  test('does not discard another tab draft after a queued save enters conflict', async () => {
    const baseLockManager = createTestLockManager();
    let blockNextRequest = false;
    let releaseBlockedRequest: () => void = () => undefined;
    const lockManager: DeckEditorDraftLockManager = {
      async request<Result>(
        name: string,
        options: { mode: 'exclusive' },
        callback: () => Result | PromiseLike<Result>,
      ): Promise<Result> {
        return await baseLockManager.request(name, options, async () => {
          if (blockNextRequest) {
            blockNextRequest = false;
            await new Promise<void>((resolve) => {
              releaseBlockedRequest = resolve;
            });
          }
          return await callback();
        });
      },
    };
    Object.defineProperty(navigator, 'locks', {
      configurable: true,
      value: lockManager,
    });
    const mounted = await mountController('/my/decks/new');
    mounted.controller.deck.setDeckName('This Tab');
    await flushAsyncEditorWork();

    const remoteForm = createEmptyDeckForm();
    remoteForm.name = 'Another Tab';
    await saveLocalDraft('user-1', remoteForm, {});

    blockNextRequest = true;
    mounted.controller.deck.setDeckName('Queued Local Save');
    await nextTick();
    await Promise.resolve();
    mounted.controller.requestDiscardLocalDraft();
    const discardPromise = mounted.controller.confirmDiscardLocalDraft();
    releaseBlockedRequest();
    await discardPromise;

    expect(mounted.controller.persistenceState.value.status).toBe('conflict');
    expect(mounted.controller.deck.form.name).toBe('Queued Local Save');
    expect(loadLocalDraft('user-1')?.form.name).toBe('Another Tab');
    mounted.unmount();
  });

  test('retains a local draft after confirmed navigation away', async () => {
    const mounted = await mountController('/my/decks/new');
    mounted.controller.deck.setDeckName('Resume After Leaving');
    await nextTick();

    const navigationPromise = mounted.router.push('/cards');
    await nextTick();

    expect(mounted.controller.discardChangesModalOpen.value).toBe(true);
    mounted.controller.confirmDiscardChanges();
    await navigationPromise;

    expect(mounted.router.currentRoute.value.fullPath).toBe('/cards');
    expect(loadLocalDraft('user-1')?.form.name).toBe(
      'Resume After Leaving',
    );

    mounted.unmount();
  });

  test('marks the current local draft as unsafe when browser persistence fails', async () => {
    const mounted = await mountController('/my/decks/new');
    const setItemSpy = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new DOMException('Storage unavailable', 'QuotaExceededError');
    });

    mounted.controller.deck.setDeckName('Only in memory');
    await flushAsyncEditorWork();

    expect(mounted.controller.localDraftPersistenceFailed.value).toBe(true);
    expect(toastErrorMock).toHaveBeenCalledWith(
      'This deck could not be saved to local browser storage.',
    );

    setItemSpy.mockRestore();
    mounted.unmount();
  });

  test('blocks route changes while the initial create request is pending', async () => {
    let resolveCreate!: (value: {
      record: { id: string; status: { is_valid: boolean } };
      replayed: boolean;
    }) => void;
    createDeckMock.mockReturnValueOnce(new Promise((resolve) => {
      resolveCreate = resolve;
    }));
    const mounted = await mountController('/my/decks/new');
    mounted.controller.openHero();
    mounted.controller.deck.handleGalleryAction(buildHero('hero-new', 'New Hero'));
    mounted.controller.deck.setDeckName('Creating Deck');

    const createPromise = mounted.controller.saveDeck();
    await flushAsyncEditorWork();

    expect(mounted.controller.isCreating.value).toBe(true);
    const navigationPromise = mounted.router.push('/cards');
    await nextTick();
    expect(mounted.router.currentRoute.value.fullPath).toBe('/my/decks/new');
    expect(mounted.controller.discardChangesModalOpen.value).toBe(false);

    resolveCreate({
      record: { id: 'deck-new', status: { is_valid: true } },
      replayed: false,
    });
    await navigationPromise;
    await createPromise;

    expect(mounted.router.currentRoute.value.fullPath).toBe(
      '/my/decks/deck-new/edit?editor_mode=cards',
    );
    mounted.unmount();
  });

  test('locks and coalesces Create while its immutable attempt is being persisted', async () => {
    const lockManager = createTestLockManager();
    Object.defineProperty(navigator, 'locks', {
      configurable: true,
      value: lockManager,
    });
    const mounted = await mountController('/my/decks/new');
    mounted.controller.openHero();
    mounted.controller.deck.handleGalleryAction(buildHero('hero-new', 'New Hero'));
    mounted.controller.deck.setDeckName('Sealed Before Persistence');
    await flushAsyncEditorWork();

    let releaseLock!: () => void;
    const heldLock = lockManager.request(
      'test-held-deck-draft-lock',
      { mode: 'exclusive' },
      async () => await new Promise<void>((resolve) => {
        releaseLock = resolve;
      }),
    );
    await Promise.resolve();

    const firstCreate = mounted.controller.saveDeck();
    await flushAsyncEditorWork();

    expect(mounted.controller.isCreating.value).toBe(true);
    expect(mounted.controller.isMutationLocked.value).toBe(true);
    expect(createDeckMock).not.toHaveBeenCalled();

    const duplicateCreate = mounted.controller.saveDeck();
    releaseLock();
    await heldLock;
    await Promise.all([firstCreate, duplicateCreate]);

    expect(createDeckMock).toHaveBeenCalledTimes(1);
    expect(createDeckMock).toHaveBeenCalledWith(
      expect.objectContaining({ name: 'Sealed Before Persistence' }),
      expect.any(String),
    );
    mounted.unmount();
  });

  test('does not retire a draft changed by another tab while creation is in flight', async () => {
    let resolveCreate!: (value: {
      record: { id: string; status: { is_valid: boolean } };
      replayed: boolean;
    }) => void;
    createDeckMock.mockReturnValueOnce(new Promise((resolve) => {
      resolveCreate = resolve;
    }));
    const mounted = await mountController('/my/decks/new');
    mounted.controller.openHero();
    mounted.controller.deck.handleGalleryAction(buildHero('hero-new', 'New Hero'));
    mounted.controller.deck.setDeckName('Creating Here');
    const createPromise = mounted.controller.saveDeck();
    await flushAsyncEditorWork();
    const otherTabForm = createEmptyDeckForm();
    otherTabForm.name = 'Changed Elsewhere During Create';
    await saveLocalDraft('user-1', otherTabForm, {});
    dispatchDraftStorageEvent('user-1');

    expect(mounted.controller.conflictActionsLocked.value).toBe(true);
    await mounted.controller.loadStoredConflictDraft();
    expect(mounted.controller.deck.form.name).toBe('Creating Here');

    resolveCreate({
      record: { id: 'deck-new', status: { is_valid: true } },
      replayed: false,
    });
    await createPromise;

    expect(mounted.router.currentRoute.value.fullPath).toBe(
      '/my/decks/deck-new/edit?editor_mode=cards',
    );
    expect(loadLocalDraft('user-1')?.form.name).toBe('Changed Elsewhere During Create');
    expect(toastInfoMock).toHaveBeenCalledWith(
      'A different local deck draft remains available in this browser.',
    );
    mounted.unmount();
  });

  test('treats a failed POST as success when creation-key lookup finds the deck', async () => {
    createDeckMock.mockRejectedValueOnce(new Error('Connection dropped'));
    fetchMyDeckByCreationKeyMock.mockResolvedValueOnce({
      status: 'found',
      record: {
        id: 'deck-found',
        status: { is_valid: true },
      },
    });
    const mounted = await mountController('/my/decks/new');
    mounted.controller.openHero();
    mounted.controller.deck.handleGalleryAction(buildHero('hero-new', 'New Hero'));
    mounted.controller.deck.setDeckName('Found After Failure');

    await mounted.controller.saveDeck();

    expect(fetchMyDeckByCreationKeyMock).toHaveBeenCalledWith(expect.any(String));
    expect(mounted.router.currentRoute.value.fullPath).toBe(
      '/my/decks/deck-found/edit?editor_mode=cards',
    );
    mounted.unmount();
  });

  test('enters unknown after ambiguous create and retries the identical key and payload', async () => {
    createDeckMock.mockRejectedValueOnce(new Error('Connection dropped'));
    fetchMyDeckByCreationKeyMock.mockRejectedValueOnce(new Error('Lookup unavailable'));
    const mounted = await mountController('/my/decks/new');
    mounted.controller.openHero();
    mounted.controller.deck.handleGalleryAction(buildHero('hero-new', 'New Hero'));
    mounted.controller.deck.setDeckName('Ambiguous Create');

    const createPromise = mounted.controller.saveDeck();
    await vi.runAllTimersAsync();
    await createPromise;

    expect(mounted.controller.creationState.value.status).toBe('unknown');
    expect(mounted.controller.isMutationLocked.value).toBe(true);
    const firstCall = createDeckMock.mock.calls[0];
    createDeckMock.mockResolvedValueOnce({
      record: { id: 'deck-retried', status: { is_valid: true } },
      replayed: true,
    });

    await mounted.controller.saveDeck();

    expect(createDeckMock.mock.calls[1]).toEqual(firstCall);
    expect(mounted.router.currentRoute.value.fullPath).toBe(
      '/my/decks/deck-retried/edit?editor_mode=cards',
    );
    mounted.unmount();
  });

  test('keeps an ambiguous Create locked after every backoff lookup misses', async () => {
    createDeckMock.mockRejectedValueOnce(new Error('Connection dropped'));
    fetchMyDeckByCreationKeyMock.mockResolvedValue({ status: 'missing' });
    const mounted = await mountController('/my/decks/new');
    mounted.controller.openHero();
    mounted.controller.deck.handleGalleryAction(buildHero('hero-new', 'New Hero'));
    mounted.controller.deck.setDeckName('Still Processing');

    const createPromise = mounted.controller.saveDeck();
    await vi.runAllTimersAsync();
    await createPromise;

    expect(fetchMyDeckByCreationKeyMock).toHaveBeenCalledTimes(4);
    expect(mounted.controller.creationState.value.status).toBe('unknown');
    expect(mounted.controller.isMutationLocked.value).toBe(true);
    expect(loadLocalDraft('user-1')?.pendingCreateAttempt?.payload.name).toBe('Still Processing');
    mounted.unmount();
  });

  test('blocks leaving when an ambiguous Create attempt is not durable', async () => {
    createDeckMock.mockRejectedValueOnce(new Error('Connection dropped'));
    fetchMyDeckByCreationKeyMock.mockResolvedValue({ status: 'missing' });
    const mounted = await mountController('/my/decks/new');
    mounted.controller.openHero();
    mounted.controller.deck.handleGalleryAction(buildHero('hero-new', 'New Hero'));
    mounted.controller.deck.setDeckName('Memory-only Attempt');
    await flushAsyncEditorWork();
    const setItemSpy = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new DOMException('Storage unavailable', 'QuotaExceededError');
    });

    const createPromise = mounted.controller.saveDeck();
    await vi.runAllTimersAsync();
    await createPromise;

    expect(mounted.controller.creationState.value).toEqual({
      status: 'unknown',
      reconciliation: 'awaiting-retry',
    });
    expect(mounted.controller.persistenceState.value.status).toBe('memory-only');
    await mounted.router.push('/cards');
    expect(mounted.router.currentRoute.value.fullPath).toBe('/my/decks/new');
    expect(mounted.controller.discardChangesModalOpen.value).toBe(false);

    setItemSpy.mockRestore();
    const navigationPromise = mounted.router.push('/cards');
    await flushAsyncEditorWork();
    await flushAsyncEditorWork();
    expect(mounted.controller.discardChangesModalOpen.value).toBe(true);
    mounted.controller.confirmDiscardChanges();
    await navigationPromise;

    expect(mounted.router.currentRoute.value.fullPath).toBe('/cards');
    expect(loadLocalDraft('user-1')?.pendingCreateAttempt?.payload.name)
      .toBe('Memory-only Attempt');
    mounted.unmount();
  });

  test('allows confirmed navigation when an ambiguous Create attempt is durable', async () => {
    createDeckMock.mockRejectedValueOnce(new Error('Connection dropped'));
    fetchMyDeckByCreationKeyMock.mockResolvedValue({ status: 'missing' });
    const mounted = await mountController('/my/decks/new');
    mounted.controller.openHero();
    mounted.controller.deck.handleGalleryAction(buildHero('hero-new', 'New Hero'));
    mounted.controller.deck.setDeckName('Durable Pending Attempt');

    const createPromise = mounted.controller.saveDeck();
    await vi.runAllTimersAsync();
    await createPromise;

    const navigationPromise = mounted.router.push('/cards');
    await nextTick();
    expect(mounted.controller.discardChangesModalOpen.value).toBe(true);
    mounted.controller.confirmDiscardChanges();
    await navigationPromise;

    expect(mounted.router.currentRoute.value.fullPath).toBe('/cards');
    expect(loadLocalDraft('user-1')?.pendingCreateAttempt?.payload.name)
      .toBe('Durable Pending Attempt');
    mounted.unmount();
  });

  test('treats gateway timeout responses as ambiguous creation outcomes', async () => {
    createDeckMock.mockRejectedValueOnce(Object.assign(new Error('Gateway timeout'), {
      isAxiosError: true,
      response: { status: 504 },
    }));
    fetchMyDeckByCreationKeyMock.mockResolvedValue({ status: 'missing' });
    const mounted = await mountController('/my/decks/new');
    mounted.controller.openHero();
    mounted.controller.deck.handleGalleryAction(buildHero('hero-new', 'New Hero'));
    mounted.controller.deck.setDeckName('Timed Out Upstream');

    const createPromise = mounted.controller.saveDeck();
    await vi.runAllTimersAsync();
    await createPromise;

    expect(fetchMyDeckByCreationKeyMock).toHaveBeenCalledTimes(4);
    expect(mounted.controller.creationState.value).toEqual({
      status: 'unknown',
      reconciliation: 'awaiting-retry',
    });
    expect(loadLocalDraft('user-1')?.pendingCreateAttempt?.payload.name)
      .toBe('Timed Out Upstream');
    mounted.unmount();
  });

  test('blocks route changes while an ambiguous Create is actively reconciling', async () => {
    createDeckMock.mockRejectedValueOnce(new Error('Connection dropped'));
    let resolveLookup!: (result: { status: 'missing' }) => void;
    fetchMyDeckByCreationKeyMock.mockReturnValueOnce(new Promise((resolve) => {
      resolveLookup = resolve;
    }));
    const mounted = await mountController('/my/decks/new');
    mounted.controller.openHero();
    mounted.controller.deck.handleGalleryAction(buildHero('hero-new', 'New Hero'));
    mounted.controller.deck.setDeckName('Reconciliation In Flight');

    const createPromise = mounted.controller.saveDeck();
    await flushAsyncEditorWork();
    expect(mounted.controller.creationState.value).toEqual({
      status: 'unknown',
      reconciliation: 'checking',
    });

    await mounted.router.push('/cards');
    expect(mounted.router.currentRoute.value.fullPath).toBe('/my/decks/new');
    expect(mounted.controller.discardChangesModalOpen.value).toBe(false);

    resolveLookup({ status: 'missing' });
    await vi.runAllTimersAsync();
    await createPromise;
    expect(mounted.controller.creationState.value).toEqual({
      status: 'unknown',
      reconciliation: 'awaiting-retry',
    });
    mounted.unmount();
  });

  test('returns an unconfirmed request to editable state after a definitive lookup miss', async () => {
    createDeckMock.mockRejectedValueOnce(Object.assign(new Error('Request rejected'), {
      isAxiosError: true,
      response: { status: 400 },
    }));
    fetchMyDeckByCreationKeyMock.mockResolvedValueOnce({ status: 'missing' });
    const mounted = await mountController('/my/decks/new');
    mounted.controller.openHero();
    mounted.controller.deck.handleGalleryAction(buildHero('hero-new', 'New Hero'));
    mounted.controller.deck.setDeckName('Definitive Failure');

    await mounted.controller.saveDeck();

    expect(mounted.controller.creationState.value.status).toBe('idle');
    expect(mounted.controller.isMutationLocked.value).toBe(false);
    expect(mounted.router.currentRoute.value.fullPath).toBe('/my/decks/new');
    mounted.unmount();
  });

  test('navigates after confirmed creation when draft retirement fails', async () => {
    const mounted = await mountController('/my/decks/new');
    mounted.controller.openHero();
    mounted.controller.deck.handleGalleryAction(buildHero('hero-new', 'New Hero'));
    mounted.controller.deck.setDeckName('Created Once');
    await nextTick();

    const originalSetItem = Storage.prototype.setItem;
    const setItemSpy = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(function (this: Storage, key, value) {
      if (value.includes('"kind":"retired"')) {
        throw new DOMException('Retirement blocked', 'SecurityError');
      }
      originalSetItem.call(this, key, value);
    });

    await mounted.controller.saveDeck();

    expect(createDeckMock).toHaveBeenCalledTimes(1);
    expect(mounted.controller.isCreating.value).toBe(false);
    expect(mounted.router.currentRoute.value.fullPath).toBe(
      '/my/decks/deck-new/edit?editor_mode=cards',
    );
    expect(toastErrorMock).toHaveBeenCalledWith(
      'The deck was created, but its browser draft could not be retired.',
    );

    setItemSpy.mockRestore();
    mounted.unmount();
  });

  test('does not reconcile a confirmed creation when editor routing fails', async () => {
    const mounted = await mountController('/my/decks/new');
    mounted.controller.openHero();
    mounted.controller.deck.handleGalleryAction(buildHero('hero-new', 'New Hero'));
    mounted.controller.deck.setDeckName('Created Before Route Failure');
    let rejectNavigation: (reason?: unknown) => void = () => undefined;
    const replaceSpy = vi.spyOn(mounted.router, 'replace').mockImplementationOnce(
      async () => await new Promise<never>((_resolve, reject) => {
        rejectNavigation = reject;
      }),
    );

    const savePromise = mounted.controller.saveDeck();
    await vi.waitFor(() => expect(replaceSpy).toHaveBeenCalledTimes(1));

    expect(mounted.controller.isMutationLocked.value).toBe(true);
    expect(mounted.controller.terminalNavigationPending.value).toBe(true);

    rejectNavigation(new Error('Router unavailable'));
    await savePromise;

    expect(createDeckMock).toHaveBeenCalledTimes(1);
    expect(fetchMyDeckByCreationKeyMock).not.toHaveBeenCalled();
    expect(mounted.controller.creationState.value).toEqual({ status: 'idle' });
    expect(mounted.controller.isMutationLocked.value).toBe(true);
    expect(mounted.controller.terminalNavigationPending.value).toBe(true);
    expect(toastErrorMock).toHaveBeenCalledWith(
      'The deck was created, but its editor could not be opened. Click Continue to try again.',
    );

    await mounted.controller.saveDeck();
    expect(createDeckMock).toHaveBeenCalledTimes(1);
    expect(mounted.router.currentRoute.value.fullPath).toBe(
      '/my/decks/deck-new/edit?editor_mode=cards',
    );
    expect(mounted.controller.terminalNavigationPending.value).toBe(false);

    replaceSpy.mockRestore();
    mounted.unmount();
  });

  test('retries deleted-outcome navigation without repeating the Create request', async () => {
    createDeckMock.mockRejectedValueOnce(new Error('Connection dropped'));
    fetchMyDeckByCreationKeyMock.mockResolvedValueOnce({ status: 'deleted' });
    const mounted = await mountController('/my/decks/new');
    mounted.controller.openHero();
    mounted.controller.deck.handleGalleryAction(buildHero('hero-new', 'New Hero'));
    mounted.controller.deck.setDeckName('Deleted Before Navigation');
    const replaceSpy = vi.spyOn(mounted.router, 'replace').mockRejectedValueOnce(
      new Error('Router unavailable'),
    );

    await mounted.controller.saveDeck();

    expect(createDeckMock).toHaveBeenCalledTimes(1);
    expect(mounted.controller.creationState.value).toEqual({ status: 'idle' });
    expect(mounted.controller.isMutationLocked.value).toBe(true);
    expect(mounted.controller.terminalNavigationPending.value).toBe(true);
    expect(toastErrorMock).toHaveBeenCalledWith(
      'The deleted deck was confirmed, but navigation failed. Click Continue to try again.',
    );

    await mounted.controller.saveDeck();
    expect(createDeckMock).toHaveBeenCalledTimes(1);
    expect(mounted.router.currentRoute.value.fullPath).toBe('/my/decks');
    expect(mounted.controller.terminalNavigationPending.value).toBe(false);

    replaceSpy.mockRestore();
    mounted.unmount();
  });

  test('pauses creation when another tab has replaced the observed draft', async () => {
    const mounted = await mountController('/my/decks/new');
    mounted.controller.openHero();
    mounted.controller.deck.handleGalleryAction(buildHero('hero-new', 'New Hero'));
    mounted.controller.deck.setDeckName('Created in first tab');
    await flushAsyncEditorWork();

    const otherTabForm = createEmptyDeckForm();
    otherTabForm.name = 'Keep from second tab';
    await saveLocalDraft('user-1', otherTabForm, {});

    await mounted.controller.saveDeck();

    expect(createDeckMock).not.toHaveBeenCalled();
    expect(mounted.controller.persistenceState.value.status).toBe('conflict');
    expect(mounted.controller.localDraftConflict.value?.kind).toBe('active-draft');

    await mounted.controller.keepThisConflictDraft();
    await mounted.controller.saveDeck();

    expect(createDeckMock).toHaveBeenCalledTimes(1);
    expect(mounted.router.currentRoute.value.fullPath).toBe('/my/decks/deck-new/edit?editor_mode=cards');

    mounted.unmount();
  });

  test('does not overwrite another tab pending Create attempt', async () => {
    const mounted = await mountController('/my/decks/new');
    mounted.controller.deck.setDeckName('Keep This Tab');
    await flushAsyncEditorWork();
    const remoteForm = {
      ...createEmptyDeckForm(),
      name: 'Remote Pending Create',
      hero_card_id: 'hero-remote',
    };
    const remoteAttempt: StoredCreateAttempt = {
      payload: {
        name: remoteForm.name,
        description: null,
        long_description: null,
        difficulty: null,
        visibility: 'private',
        hero_card_id: remoteForm.hero_card_id,
        entries: [],
        sideboards: [],
        tag_ids: [],
        suggested_type_labels: [],
      },
      signature: 'remote-pending-signature',
      startedAt: '2026-08-09T05:00:00Z',
    };
    await saveLocalDraft('user-1', remoteForm, {}, remoteAttempt);
    dispatchDraftStorageEvent('user-1');

    await mounted.controller.keepThisConflictDraft();

    expect(mounted.controller.persistenceState.value.status).toBe('conflict');
    expect(mounted.controller.deck.form.name).toBe('Keep This Tab');
    expect(loadLocalDraft('user-1')?.pendingCreateAttempt?.signature)
      .toBe('remote-pending-signature');
    expect(toastInfoMock).toHaveBeenCalledWith(
      'The stored draft has an unconfirmed Create request. Load it before replacing it.',
    );
    mounted.unmount();
  });

  test('closes a stale discard confirmation when a storage conflict arrives', async () => {
    const mounted = await mountController('/my/decks/new');
    mounted.controller.deck.setDeckName('Discard Prompt Draft');
    await flushAsyncEditorWork();
    mounted.controller.requestDiscardLocalDraft();
    expect(mounted.controller.discardLocalDraftModalOpen.value).toBe(true);

    const remoteForm = createEmptyDeckForm();
    remoteForm.name = 'Remote Draft After Prompt';
    await saveLocalDraft('user-1', remoteForm, {});
    dispatchDraftStorageEvent('user-1');
    await nextTick();

    expect(mounted.controller.discardLocalDraftModalOpen.value).toBe(false);
    expect(mounted.controller.localDraftConflictModalOpen.value).toBe(true);
    await mounted.controller.confirmDiscardLocalDraft();
    expect(loadLocalDraft('user-1')?.form.name).toBe('Remote Draft After Prompt');
    mounted.unmount();
  });

  test('loads a newer stored draft after a cross-tab conflict', async () => {
    const mounted = await mountController('/my/decks/new');
    mounted.controller.deck.setDeckName('This Tab');
    await flushAsyncEditorWork();
    const remoteForm = createEmptyDeckForm();
    remoteForm.name = 'Stored Tab';
    await saveLocalDraft('user-1', remoteForm, {});
    dispatchDraftStorageEvent('user-1');

    expect(mounted.controller.localDraftConflict.value?.kind).toBe('active-draft');
    await mounted.controller.loadStoredConflictDraft();

    expect(mounted.controller.deck.form.name).toBe('Stored Tab');
    expect(mounted.controller.persistenceState.value.status).toBe('synced');
    mounted.unmount();
  });

  test('uses the pending recovery as the local candidate when storage changes', async () => {
    const recoverableForm = createEmptyDeckForm();
    recoverableForm.name = 'Recover This Draft';
    await saveLocalDraft('user-1', recoverableForm, {});
    const mounted = await mountController('/my/decks/new');

    expect(mounted.controller.localDraftRecoveryModalOpen.value).toBe(true);

    const remoteForm = createEmptyDeckForm();
    remoteForm.name = 'Changed in Another Tab';
    await saveLocalDraft('user-1', remoteForm, {});
    dispatchDraftStorageEvent('user-1');
    await flushAsyncEditorWork();
    await flushAsyncEditorWork();

    expect(mounted.controller.localDraftRecoveryModalOpen.value).toBe(false);
    expect(mounted.controller.localDraftConflict.value?.kind).toBe('active-draft');
    expect(mounted.controller.localDraftConflictModalOpen.value).toBe(true);
    expect(mounted.controller.deck.form.name).toBe('Recover This Draft');

    await mounted.controller.keepThisConflictDraft();

    expect(loadLocalDraft('user-1')?.form.name).toBe('Recover This Draft');
    expect(mounted.controller.persistenceState.value.status).toBe('synced');
    mounted.unmount();
  });

  test('keeps an interrupted recovered Create locked and retries its original payload', async () => {
    const recoverableForm = {
      ...createEmptyDeckForm(),
      name: 'Pending Local Create',
      hero_card_id: 'hero-pending-conflict',
    };
    const pendingAttempt: StoredCreateAttempt = {
      payload: {
        name: recoverableForm.name,
        description: null,
        long_description: null,
        difficulty: null,
        visibility: 'private',
        hero_card_id: recoverableForm.hero_card_id,
        entries: [],
        sideboards: [],
        tag_ids: [],
        suggested_type_labels: [],
      },
      signature: 'pending-conflict-signature',
      startedAt: '2026-08-09T04:00:00Z',
    };
    await saveLocalDraft('user-1', recoverableForm, {}, pendingAttempt);
    const mounted = await mountController('/my/decks/new');

    const remoteForm = createEmptyDeckForm();
    remoteForm.name = 'Remote Draft During Recovery';
    await saveLocalDraft('user-1', remoteForm, {});
    dispatchDraftStorageEvent('user-1');
    await vi.runAllTimersAsync();
    await flushAsyncEditorWork();

    expect(mounted.controller.localDraftRecoveryModalOpen.value).toBe(false);
    expect(mounted.controller.localDraftConflict.value?.kind).toBe('active-draft');
    expect(mounted.controller.localDraftConflictModalOpen.value).toBe(false);
    expect(mounted.controller.creationState.value).toEqual({
      status: 'unknown',
      reconciliation: 'awaiting-retry',
    });
    expect(mounted.controller.deck.form.name).toBe('Pending Local Create');

    await mounted.controller.saveDeck();

    expect(createDeckMock).toHaveBeenCalledWith(
      pendingAttempt.payload,
      'draft-user-1',
    );
    expect(mounted.router.currentRoute.value.fullPath).toBe(
      '/my/decks/deck-new/edit?editor_mode=cards',
    );
    expect(loadLocalDraft('user-1')?.form.name).toBe('Remote Draft During Recovery');
    mounted.unmount();
  });

  test('discards this tab after a draft is removed elsewhere', async () => {
    const mounted = await mountController('/my/decks/new');
    mounted.controller.deck.setDeckName('Removed Elsewhere');
    await flushAsyncEditorWork();
    localStorage.removeItem('card-reader.deck-editor.new-draft.user-1');
    dispatchDraftStorageEvent('user-1');

    expect(mounted.controller.localDraftConflict.value?.kind).toBe('remote-deletion');
    mounted.controller.discardThisConflictedTab();

    expect(mounted.controller.deck.form.name).toBe('');
    expect(mounted.controller.persistenceState.value.status).toBe('synced');
    mounted.unmount();
  });

  test('keeps a draft created elsewhere as a new browser draft', async () => {
    const mounted = await mountController('/my/decks/new');
    mounted.controller.deck.setDeckName('Keep Separate');
    await flushAsyncEditorWork();
    const activeDraft = loadLocalDraft('user-1');
    if (!activeDraft) throw new Error('Expected an active local draft');
    const storage = createDeckEditorLocalDraftStorage();
    const retirement = await storage.retire(
      'user-1',
      activeDraft.draftId,
      'deck-created-elsewhere',
      { kind: 'draft', revision: activeDraft.revision },
    );
    expect(retirement.status).toBe('retired');
    dispatchDraftStorageEvent('user-1');

    expect(mounted.controller.localDraftConflict.value?.kind).toBe('created-elsewhere');

    const replacementForm = createEmptyDeckForm();
    replacementForm.name = 'New Draft in Creating Tab';
    const replacementDraft = buildStoredDeckEditorDraft(
      'user-1',
      'replacement-draft-id',
      replacementForm,
      {},
    );
    const replacement = await storage.save(
      replacementDraft,
      retirement.status === 'retired'
        ? { kind: 'retired', revision: retirement.marker.revision }
        : { kind: 'empty' },
    );
    expect(replacement.status).toBe('saved');
    dispatchDraftStorageEvent('user-1');

    expect(mounted.controller.localDraftConflict.value?.kind).toBe('active-draft');
    await mounted.controller.keepThisConflictDraft();
    const keptDraft = loadLocalDraft('user-1');

    expect(keptDraft?.draftId).not.toBe(activeDraft.draftId);
    expect(keptDraft?.draftId).not.toBe(replacementDraft.draftId);
    expect(keptDraft?.form.name).toBe('Keep Separate');
    expect(mounted.controller.persistenceState.value.status).toBe('synced');
    mounted.unmount();
  });

  test('keeps local contents under a new key when the created deck was deleted', async () => {
    const mounted = await mountController('/my/decks/new');
    mounted.controller.deck.setDeckName('Keep After Created Deck Deletion');
    await flushAsyncEditorWork();
    const activeDraft = loadLocalDraft('user-1');
    if (!activeDraft) throw new Error('Expected an active local draft');
    const storage = createDeckEditorLocalDraftStorage();
    const retirement = await storage.retire(
      'user-1',
      activeDraft.draftId,
      'deck-deleted-elsewhere',
      { kind: 'draft', revision: activeDraft.revision },
    );
    expect(retirement.status).toBe('retired');
    dispatchDraftStorageEvent('user-1');
    fetchMyDeckByCreationKeyMock.mockResolvedValueOnce({ status: 'deleted' });

    await mounted.controller.openCreatedConflictDeck();
    const keptDraft = loadLocalDraft('user-1');

    expect(fetchMyDeckByCreationKeyMock).toHaveBeenCalledWith(activeDraft.draftId);
    expect(mounted.router.currentRoute.value.fullPath).toBe('/my/decks/new');
    expect(keptDraft?.draftId).not.toBe(activeDraft.draftId);
    expect(keptDraft?.form.name).toBe('Keep After Created Deck Deletion');
    expect(mounted.controller.persistenceState.value.status).toBe('synced');
    expect(toastInfoMock).toHaveBeenCalledWith(
      'The created deck was deleted. This tab was kept as a new local draft.',
    );
    mounted.unmount();
  });

  test('retains a retired marker until a new local draft replaces it', async () => {
    const retiredForm = createEmptyDeckForm();
    retiredForm.name = 'Already Created';
    const activeDraft = await saveLocalDraft('user-1', retiredForm, {});
    const storage = createDeckEditorLocalDraftStorage();
    const retirement = await storage.retire(
      'user-1',
      activeDraft.draftId,
      'deck-already-created',
      { kind: 'draft', revision: activeDraft.revision },
    );
    expect(retirement.status).toBe('retired');

    const mounted = await mountController('/my/decks/new');
    await flushAsyncEditorWork();

    const retained = storage.read('user-1');
    expect(retained.status === 'loaded' ? retained.slot.kind : null).toBe('retired');
    expect(mounted.controller.localDraftRecoveryModalOpen.value).toBe(false);

    mounted.controller.deck.setDeckName('Replacement Draft');
    await flushAsyncEditorWork();

    const replacement = loadLocalDraft('user-1');
    expect(replacement?.draftId).not.toBe(activeDraft.draftId);
    expect(replacement?.form.name).toBe('Replacement Draft');
    mounted.unmount();
  });

  test('finishes creation when draft storage was confirmed empty before writes failed', async () => {
    const draftStorageKey = 'card-reader.deck-editor.new-draft.user-1';
    const originalGetItem = Storage.prototype.getItem;
    const originalSetItem = Storage.prototype.setItem;
    const originalRemoveItem = Storage.prototype.removeItem;
    const getItemSpy = vi.spyOn(Storage.prototype, 'getItem').mockImplementation(function (this: Storage, key) {
      return originalGetItem.call(this, key);
    });
    const setItemSpy = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(function (this: Storage, key, value) {
      if (key === draftStorageKey) {
        throw new DOMException('Writes blocked', 'SecurityError');
      }
      originalSetItem.call(this, key, value);
    });
    const removeItemSpy = vi.spyOn(Storage.prototype, 'removeItem').mockImplementation(function (this: Storage, key) {
      if (key === draftStorageKey) {
        throw new DOMException('Removal blocked', 'SecurityError');
      }
      originalRemoveItem.call(this, key);
    });
    const mounted = await mountController('/my/decks/new');
    mounted.controller.openHero();
    mounted.controller.deck.handleGalleryAction(buildHero('hero-new', 'New Hero'));
    mounted.controller.deck.setDeckName('Memory Only');
    await nextTick();

    await mounted.controller.saveDeck();

    expect(createDeckMock).toHaveBeenCalledTimes(1);
    expect(mounted.router.currentRoute.value.fullPath).toBe(
      '/my/decks/deck-new/edit?editor_mode=cards',
    );

    getItemSpy.mockRestore();
    setItemSpy.mockRestore();
    removeItemSpy.mockRestore();
    mounted.unmount();
  });

  test('confirmed creation outranks an unreadable stale browser draft', async () => {
    const staleForm = createEmptyDeckForm();
    staleForm.name = 'Hidden Older Draft';
    await saveLocalDraft('user-1', staleForm, {});
    const draftStorageKey = 'card-reader.deck-editor.new-draft.user-1';
    const originalGetItem = Storage.prototype.getItem;
    const originalSetItem = Storage.prototype.setItem;
    const originalRemoveItem = Storage.prototype.removeItem;
    const getItemSpy = vi.spyOn(Storage.prototype, 'getItem').mockImplementation(function (this: Storage, key) {
      if (key === draftStorageKey) {
        throw new DOMException('Reads blocked', 'SecurityError');
      }
      return originalGetItem.call(this, key);
    });
    const setItemSpy = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(function (this: Storage, key, value) {
      if (key === draftStorageKey) {
        throw new DOMException('Writes blocked', 'SecurityError');
      }
      originalSetItem.call(this, key, value);
    });
    const removeItemSpy = vi.spyOn(Storage.prototype, 'removeItem').mockImplementation(function (this: Storage, key) {
      if (key === draftStorageKey) {
        throw new DOMException('Removal blocked', 'SecurityError');
      }
      originalRemoveItem.call(this, key);
    });
    const mounted = await mountController('/my/decks/new');
    mounted.controller.openHero();
    mounted.controller.deck.handleGalleryAction(buildHero('hero-new', 'New Hero'));
    mounted.controller.deck.setDeckName('Created While Storage Was Hidden');
    await nextTick();

    await mounted.controller.saveDeck();

    expect(createDeckMock).toHaveBeenCalledTimes(1);
    expect(mounted.router.currentRoute.value.fullPath).toBe(
      '/my/decks/deck-new/edit?editor_mode=cards',
    );

    getItemSpy.mockRestore();
    setItemSpy.mockRestore();
    removeItemSpy.mockRestore();
    expect(loadLocalDraft('user-1')?.form.name).toBe(
      'Hidden Older Draft',
    );

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
