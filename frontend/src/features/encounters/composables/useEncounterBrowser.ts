import { computed, onMounted, ref, watch, type Ref } from 'vue';
import { fetchCards } from '@/domain/cards/api';
import { fetchEncounterBosses } from '@/domain/encounters/api';
import type { CardFaction } from '@/domain/cards/cardFactions';
import type { GalleryItem } from '@/domain/cards/types';
import { useCardFilterController } from '@/domain/cards/composables/filters/useCardFilterController';
import { useCardCollection } from '@/domain/cards/composables/useCardCollection';
import { useCardIdFilter } from '@/domain/cards/composables/useCardIdFilter';
import { useGalleryOptions } from '@/domain/cards/composables/useGalleryOptions';
import { useHoverModeSurface } from '@/domain/cards/composables/useHoverModePreferences';
import { useCardSortSurface } from '@/domain/cards/composables/useCardSortPreferences';
import { createEmptyCardFilterState } from '@/domain/cards/utils/filters/cardFilterState';
import { buildCardFilterApiSearchParams } from '@/domain/cards/utils/filters/cardFilterRequest';
import { appendCardSortSearchParam } from '@/domain/cards/utils/gallery/cardSort';
import { getApiErrorMessage } from '@/shared/api/errors';

export const useEncounterBrowser = (options: {
  mode: Ref<'boss' | 'cards'>;
  bossFactions: Ref<CardFaction[]>;
  cardIds: Ref<string[]>;
}) => {
  const controller = useCardFilterController({ cardPool: 'evil' });
  controller.applyRouteFilterState(createEmptyCardFilterState('evil'));
  const currentDeckOnly = ref(false);
  const error = ref('');
  const { cardScale } = useGalleryOptions();
  const hover = useHoverModeSurface('deckBuilder');
  const sort = useCardSortSurface('deckBuilder');
  const selectionMode = computed(() => options.mode.value === 'boss');
  const filteredCardIds = useCardIdFilter(
    options.cardIds,
    computed(() => currentDeckOnly.value && options.mode.value === 'cards'),
    '__empty_encounter__',
  );
  let requestGeneration = 0;
  watch(
    options.mode,
    () => {
      requestGeneration += 1;
      error.value = '';
    },
    { flush: 'sync' },
  );
  // The boss's factions preset the Cards filters. Apply the preset outside the boss step and
  // only when the boss's faction set changes, so picking a boss neither narrows nor reloads
  // the boss gallery, and a manual faction choice survives switching steps.
  let appliedBossFactionSignature: string | null = null;
  const applyBossFactionPreset = () => {
    if (options.mode.value === 'boss') return;
    const factions = options.bossFactions.value;
    const signature = [...factions].sort().join(',');
    if (signature === appliedBossFactionSignature) return;
    appliedBossFactionSignature = signature;
    controller.applyRouteFilterState({
      ...controller.readFilterState(),
      cardPool: 'evil',
      cardFactionKeys: [...factions],
      cardFactionExcludeKeys: [],
      cardFactionMatch: 'any',
    });
  };
  watch([options.bossFactions, options.mode], applyBossFactionPreset, {
    immediate: true,
    flush: 'sync',
  });
  const buildSearchParams = () => {
    const params = buildCardFilterApiSearchParams(controller.selectionState.value);
    params.set('card_pool', 'evil');
    params.set('lifecycle_status', 'active');
    params.delete('card_roles');
    params.delete('card_role_exclude');
    if (selectionMode.value) {
      params.set('card_roles', 'boss');
      params.set('show_groups', 'true');
    } else {
      params.set('show_groups', 'false');
      filteredCardIds.value.forEach((id) => params.append('card_ids', id));
    }
    return appendCardSortSearchParam(params, sort.effectiveSort.value);
  };
  const collection = useCardCollection<GalleryItem>({
    filtersLoaded: controller.filtersLoaded,
    resultSetKey: selectionMode,
    pageSize: 30,
    buildSearchParams,
    watchSource: [controller.selectionState, filteredCardIds, sort.effectiveSort],
    fetchPage: async (params) => {
      const generation = ++requestGeneration;
      try {
        const result = await (params.get('card_roles') === 'boss'
          ? fetchEncounterBosses(params)
          : fetchCards<GalleryItem>(params));
        if (generation === requestGeneration) error.value = '';
        return result;
      } catch (cause) {
        if (generation === requestGeneration)
          error.value = getApiErrorMessage(cause, 'Could not load cards.');
        // Keep failure explicit and retryable; useCardCollection owns request staleness.
        return {
          results: [],
          count: 0,
          page: 1,
          page_size: 30,
          next_page: null,
          previous_page: null,
        };
      }
    },
  });
  const cardHeightRem = computed(() =>
    Number(((selectionMode.value ? 24 : 21) * cardScale.value).toFixed(2)),
  );
  const galleryTileWidthRem = computed(() =>
    Number(((cardHeightRem.value * 63) / 88 + 1.5).toFixed(2)),
  );
  const filters = {
    ...controller,
    currentDeckOnly,
    setCurrentDeckOnly: (value: boolean) => {
      currentDeckOnly.value = value;
    },
    resetFilters: () => {
      controller.applyRouteFilterState(createEmptyCardFilterState('evil'));
      currentDeckOnly.value = false;
    },
    defaultHoverMode: hover.defaultHoverMode,
    hoverModeOverride: hover.overrideHoverMode,
    hoverMode: hover.effectiveHoverMode,
    setHoverMode: hover.setOverrideHoverMode,
    clearHoverModeOverride: hover.clearOverrideHoverMode,
    cardScale,
    setCardScale: (value: number) => {
      cardScale.value = value;
    },
    defaultSort: sort.defaultSort,
    sortOverride: sort.overrideSort,
    effectiveSort: sort.effectiveSort,
    setSortOverride: sort.setOverrideSort,
    clearSortOverride: sort.clearOverrideSort,
  };
  const reload = async () => {
    try {
      await controller.loadFilters();
      await collection.searchCards();
    } catch (cause) {
      error.value = getApiErrorMessage(cause, 'Could not load filters.');
    }
  };
  onMounted(reload);
  return {
    filters,
    error,
    reload,
    buildSearchParams,
    selectionMode,
    gallery: {
      ...collection,
      galleryCards: collection.cards,
      cardHeightRem,
      galleryTileWidthRem,
      loadingShimCount: computed(() => 30),
      galleryGridStyle: computed(() => ({
        gridTemplateColumns: `repeat(auto-fill, minmax(${Math.round(galleryTileWidthRem.value * 16)}px, 1fr))`,
        justifyContent: 'start',
      })),
    },
  };
};
