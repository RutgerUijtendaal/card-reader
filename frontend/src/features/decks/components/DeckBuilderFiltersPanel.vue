<template>
  <GalleryFilterSidebar
    :title="controller.deck.isHeroStep.value ? 'Hero Gallery' : 'Card Gallery'"
    :description="controller.deck.isHeroStep.value ? 'Browse hero cards.' : 'Search and filter cards.'"
    :query="controller.filters.query.value"
    :on-update-query="controller.filters.updateQuery"
    :search-placeholder="controller.deck.isHeroStep.value ? 'Search heroes...' : 'Search cards...'"
    :total-count="controller.gallery.totalCount.value"
    :on-reset="controller.filters.resetFilters"
  >
    <div
      v-if="controller.deck.isHeroStep.value"
      class="theme-muted-panel space-y-3 p-3"
    >
      <p class="theme-section-title text-sm font-semibold">
        Setup
      </p>
      <p class="theme-section-muted text-sm">
        Choose a hero for this deck. Use mana type or unmatched affinity to narrow the hero pool.
      </p>
    </div>

    <label
      v-if="controller.deck.isCardsStep.value"
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
      :show-card-pool="false"
      :visible-sections="controller.deck.isHeroStep.value ? ['mana', 'affinity'] : undefined"
      :default-open-sections="controller.deck.isHeroStep.value ? ['mana', 'affinity'] : undefined"
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
import CardSortMenu from '@/domain/cards/components/CardSortMenu.vue';
import GalleryOptionsMenu from '@/domain/cards/components/GalleryOptionsMenu.vue';
import CardFilterSections from '@/domain/cards/components/filters/CardFilterSections.vue';
import GalleryFilterSidebar from '@/domain/cards/components/filters/GalleryFilterSidebar.vue';
import type { DeckEditorController } from '@/features/decks/composables/useDeckEditor';

defineProps<{
  controller: DeckEditorController;
}>();
</script>
