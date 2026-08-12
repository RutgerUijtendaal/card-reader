<template>
  <div class="space-y-3">
    <div
      v-if="isSectionVisible('classification')"
      class="space-y-3"
    >
      <label
        v-if="state.cardPoolOptions.length > 1"
        class="block space-y-1"
      >
        <span class="theme-section-title text-sm font-semibold">Card pool</span>
        <select
          v-model="cardPool"
          class="input-base w-full"
        >
          <option
            v-for="option in state.cardPoolOptions"
            :key="option.key"
            :value="option.key"
          >
            {{ option.label }}
          </option>
        </select>
      </label>

      <MetadataPillGroup
        v-model:included-value="selectedCardRoles"
        v-model:excluded-value="excludedCardRoles"
        v-model:match-mode="cardRoleMatch"
        :default-open="isSectionOpenByDefault('classification', true)"
        label="Card roles"
        :options="state.cardRoleOptions"
        @reset="state.resetClassificationGroup"
      />
    </div>

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
      <div class="theme-divider border-t pt-3">
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
      v-model:included-value="selectedTypeIds"
      v-model:excluded-value="excludedTypeIds"
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
      <div class="theme-divider space-y-2 border-t pt-3">
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
      :favorite-group="state.keywordFavoriteGroup"
      :favorite-keys="state.keywordFavoriteKeys"
      label="Keywords"
      :options="state.keywordOptions"
      @toggle-favorite="state.toggleKeywordFavorite"
      @reset="state.resetKeywordGroup"
    />

    <MetadataChecklistGroup
      v-if="isSectionVisible('tags')"
      v-model="selectedTagIds"
      v-model:match-mode="tagMatch"
      :default-open="isSectionOpenByDefault('tags')"
      :favorite-group="state.tagFavoriteGroup"
      :favorite-keys="state.tagFavoriteKeys"
      label="Tags"
      :options="state.tagOptions"
      @toggle-favorite="state.toggleTagFavorite"
      @reset="state.resetTagGroup"
    />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import MetadataChecklistGroup from '@/domain/cards/components/filters/MetadataChecklistGroup.vue';
import MetadataPillGroup from '@/domain/cards/components/filters/MetadataPillGroup.vue';
import SymbolToggleGroup from '@/domain/cards/components/filters/SymbolToggleGroup.vue';
import type {
  CardFilterSectionKey,
  CardFilterSectionsState,
} from '@/domain/cards/utils/filters/cardFilterSectionsState';
import type { CardPool } from '@/domain/cards/cardPools';

const props = defineProps<{
  state: CardFilterSectionsState;
  visibleSections?: CardFilterSectionKey[];
  defaultOpenSections?: CardFilterSectionKey[];
}>();

const visibleSections = computed(() =>
  props.visibleSections ? new Set(props.visibleSections) : null,
);
const defaultOpenSections = computed(() =>
  props.defaultOpenSections ? new Set(props.defaultOpenSections) : null,
);

const isSectionVisible = (section: CardFilterSectionKey): boolean =>
  visibleSections.value?.has(section) ?? true;
const isSectionOpenByDefault = (section: CardFilterSectionKey, fallback = false): boolean =>
  defaultOpenSections.value?.has(section) ?? fallback;

const cardPool = computed({
  get: () => props.state.cardPool,
  set: (value: CardPool) => props.state.onUpdateCardPool(value),
});
const selectedCardRoles = computed({
  get: () => props.state.selectedCardRoles,
  set: props.state.onUpdateSelectedCardRoles,
});
const excludedCardRoles = computed({
  get: () => props.state.excludedCardRoles,
  set: props.state.onUpdateExcludedCardRoles,
});
const cardRoleMatch = computed({
  get: () => props.state.cardRoleMatch,
  set: props.state.onUpdateCardRoleMatch,
});

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
const excludedTypeIds = computed({
  get: () => props.state.excludedTypeIds,
  set: props.state.onUpdateExcludedTypeIds,
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
