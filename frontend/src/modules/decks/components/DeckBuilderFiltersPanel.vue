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
        Select a hero to continue.
      </p>
    </div>

    <CardFilterSections
      v-else
      :state="controller.filters.filterSectionsState.value"
    />

    <template #footer>
      <GalleryOptionsMenu
        :tooltip-enabled="controller.filters.tooltipEnabled.value"
        :card-scale="controller.filters.cardScale.value"
        :show-card-groups="false"
        :show-card-groups-control="false"
        @update:tooltip-enabled="controller.filters.setTooltipEnabled"
        @update:card-scale="controller.filters.setCardScale"
      />
    </template>
  </GalleryFilterSidebar>
</template>

<script setup lang="ts">
import GalleryOptionsMenu from '@/components/cards/GalleryOptionsMenu.vue';
import CardFilterSections from '@/modules/card-search/components/CardFilterSections.vue';
import GalleryFilterSidebar from '@/modules/card-search/components/GalleryFilterSidebar.vue';
import type { DeckEditorController } from '@/modules/decks/composables/useDeckEditor';

defineProps<{
  controller: DeckEditorController;
}>();
</script>
