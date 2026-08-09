import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue';
import { useDebounceFn, useEventListener, useLocalStorage } from '@vueuse/core';
import { toast } from 'vue-sonner';
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router';
import { fetchCard, fetchCards } from '@/domain/cards/api';
import type { CardListItem } from '@/domain/cards/types';
import { MANAGEMENT_CARD_LIFECYCLE_FILTER } from '@/domain/cards/utils/filters/cardLifecycle';
import {
  fetchDeckRulesMetadata,
  fetchDeckTags,
  fetchMyDeck,
  fetchMyDeckByCreationKey,
  updateDeck,
} from '@/domain/decks/api';
import { useDeckEditorDraft } from '@/features/decks/composables/useDeckEditorDraft';
import type {
  DeckEditorMode,
  DeckFormEntry,
} from '@/features/decks/composables/deckEditorDraftTypes';
import { useDeckEditorFilters } from '@/features/decks/composables/useDeckEditorFilters';
import { useDeckEditorGallery } from '@/features/decks/composables/useDeckEditorGallery';
import { useDeckEditorLocalDraft } from '@/features/decks/composables/useDeckEditorLocalDraft';
import { useDeckEditorPublication } from '@/features/decks/composables/useDeckEditorPublication';
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
import { isDeckMutationLocked } from '@/features/decks/utils/deckEditorLifecycle';

