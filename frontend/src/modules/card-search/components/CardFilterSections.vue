<template>
  <div class="space-y-3">
    <SymbolToggleGroup
      v-if="isSectionVisible('mana')"
      v-model:included-value="selectedManaTypeSymbolIds"
      v-model:excluded-value="excludedManaTypeSymbolIds"
      v-model:match-mode="manaSymbolMatch"
      :default-open="isSectionOpenByDefault('mana', true)"
      label="Mana"
      :options="state.manaTypeOptions"
      @reset="state.resetManaGroup"
    >
      <div class="theme-muted-panel p-3">
        <div class="flex items-center gap-3">
          <h4 class="theme-section-title w-16 shrink-0 text-sm font-semibold">
            Cost
          </h4>
          <div class="grid min-w-0 flex-1 grid-cols-2 gap-2">
            <input
              v-model="manaCostMin"
              class="input-base min-w-0"
              type="number"
              placeholder="Min"
            >
            <input
              v-model="manaCostMax"
              class="input-base min-w-0"
              type="number"
              placeholder="Max"
            >
          </div>
        </div>
      </div>
    </SymbolToggleGroup>

    <MetadataPillGroup
      v-if="isSectionVisible('types')"
      v-model="selectedTypeIds"
      v-model:match-mode="typeMatch"
      :default-open="isSectionOpenByDefault('types', true)"
      :initial-visible-count="7"
      label="Types"
      :options="state.typeOptions"
      @reset="state.resetTypeGroup"
    />

    <SymbolToggleGroup
      v-if="isSectionVisible('affinity')"
      v-model:included-value="selectedAffinitySymbolIds"
      v-model:excluded-value="excludedAffinitySymbolIds"
      v-model:match-mode="affinitySymbolMatch"
      :default-open="isSectionOpenByDefault('affinity')"
      label="Affinity"
      :options="state.affinityTypeOptions"
      @reset="state.resetAffinityGroup"
    />

    <SymbolToggleGroup
      v-if="isSectionVisible('devotion')"
      v-model:included-value="selectedDevotionSymbolIds"
      v-model:excluded-value="excludedDevotionSymbolIds"
      v-model:match-mode="devotionSymbolMatch"
      :default-open="isSectionOpenByDefault('devotion')"
      label="Devotion"
      :options="state.devotionTypeOptions"
      @reset="state.resetDevotionGroup"
    />

    <SymbolToggleGroup
      v-if="isSectionVisible('generic')"
      v-model:included-value="selectedOtherSymbolIds"
      v-model:excluded-value="excludedOtherSymbolIds"
      v-model:match-mode="otherSymbolMatch"
      :default-open="isSectionOpenByDefault('generic')"
      label="Generic"
      :options="state.otherSymbolOptions"
      @reset="state.resetGenericGroup"
    >
      <div class="theme-muted-panel space-y-2 p-3">
        <div class="flex items-center gap-3">
          <h4 class="theme-section-title w-16 shrink-0 text-sm font-semibold">
            Attack
          </h4>
          <div class="grid min-w-0 flex-1 grid-cols-2 gap-2">
            <input
              v-model="attackMin"
              class="input-base min-w-0"
              type="number"
              placeholder="Min"
            >
            <input
              v-model="attackMax"
              class="input-base min-w-0"
              type="number"
              placeholder="Max"
            >
          </div>
        </div>

        <div class="flex items-center gap-3">
          <h4 class="theme-section-title w-16 shrink-0 text-sm font-semibold">
            Health
          </h4>
          <div class="grid min-w-0 flex-1 grid-cols-2 gap-2">
            <input
              v-model="healthMin"
              class="input-base min-w-0"
              type="number"
              placeholder="Min"
            >
            <input
              v-model="healthMax"
              class="input-base min-w-0"
              type="number"
              placeholder="Max"
            >
          </div>
        </div>
      </div>
    </SymbolToggleGroup>

    <MetadataChecklistGroup
      v-if="isSectionVisible('keywords')"
      v-model="selectedKeywordIds"
      v-model:match-mode="keywordMatch"
      :default-open="isSectionOpenByDefault('keywords')"
      label="Keywords"
      :options="state.keywordOptions"
      @reset="state.resetKeywordGroup"
    />

    <MetadataChecklistGroup
      v-if="isSectionVisible('tags')"
      v-model="selectedTagIds"
      v-model:match-mode="tagMatch"
      :default-open="isSectionOpenByDefault('tags')"
      label="Tags"
      :options="state.tagOptions"
      @reset="state.resetTagGroup"
    />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import MetadataChecklistGroup from '@/components/filters/MetadataChecklistGroup.vue';
