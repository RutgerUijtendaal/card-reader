import { computed, onMounted, onUnmounted, ref, watch } from 'vue';
import { useDebounceFn, useEventListener, useLocalStorage } from '@vueuse/core';
import { toast } from 'vue-sonner';
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router';
import type { CardListItem } from '@/modules/card-detail/types';
import { createDeck, fetchMyDeck, updateDeck } from '@/modules/decks/api';
import { useDeckEditorDraft, type BuilderStep } from '@/modules/decks/composables/useDeckEditorDraft';
import { useDeckEditorFilters } from '@/modules/decks/composables/useDeckEditorFilters';
import { useDeckEditorGallery } from '@/modules/decks/composables/useDeckEditorGallery';
import {
  buildDeckEditorLocation,
  buildDeckEditorReturnLocation,
  getDeckEditorReturnLabel,
} from '@/composables/decks/deckRouteState';
import type { DeckCardSummary, DeckRecord } from '@/modules/decks/types';
import { fallbackDeckBuildingRules, fetchDeckRulesMetadata } from '@/composables/decks/deckRules';

export const useDeckEditor = () => {
  const route = useRoute();
  const router = useRouter();

  const deckId = computed(() => (typeof route.params.id === 'string' ? route.params.id : ''));
  const builderStep = ref<BuilderStep>(deckId.value ? 'build' : 'setup');
  const loading = ref(false);
  const saving = ref(false);
  const manualSaving = ref(false);
  const cardLookup = ref<Record<string, DeckCardSummary>>({});
  const deckBuildingRules = ref(fallbackDeckBuildingRules());
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
    builderStep,
    cardLookup,
    deckBuildingRules,
    rememberCards,
  });
  const filters = useDeckEditorFilters({
    deckCardIds: deck.allCardIds,
    builderStep,
  });
  const gallery = useDeckEditorGallery({
    filtersLoaded: filters.filtersLoaded,
    buildSearchParams: filters.buildSearchParams,
    selectionState: filters.selectionState,
    currentDeckOnly: filters.currentDeckOnly,
    currentDeckCardIds: filters.currentDeckCardIds,
    builderStep,
    sort: filters.effectiveSort,
    cardScale: filters.cardScale,
    rememberCards,
  });

  const setBuilderStep = (step: BuilderStep): void => {
    builderStep.value = step;
  };

  const hydrateFromDeck = (record: DeckRecord): void => {
    deck.hydrateFromDeck(record);
  };

  const loadDeck = async (): Promise<void> => {
    if (!deckId.value) return;
    loading.value = true;
    try {
      const record = await fetchMyDeck(deckId.value);
      hydrateFromDeck(record);
    } finally {
      loading.value = false;
    }
  };

  const loadDeckRules = async (): Promise<void> => {
    try {
      deckBuildingRules.value = (await fetchDeckRulesMetadata()).default_rules;
    } catch {
      deckBuildingRules.value = fallbackDeckBuildingRules();
    }
  };

  const persistDeck = async (): Promise<DeckRecord> => {
    const payload = deck.buildPayload();
    if (deckId.value) {
      return await updateDeck(deckId.value, payload);
    }
    return await createDeck(payload);
  };

  const payloadSignature = computed(() => JSON.stringify(deck.buildPayload()));
  const hasUnsavedChanges = computed(() => savedPayloadSignature.value !== '' && payloadSignature.value !== savedPayloadSignature.value);
  const canAutosync = computed(() => builderStep.value === 'build');
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

  const lockSetup = async (): Promise<void> => {
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
      setBuilderStep('build');
      if (!deckId.value) {
        bypassNextUnsavedPrompt = true;
        try {
          await router.replace(buildDeckEditorLocation(record.id, route.query));
        } finally {
          bypassNextUnsavedPrompt = false;
        }
      }
      markSavedPayload(persistedSignature);
      toast.success('Deck saved.');
      filters.applyHeroAffinityManaPreset(deck.selectedHero.value);
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
      if (!deckId.value) {
        bypassNextUnsavedPrompt = true;
        try {
          await router.replace(buildDeckEditorLocation(record.id, route.query));
        } finally {
          bypassNextUnsavedPrompt = false;
        }
      }
      markSavedPayload(persistedSignature);
      if (!options.silent) {
        toast.success(record.status.is_valid ? 'Deck saved.' : 'Draft saved.');
      }
    } finally {
      saving.value = false;
      manualSaving.value = false;
    }
  };

  const confirmDiscardUnsavedChanges = async (): Promise<boolean> => {
    if (!hasUnsavedChanges.value || saving.value) {
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
    await Promise.all([filters.loadFilters(), loadDeckRules(), loadDeck()]);
    if (builderStep.value === 'build') {
      filters.applyHeroAffinityManaPreset(deck.selectedHero.value);
    }
    markSavedPayload();
    await gallery.searchCards();
  });

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
    builderStep,
    loading,
    saving,
    manualSaving,
    hasUnsavedChanges,
    canAutosync,
    changeStatusLabel,
    autosyncEnabled,
    discardChangesModalOpen,
    deckBuildingRules,
    filters,
    gallery,
    deck,
    setBuilderStep,
    lockSetup,
    saveDeck,
    confirmDiscardChanges: () => resolveDiscardChangesModal(true),
    cancelDiscardChanges: () => resolveDiscardChangesModal(false),
  };
};

export type DeckEditorController = ReturnType<typeof useDeckEditor>;
