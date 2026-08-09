import { computed, type Ref } from 'vue';
import type { CardListItem } from '@/domain/cards/types';
import type { CardFilterSelectionState } from '@/domain/cards/utils/filters/cardFilterState';
import type { CardSort } from '@/domain/cards/utils/gallery/cardSort';
import { useCardCollection } from '@/domain/cards/composables/useCardCollection';
import type { DeckEditorMode } from '@/features/decks/composables/deckEditorDraftTypes';

type UseDeckEditorGalleryOptions = {
  filtersLoaded: Ref<boolean>;
  buildSearchParams: () => URLSearchParams;
  selectionState: Readonly<Ref<CardFilterSelectionState>>;
  currentDeckOnly: Ref<boolean>;
  currentDeckCardIds: Readonly<Ref<string[]>>;
  editorMode: Ref<DeckEditorMode>;
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
  editorMode,
  sort,
  cardScale,
  rememberCards,
}: UseDeckEditorGalleryOptions) => {
  const isHeroStep = computed(() => editorMode.value === 'hero');
  const isGalleryVisible = computed(() => editorMode.value === 'hero' || editorMode.value === 'cards');
  const collection = useCardCollection<CardListItem>({
    buildSearchParams: () => {
      const params = buildSearchParams();
      params.set('card_pool', 'player');
      params.delete('card_roles');
      params.delete('card_role_exclude');
      params.delete('card_role_match');
      if (isHeroStep.value) params.append('card_roles', 'hero');
      else params.append('card_role_exclude', 'hero');
      return params;
    },
    filtersLoaded,
    enabled: isGalleryVisible,
    resultSetKey: isHeroStep,
    pageSize: computed(() => (isHeroStep.value ? 24 : 30)),
    watchSource: [selectionState, currentDeckOnly, currentDeckCardIds, sort],
    onResults: rememberCards,
  });

  const cardHeightRem = computed(() => Number(((isHeroStep.value ? 24 : 21) * cardScale.value).toFixed(2)));
  const cardFrameWidthRem = computed(() => Number(((cardHeightRem.value * 63) / 88).toFixed(2)));
  const galleryTileWidthRem = computed(() => Number((cardFrameWidthRem.value + 1.5).toFixed(2)));
  const loadingShimCount = computed(() => (isHeroStep.value ? 24 : 30));
  const galleryGridStyle = computed(() => ({
    gridTemplateColumns: `repeat(auto-fill, minmax(${Math.round(galleryTileWidthRem.value * 16)}px, 1fr))`,
    justifyContent: 'start',
  }));

  return {
    totalCount: collection.totalCount,
    galleryCards: collection.cards,
    nextPage: collection.nextPage,
    isLoadingInitial: collection.isLoadingInitial,
    isRefreshing: collection.isRefreshing,
    isLoadingPage: collection.isLoadingPage,
    hasLoadedOnce: collection.hasLoadedOnce,
    cardHeightRem,
    cardFrameWidthRem,
    galleryTileWidthRem,
    loadingShimCount,
    galleryGridStyle,
    searchCards: collection.searchCards,
    setLoadMoreSentinel: collection.setLoadMoreSentinel,
  };
};

export type DeckEditorGalleryController = ReturnType<typeof useDeckEditorGallery>;