import MetadataPillGroup from '@/components/filters/MetadataPillGroup.vue';
import SymbolToggleGroup from '@/components/filters/SymbolToggleGroup.vue';
import type { CardFilterSectionKey, CardFilterSectionsState } from '@/modules/card-search/cardFilterSectionsState';

const props = defineProps<{
  state: CardFilterSectionsState;
  visibleSections?: CardFilterSectionKey[];
  defaultOpenSections?: CardFilterSectionKey[];
}>();

const visibleSections = computed(
  () => (props.visibleSections ? new Set(props.visibleSections) : null),
);
const defaultOpenSections = computed(
  () => (props.defaultOpenSections ? new Set(props.defaultOpenSections) : null),
);

const isSectionVisible = (section: CardFilterSectionKey): boolean =>
  visibleSections.value?.has(section) ?? true;
const isSectionOpenByDefault = (section: CardFilterSectionKey, fallback = false): boolean =>
  defaultOpenSections.value?.has(section) ?? fallback;

const selectedManaTypeSymbolIds = computed({
  get: () => props.state.selectedManaTypeSymbolIds,
  set: props.state.onUpdateSelectedManaTypeSymbolIds,
});
const excludedManaTypeSymbolIds = computed({
  get: () => props.state.excludedManaTypeSymbolIds,
  set: props.state.onUpdateExcludedManaTypeSymbolIds,
});
const manaSymbolMatch = computed({
  get: () => props.state.manaSymbolMatch,
  set: props.state.onUpdateManaSymbolMatch,
});
const manaCostMin = computed({
  get: () => props.state.manaCostMin,
  set: props.state.onUpdateManaCostMin,
});
const manaCostMax = computed({
  get: () => props.state.manaCostMax,
  set: props.state.onUpdateManaCostMax,
});
const selectedTypeIds = computed({
  get: () => props.state.selectedTypeIds,
  set: props.state.onUpdateSelectedTypeIds,
});
const typeMatch = computed({
  get: () => props.state.typeMatch,
  set: props.state.onUpdateTypeMatch,
});
const selectedAffinitySymbolIds = computed({
  get: () => props.state.selectedAffinitySymbolIds,
  set: props.state.onUpdateSelectedAffinitySymbolIds,
});
const excludedAffinitySymbolIds = computed({
  get: () => props.state.excludedAffinitySymbolIds,
  set: props.state.onUpdateExcludedAffinitySymbolIds,
});
const affinitySymbolMatch = computed({
  get: () => props.state.affinitySymbolMatch,
  set: props.state.onUpdateAffinitySymbolMatch,
});
const selectedDevotionSymbolIds = computed({
  get: () => props.state.selectedDevotionSymbolIds,
  set: props.state.onUpdateSelectedDevotionSymbolIds,
});
const excludedDevotionSymbolIds = computed({
  get: () => props.state.excludedDevotionSymbolIds,
  set: props.state.onUpdateExcludedDevotionSymbolIds,
});
const devotionSymbolMatch = computed({
  get: () => props.state.devotionSymbolMatch,
  set: props.state.onUpdateDevotionSymbolMatch,
});
const selectedOtherSymbolIds = computed({
  get: () => props.state.selectedOtherSymbolIds,
  set: props.state.onUpdateSelectedOtherSymbolIds,
});
const excludedOtherSymbolIds = computed({
  get: () => props.state.excludedOtherSymbolIds,
  set: props.state.onUpdateExcludedOtherSymbolIds,
});
const otherSymbolMatch = computed({
  get: () => props.state.otherSymbolMatch,
  set: props.state.onUpdateOtherSymbolMatch,
});
const attackMin = computed({
  get: () => props.state.attackMin,
  set: props.state.onUpdateAttackMin,
});
const attackMax = computed({
  get: () => props.state.attackMax,
  set: props.state.onUpdateAttackMax,
});
const healthMin = computed({
  get: () => props.state.healthMin,
  set: props.state.onUpdateHealthMin,
});
const healthMax = computed({
  get: () => props.state.healthMax,
  set: props.state.onUpdateHealthMax,
});
const selectedKeywordIds = computed({
  get: () => props.state.selectedKeywordIds,
  set: props.state.onUpdateSelectedKeywordIds,
});
const keywordMatch = computed({
  get: () => props.state.keywordMatch,
  set: props.state.onUpdateKeywordMatch,
});
const selectedTagIds = computed({
  get: () => props.state.selectedTagIds,
  set: props.state.onUpdateSelectedTagIds,
});
const tagMatch = computed({
  get: () => props.state.tagMatch,
  set: props.state.onUpdateTagMatch,
});
</script>
