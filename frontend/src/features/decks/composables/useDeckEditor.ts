import { computed, onMounted, onUnmounted, ref, watch } from 'vue';
import { useDebounceFn, useEventListener, useLocalStorage } from '@vueuse/core';
import { toast } from 'vue-sonner';
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router';
import type { CardListItem } from '@/domain/cards/types';
import { createDeck, fetchDeckTags, fetchMyDeck, updateDeck } from '@/domain/decks/api';
import { useDeckEditorDraft, type DeckEditorMode } from '@/features/decks/composables/useDeckEditorDraft';
import { useDeckEditorFilters } from '@/features/decks/composables/useDeckEditorFilters';
import { useDeckEditorGallery } from '@/features/decks/composables/useDeckEditorGallery';
import {
  buildDeckEditorLocation,
  buildDeckEditorReturnLocation,
  getDeckEditorReturnLabel,
  getRequestedDeckEditorMode,
  withDeckEditorMode,
} from '@/domain/decks/utils/deckRouteState';
import { getDeckTagSuggestionFeedback } from '@/domain/decks/utils/deckTagSuggestionFeedback';
import type { DeckCardSummary, DeckRecord, DeckTagCatalog } from '@/domain/decks/types';
import { fallbackDeckBuildingRules, fetchDeckRulesMetadata } from '@/domain/decks/utils/deckRules';

export const useDeckEditor = () => {
  const route = useRoute();
  const router = useRouter();

  const deckId = computed(() => (typeof route.params.id === 'string' ? route.params.id : ''));
  const requestedEditorMode = deckId.value ? getRequestedDeckEditorMode(route.query) : 'details';
  const editorMode = ref<DeckEditorMode>(deckId.value ? requestedEditorMode : 'hero');
  const originalHeroId = ref<string | null>(null);
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
  let bypassNextUnsavedPrompt = false;
  let pendingDiscardConfirmation: ((confirmed: boolean) => void) | null = null;
  let pendingDiscardConfirmationPromise: Promise<boolean> | null = null;
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

  const syncEditorModeRoute = (mode: 'details' | 'cards'): void => {
    if (!deckId.value) {
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
    originalHeroId.value = deck.form.hero_card_id;
    filters.resetFilters();
    editorMode.value = 'hero';
  };

  const applyHeroChange = (): void => {
    if (originalHeroId.value === null || !deck.form.hero_card_id) {
      return;
    }
    shouldApplyHeroCardPreset.value = true;
    originalHeroId.value = null;
    openDetails();
  };

  const cancelHeroChange = (): void => {
    if (originalHeroId.value === null) {
      return;
    }
    deck.form.hero_card_id = originalHeroId.value;
    shouldApplyHeroCardPreset.value = true;
    originalHeroId.value = null;
    openDetails();
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
  const hasUnsavedChanges = computed(() => savedPayloadSignature.value !== '' && payloadSignature.value !== savedPayloadSignature.value);
  const isChangingHero = computed(() => originalHeroId.value !== null);
  const canApplyHeroChange = computed(
    () => isChangingHero.value
      && Boolean(deck.form.hero_card_id)
      && deck.form.hero_card_id !== originalHeroId.value,
  );
  const canAutosync = computed(() => editorMode.value === 'cards');
  const changeStatusLabel = computed(() => {
    if (loading.value) {
      return 'Loading';
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

  const completeInitialHeroSelection = async (): Promise<void> => {
    if (!deck.form.hero_card_id) {
      return;
    }
    if (!deck.form.name.trim()) {
      return;
    }
    if (deck.setupMessages.value.length > 0) {
      toast.error(deck.setupMessages.value[0]);
      return;
    }
    if (deck.blockingMessages.value.length > 0) {
      toast.error(deck.blockingMessages.value[0]);
      return;
    }
    saving.value = true;
    manualSaving.value = true;
    try {
      const persistedSignature = payloadSignature.value;
      const record = await persistDeck();
      const savedSignature = reconcilePersistedTagState(record, persistedSignature);
      showTagSuggestionFeedback(record);
      openDetails();
      if (!deckId.value) {
        bypassNextUnsavedPrompt = true;
        try {
          await router.replace(buildDeckEditorLocation(record.id, route.query));
        } finally {
          bypassNextUnsavedPrompt = false;
        }
      }
      markSavedPayload(savedSignature);
      toast.success('Deck saved.');
      shouldApplyHeroCardPreset.value = true;
    } finally {
      saving.value = false;
      manualSaving.value = false;
    }
  };

  const saveDeck = async (options: { silent?: boolean } = {}): Promise<void> => {
    if (saving.value) {
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
      const savedSignature = reconcilePersistedTagState(record, persistedSignature);
      showTagSuggestionFeedback(record);
      if (!deckId.value) {
        bypassNextUnsavedPrompt = true;
        try {
          await router.replace(buildDeckEditorLocation(record.id, route.query));
        } finally {
          bypassNextUnsavedPrompt = false;
        }
      }
      markSavedPayload(savedSignature);
      if (!options.silent) {
        toast.success(record.status.is_valid ? 'Deck saved.' : 'Draft saved.');
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
      await Promise.all([filters.loadFilters(), loadDeckRules(), loadDeckTags(), loadDeck()]);
      markSavedPayload();
      if (editorMode.value === 'hero') {
        await gallery.searchCards();
      } else if (editorMode.value === 'cards') {
        activateCards();
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
    return await confirmDiscardUnsavedChanges();
  });

  useEventListener(window, 'beforeunload', (event) => {
    if (!hasUnsavedChanges.value) {
      return;
    }
    event.preventDefault();
    event.returnValue = '';
  });

  onUnmounted(() => {
    resolveDiscardChangesModal(false);
  });
  return {
    deckId,
    backLink,
    backLabel,
    editorMode,
    loading,
    saving,
    manualSaving,
    hasUnsavedChanges,
    canAutosync,
    isChangingHero,
    canApplyHeroChange,
    changeStatusLabel,
    autosyncEnabled,
    discardChangesModalOpen,
    deckBuildingRules,
    deckTagCatalog,
    filters,
    gallery,
    deck,
    openDetails,
    openCards,
    beginHeroChange,
    applyHeroChange,
    cancelHeroChange,
    completeInitialHeroSelection,
    saveDeck,
    confirmDiscardChanges: () => resolveDiscardChangesModal(true),
    cancelDiscardChanges: () => resolveDiscardChangesModal(false),
  };
};

export type DeckEditorController = ReturnType<typeof useDeckEditor>;
