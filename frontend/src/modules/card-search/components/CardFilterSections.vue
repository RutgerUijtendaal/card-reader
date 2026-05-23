<template>
  <div class="space-y-3">
    <SymbolToggleGroup
      v-model="state.selectedManaTypeSymbolIds.value"
      v-model:match-mode="state.manaSymbolMatch.value"
      :default-open="true"
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
              v-model="state.manaCostMin.value"
              class="input-base min-w-0"
              type="number"
              placeholder="Min"
            >
            <input
              v-model="state.manaCostMax.value"
              class="input-base min-w-0"
              type="number"
              placeholder="Max"
            >
          </div>
        </div>
      </div>
    </SymbolToggleGroup>

    <MetadataPillGroup
      v-model="state.selectedTypeIds.value"
      v-model:match-mode="state.typeMatch.value"
      :default-open="true"
      :initial-visible-count="7"
      label="Types"
      :options="state.typeOptions"
      @reset="state.resetTypeGroup"
    />

    <SymbolToggleGroup
      v-model="state.selectedAffinitySymbolIds.value"
      v-model:match-mode="state.affinitySymbolMatch.value"
      label="Affinity"
      :options="state.affinityTypeOptions"
      @reset="state.resetAffinityGroup"
    />

    <SymbolToggleGroup
      v-model="state.selectedDevotionSymbolIds.value"
      v-model:match-mode="state.devotionSymbolMatch.value"
      label="Devotion"
      :options="state.devotionTypeOptions"
      @reset="state.resetDevotionGroup"
    />

    <SymbolToggleGroup
      v-model="state.selectedOtherSymbolIds.value"
      v-model:match-mode="state.otherSymbolMatch.value"
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
              v-model="state.attackMin.value"
              class="input-base min-w-0"
              type="number"
              placeholder="Min"
            >
            <input
              v-model="state.attackMax.value"
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
              v-model="state.healthMin.value"
              class="input-base min-w-0"
              type="number"
              placeholder="Min"
            >
            <input
              v-model="state.healthMax.value"
              class="input-base min-w-0"
              type="number"
              placeholder="Max"
            >
          </div>
        </div>
      </div>
    </SymbolToggleGroup>

    <MetadataChecklistGroup
      v-model="state.selectedKeywordIds.value"
      v-model:match-mode="state.keywordMatch.value"
      label="Keywords"
      :options="state.keywordOptions"
      @reset="state.resetKeywordGroup"
    />

    <MetadataChecklistGroup
      v-model="state.selectedTagIds.value"
      v-model:match-mode="state.tagMatch.value"
      label="Tags"
      :options="state.tagOptions"
      @reset="state.resetTagGroup"
    />
  </div>
</template>

<script setup lang="ts">
import type { Ref } from 'vue';
import MetadataChecklistGroup from '@/components/filters/MetadataChecklistGroup.vue';
import MetadataPillGroup from '@/components/filters/MetadataPillGroup.vue';
import SymbolToggleGroup from '@/components/filters/SymbolToggleGroup.vue';
import type { MetadataOption, SymbolFilterOption } from '@/modules/card-detail/types';

export type CardFilterSectionsState = {
  selectedManaTypeSymbolIds: Ref<string[]>;
  manaSymbolMatch: Ref<'any' | 'all'>;
  manaTypeOptions: SymbolFilterOption[];
  manaCostMin: Ref<string>;
  manaCostMax: Ref<string>;
  resetManaGroup: () => void;
  selectedTypeIds: Ref<string[]>;
  typeMatch: Ref<'any' | 'all'>;
  typeOptions: MetadataOption[];
  resetTypeGroup: () => void;
  selectedAffinitySymbolIds: Ref<string[]>;
  affinitySymbolMatch: Ref<'any' | 'all'>;
  affinityTypeOptions: SymbolFilterOption[];
  resetAffinityGroup: () => void;
  selectedDevotionSymbolIds: Ref<string[]>;
  devotionSymbolMatch: Ref<'any' | 'all'>;
  devotionTypeOptions: SymbolFilterOption[];
  resetDevotionGroup: () => void;
  selectedOtherSymbolIds: Ref<string[]>;
  otherSymbolMatch: Ref<'any' | 'all'>;
  otherSymbolOptions: SymbolFilterOption[];
  resetGenericGroup: () => void;
  attackMin: Ref<string>;
  attackMax: Ref<string>;
  healthMin: Ref<string>;
  healthMax: Ref<string>;
  selectedKeywordIds: Ref<string[]>;
  keywordMatch: Ref<'any' | 'all'>;
  keywordOptions: MetadataOption[];
  resetKeywordGroup: () => void;
  selectedTagIds: Ref<string[]>;
  tagMatch: Ref<'any' | 'all'>;
  tagOptions: MetadataOption[];
  resetTagGroup: () => void;
};

defineProps<{
  state: CardFilterSectionsState;
}>();
</script>
