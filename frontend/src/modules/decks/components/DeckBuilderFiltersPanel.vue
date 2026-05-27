<template>
  <GalleryFilterSidebar
    :title="controller.deck.isSetupStep.value ? 'Hero Gallery' : 'Card Gallery'"
    :description="controller.deck.isSetupStep.value ? 'Browse hero cards.' : 'Search and filter cards.'"
    :query="controller.filters.query.value"
    :on-update-query="controller.filters.updateQuery"
    :search-placeholder="controller.deck.isSetupStep.value ? 'Search heroes...' : 'Search cards...'"
    :total-count="controller.gallery.totalCount.value"
    :on-reset="controller.filters.resetFilters"
    :sticky-to-viewport="false"
  >
    <div
      v-if="controller.deck.isSetupStep.value"
      class="theme-muted-panel space-y-3 p-3"
    >
      <p class="theme-section-title text-sm font-semibold">
        Setup
      </p>
      <p class="theme-section-muted text-sm">
        Select a hero to continue. Use affinity to narrow the hero pool.
      </p>
    </div>

    <label
      v-if="!controller.deck.isSetupStep.value"
      class="theme-muted-panel flex items-center gap-3 p-3 text-sm"
    >
      <input
        :checked="controller.filters.currentDeckOnly.value"
        type="checkbox"
        class="theme-checkbox h-4 w-4"
        @change="controller.filters.setCurrentDeckOnly(($event.target as HTMLInputElement).checked)"
      >
      <span class="theme-section-title font-medium">Current Deck Only</span>
    </label>

    <CardFilterSections
      :state="controller.filters.filterSectionsState.value"
      :visible-sections="controller.deck.isSetupStep.value ? ['affinity'] : undefined"
      :default-open-sections="controller.deck.isSetupStep.value ? ['affinity'] : undefined"
    />

    <template #footer>
      <div class="flex flex-wrap items-center gap-2">
        <CardSortMenu
          :sort="controller.filters.effectiveSort.value"
          :default-sort="controller.filters.defaultSort.value"
          :override-active="controller.filters.sortOverride.value !== null"
          allow-default-option
          @update:sort="controller.filters.setSortOverride"
          @reset="controller.filters.clearSortOverride"
        />
        <GalleryOptionsMenu
          :hover-mode="controller.filters.hoverMode.value"
          :default-hover-mode="controller.filters.defaultHoverMode.value"
          :hover-mode-override-active="controller.filters.hoverModeOverride.value !== null"
          allow-hover-mode-default-option
          :card-scale="controller.filters.cardScale.value"
          :show-card-groups="false"
          :show-card-groups-control="false"
          @update:hover-mode="controller.filters.setHoverMode"
          @reset:hover-mode="controller.filters.clearHoverModeOverride"
          @update:card-scale="controller.filters.setCardScale"
        />
      </div>
    </template>
  </GalleryFilterSidebar>
</template>

<script setup lang="ts">
import CardSortMenu from '@/components/cards/CardSortMenu.vue';
import GalleryOptionsMenu from '@/components/cards/GalleryOptionsMenu.vue';
import CardFilterSections from '@/modules/card-search/components/CardFilterSections.vue';
import GalleryFilterSidebar from '@/modules/card-search/components/GalleryFilterSidebar.vue';
import type { DeckEditorController } from '@/modules/decks/composables/useDeckEditor';

defineProps<{
  controller: DeckEditorController;
}>();
</script>