export const useDeckEditor = () => {
  const route = useRoute();
  const router = useRouter();
  const auth = useAuthStore();
  const localDraftOwnerId = auth.user?.id ?? '';

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
  const recoveryActionPending = ref(false);
  const focusDeckNameRequest = ref(0);
  let bypassNextUnsavedPrompt = false;
  let pendingDiscardConfirmation: ((confirmed: boolean) => void) | null = null;
  let pendingDiscardConfirmationPromise: Promise<boolean> | null = null;
  let filtersLoadPromise: Promise<void> | null = null;
  let deckTagsLoadPromise: Promise<boolean> | null = null;
  let localDraftResumePromise: Promise<void> | null = null;
  const backLink = computed(() => buildDeckEditorReturnLocation(route.query));
  const backLabel = computed(() => `Back to ${getDeckEditorReturnLabel(route.query)}`);
  const autosyncEnabled = useLocalStorage('card-reader.deck-editor.autosync', false, {
    writeDefaults: true,
  });

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

  const payloadSignature = computed(() => JSON.stringify(deck.buildPayload()));
  const emptyLocalDraftPayloadSignature = payloadSignature.value;
  if (!isPublished.value) {
    savedPayloadSignature.value = emptyLocalDraftPayloadSignature;
  }
  const localDraft = useDeckEditorLocalDraft({
    ownerId: localDraftOwnerId,
    enabled: !isPublished.value && Boolean(localDraftOwnerId),
    form: deck.form,
    cardLookup,
    contentSignature: payloadSignature,
    emptyContentSignature: emptyLocalDraftPayloadSignature,
  });
  const localDraftRecoveryModalOpen = computed(
    () => localDraft.pendingRecovery.value !== null,
  );
  const pendingLocalDraft = localDraft.pendingRecovery;

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
    if (isMutationLocked.value) return;
    editorMode.value = 'details';
    syncEditorModeRoute('details');
  };

  const openCards = (): void => {
    if (isMutationLocked.value) return;
    activateCards();
    syncEditorModeRoute('cards');
  };

  const beginHeroChange = (): void => {
    if (isMutationLocked.value) return;
    heroReturnMode.value = editorMode.value === 'cards' ? 'cards' : 'details';
    originalHeroId.value = deck.form.hero_card_id;
    filters.resetFilters();
    editorMode.value = 'hero';
  };

  const openHero = (): void => {
    if (isMutationLocked.value) return;
    if (isPublished.value) {
      beginHeroChange();
      return;
    }
    filters.resetFilters();
    originalHeroId.value = null;
    editorMode.value = 'hero';
  };

  const applyHeroChange = (): void => {
    if (isMutationLocked.value) return;
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
    if (isMutationLocked.value) return;
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

  const refreshRecoveredDraftDependencies = async (): Promise<void> => {
    const [filtersResult, tagsResult, cardsResult] = await Promise.allSettled([
      loadEditorFilters(),
      loadDeckTags(),
      refreshLocalDraftCards(),
    ]);
    if (tagsResult.status === 'fulfilled' && tagsResult.value) {
      reconcileRecoveredTagIds();
    }
    if (
      filtersResult.status === 'rejected'
      || tagsResult.status === 'rejected'
      || cardsResult.status === 'rejected'
    ) {
      toast.error('Some local draft details could not be refreshed.');
    }
  };

  const resumeLocalDraft = async (reconcilePendingCreation = true): Promise<void> => {
    const storedDraft = pendingLocalDraft.value;
    if (storedDraft === null) {
      return;
    }
    deck.hydrateFromLocalDraft(storedDraft.form);
    cardLookup.value = { ...cardLookup.value, ...storedDraft.cards };
    localDraft.beginRecoveredDraft(storedDraft);
    shouldApplyHeroCardPreset.value = Boolean(deck.form.hero_card_id);
    editorMode.value = 'cards';

    localDraftResumePromise = refreshRecoveredDraftDependencies();
    try {
      await localDraftResumePromise;
      if (editorMode.value === 'cards') {
        activateCards();
      }
    } finally {
      localDraft.completeRecovery();
      if (reconcilePendingCreation && storedDraft.pendingCreateAttempt) {
        await publication.recoverPendingAttempt(storedDraft.pendingCreateAttempt);
      } else {
        await localDraft.persist();
      }
      localDraftResumePromise = null;
    }
  };

  const discardPendingLocalDraft = async (): Promise<void> => {
    const storedDraft = pendingLocalDraft.value;
    if (!storedDraft || recoveryActionPending.value) return;
    recoveryActionPending.value = true;
    try {
      if (storedDraft.pendingCreateAttempt) {
        const resolution = await publication.recoverPendingAttempt(
          storedDraft.pendingCreateAttempt,
        );
        if (resolution === 'created' || resolution === 'deleted') return;
        await resumeLocalDraft(false);
        toast.info('The previous Create request is still unconfirmed. Retry it before discarding.');
        return;
      }
      await localDraft.discardRecovery();
    } finally {
      recoveryActionPending.value = false;
    }
  };

  watch(localDraft.recoveryConflictCandidate, (storedDraft) => {
    if (!storedDraft) return;
    deck.hydrateFromLocalDraft(storedDraft.form);
    cardLookup.value = { ...cardLookup.value, ...storedDraft.cards };
    shouldApplyHeroCardPreset.value = Boolean(deck.form.hero_card_id);
    editorMode.value = 'cards';
    recoveryActionPending.value = true;
    void (async () => {
      try {
        await refreshRecoveredDraftDependencies();
        activateCards();
        if (storedDraft.pendingCreateAttempt) {
          await publication.recoverPendingAttempt(storedDraft.pendingCreateAttempt);
        }
      } finally {
        recoveryActionPending.value = false;
      }
    })();
  });

  watch(localDraft.conflict, (currentConflict) => {
    if (currentConflict) {
      discardLocalDraftModalOpen.value = false;
    }
  });

  const persistDeck = async (): Promise<DeckRecord> =>
    await updateDeck(deckId.value, deck.buildPayload());

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

  const hasUnsavedChanges = computed(() => savedPayloadSignature.value !== '' && payloadSignature.value !== savedPayloadSignature.value);
  const hasLocalDraft = computed(() => !isPublished.value && hasUnsavedChanges.value);
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
      if (publication.creationState.value.status === 'creating') {
        return 'Creating';
      }
      if (publication.creationState.value.status === 'unknown') {
        return 'Creation Unconfirmed';
      }
      if (localDraft.persistenceState.value.status === 'conflict') {
        return 'Draft Conflict';
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

  const finishCreatedDeck = async (
    record: DeckRecord,
    savedSignature: string,
  ): Promise<void> => {
    const reconciledSignature = reconcilePersistedTagState(record, savedSignature);
    showTagSuggestionFeedback(record);
    shouldApplyHeroCardPreset.value = true;
    activateCards();
    markSavedPayload(reconciledSignature);
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
    toast.success('Deck created.');
  };

  const finishDeletedDeckCreation = async (): Promise<void> => {
    bypassNextUnsavedPrompt = true;
    try {
      await router.replace('/my/decks');
    } finally {
      bypassNextUnsavedPrompt = false;
    }
    toast.info('This deck was already created and has since been deleted.');
  };

  const publication = useDeckEditorPublication({
    persistenceState: localDraft.persistenceState,
    draftId: localDraft.draftId,
    payloadSignature,
    buildPayload: deck.buildPayload,
    validate: validateLocalDraftForCreation,
    persistAttempt: localDraft.persist,
    retireAfterCreation: localDraft.retireAfterCreation,
    discardAfterDeletedCreation: localDraft.discardAfterDeletedCreation,
    onSuccess: async (record, attempt) => await finishCreatedDeck(record, attempt.signature),
    onDeleted: finishDeletedDeckCreation,
  });

  const isMutationLocked = computed(() => !isPublished.value && isDeckMutationLocked(
    localDraft.persistenceState.value,
    publication.creationState.value,
  ));
  const isCreating = publication.isCreating;
  const hasNonDurableUnknownAttempt = computed(() => {
    if (publication.creationState.value.status !== 'unknown') return false;
    const currentAttempt = publication.attempt.value;
    if (!currentAttempt) return true;
    return !localDraft.isCreateAttemptDurable(currentAttempt.draftId, {
      payload: currentAttempt.payload,
      signature: currentAttempt.signature,
      startedAt: currentAttempt.startedAt,
    });
  });
  const conflictActionsLocked = computed(
    () => publication.creationState.value.status !== 'idle' || recoveryActionPending.value,
  );
  const localDraftConflictModalOpen = computed(
    () => localDraft.conflict.value !== null && !conflictActionsLocked.value,
  );

  const saveDeck = async (options: { silent?: boolean } = {}): Promise<void> => {
    if (!isPublished.value) {
      if (publication.creationState.value.status === 'unknown') {
        await publication.retry();
      } else {
        await publication.create();
      }
      return;
    }
    if (saving.value) return;
    if (!options.silent) {
      autosyncFailedSignature.value = '';
    }
    saving.value = true;
    manualSaving.value = !options.silent;
    try {
      const persistedSignature = payloadSignature.value;
      const record = await persistDeck();
      const savedSignature = reconcilePersistedTagState(record, persistedSignature);
      showTagSuggestionFeedback(record);
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

  const confirmDiscardLocalDraft = async (): Promise<void> => {
    if (!discardLocalDraftModalOpen.value) return;
    discardLocalDraftModalOpen.value = false;
    if (!await localDraft.discardActiveDraft()) return;
    deck.resetLocalDraft();
    cardLookup.value = {};
    filters.resetFilters();
    shouldApplyHeroCardPreset.value = false;
    originalHeroId.value = null;
    editorMode.value = 'cards';
    markSavedPayload();
    void gallery.searchCards();
  };

  const persistLocalDraft = (): void => {
    void localDraft.persist();
  };

  const loadStoredConflictDraft = async (): Promise<void> => {
    if (conflictActionsLocked.value) return;
    const storedDraft = localDraft.loadConflictDraft();
    if (!storedDraft) return;
    deck.hydrateFromLocalDraft(storedDraft.form);
    cardLookup.value = { ...cardLookup.value, ...storedDraft.cards };
    shouldApplyHeroCardPreset.value = Boolean(deck.form.hero_card_id);
    editorMode.value = 'cards';
    try {
      await refreshRecoveredDraftDependencies();
      activateCards();
    } finally {
      localDraft.completeRecovery();
      if (storedDraft.pendingCreateAttempt) {
        await publication.recoverPendingAttempt(storedDraft.pendingCreateAttempt);
      } else {
        await localDraft.persist();
      }
    }
  };

  const keepThisConflictDraft = async (): Promise<void> => {
    if (conflictActionsLocked.value) return;
    await localDraft.overwriteConflict(false);
  };

  const discardThisConflictedTab = (): void => {
    if (conflictActionsLocked.value) return;
    if (!localDraft.discardThisTab()) return;
    deck.resetLocalDraft();
    cardLookup.value = {};
    filters.resetFilters();
    shouldApplyHeroCardPreset.value = false;
    originalHeroId.value = null;
    editorMode.value = 'cards';
    markSavedPayload();
    void gallery.searchCards();
  };

  const openCreatedConflictDeck = async (): Promise<void> => {
    if (conflictActionsLocked.value) return;
    const currentConflict = localDraft.conflict.value;
    if (currentConflict?.kind !== 'created-elsewhere') return;
    recoveryActionPending.value = true;
    try {
      const result = await fetchMyDeckByCreationKey(currentConflict.slot.marker.draftId);
      if (result.status === 'deleted') {
        if (await localDraft.overwriteConflict(true)) {
          toast.info('The created deck was deleted. This tab was kept as a new local draft.');
        }
        return;
      }
      if (result.status !== 'found') {
        toast.error('The created deck could not be confirmed. This local draft was kept.');
        return;
      }
      bypassNextUnsavedPrompt = true;
      try {
        await router.replace({
          path: `/my/decks/${result.record.id}/edit`,
          query: withDeckEditorMode(route.query, 'cards'),
          hash: route.hash,
        });
      } finally {
        bypassNextUnsavedPrompt = false;
      }
    } catch {
      toast.error('The created deck could not be confirmed. This local draft was kept.');
    } finally {
      recoveryActionPending.value = false;
    }
  };

  const keepConflictAsNewDraft = async (): Promise<void> => {
    if (conflictActionsLocked.value) return;
    await localDraft.overwriteConflict(true);
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
      const initialLoads = await Promise.allSettled([
        loadEditorFilters(),
        loadDeckRules(),
        loadDeckTags(),
        loadDeck(),
      ]);
      if (initialLoads.some((result) => result.status === 'rejected')) {
        toast.error('Some deck editor data could not be loaded.');
      }
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
    if (isCreating.value || publication.isReconciling.value) {
      return false;
    }
    if (hasNonDurableUnknownAttempt.value) {
      await publication.persistCurrentAttempt();
      if (hasNonDurableUnknownAttempt.value) return false;
    }
    if (!isPublished.value && hasUnsavedChanges.value) {
      persistLocalDraft();
    }
    return await confirmDiscardUnsavedChanges();
  });

  useEventListener(window, 'beforeunload', (event) => {
    if (!hasUnsavedChanges.value && !hasNonDurableUnknownAttempt.value) {
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
    isMutationLocked,
    creationState: publication.creationState,
    persistenceState: localDraft.persistenceState,
    hasUnsavedChanges,
    hasLocalDraft,
    localDraftPersistenceFailed: localDraft.storageUnavailable,
    canAutosync,
    isChangingHero,
    canApplyHeroChange,
    changeStatusLabel,
    autosyncEnabled,
    discardChangesModalOpen,
    discardLocalDraftModalOpen,
    localDraftRecoveryModalOpen,
    recoveryActionPending,
    localDraftConflict: localDraft.conflict,
    localDraftConflictModalOpen,
    conflictActionsLocked,
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
    loadStoredConflictDraft,
    keepThisConflictDraft,
    discardThisConflictedTab,
    openCreatedConflictDeck,
    keepConflictAsNewDraft,
    requestDiscardLocalDraft,
    confirmDiscardLocalDraft,
    cancelDiscardLocalDraft,
    confirmDiscardChanges: () => resolveDiscardChangesModal(true),
    cancelDiscardChanges: () => resolveDiscardChangesModal(false),
  };
};

export type DeckEditorController = ReturnType<typeof useDeckEditor>;
