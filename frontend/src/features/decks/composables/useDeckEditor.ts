import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue';
import { useDebounceFn, useEventListener, useLocalStorage } from '@vueuse/core';
import { toast } from 'vue-sonner';
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router';
import { fetchCards } from '@/domain/cards/api';
import type { CardListItem } from '@/domain/cards/types';
import { MANAGEMENT_CARD_LIFECYCLE_FILTER } from '@/domain/cards/utils/filters/cardLifecycle';
import {
  createDeck,
  fetchDeckRulesMetadata,
  fetchDeckTags,
  fetchMyDeck,
  updateDeck,
} from '@/domain/decks/api';
import { useDeckEditorDraft } from '@/features/decks/composables/useDeckEditorDraft';
import type { DeckEditorMode } from '@/features/decks/composables/deckEditorDraftTypes';
import { useDeckEditorFilters } from '@/features/decks/composables/useDeckEditorFilters';
import { useDeckEditorGallery } from '@/features/decks/composables/useDeckEditorGallery';
import {
  buildDeckEditorReturnLocation,
  getDeckEditorReturnLabel,
  getRequestedDeckEditorMode,
  withDeckEditorMode,
} from '@/domain/decks/utils/deckRouteState';
import { getDeckTagSuggestionFeedback } from '@/domain/decks/utils/deckTagSuggestionFeedback';
import type { DeckCardSummary, DeckRecord, DeckTagCatalog } from '@/domain/decks/types';
import { fallbackDeckBuildingRules } from '@/domain/decks/utils/deckRules';
import { useAuthStore } from '@/domain/session/store';
import {
  buildStoredDeckEditorDraft,
  createDeckEditorLocalDraftStorage,
  type StoredDeckEditorDraft,
} from '@/features/decks/utils/deckEditorLocalDraftStorage';

