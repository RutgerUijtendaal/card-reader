<template>
  <GalleryFilterSidebar
    :title="title"
    :description="description"
    :query="filters.query.value"
    :on-update-query="filters.updateQuery"
    :search-placeholder="searchPlaceholder"
    :total-count="totalCount"
    :on-reset="filters.resetFilters"
  >
    <slot />

    <label
      v-if="showCurrentOnly"
      class="theme-muted-panel flex items-center gap-3 p-3 text-sm"
    >
      <input
        :checked="filters.currentDeckOnly.value"
        type="checkbox"
        class="theme-checkbox h-4 w-4"
        @change="filters.setCurrentDeckOnly(($event.target as HTMLInputElement).checked)"
      >
      <span class="theme-section-title font-medium">{{ currentOnlyLabel }}</span>
    </label>

    <CardFilterSections
      :state="filters.filterSectionsState.value"
      :show-card-pool="false"
      :visible-sections="visibleSections"
      :default-open-sections="defaultOpenSections"
    />

    <template #footer>
      <div class="flex flex-wrap items-center gap-2">
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
      </div>
    </template>
  </GalleryFilterSidebar>
</template>

<script setup lang="ts">
import CardSortMenu from '@/domain/cards/components/CardSortMenu.vue';
import GalleryOptionsMenu from '@/domain/cards/components/GalleryOptionsMenu.vue';
import CardFilterSections from '@/domain/cards/components/filters/CardFilterSections.vue';
import GalleryFilterSidebar from '@/domain/cards/components/filters/GalleryFilterSidebar.vue';
import type { CardBuilderFilters } from '@/domain/cards/types/cardBuilder';
import type { CardFilterSectionKey } from '@/domain/cards/utils/filters/cardFilterSectionsState';

defineProps<{
  filters: CardBuilderFilters;
  title: string;
  description: string;
  searchPlaceholder: string;
  totalCount: number;
  showCurrentOnly: boolean;
  currentOnlyLabel: string;
  visibleSections: readonly CardFilterSectionKey[];
  defaultOpenSections?: readonly CardFilterSectionKey[];
}>();
</script>
