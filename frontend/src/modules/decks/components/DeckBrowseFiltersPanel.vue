<template>
  <GalleryFilterSidebar
    title="Deck Filters"
    :description="description"
    :query="controller.heroQuery.value"
    :on-update-query="controller.updateHeroQuery"
    search-placeholder="Search hero cards..."
    :total-count="totalCount"
    :on-reset="controller.resetFilters"
  >
    <div class="theme-divider space-y-3 border-b pb-4">
      <div class="space-y-1">
        <p class="theme-kicker text-xs font-semibold uppercase tracking-[0.16em]">
          Deck Library
        </p>
      </div>

      <div class="theme-tablist w-full">
        <RouterLink
          class="theme-tab flex-1"
          :class="mode === 'public' ? 'theme-tab-active' : ''"
          :to="publicTo"
        >
          Public
        </RouterLink>
        <RouterLink
          v-if="canUseOwnedDecks"
          class="theme-tab flex-1"
          :class="mode === 'owned' ? 'theme-tab-active' : ''"
          :to="ownedTo"
        >
          My Decks
        </RouterLink>
      </div>
    </div>

    <div
      v-if="showAuthor"
      class="theme-muted-panel space-y-2 p-3"
    >
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
import { RouterLink } from 'vue-router';
import type { RouteLocationRaw } from 'vue-router';
import SymbolToggleGroup from '@/components/filters/SymbolToggleGroup.vue';
import GalleryFilterSidebar from '@/components/filters/GalleryFilterSidebar.vue';
import type { DeckBrowseFiltersController } from '@/modules/decks/composables/useDeckBrowseFilters';

const props = defineProps<{
  controller: DeckBrowseFiltersController;
  totalCount: number;
  description?: string;
  showAuthor?: boolean;
  mode: 'public' | 'owned';
  canUseOwnedDecks: boolean;
  publicTo: RouteLocationRaw;
  ownedTo: RouteLocationRaw;
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
