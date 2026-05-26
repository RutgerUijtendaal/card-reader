import { computed, type Ref } from 'vue';
import type { CardListItem } from '@/modules/card-detail/types';
import type { CardFilterSelectionState } from '@/modules/card-filters/cardFilterState';
import type { CardSort } from '@/modules/card-search/cardSort';
import { useCardCollection } from '@/modules/card-search/useCardCollection';
import type { BuilderStep } from '@/modules/decks/composables/useDeckEditorDraft';

type UseDeckEditorGalleryOptions = {
  filtersLoaded: Ref<boolean>;
  buildSearchParams: () => URLSearchParams;
  selectionState: Readonly<Ref<CardFilterSelectionState>>;
  currentDeckOnly: Ref<boolean>;
  currentDeckCardIds: Readonly<Ref<string[]>>;
  builderStep: Ref<BuilderStep>;
  sort: Ref<CardSort>;
  cardScale: Ref<number>;
  rememberCards: (cards: CardListItem[]) => void;
};

export const useDeckEditorGallery = ({
  filtersLoaded,
  buildSearchParams,
  selectionState,
  currentDeckOnly,
  currentDeckCardIds,
  builderStep,
  sort,
  cardScale,
  rememberCards,
}: UseDeckEditorGalleryOptions) => {
  const isSetupStep = computed(() => builderStep.value === 'setup');
  const collection = useCardCollection<CardListItem>({
    buildSearchParams: () => {
      const params = buildSearchParams();
      params.set('is_hero', isSetupStep.value ? 'true' : 'false');
      return params;
    },
    filtersLoaded,
    pageSize: computed(() => (isSetupStep.value ? 24 : 30)),
    watchSource: [selectionState, currentDeckOnly, currentDeckCardIds, isSetupStep, sort],
    onResults: rememberCards,
  });

  const cardHeightRem = computed(() => Number(((isSetupStep.value ? 24 : 21) * cardScale.value).toFixed(2)));
  const cardFrameWidthRem = computed(() => Number(((cardHeightRem.value * 63) / 88).toFixed(2)));
  const galleryTileWidthRem = computed(() => Number((cardFrameWidthRem.value + 1.5).toFixed(2)));
  const galleryGridStyle = computed(() => ({
    gridTemplateColumns: `repeat(auto-fill, minmax(${Math.round(galleryTileWidthRem.value * 16)}px, 1fr))`,
    justifyContent: 'start',
  }));

  return {
    totalCount: collection.totalCount,
    galleryCards: collection.cards,
    nextPage: collection.nextPage,
    isLoadingInitial: collection.isLoadingInitial,
    isLoadingPage: collection.isLoadingPage,
    cardHeightRem,
    galleryTileWidthRem,
    galleryGridStyle,
    searchCards: collection.searchCards,
    setLoadMoreSentinel: collection.setLoadMoreSentinel,
  };
};

export type DeckEditorGalleryController = ReturnType<typeof useDeckEditorGallery>;
