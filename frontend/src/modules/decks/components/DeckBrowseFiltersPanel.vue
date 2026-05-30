<template>
  <GalleryFilterSidebar
    title="Deck Filters"
    :description="description"
    :query="controller.heroQuery.value"
    :on-update-query="controller.updateHeroQuery"
    search-placeholder="Search hero cards..."
    :total-count="totalCount"
    :on-reset="controller.resetFilters"
    :sticky-to-viewport="false"
  >
    <div class="theme-muted-panel space-y-2 p-3">
      <div class="space-y-1">
        <h4 class="theme-section-title text-sm font-semibold">
          Author
        </h4>
        <p class="theme-section-muted text-xs">
          Match decks published by a username.
        </p>
      </div>
      <input
        :value="controller.authorQuery.value"
        class="input-base"
        placeholder="Search authors..."
        @input="controller.updateAuthorQuery(($event.target as HTMLInputElement).value)"
      >
    </div>

    <div class="theme-muted-panel space-y-2 p-3">
      <div class="space-y-1">
        <h4 class="theme-section-title text-sm font-semibold">
          Cards In Deck
        </h4>
        <p class="theme-section-muted text-xs">
          Match decks containing any mainboard or sideboard card with this name.
        </p>
      </div>
      <input
        :value="controller.cardQuery.value"
        class="input-base"
        placeholder="Search deck cards..."
        @input="controller.updateCardQuery(($event.target as HTMLInputElement).value)"
      >
    </div>

    <SymbolToggleGroup
      v-model:included-value="selectedAffinitySymbolIds"
      v-model:excluded-value="excludedAffinitySymbolIds"
      v-model:match-mode="affinitySymbolMatch"
      :default-open="true"
      label="Affinity"
      :options="controller.filterCatalog.value.affinitySymbols"
      @reset="controller.resetAffinitySymbols"
    />
  </GalleryFilterSidebar>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import SymbolToggleGroup from '@/components/filters/SymbolToggleGroup.vue';
import GalleryFilterSidebar from '@/modules/card-search/components/GalleryFilterSidebar.vue';
import type { DeckBrowseFiltersController } from '@/modules/decks/composables/useDeckBrowseFilters';

const props = defineProps<{
  controller: DeckBrowseFiltersController;
  totalCount: number;
  description?: string;
}>();

const description = computed(
  () => props.description ?? 'Filter public decks by hero, author, included cards, and affinity.',
);

const selectedAffinitySymbolIds = computed({
  get: () => props.controller.affinitySymbolIds.value,
  set: props.controller.updateAffinitySymbolIds,
});
const excludedAffinitySymbolIds = computed({
  get: () => props.controller.affinitySymbolExcludeIds.value,
  set: props.controller.updateAffinitySymbolExcludeIds,
});

const affinitySymbolMatch = computed({
  get: () => props.controller.affinitySymbolMatch.value,
  set: props.controller.updateAffinitySymbolMatch,
});
</script>
