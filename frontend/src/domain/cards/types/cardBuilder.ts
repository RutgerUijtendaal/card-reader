import type { CardListItem } from '@/domain/cards/types';
import type { GalleryItem } from '@/domain/cards/types';
import type { Ref } from 'vue';
import type { CardFilterController } from '@/domain/cards/composables/filters/useCardFilterController';
import type { HoverMode } from '@/domain/cards/utils/gallery/hoverMode';
import type { CardSort } from '@/domain/cards/utils/gallery/cardSort';

export type CardBuilderEntry = { quantity: number; card: CardListItem };
export type CardBuilderMoveDestination = {
  boardId: string;
  label: string;
  description?: string;
  disabled: boolean;
};

export type CardBuilderFilters = Pick<
  CardFilterController,
  'query' | 'updateQuery' | 'filterSectionsState' | 'resetFilters'
> & {
  currentDeckOnly: Ref<boolean>;
  setCurrentDeckOnly: (value: boolean) => void;
  defaultHoverMode: Ref<HoverMode>;
  hoverModeOverride: Ref<HoverMode | null>;
  hoverMode: Ref<HoverMode>;
  setHoverMode: (value: HoverMode) => void;
  clearHoverModeOverride: () => void;
  cardScale: Ref<number>;
  setCardScale: (value: number) => void;
  defaultSort: Ref<CardSort>;
  sortOverride: Ref<CardSort | null>;
  effectiveSort: Ref<CardSort>;
  setSortOverride: (value: CardSort) => void;
  clearSortOverride: () => void;
};

export type CardBuilderGalleryState = {
  galleryCards: Ref<GalleryItem[]>;
  hasLoadedOnce: Ref<boolean>;
  isRefreshing: Ref<boolean>;
  isLoadingInitial: Ref<boolean>;
  isLoadingPage: Ref<boolean>;
  nextPage: Ref<number | null>;
  loadingShimCount: Ref<number>;
  galleryGridStyle: Ref<{ gridTemplateColumns: string; justifyContent: string }>;
  galleryTileWidthRem: Ref<number>;
  cardHeightRem: Ref<number>;
  setLoadMoreSentinel: (element: HTMLElement | null) => void;
};
