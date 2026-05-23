import { onMounted, ref, computed } from 'vue';
import { toast } from 'vue-sonner';
import { useRoute, useRouter } from 'vue-router';
import type { CardListItem } from '@/modules/card-detail/types';
import { createDeck, fetchMyDeck, updateDeck } from '@/modules/decks/api';
import { useDeckEditorDraft, type BuilderStep } from '@/modules/decks/composables/useDeckEditorDraft';
import { useDeckEditorFilters } from '@/modules/decks/composables/useDeckEditorFilters';
import { useDeckEditorGallery } from '@/modules/decks/composables/useDeckEditorGallery';
import type { DeckCardSummary, DeckRecord } from '@/modules/decks/types';

export const useDeckEditor = () => {
  const route = useRoute();
  const router = useRouter();

  const deckId = computed(() => (typeof route.params.id === 'string' ? route.params.id : ''));
  const builderStep = ref<BuilderStep>(deckId.value ? 'build' : 'setup');
  const loading = ref(false);
  const saving = ref(false);
  const cardLookup = ref<Record<string, DeckCardSummary>>({});

  const rememberCards = (cards: CardListItem[]): void => {
    const nextLookup = { ...cardLookup.value };
    for (const card of cards) {
      nextLookup[card.id] = {
        id: card.id,
        key: card.key,
        label: card.label,
        name: card.name,
        mana_cost: card.mana_cost,
        types: card.types,
        is_hero: card.is_hero,
        image_url: card.image_url,
      };
    }
    cardLookup.value = nextLookup;
  };

  const filters = useDeckEditorFilters();
  const deck = useDeckEditorDraft({
    builderStep,
    cardLookup,
    rememberCards,
  });
  const gallery = useDeckEditorGallery({
    filtersLoaded: filters.filtersLoaded,
    buildSearchParams: filters.buildSearchParams,
    selectionState: filters.selectionState,
    builderStep,
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

  const persistDeck = async (): Promise<DeckRecord> => {
    const payload = deck.buildPayload();
    if (deckId.value) {
      return await updateDeck(deckId.value, payload);
    }
    return await createDeck(payload);
  };

  const lockSetup = async (): Promise<void> => {
    if (deck.setupMessages.value.length > 0) {
      toast.error(deck.setupMessages.value[0]);
      return;
    }
    saving.value = true;
    try {
      const record = await persistDeck();
      setBuilderStep('build');
      if (!deckId.value) {
        await router.replace(`/my/decks/${record.id}/edit`);
      }
      toast.success('Deck saved.');
      filters.resetFilters();
    } finally {
      saving.value = false;
    }
  };

  const saveDeck = async (): Promise<void> => {
    saving.value = true;
    try {
      const record = await persistDeck();
      if (!deckId.value) {
        await router.replace(`/my/decks/${record.id}/edit`);
      }
      toast.success(record.status.is_valid ? 'Deck saved.' : 'Draft saved.');
    } finally {
      saving.value = false;
    }
  };

  onMounted(async () => {
    await Promise.all([filters.loadFilters(), loadDeck()]);
    await gallery.searchCards();
  });

  return {
    deckId,
    builderStep,
    loading,
    saving,
    filters,
    gallery,
    deck,
    setBuilderStep,
    lockSetup,
    saveDeck,
  };
};

export type DeckEditorController = ReturnType<typeof useDeckEditor>;
