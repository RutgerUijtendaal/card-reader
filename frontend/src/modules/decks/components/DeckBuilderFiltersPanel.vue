<template>
  <GalleryFilterSidebar
    :title="controller.isSetupStep.value ? 'Hero Gallery' : 'Card Gallery'"
    :description="controller.isSetupStep.value ? 'Browse hero cards.' : 'Search and filter cards.'"
    :query="controller.query.value"
    :on-update-query="updateQuery"
    :search-placeholder="controller.isSetupStep.value ? 'Search heroes...' : 'Search cards...'"
    :total-count="controller.totalCount.value"
    :on-reset="controller.resetFilters"
    :sticky-to-viewport="false"
  >
    <div
      v-if="controller.isSetupStep.value"
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
      :state="filterSectionsState"
    />

    <template #footer>
      <GalleryOptionsMenu
        :tooltip-enabled="controller.tooltipEnabled.value"
        :card-scale="controller.cardScale.value"
        :show-card-groups="false"
        :show-card-groups-control="false"
        @update:tooltip-enabled="controller.tooltipEnabled.value = $event"
        @update:card-scale="controller.cardScale.value = $event"
      />
    </template>
  </GalleryFilterSidebar>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import GalleryOptionsMenu from '@/components/cards/GalleryOptionsMenu.vue';
import CardFilterSections, { type CardFilterSectionsState } from '@/modules/card-search/components/CardFilterSections.vue';
import GalleryFilterSidebar from '@/modules/card-search/components/GalleryFilterSidebar.vue';
import type { DeckEditorController } from '@/modules/decks/composables/useDeckEditor';

const props = defineProps<{
  controller: DeckEditorController;
}>();

const updateQuery = (value: string): void => {
  props.controller.query.value = value;
};

const filterSectionsState = computed<CardFilterSectionsState>(() => ({
  selectedManaTypeSymbolIds: props.controller.selectedManaTypeSymbolIds,
  manaSymbolMatch: props.controller.manaSymbolMatch,
  manaTypeOptions: props.controller.manaTypeOptions.value,
  manaCostMin: props.controller.manaCostMin,
  manaCostMax: props.controller.manaCostMax,
  resetManaGroup: props.controller.resetManaGroup,
  selectedTypeIds: props.controller.selectedTypeIds,
  typeMatch: props.controller.typeMatch,
  typeOptions: props.controller.filters.value.types,
  resetTypeGroup: props.controller.resetTypeGroup,
  selectedAffinitySymbolIds: props.controller.selectedAffinitySymbolIds,
  affinitySymbolMatch: props.controller.affinitySymbolMatch,
  affinityTypeOptions: props.controller.affinityTypeOptions.value,
  resetAffinityGroup: props.controller.resetAffinityGroup,
  selectedDevotionSymbolIds: props.controller.selectedDevotionSymbolIds,
  devotionSymbolMatch: props.controller.devotionSymbolMatch,
  devotionTypeOptions: props.controller.devotionTypeOptions.value,
  resetDevotionGroup: props.controller.resetDevotionGroup,
  selectedOtherSymbolIds: props.controller.selectedOtherSymbolIds,
  otherSymbolMatch: props.controller.otherSymbolMatch,
  otherSymbolOptions: props.controller.otherSymbolOptions.value,
  resetGenericGroup: props.controller.resetGenericGroup,
  attackMin: props.controller.attackMin,
  attackMax: props.controller.attackMax,
  healthMin: props.controller.healthMin,
  healthMax: props.controller.healthMax,
  selectedKeywordIds: props.controller.selectedKeywordIds,
  keywordMatch: props.controller.keywordMatch,
  keywordOptions: props.controller.filters.value.keywords,
  resetKeywordGroup: props.controller.resetKeywordGroup,
  selectedTagIds: props.controller.selectedTagIds,
  tagMatch: props.controller.tagMatch,
  tagOptions: props.controller.filters.value.tags,
  resetTagGroup: props.controller.resetTagGroup,
}));
</script>
