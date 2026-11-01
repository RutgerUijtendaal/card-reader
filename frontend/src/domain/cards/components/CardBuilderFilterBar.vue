<template>
  <AppCollectionToolbar>
    <template #search>
      <AppCollectionSearch
        :query="filters.query.value"
        :placeholder="searchPlaceholder"
        :total-count="totalCount"
        :result-noun="resultNoun"
        @update:query="filters.updateQuery"
      />
    </template>
    <template #filters>
      <button
        v-if="showCurrentOnly"
        type="button"
        class="theme-choice-chip min-h-9 gap-1.5 px-3 py-1"
        :class="{ 'theme-choice-chip-active': filters.currentDeckOnly.value }"
        :aria-pressed="filters.currentDeckOnly.value"
        @click="filters.setCurrentDeckOnly(!filters.currentDeckOnly.value)"
      >
        {{ currentOnlyLabel }}
      </button>
      <CardFilterSections
        layout="bar"
        :state="filters.filterSectionsState.value"
        :show-card-pool="false"
        :visible-sections="visibleSections"
        :on-reset="filters.resetFilters"
        :has-active-state="hasActiveState"
      />
    </template>
    <template #actions>
      <CardSortMenu
        :sort="filters.effectiveSort.value"
        :default-sort="filters.defaultSort.value"
        :override-active="filters.sortOverride.value !== null"
        allow-default-option
        @update:sort="filters.setSortOverride"
        @reset="filters.clearSortOverride"
      />
      <GalleryOptionsMenu
        :hover-mode="filters.hoverMode.value"
        :default-hover-mode="filters.defaultHoverMode.value"
        :hover-mode-override-active="filters.hoverModeOverride.value !== null"
        allow-hover-mode-default-option
        :card-scale="filters.cardScale.value"
        :show-card-groups="false"
        :show-card-groups-control="false"
        @update:hover-mode="filters.setHoverMode"
        @reset:hover-mode="filters.clearHoverModeOverride"
        @update:card-scale="filters.setCardScale"
      />
    </template>
  </AppCollectionToolbar>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import CardSortMenu from '@/domain/cards/components/CardSortMenu.vue';
import GalleryOptionsMenu from '@/domain/cards/components/GalleryOptionsMenu.vue';
import CardFilterSections from '@/domain/cards/components/filters/CardFilterSections.vue';
import AppCollectionSearch from '@/shared/components/app/AppCollectionSearch.vue';
import AppCollectionToolbar from '@/shared/components/app/AppCollectionToolbar.vue';
import type { CardBuilderFilters } from '@/domain/cards/types/cardBuilder';
import type { CardFilterSectionKey } from '@/domain/cards/utils/filters/cardFilterSectionsState';

const props = withDefaults(
  defineProps<{
    filters: CardBuilderFilters;
    searchPlaceholder: string;
    totalCount: number;
    showCurrentOnly: boolean;
    currentOnlyLabel: string;
    visibleSections: readonly CardFilterSectionKey[];
    resultNoun?: readonly [string, string];
  }>(),
  {
    resultNoun: () => ['card', 'cards'],
  },
);

// The search query and the current-collection toggle also count as filters for Clear filters.
const hasActiveState = computed(
  () =>
    props.filters.query.value.trim() !== '' ||
    (props.showCurrentOnly && props.filters.currentDeckOnly.value),
);
</script>
