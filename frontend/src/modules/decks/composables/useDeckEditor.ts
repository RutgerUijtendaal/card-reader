import { onMounted, ref, computed } from 'vue';
import { toast } from 'vue-sonner';
import { useRoute, useRouter } from 'vue-router';
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
  const cardLookup = ref<Record<string, DeckCardSummary>>({});
  const deckBuildingRules = ref(fallbackDeckBuildingRules());
  const backLink = computed(() => buildDeckEditorReturnLocation(route.query));
  const backLabel = computed(() => `Back to ${getDeckEditorReturnLabel(route.query)}`);

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
    try {
      const record = await persistDeck();
      setBuilderStep('build');
      if (!deckId.value) {
        await router.replace(buildDeckEditorLocation(record.id, route.query));
      }
      toast.success('Deck saved.');
      filters.applyHeroAffinityManaPreset(deck.selectedHero.value);
    } finally {
      saving.value = false;
    }
  };

  const saveDeck = async (): Promise<void> => {
    saving.value = true;
    try {
      const record = await persistDeck();
      if (!deckId.value) {
        await router.replace(buildDeckEditorLocation(record.id, route.query));
      }
      toast.success(record.status.is_valid ? 'Deck saved.' : 'Draft saved.');
    } finally {
      saving.value = false;
    }
  };

  onMounted(async () => {
    await Promise.all([filters.loadFilters(), loadDeckRules(), loadDeck()]);
    if (builderStep.value === 'build') {
      filters.applyHeroAffinityManaPreset(deck.selectedHero.value);
    }
    await gallery.searchCards();
  });

  return {
    deckId,
    backLink,
    backLabel,
    builderStep,
    loading,
    saving,
    deckBuildingRules,
    filters,
    gallery,
    deck,
    setBuilderStep,
    lockSetup,
    saveDeck,
  };
};

export type DeckEditorController = ReturnType<typeof useDeckEditor>;