export const useDeckEditor = () => {
  const route = useRoute();
  const router = useRouter();
  const auth = useAuthStore();
  const localDraftOwnerId = auth.user?.id ?? '';
  const localDraftStorage = createDeckEditorLocalDraftStorage();

  const deckId = computed(() => (typeof route.params.id === 'string' ? route.params.id : ''));
  const isPublished = computed(() => Boolean(deckId.value));
  const requestedEditorMode = deckId.value ? getRequestedDeckEditorMode(route.query) : 'details';
  const editorMode = ref<DeckEditorMode>(deckId.value ? requestedEditorMode : 'cards');
  const originalHeroId = ref<string | null>(null);
  const heroReturnMode = ref<'details' | 'cards'>('details');
  const shouldApplyHeroCardPreset = ref(Boolean(deckId.value));
  const loading = ref(Boolean(deckId.value));
  const saving = ref(false);
  const manualSaving = ref(false);
  const cardLookup = ref<Record<string, DeckCardSummary>>({});
  const deckBuildingRules = ref(fallbackDeckBuildingRules());
  const deckTagCatalog = ref<DeckTagCatalog>({ roles: [], types: [] });
  const savedPayloadSignature = ref('');
  const autosyncFailedSignature = ref('');
  const discardChangesModalOpen = ref(false);
  const discardLocalDraftModalOpen = ref(false);
  const localDraftRecoveryModalOpen = ref(false);
  const pendingLocalDraft = ref<StoredDeckEditorDraft | null>(null);
  const localDraftDecisionResolved = ref(Boolean(deckId.value) || !localDraftOwnerId);
  const localDraftPersistenceFailed = ref(false);
  const focusDeckNameRequest = ref(0);
  let bypassNextUnsavedPrompt = false;
  let localDraftStorageWarningShown = false;
  let lastLocalDraftSignature = '';
  let pendingDiscardConfirmation: ((confirmed: boolean) => void) | null = null;
  let pendingDiscardConfirmationPromise: Promise<boolean> | null = null;
  let filtersLoadPromise: Promise<void> | null = null;
  let localDraftResumePromise: Promise<void> | null = null;
  const backLink = computed(() => buildDeckEditorReturnLocation(route.query));
  const backLabel = computed(() => `Back to ${getDeckEditorReturnLabel(route.query)}`);
  const autosyncEnabled = useLocalStorage('card-reader.deck-editor.autosync', false, {
    writeDefaults: true,
  });

  if (!deckId.value && localDraftOwnerId) {
    try {
      pendingLocalDraft.value = localDraftStorage.load(localDraftOwnerId);
      localDraftRecoveryModalOpen.value = pendingLocalDraft.value !== null;
      localDraftDecisionResolved.value = pendingLocalDraft.value === null;
    } catch {
      localDraftDecisionResolved.value = true;
      localDraftPersistenceFailed.value = true;
      localDraftStorageWarningShown = true;
      toast.error('Local draft recovery is unavailable in this browser.');
    }
  }

  const rememberCards = (cards: CardListItem[]): void => {
    const nextLookup = { ...cardLookup.value };
    for (const card of cards) {
      nextLookup[card.id] = {
        ...card,
      };
    }
    cardLookup.value = nextLookup;
  };

  const deck = useDeckEditorDraft({
    editorMode,
    cardLookup,
    deckBuildingRules,
    rememberCards,
  });
  const filters = useDeckEditorFilters({
    deckCardIds: deck.allCardIds,
    editorMode,
  });
  const gallery = useDeckEditorGallery({
    filtersLoaded: filters.filtersLoaded,
    buildSearchParams: filters.buildSearchParams,
    selectionState: filters.selectionState,
    currentDeckOnly: filters.currentDeckOnly,
    currentDeckCardIds: filters.currentDeckCardIds,
    editorMode,
    sort: filters.effectiveSort,
    cardScale: filters.cardScale,
    rememberCards,
  });

  const loadEditorFilters = (): Promise<void> => {
    filtersLoadPromise ??= filters.loadFilters();
    return filtersLoadPromise;
  };

  const syncEditorModeRoute = (mode: 'details' | 'cards'): void => {
    if (!isPublished.value) {
      return;
    }
    void router.replace({
      path: route.path,
      query: withDeckEditorMode(route.query, mode),
      hash: route.hash,
    });
  };

  const activateCards = (): void => {
    editorMode.value = 'cards';
    if (shouldApplyHeroCardPreset.value) {
      filters.applyHeroAffinityManaPreset(deck.selectedHero.value);
      shouldApplyHeroCardPreset.value = false;
    }
  };

  const openDetails = (): void => {
    editorMode.value = 'details';
    syncEditorModeRoute('details');
  };

  const openCards = (): void => {
    activateCards();
    syncEditorModeRoute('cards');
  };

  const beginHeroChange = (): void => {
    heroReturnMode.value = editorMode.value === 'cards' ? 'cards' : 'details';
    originalHeroId.value = deck.form.hero_card_id;
    filters.resetFilters();
    editorMode.value = 'hero';
  };

  const openHero = (): void => {
    if (isPublished.value) {
      beginHeroChange();
      return;
    }
    filters.resetFilters();
    originalHeroId.value = null;
    editorMode.value = 'hero';
  };

  const applyHeroChange = (): void => {
    if (originalHeroId.value === null || !deck.form.hero_card_id) {
      return;
    }
    shouldApplyHeroCardPreset.value = true;
    originalHeroId.value = null;
    if (heroReturnMode.value === 'cards') {
      openCards();
    } else {
      openDetails();
    }
  };

  const cancelHeroChange = (): void => {
    if (originalHeroId.value === null) {
      return;
    }
    deck.form.hero_card_id = originalHeroId.value;
    shouldApplyHeroCardPreset.value = true;
    originalHeroId.value = null;
    if (heroReturnMode.value === 'cards') {
      openCards();
    } else {
      openDetails();
    }
  };

  const hydrateFromDeck = (record: DeckRecord): void => {
    deck.hydrateFromDeck(record);
  };

  const loadDeck = async (): Promise<void> => {
    if (!deckId.value) return;
    const record = await fetchMyDeck(deckId.value);
    hydrateFromDeck(record);
  };

  const loadDeckRules = async (): Promise<void> => {
    try {
      deckBuildingRules.value = (await fetchDeckRulesMetadata()).default_rules;
    } catch {
      deckBuildingRules.value = fallbackDeckBuildingRules();
    }
  };

  const loadDeckTags = async (): Promise<void> => {
    try {
      deckTagCatalog.value = await fetchDeckTags();
    } catch {
      deckTagCatalog.value = { roles: [], types: [] };
    }
  };

  const referencedLocalDraftCardIds = (): string[] => [
    ...new Set([
      ...(deck.form.hero_card_id ? [deck.form.hero_card_id] : []),
      ...deck.allCardIds.value,
    ]),
  ];

  const refreshLocalDraftCards = async (): Promise<void> => {
    const cardIds = referencedLocalDraftCardIds();
    if (cardIds.length === 0) {
      return;
    }
    const params = new URLSearchParams({
      lifecycle_status: MANAGEMENT_CARD_LIFECYCLE_FILTER,
      page_size: '100',
      show_groups: 'false',
    });
    for (const cardId of cardIds) {
      params.append('card_ids', cardId);
    }
    let page = 1;
    try {
      while (true) {
        params.set('page', String(page));
        const response = await fetchCards<CardListItem>(params);
        rememberCards(response.results);
        if (response.next_page === null) {
          return;
        }
        page = response.next_page;
      }
    } catch {
      toast.error('Some local draft card details could not be refreshed.');
    }
  };

  const localDraftContentSignature = (draft: StoredDeckEditorDraft): string =>
    JSON.stringify({
      version: draft.version,
      ownerId: draft.ownerId,
      form: draft.form,
      cards: draft.cards,
    });

  const warnLocalDraftStorageUnavailable = (message: string): void => {
    if (localDraftStorageWarningShown) {
      return;
    }
    localDraftStorageWarningShown = true;
    toast.error(message);
  };

  const clearLocalDraftStorage = (): boolean => {
    try {
      localDraftStorage.clear(localDraftOwnerId);
      return true;
    } catch {
      warnLocalDraftStorageUnavailable('The local deck draft could not be removed from this browser.');
      return false;
    }
  };

  const resumeLocalDraft = async (): Promise<void> => {
    const storedDraft = pendingLocalDraft.value;
    if (storedDraft === null) {
      return;
    }
    deck.hydrateFromLocalDraft(storedDraft.form);
    cardLookup.value = { ...cardLookup.value, ...storedDraft.cards };
    pendingLocalDraft.value = null;
    localDraftRecoveryModalOpen.value = false;
    localDraftDecisionResolved.value = true;
    lastLocalDraftSignature = localDraftContentSignature(storedDraft);
    localDraftPersistenceFailed.value = false;
    shouldApplyHeroCardPreset.value = Boolean(deck.form.hero_card_id);
    editorMode.value = 'cards';

    localDraftResumePromise = Promise.all([
      loadEditorFilters(),
      refreshLocalDraftCards(),
    ]).then(() => undefined);
    try {
      await localDraftResumePromise;
      if (editorMode.value === 'cards') {
        activateCards();
      }
    } finally {
      localDraftResumePromise = null;
    }
  };

  const discardPendingLocalDraft = (): void => {
    if (!clearLocalDraftStorage()) {
      return;
    }
    pendingLocalDraft.value = null;
    localDraftRecoveryModalOpen.value = false;
    localDraftDecisionResolved.value = true;
    lastLocalDraftSignature = '';
    localDraftPersistenceFailed.value = false;
  };

  const persistDeck = async (): Promise<DeckRecord> => {
    const payload = deck.buildPayload();
    if (deckId.value) {
      return await updateDeck(deckId.value, payload);
    }
    return await createDeck(payload);
  };

  const reconcilePersistedTagState = (record: DeckRecord, persistedSignature: string): string => {
    if (payloadSignature.value !== persistedSignature) {
      return persistedSignature;
    }
    if (record.tags !== undefined) {
      deck.setDeckTagIds(record.tags.map((tag) => tag.id));
    }
    if (record.pending_tag_suggestions !== undefined) {
      deck.setSuggestedTypeLabels(record.pending_tag_suggestions.map((suggestion) => suggestion.label));
    }
    return payloadSignature.value;
  };

  const showTagSuggestionFeedback = (record: DeckRecord): void => {
    const feedback = getDeckTagSuggestionFeedback(record.tag_suggestion_results);
    if (feedback) {
      toast.info(feedback);
    }
  };

  const payloadSignature = computed(() => JSON.stringify(deck.buildPayload()));
  const emptyLocalDraftPayloadSignature = payloadSignature.value;
  if (!isPublished.value) {
    savedPayloadSignature.value = emptyLocalDraftPayloadSignature;
  }
  const hasUnsavedChanges = computed(() => savedPayloadSignature.value !== '' && payloadSignature.value !== savedPayloadSignature.value);
  const hasLocalDraft = computed(() => !isPublished.value && hasUnsavedChanges.value);
  const isCreating = computed(() => !isPublished.value && saving.value);
  const isChangingHero = computed(() => originalHeroId.value !== null);
  const canApplyHeroChange = computed(
    () => isChangingHero.value
      && Boolean(deck.form.hero_card_id)
      && deck.form.hero_card_id !== originalHeroId.value,
  );
  const canAutosync = computed(() => isPublished.value && editorMode.value === 'cards');
  const changeStatusLabel = computed(() => {
    if (loading.value) {
      return 'Loading';
    }
    if (!isPublished.value) {
      if (saving.value) {
        return 'Creating';
      }
      return hasLocalDraft.value ? 'Local Draft' : 'Not Created';
    }
    if (saving.value) {
      return autosyncEnabled.value && canAutosync.value ? 'Autosyncing' : 'Saving';
    }
    if (hasUnsavedChanges.value) {
      if (autosyncFailedSignature.value === payloadSignature.value) {
        return 'Autosync Paused';
      }
      return autosyncEnabled.value && canAutosync.value ? 'Queued' : 'Unsaved';
    }
    return 'Saved';
  });

  const markSavedPayload = (signature = payloadSignature.value): void => {
    savedPayloadSignature.value = signature;
    autosyncFailedSignature.value = '';
  };

  const validateLocalDraftForCreation = async (): Promise<boolean> => {
    const missingHero = !deck.form.hero_card_id;
    const missingName = !deck.form.name.trim();
    if (missingHero) {
      openHero();
      toast.error(missingName
        ? 'Choose a hero and name your deck before creating it.'
        : 'Choose a hero before creating your deck.');
      return false;
    }
    if (missingName) {
      openDetails();
      await nextTick();
      focusDeckNameRequest.value += 1;
      toast.error('Name your deck before creating it.');
      return false;
    }
    if (deck.form.sideboards.some((sideboard) => !sideboard.name.trim())) {
      toast.error('Each sideboard needs a name.');
      return false;
    }
    if (deck.blockingMessages.value.length > 0) {
      toast.error(deck.blockingMessages.value[0]);
      return false;
    }
    return true;
  };

  const saveDeck = async (options: { silent?: boolean } = {}): Promise<void> => {
    if (saving.value) {
      return;
    }
    const creating = !isPublished.value;
    if (creating && !await validateLocalDraftForCreation()) {
      return;
    }
    if (!options.silent) {
      autosyncFailedSignature.value = '';
    }
    saving.value = true;
    manualSaving.value = !options.silent;
    try {
      const persistedSignature = payloadSignature.value;
      const record = await persistDeck();
      if (creating) {
        localDraftDecisionResolved.value = false;
      }
      const savedSignature = reconcilePersistedTagState(record, persistedSignature);
      showTagSuggestionFeedback(record);
      if (creating) {
        clearLocalDraftStorage();
        lastLocalDraftSignature = '';
        localDraftPersistenceFailed.value = false;
        shouldApplyHeroCardPreset.value = true;
        activateCards();
        bypassNextUnsavedPrompt = true;
        try {
          await router.replace({
            path: `/my/decks/${record.id}/edit`,
            query: withDeckEditorMode(route.query, 'cards'),
            hash: route.hash,
          });
        } finally {
          bypassNextUnsavedPrompt = false;
        }
      }
      markSavedPayload(savedSignature);
      if (!options.silent) {
        toast.success(
          creating
            ? 'Deck created.'
            : record.status.is_valid
              ? 'Deck saved.'
              : 'Draft saved.',
        );
      }
    } finally {
      saving.value = false;
      manualSaving.value = false;
    }
  };

  const confirmDiscardUnsavedChanges = async (): Promise<boolean> => {
    if (!hasUnsavedChanges.value) {
      return true;
    }
    if (pendingDiscardConfirmationPromise) {
      return await pendingDiscardConfirmationPromise;
    }
    discardChangesModalOpen.value = true;
    pendingDiscardConfirmationPromise = new Promise<boolean>((resolve) => {
      pendingDiscardConfirmation = resolve;
    });
    return await pendingDiscardConfirmationPromise;
  };

  const resolveDiscardChangesModal = (confirmed: boolean): void => {
    discardChangesModalOpen.value = false;
    pendingDiscardConfirmation?.(confirmed);
    pendingDiscardConfirmation = null;
    pendingDiscardConfirmationPromise = null;
  };

  const requestDiscardLocalDraft = (): void => {
    if (hasLocalDraft.value) {
      discardLocalDraftModalOpen.value = true;
    }
  };

  const cancelDiscardLocalDraft = (): void => {
    discardLocalDraftModalOpen.value = false;
  };

  const confirmDiscardLocalDraft = (): void => {
    if (!clearLocalDraftStorage()) {
      return;
    }
    lastLocalDraftSignature = '';
    localDraftPersistenceFailed.value = false;
    deck.resetLocalDraft();
    cardLookup.value = {};
    filters.resetFilters();
    shouldApplyHeroCardPreset.value = false;
    originalHeroId.value = null;
    editorMode.value = 'cards';
    discardLocalDraftModalOpen.value = false;
    markSavedPayload();
    void gallery.searchCards();
  };

  const persistLocalDraft = (): boolean => {
    if (
      isPublished.value
      || !localDraftOwnerId
      || !localDraftDecisionResolved.value
    ) {
      return true;
    }
    if (payloadSignature.value === emptyLocalDraftPayloadSignature) {
      if (lastLocalDraftSignature) {
        if (clearLocalDraftStorage()) {
          lastLocalDraftSignature = '';
          localDraftPersistenceFailed.value = false;
        } else {
          localDraftPersistenceFailed.value = true;
          return false;
        }
      }
      return true;
    }
    const draft = buildStoredDeckEditorDraft(
      localDraftOwnerId,
      deck.form,
      cardLookup.value,
    );
    const signature = localDraftContentSignature(draft);
    if (signature === lastLocalDraftSignature) {
      localDraftPersistenceFailed.value = false;
      return true;
    }
    try {
      localDraftStorage.save(localDraftOwnerId, deck.form, cardLookup.value);
      lastLocalDraftSignature = signature;
      localDraftPersistenceFailed.value = false;
      return true;
    } catch {
      localDraftPersistenceFailed.value = true;
      warnLocalDraftStorageUnavailable('This deck could not be saved to local browser storage.');
      return false;
    }
  };

  const autosyncDeck = useDebounceFn(async () => {
    if (
      !autosyncEnabled.value
      || !canAutosync.value
      || !hasUnsavedChanges.value
      || saving.value
      || loading.value
      || autosyncFailedSignature.value === payloadSignature.value
    ) {
      return;
    }
    const attemptedSignature = payloadSignature.value;
    try {
      await saveDeck({ silent: true });
    } catch {
      autosyncFailedSignature.value = attemptedSignature;
      toast.error('Autosync failed. Changes are still unsaved.');
    }
  }, 900);

  onMounted(async () => {
    try {
      await Promise.all([loadEditorFilters(), loadDeckRules(), loadDeckTags(), loadDeck()]);
      if (localDraftResumePromise) {
        await localDraftResumePromise;
      }
      if (isPublished.value) {
        markSavedPayload();
      }
      if (editorMode.value === 'hero') {
        await gallery.searchCards();
      } else if (editorMode.value === 'cards') {
        activateCards();
        if (!isPublished.value) {
          await gallery.searchCards();
        }
      }
    } finally {
      loading.value = false;
    }
  });

  watch(
    () => getRequestedDeckEditorMode(route.query),
    (mode) => {
      if (!deckId.value || mode === editorMode.value) {
        return;
      }
      if (mode === 'cards') {
        activateCards();
      } else {
        editorMode.value = 'details';
      }
    },
  );

  watch(
    () => deck.form.hero_card_id,
    (heroCardId, previousHeroCardId) => {
      if (!isPublished.value && heroCardId !== previousHeroCardId) {
        shouldApplyHeroCardPreset.value = Boolean(heroCardId);
      }
    },
  );

  watch(
    [payloadSignature, () => cardLookup.value],
    persistLocalDraft,
    { deep: true, flush: 'post' },
  );

  watch(
    () => [autosyncEnabled.value, canAutosync.value, hasUnsavedChanges.value, saving.value, loading.value, payloadSignature.value] as const,
    ([autosync, canSync, dirty, isSaving, isLoading]) => {
      if (autosync && canSync && dirty && !isSaving && !isLoading) {
        void autosyncDeck();
      }
    },
  );

  onBeforeRouteLeave(async () => {
    if (bypassNextUnsavedPrompt) {
      return true;
    }
    if (isCreating.value) {
      return false;
    }
    if (!isPublished.value && hasUnsavedChanges.value) {
      persistLocalDraft();
    }
    return await confirmDiscardUnsavedChanges();
  });

  useEventListener(window, 'beforeunload', (event) => {
    if (!hasUnsavedChanges.value) {
      return;
    }
    persistLocalDraft();
    event.preventDefault();
    event.returnValue = '';
  });

  onUnmounted(() => {
    resolveDiscardChangesModal(false);
  });
  return {
    deckId,
    isPublished,
    backLink,
    backLabel,
    editorMode,
    loading,
    saving,
    manualSaving,
    isCreating,
    hasUnsavedChanges,
    hasLocalDraft,
    localDraftPersistenceFailed,
    canAutosync,
    isChangingHero,
    canApplyHeroChange,
    changeStatusLabel,
    autosyncEnabled,
    discardChangesModalOpen,
    discardLocalDraftModalOpen,
    localDraftRecoveryModalOpen,
    pendingLocalDraft,
    focusDeckNameRequest,
    deckBuildingRules,
    deckTagCatalog,
    filters,
    gallery,
    deck,
    openHero,
    openDetails,
    openCards,
    beginHeroChange,
    applyHeroChange,
    cancelHeroChange,
    saveDeck,
    resumeLocalDraft,
    discardPendingLocalDraft,
    requestDiscardLocalDraft,
    confirmDiscardLocalDraft,
    cancelDiscardLocalDraft,
    confirmDiscardChanges: () => resolveDiscardChangesModal(true),
    cancelDiscardChanges: () => resolveDiscardChangesModal(false),
  };
};

export type DeckEditorController = ReturnType<typeof useDeckEditor>;
