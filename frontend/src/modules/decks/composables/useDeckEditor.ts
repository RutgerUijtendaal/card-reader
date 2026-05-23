import { useDebounceFn, useIntersectionObserver } from '@vueuse/core';
import { computed, onMounted, reactive, ref, watch } from 'vue';
import { toast } from 'vue-sonner';
import { useRoute, useRouter } from 'vue-router';
import { api } from '@/api/client';
import type { CardFiltersResponse, CardListItem, PaginatedCardsResponse } from '@/modules/card-detail/types';
import {
  buildCardFilterApiSearchParams,
  createCardFilterCatalog,
} from '@/modules/card-filters/cardFilterState';
import { useCardFilterState } from '@/modules/card-filters/useCardFilterState';
import { appendGalleryPage, createEmptyGalleryPageState, replaceGalleryPage } from '@/modules/card-search/galleryState';
import { useGalleryOptions } from '@/modules/card-search/useGalleryOptions';
import { createDeck, fetchMyDeck, updateDeck } from '@/modules/decks/api';
import type { DeckCardSummary, DeckMetadataOption, DeckRecord, DeckUpsertRequest } from '@/modules/decks/types';

export type DeckForm = {
  name: string;
  description: string;
  is_public: boolean;
  hero_card_id: string;
  entries: Array<{ card_id: string; quantity: number }>;
};

export type BuilderStep = 'setup' | 'build';

