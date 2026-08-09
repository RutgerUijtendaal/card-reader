import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue';
import { useDebounceFn, useEventListener, useLocalStorage } from '@vueuse/core';
import { toast } from 'vue-sonner';
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router';
import { fetchCard, fetchCards } from '@/domain/cards/api';
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
import type {
  DeckEditorMode,
  DeckFormEntry,
} from '@/features/decks/composables/deckEditorDraftTypes';
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

type PendingCreatedDeck = {
  record: DeckRecord;
  savedSignature: string;
  showSuccessToast: boolean;
};

type LocalDraftPresence = 'absent' | 'present' | 'unknown';

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
  const pendingCreatedDeck = ref<PendingCreatedDeck | null>(null);
  const localDraftDecisionResolved = ref(Boolean(deckId.value) || !localDraftOwnerId);
  const localDraftPersistenceFailed = ref(false);
  const focusDeckNameRequest = ref(0);
  let bypassNextUnsavedPrompt = false;
  let localDraftStorageWarningShown = false;
  let lastLocalDraftSignature = '';
  let localDraftPresence: LocalDraftPresence = localDraftOwnerId && !deckId.value
    ? 'unknown'
    : 'absent';
  let pendingDiscardConfirmation: ((confirmed: boolean) => void) | null = null;
  let pendingDiscardConfirmationPromise: Promise<boolean> | null = null;
  let filtersLoadPromise: Promise<void> | null = null;
  let deckTagsLoadPromise: Promise<boolean> | null = null;
  let localDraftResumePromise: Promise<void> | null = null;
  let lastPersistedLocalDraft: StoredDeckEditorDraft | null = null;
  const backLink = computed(() => buildDeckEditorReturnLocation(route.query));
  const backLabel = computed(() => `Back to ${getDeckEditorReturnLabel(route.query)}`);
  const autosyncEnabled = useLocalStorage('card-reader.deck-editor.autosync', false, {
    writeDefaults: true,
  });

  if (!deckId.value && localDraftOwnerId) {
    try {
      pendingLocalDraft.value = localDraftStorage.load(localDraftOwnerId);
      localDraftPresence = pendingLocalDraft.value === null ? 'absent' : 'present';
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

  const loadDeckTags = (): Promise<boolean> => {
    deckTagsLoadPromise ??= (async () => {
      try {
        deckTagCatalog.value = await fetchDeckTags();
        return true;
      } catch {
        deckTagCatalog.value = { roles: [], types: [] };
        return false;
      }
    })();
    return deckTagsLoadPromise;
  };

  const referencedLocalDraftCardIds = (): string[] => [
    ...new Set([
      ...(deck.form.hero_card_id ? [deck.form.hero_card_id] : []),
      ...deck.allCardIds.value,
    ]),
  ];

  const remapRecoveredEntries = (
    entries: DeckFormEntry[],
    redirectedCardIds: ReadonlyMap<string, string>,
  ): DeckFormEntry[] => {
    const remappedEntries: DeckFormEntry[] = [];
    const entryIndexByCardId = new Map<string, number>();
    for (const entry of entries) {
      const cardId = redirectedCardIds.get(entry.card_id) ?? entry.card_id;
      const existingIndex = entryIndexByCardId.get(cardId);
      if (existingIndex === undefined) {
        entryIndexByCardId.set(cardId, remappedEntries.length);
        remappedEntries.push({ card_id: cardId, quantity: entry.quantity });
      } else {
        const existingEntry = remappedEntries[existingIndex];
        if (existingEntry) {
          existingEntry.quantity += entry.quantity;
        }
      }
    }
    return remappedEntries;
  };

  const applyRecoveredCardRedirects = (redirectedCardIds: ReadonlyMap<string, string>): void => {
    if (redirectedCardIds.size === 0) {
      return;
    }
    deck.form.hero_card_id = redirectedCardIds.get(deck.form.hero_card_id)
      ?? deck.form.hero_card_id;
    deck.form.entries = remapRecoveredEntries(deck.form.entries, redirectedCardIds);
    for (const sideboard of deck.form.sideboards) {
      sideboard.entries = remapRecoveredEntries(sideboard.entries, redirectedCardIds);
    }
  };

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
    const refreshedCardIds = new Set<string>();
    try {
      while (true) {
        params.set('page', String(page));
        const response = await fetchCards<CardListItem>(params);
        rememberCards(response.results);
        response.results.forEach((card) => refreshedCardIds.add(card.id));
        if (response.next_page === null) {
          break;
        }
        page = response.next_page;
      }
    } catch {
      toast.error('Some local draft card details could not be refreshed.');
      return;
    }

    const unresolvedCardIds = cardIds.filter((cardId) => !refreshedCardIds.has(cardId));
    if (unresolvedCardIds.length === 0) {
      return;
    }
    const detailResults = await Promise.allSettled(
      unresolvedCardIds.map(async (cardId) => ({
        cardId,
        card: await fetchCard<CardListItem>(cardId),
      })),
    );
    const redirectedCardIds = new Map<string, string>();
    const resolvedCards: CardListItem[] = [];
    let refreshFailed = false;
    for (const result of detailResults) {
      if (result.status === 'rejected') {
        refreshFailed = true;
        continue;
      }
      resolvedCards.push(result.value.card);
      if (result.value.card.id !== result.value.cardId) {
        redirectedCardIds.set(result.value.cardId, result.value.card.id);
      }
    }
    rememberCards(resolvedCards);
    applyRecoveredCardRedirects(redirectedCardIds);
    if (refreshFailed) {
      toast.error('Some local draft card details could not be refreshed.');
    }
  };

  const reconcileRecoveredTagIds = (): void => {
    const currentTagIds = new Set([
      ...deckTagCatalog.value.roles.map((tag) => tag.id),
      ...deckTagCatalog.value.types.map((tag) => tag.id),
    ]);
    deck.setDeckTagIds(deck.form.tag_ids.filter((tagId) => currentTagIds.has(tagId)));
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
    lastPersistedLocalDraft = storedDraft;
    localDraftPresence = 'present';
    localDraftPersistenceFailed.value = false;
    shouldApplyHeroCardPreset.value = Boolean(deck.form.hero_card_id);
    editorMode.value = 'cards';

    localDraftResumePromise = (async () => {
      const [, tagsLoaded] = await Promise.all([
        loadEditorFilters(),
        loadDeckTags(),
        refreshLocalDraftCards(),
      ]);
      if (tagsLoaded) {
        reconcileRecoveredTagIds();
      }
    })();
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
    lastPersistedLocalDraft = null;
    localDraftPresence = 'absent';
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
  const creationCleanupPending = computed(() => pendingCreatedDeck.value !== null);
  const isCreating = computed(
    () => !isPublished.value && (saving.value || creationCleanupPending.value),
  );
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
      if (creationCleanupPending.value) {
        return 'Finishing';
      }
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

  const retireLocalDraftAfterCreation = (createdDeckId: string): boolean => {
    if (localDraftPresence === 'absent') {
      lastPersistedLocalDraft = null;
      localDraftPersistenceFailed.value = false;
      return true;
    }
    try {
      const retirement = localDraftStorage.retire(
        localDraftOwnerId,
        createdDeckId,
        lastPersistedLocalDraft,
      );
      lastLocalDraftSignature = '';
      lastPersistedLocalDraft = null;
      localDraftPresence = 'absent';
      localDraftPersistenceFailed.value = false;
      if (retirement === 'conflict') {
        toast.info('A different local deck draft remains available in this browser.');
      }
      return true;
    } catch {
      localDraftPersistenceFailed.value = true;
      warnLocalDraftStorageUnavailable(
        'The deck was created, but its local draft could not be retired. Click Finish to retry.',
      );
      return false;
    }
  };

  const finishCreatedDeck = async (pending: PendingCreatedDeck): Promise<boolean> => {
    if (!retireLocalDraftAfterCreation(pending.record.id)) {
      return false;
    }
    pendingCreatedDeck.value = null;
    shouldApplyHeroCardPreset.value = true;
    activateCards();
    bypassNextUnsavedPrompt = true;
    try {
      await router.replace({
        path: `/my/decks/${pending.record.id}/edit`,
        query: withDeckEditorMode(route.query, 'cards'),
        hash: route.hash,
      });
    } finally {
      bypassNextUnsavedPrompt = false;
    }
    markSavedPayload(pending.savedSignature);
    if (pending.showSuccessToast) {
      toast.success('Deck created.');
    }
    return true;
  };

  const saveDeck = async (options: { silent?: boolean } = {}): Promise<void> => {
    if (saving.value) {
      return;
    }
    if (pendingCreatedDeck.value) {
      saving.value = true;
      manualSaving.value = true;
      try {
        await finishCreatedDeck(pendingCreatedDeck.value);
      } finally {
        saving.value = false;
        manualSaving.value = false;
      }
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
        pendingCreatedDeck.value = {
          record,
          savedSignature,
          showSuccessToast: !options.silent,
        };
        await finishCreatedDeck(pendingCreatedDeck.value);
        return;
      }
      markSavedPayload(savedSignature);
      if (!options.silent) {
        toast.success(
          record.status.is_valid ? 'Deck saved.' : 'Draft saved.',
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
    lastPersistedLocalDraft = null;
    localDraftPresence = 'absent';
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
          lastPersistedLocalDraft = null;
          localDraftPresence = 'absent';
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
      const storedDraft = localDraftStorage.save(localDraftOwnerId, deck.form, cardLookup.value);
      lastLocalDraftSignature = localDraftContentSignature(storedDraft);
      lastPersistedLocalDraft = storedDraft;
      localDraftPresence = 'present';
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
    creationCleanupPending,
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
