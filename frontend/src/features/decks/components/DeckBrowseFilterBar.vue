<template>
  <div class="contents">
    <AppFilterChip
      label="Affinity"
      :active-count="affinityCount"
    >
      <SymbolToggleGroup
        v-model:included-value="selectedAffinitySymbolIds"
        v-model:excluded-value="excludedAffinitySymbolIds"
        v-model:match-mode="affinitySymbolMatch"
        :default-open="true"
        :collapsible="false"
        label="Affinity"
        :options="controller.filterCatalog.value.affinitySymbols"
        @reset="controller.resetAffinitySymbols"
      />
    </AppFilterChip>

    <AppFilterChip
      label="Tags"
      :active-count="deckTagCount"
    >
      <MetadataPillGroup
        v-model:included-value="selectedDeckTagIds"
        v-model:excluded-value="excludedDeckTagIds"
        v-model:match-mode="deckTagMatch"
        label="Tags"
        :options="controller.filterCatalog.value.deckTags"
        :groups="deckTagGroups"
        :default-open="true"
        :collapsible="false"
        @reset="controller.resetDeckTags"
      />
    </AppFilterChip>

    <button
      v-if="hasActiveFilters"
      type="button"
      class="theme-ghost-button inline-flex min-h-9 items-center gap-1.5 rounded-full px-3 text-sm font-medium"
      @click="controller.resetFilters"
    >
      <X
        class="h-3.5 w-3.5"
        aria-hidden="true"
      />
      Clear filters
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import SymbolToggleGroup from '@/domain/cards/components/filters/SymbolToggleGroup.vue';
import MetadataPillGroup, {
  type MetadataPillOptionGroup,
} from '@/domain/cards/components/filters/MetadataPillGroup.vue';
import AppFilterChip from '@/shared/components/app/AppFilterChip.vue';
import { X } from 'lucide-vue-next';
import type { DeckBrowseFiltersController } from '@/features/decks/composables/useDeckBrowseFilters';

const props = defineProps<{
  controller: DeckBrowseFiltersController;
  /** Whether any search or filter is applied, including the search query. */
  hasActiveFilters: boolean;
}>();

const affinityCount = computed(
  () => props.controller.affinitySymbolIds.value.length + props.controller.affinitySymbolExcludeIds.value.length,
);
const deckTagCount = computed(
  () => props.controller.deckTagIds.value.length + props.controller.deckTagExcludeIds.value.length,
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
