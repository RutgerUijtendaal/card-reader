<template>
  <GalleryFilterSidebar
    title="Filters"
    :show-search="false"
    :on-reset="controller.resetFilters"
  >
    <SymbolToggleGroup
      v-model:included-value="selectedAffinitySymbolIds"
      v-model:excluded-value="excludedAffinitySymbolIds"
      v-model:match-mode="affinitySymbolMatch"
      :default-open="true"
      label="Affinity"
      :options="controller.filterCatalog.value.affinitySymbols"
      @reset="controller.resetAffinitySymbols"
    />

    <MetadataPillGroup
      v-model:included-value="selectedDeckTagIds"
      v-model:excluded-value="excludedDeckTagIds"
      v-model:match-mode="deckTagMatch"
      label="Tags"
      :options="controller.filterCatalog.value.deckTags"
      :groups="deckTagGroups"
      :default-open="true"
      @reset="controller.resetDeckTags"
    />
  </GalleryFilterSidebar>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import SymbolToggleGroup from '@/domain/cards/components/filters/SymbolToggleGroup.vue';
import MetadataPillGroup, {
  type MetadataPillOptionGroup,
} from '@/domain/cards/components/filters/MetadataPillGroup.vue';
import GalleryFilterSidebar from '@/domain/cards/components/filters/GalleryFilterSidebar.vue';
import type { DeckBrowseFiltersController } from '@/features/decks/composables/useDeckBrowseFilters';

const props = defineProps<{
  controller: DeckBrowseFiltersController;
}>();

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

const selectedDeckTagIds = computed({
  get: () => props.controller.deckTagIds.value,
  set: props.controller.updateDeckTagIds,
});
const excludedDeckTagIds = computed({
  get: () => props.controller.deckTagExcludeIds.value,
  set: props.controller.updateDeckTagExcludeIds,
});
const deckTagMatch = computed({
  get: () => props.controller.deckTagMatch.value,
  set: props.controller.updateDeckTagMatch,
});
const deckTagGroups = computed<MetadataPillOptionGroup[]>(() => [
  {
    key: 'roles',
    label: 'Roles',
    options: props.controller.filterCatalog.value.deckTags.filter((tag) => tag.kind === 'role'),
    selectedClass: 'theme-choice-chip-accent',
  },
  {
    key: 'types',
    label: 'Types',
    options: props.controller.filterCatalog.value.deckTags.filter((tag) => tag.kind === 'type'),
    selectedClass: 'theme-choice-chip-keyword',
  },
]);
</script>