export const useDeckEditor = () => {
  const route = useRoute();
  const router = useRouter();

  const deckId = computed(() => (typeof route.params.id === 'string' ? route.params.id : ''));
  const builderStep = ref<BuilderStep>(deckId.value ? 'build' : 'setup');
  const loading = ref(false);
  const saving = ref(false);
  const filtersLoaded = ref(false);
  const filters = ref<CardFiltersResponse>({
    keywords: [],
    tags: [],
    symbols: [],
    types: [],
  });
  const filterCatalog = computed(() => createCardFilterCatalog(filters.value));
  const {
    query,
    keywordMatch,
    tagMatch,
    typeMatch,
    manaCostMin,
    manaCostMax,
    manaSymbolMatch,
    affinitySymbolMatch,
    devotionSymbolMatch,
    otherSymbolMatch,
    attackMin,
    attackMax,
    healthMin,
    healthMax,
    keywordIds: selectedKeywordIds,
    tagIds: selectedTagIds,
    manaTypeSymbolIds: selectedManaTypeSymbolIds,
    affinitySymbolIds: selectedAffinitySymbolIds,
    devotionSymbolIds: selectedDevotionSymbolIds,
    otherSymbolIds: selectedOtherSymbolIds,
    typeIds: selectedTypeIds,
    selectionState,
    reset: resetCardFilterState,
  } = useCardFilterState(filterCatalog);
  const galleryState = ref(createEmptyGalleryPageState<CardListItem>());
  const totalCount = computed(() => galleryState.value.count);
  const galleryCards = computed(() => galleryState.value.cards);
  const nextPage = computed(() => galleryState.value.nextPage);
  const isLoadingInitial = ref(false);
  const isLoadingPage = ref(false);
  const loadMoreSentinelRef = ref<HTMLElement | null>(null);
  const cardLookup = ref<Record<string, DeckCardSummary>>({});
  let latestSearchRequestId = 0;
  const { tooltipEnabled, cardScale } = useGalleryOptions();

  const form = reactive<DeckForm>({
    name: '',
    description: '',
    is_public: false,
    hero_card_id: '',
    entries: [],
  });

  const isSetupStep = computed(() => builderStep.value === 'setup');
  const cardHeightRem = computed(() => Number(((isSetupStep.value ? 24 : 21) * cardScale.value).toFixed(2)));
  const cardFrameWidthRem = computed(() => Number(((cardHeightRem.value * 63) / 88).toFixed(2)));
  const galleryTileWidthRem = computed(() => Number((cardFrameWidthRem.value + 1.5).toFixed(2)));
  const galleryGridStyle = computed(() => ({
    gridTemplateColumns: `repeat(auto-fill, minmax(${Math.round(galleryTileWidthRem.value * 16)}px, 1fr))`,
    justifyContent: 'start',
  }));
  const manaTypeOptions = computed(() => filterCatalog.value.manaSymbols);
  const affinityTypeOptions = computed(() => filterCatalog.value.affinitySymbols);
  const devotionTypeOptions = computed(() => filterCatalog.value.devotionSymbols);
  const otherSymbolOptions = computed(() => filterCatalog.value.otherSymbols);
  const totalMainboardCards = computed(() => form.entries.reduce((sum, entry) => sum + entry.quantity, 0));
  const selectedHero = computed(() => (form.hero_card_id ? cardLookup.value[form.hero_card_id] ?? null : null));
  const detailedEntries = computed(() =>
    form.entries
      .map((entry) => ({
        card: cardLookup.value[entry.card_id],
        quantity: entry.quantity,
      }))
      .filter((entry): entry is { card: DeckCardSummary; quantity: number } => Boolean(entry.card)),
  );
  const deckTypeCounts = computed(() => {
    const counts = new Map<string, { type: DeckMetadataOption; count: number }>();

    const addTypes = (types: DeckMetadataOption[], quantity: number): void => {
      for (const type of types) {
        const existing = counts.get(type.id);
        if (existing) {
          existing.count += quantity;
          continue;
        }
        counts.set(type.id, { type, count: quantity });
      }
    };

    if (selectedHero.value) {
      addTypes(selectedHero.value.types, 1);
    }

    for (const entry of detailedEntries.value) {
      addTypes(entry.card.types, entry.quantity);
    }

    return [...counts.values()].sort((left, right) => {
      if (right.count !== left.count) {
        return right.count - left.count;
      }
      return left.type.label.localeCompare(right.type.label);
    });
  });
  const headerDeckTypeCounts = computed(() => deckTypeCounts.value.slice(0, 4));
  const remainingDeckTypeCount = computed(() => Math.max(deckTypeCounts.value.length - headerDeckTypeCounts.value.length, 0));

  const setupMessages = computed(() => {
    const messages: string[] = [];
    if (!form.name.trim()) messages.push('Deck name is required.');
    if (!form.hero_card_id) messages.push('A hero card is required.');
    return messages;
  });

  const validationMessages = computed(() => {
    const messages = [...setupMessages.value];
    if (totalMainboardCards.value !== 60) messages.push('Deck must contain exactly 60 mainboard cards.');
    for (const entry of form.entries) {
      if (entry.quantity < 1 || entry.quantity > 4) {
        messages.push('Each mainboard card quantity must stay between 1 and 4.');
        break;
      }
    }
    return messages;
  });
  const isDeckValid = computed(() => validationMessages.value.length === 0);
  const deckStatusLabel = computed(() => (isDeckValid.value ? 'Ready' : 'In Progress'));

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

  const resetManaGroup = (): void => {
    selectedManaTypeSymbolIds.value = [];
    manaSymbolMatch.value = 'any';
    manaCostMin.value = '';
    manaCostMax.value = '';
  };

  const resetAffinityGroup = (): void => {
    selectedAffinitySymbolIds.value = [];
    affinitySymbolMatch.value = 'any';
  };

  const resetDevotionGroup = (): void => {
    selectedDevotionSymbolIds.value = [];
    devotionSymbolMatch.value = 'any';
  };

  const resetGenericGroup = (): void => {
    selectedOtherSymbolIds.value = [];
    otherSymbolMatch.value = 'any';
    attackMin.value = '';
    attackMax.value = '';
    healthMin.value = '';
    healthMax.value = '';
  };

  const resetKeywordGroup = (): void => {
    selectedKeywordIds.value = [];
    keywordMatch.value = 'any';
  };

  const resetTagGroup = (): void => {
    selectedTagIds.value = [];
    tagMatch.value = 'any';
  };

  const resetTypeGroup = (): void => {
    selectedTypeIds.value = [];
    typeMatch.value = 'any';
  };

  const resetFilters = (): void => {
    resetCardFilterState();
  };

  const loadFilters = async (): Promise<void> => {
    const response = await api.get<CardFiltersResponse>('/cards/filters');
    filters.value = response.data;
    filtersLoaded.value = true;
  };

  const loadCardsPage = async (page: number, mode: 'replace' | 'append'): Promise<void> => {
    const requestId = ++latestSearchRequestId;
    const params = buildCardFilterApiSearchParams(selectionState.value);
    params.set('is_hero', isSetupStep.value ? 'true' : 'false');
    params.set('page', String(page));
    params.set('page_size', isSetupStep.value ? '24' : '30');

    if (mode === 'replace') {
      isLoadingInitial.value = true;
    } else {
      isLoadingPage.value = true;
    }

    try {
      const response = await api.get<PaginatedCardsResponse<CardListItem>>(`/cards?${params.toString()}`);
      if (requestId !== latestSearchRequestId) {
        return;
      }
      rememberCards(response.data.results);
      galleryState.value =
        mode === 'replace'
          ? replaceGalleryPage(response.data)
          : appendGalleryPage(galleryState.value, response.data);
    } finally {
      if (requestId === latestSearchRequestId) {
        isLoadingInitial.value = false;
        isLoadingPage.value = false;
      }
    }
  };

  const searchCards = async (): Promise<void> => {
    galleryState.value = createEmptyGalleryPageState<CardListItem>();
    await loadCardsPage(1, 'replace');
  };

  const loadNextPage = async (): Promise<void> => {
    if (isLoadingInitial.value || isLoadingPage.value || nextPage.value === null) {
      return;
    }
    await loadCardsPage(nextPage.value, 'append');
  };

  const debouncedSearchCards = useDebounceFn(() => {
    if (!filtersLoaded.value) {
      return;
    }
    void searchCards();
  }, 200);

  const hydrateFromDeck = (deck: DeckRecord): void => {
    form.name = deck.name;
    form.description = deck.description ?? '';
    form.is_public = deck.is_public;
    form.hero_card_id = deck.hero_card.id;
    form.entries = deck.mainboard.entries.map((entry) => ({
      card_id: entry.card.id,
      quantity: entry.quantity,
    }));

    const nextLookup = { ...cardLookup.value, [deck.hero_card.id]: deck.hero_card };
    for (const entry of deck.mainboard.entries) {
      nextLookup[entry.card.id] = entry.card;
    }
    cardLookup.value = nextLookup;
  };

  const loadDeck = async (): Promise<void> => {
    if (!deckId.value) return;
    loading.value = true;
    try {
      const deck = await fetchMyDeck(deckId.value);
      hydrateFromDeck(deck);
    } finally {
      loading.value = false;
    }
  };

  const getEntryQuantity = (cardId: string): number =>
    form.entries.find((entry) => entry.card_id === cardId)?.quantity ?? 0;

  const addEntry = (card: CardListItem): void => {
    rememberCards([card]);
    const currentQuantity = getEntryQuantity(card.id);
    if (currentQuantity >= 4 || totalMainboardCards.value >= 60) {
      return;
    }
    if (currentQuantity === 0) {
      form.entries.push({ card_id: card.id, quantity: 1 });
      return;
    }
    form.entries = form.entries.map((entry) =>
      entry.card_id === card.id ? { ...entry, quantity: Math.min(4, entry.quantity + 1) } : entry,
    );
  };

  const removeEntry = (cardId: string): void => {
    form.entries = form.entries.filter((entry) => entry.card_id !== cardId);
  };

  const changeQuantity = (cardId: string, delta: number): void => {
    form.entries = form.entries.map((entry) =>
      entry.card_id === cardId
        ? { ...entry, quantity: Math.max(1, Math.min(4, entry.quantity + delta)) }
        : entry,
    );
  };

  const setQuantity = (cardId: string, rawValue: string): void => {
    const parsed = Number.parseInt(rawValue, 10);
    const quantity = Number.isNaN(parsed) ? 1 : Math.max(1, Math.min(4, parsed));
    form.entries = form.entries.map((entry) => (entry.card_id === cardId ? { ...entry, quantity } : entry));
  };

  const galleryActionLabel = (card: CardListItem): string => {
    if (isSetupStep.value) {
      return form.hero_card_id === card.id ? 'Selected Hero' : 'Use As Hero';
    }

    const quantity = getEntryQuantity(card.id);
    if (quantity === 0) return 'Add To Deck';
    if (quantity >= 4) return 'At Copy Limit';
    if (totalMainboardCards.value >= 60) return `In Deck (${quantity})`;
    return `Add Copy (${quantity}/4)`;
  };

  const galleryActionDisabled = (card: CardListItem): boolean => {
    if (isSetupStep.value) {
      return form.hero_card_id === card.id;
    }

    const quantity = getEntryQuantity(card.id);
    return quantity >= 4 || (quantity === 0 && totalMainboardCards.value >= 60);
  };

  const handleGalleryAction = (card: CardListItem): void => {
    if (isSetupStep.value) {
      rememberCards([card]);
      form.hero_card_id = card.id;
      return;
    }
    addEntry(card);
  };

  const persistDeck = async (): Promise<DeckRecord> => {
    const payload = buildPayload();
    if (deckId.value) {
      return await updateDeck(deckId.value, payload);
    }
    return await createDeck(payload);
  };

  const lockSetup = async (): Promise<void> => {
    if (setupMessages.value.length > 0) {
      toast.error(setupMessages.value[0]);
      return;
    }
    saving.value = true;
    try {
      const deck = await persistDeck();
      builderStep.value = 'build';
      if (!deckId.value) {
        await router.replace(`/my/decks/${deck.id}/edit`);
      }
      toast.success('Deck saved.');
      resetCardFilterState();
    } finally {
      saving.value = false;
    }
  };

  const buildPayload = (): DeckUpsertRequest => ({
    name: form.name.trim(),
    description: form.description.trim() || null,
    is_public: form.is_public,
    hero_card_id: form.hero_card_id,
    entries: form.entries.map((entry) => ({
      card_id: entry.card_id,
      quantity: entry.quantity,
    })),
  });

  const saveDeck = async (): Promise<void> => {
    saving.value = true;
    try {
      const deck = await persistDeck();
      if (!deckId.value) {
        await router.replace(`/my/decks/${deck.id}/edit`);
      }
      toast.success(deck.status.is_valid ? 'Deck saved.' : 'Draft saved.');
    } finally {
      saving.value = false;
    }
  };

  watch(
    selectionState,
    () => {
      debouncedSearchCards();
    },
    { deep: true },
  );

  watch(
    isSetupStep,
    () => {
      if (!filtersLoaded.value) {
        return;
      }
      void searchCards();
    },
  );

  useIntersectionObserver(
    loadMoreSentinelRef,
    (entries) => {
      if (entries.some((entry) => entry.isIntersecting)) {
        void loadNextPage();
      }
    },
    { rootMargin: '400px 0px' },
  );

  onMounted(async () => {
    await Promise.all([loadFilters(), loadDeck()]);
    await searchCards();
  });

  return {
    deckId,
    builderStep,
    loading,
    saving,
    filters,
    query,
    keywordMatch,
    tagMatch,
    typeMatch,
    manaCostMin,
    manaCostMax,
    manaSymbolMatch,
    affinitySymbolMatch,
    devotionSymbolMatch,
    otherSymbolMatch,
    attackMin,
    attackMax,
    healthMin,
    healthMax,
    selectedKeywordIds,
    selectedTagIds,
    selectedManaTypeSymbolIds,
    selectedAffinitySymbolIds,
    selectedDevotionSymbolIds,
    selectedOtherSymbolIds,
    selectedTypeIds,
    totalCount,
    galleryCards,
    nextPage,
    isLoadingInitial,
    isLoadingPage,
    loadMoreSentinelRef,
    form,
    isSetupStep,
    cardHeightRem,
    cardFrameWidthRem,
    galleryTileWidthRem,
    galleryGridStyle,
    tooltipEnabled,
    cardScale,
    manaTypeOptions,
    affinityTypeOptions,
    devotionTypeOptions,
    otherSymbolOptions,
    totalMainboardCards,
    selectedHero,
    detailedEntries,
    deckTypeCounts,
    headerDeckTypeCounts,
    remainingDeckTypeCount,
    setupMessages,
    validationMessages,
    isDeckValid,
    deckStatusLabel,
    resetManaGroup,
    resetAffinityGroup,
    resetDevotionGroup,
    resetGenericGroup,
    resetKeywordGroup,
    resetTagGroup,
    resetTypeGroup,
    resetFilters,
    changeQuantity,
    setQuantity,
    removeEntry,
    galleryActionLabel,
    galleryActionDisabled,
    handleGalleryAction,
    lockSetup,
    saveDeck,
  };
};

export type DeckEditorController = ReturnType<typeof useDeckEditor>;
