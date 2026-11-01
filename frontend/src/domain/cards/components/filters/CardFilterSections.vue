<template>
  <div :class="layout === 'bar' ? 'contents' : 'space-y-3'">
    <label
      v-if="showCardPool && state.cardPoolOptions.length > 1"
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

    <FilterSlot
      v-if="isSectionVisible('roles')"
      label="Card roles"
      :active-count="activeCounts.roles"
    >
      <MetadataPillGroup
        v-model:included-value="selectedCardRoles"
        v-model:excluded-value="excludedCardRoles"
        v-model:match-mode="cardRoleMatch"
        :default-open="isSectionOpenByDefault('roles', true)"
        :collapsible="layout !== 'bar'"
        label="Card roles"
        :options="state.cardRoleOptions"
        @reset="state.resetCardRoleGroup"
      />
    </FilterSlot>

    <FilterSlot
      v-if="isSectionVisible('factions')"
      label="Factions"
      :active-count="activeCounts.factions"
    >
      <MetadataPillGroup
        v-model:included-value="selectedCardFactions"
        v-model:excluded-value="excludedCardFactions"
        v-model:match-mode="cardFactionMatch"
        :default-open="isSectionOpenByDefault('factions', true)"
        :collapsible="layout !== 'bar'"
        label="Factions"
        :options="state.cardFactionOptions"
        @reset="state.resetCardFactionGroup"
      />
    </FilterSlot>

    <FilterSlot
      v-if="isSectionVisible('mana')"
      label="Mana"
      :active-count="activeCounts.mana"
    >
      <SymbolToggleGroup
        v-model:included-value="selectedManaFamilyIds"
        v-model:excluded-value="excludedManaFamilyIds"
        v-model:match-mode="manaFamilyMatch"
        :default-open="isSectionOpenByDefault('mana', true)"
        :collapsible="layout !== 'bar'"
        label="Mana"
        :options="state.manaFamilyOptions"
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
    </FilterSlot>

    <FilterSlot
      v-if="isSectionVisible('types')"
      label="Types"
      :active-count="activeCounts.types"
    >
      <MetadataPillGroup
        v-model:included-value="selectedTypeIds"
        v-model:excluded-value="excludedTypeIds"
        v-model:match-mode="typeMatch"
        :default-open="isSectionOpenByDefault('types', true)"
        :collapsible="layout !== 'bar'"
        :initial-visible-count="7"
        label="Types"
        :options="state.typeOptions"
        @reset="state.resetTypeGroup"
      />
    </FilterSlot>

    <FilterSlot
      v-if="isSectionVisible('generic')"
      label="Generic"
      :active-count="activeCounts.generic"
    >
      <SymbolToggleGroup
        v-model:included-value="selectedOtherSymbolIds"
        v-model:excluded-value="excludedOtherSymbolIds"
        v-model:match-mode="otherSymbolMatch"
        :default-open="isSectionOpenByDefault('generic')"
        :collapsible="layout !== 'bar'"
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
    </FilterSlot>

    <FilterSlot
      v-if="isSectionVisible('keywords')"
      label="Keywords"
      :active-count="activeCounts.keywords"
    >
      <MetadataChecklistGroup
        v-model="selectedKeywordIds"
        v-model:match-mode="keywordMatch"
        :default-open="isSectionOpenByDefault('keywords')"
        :collapsible="layout !== 'bar'"
        :favorite-group="state.keywordFavoriteGroup"
        :favorite-keys="state.keywordFavoriteKeys"
        label="Keywords"
        :options="state.keywordOptions"
        @toggle-favorite="state.toggleKeywordFavorite"
        @reset="state.resetKeywordGroup"
      />
    </FilterSlot>

    <FilterSlot
      v-if="isSectionVisible('tags')"
      label="Tags"
      :active-count="activeCounts.tags"
    >
      <MetadataChecklistGroup
        v-model="selectedTagIds"
        v-model:match-mode="tagMatch"
        :default-open="isSectionOpenByDefault('tags')"
        :collapsible="layout !== 'bar'"
        :favorite-group="state.tagFavoriteGroup"
        :favorite-keys="state.tagFavoriteKeys"
        label="Tags"
        :options="state.tagOptions"
        @toggle-favorite="state.toggleTagFavorite"
        @reset="state.resetTagGroup"
      />
    </FilterSlot>

    <FilterSlot
      v-if="isSectionVisible('affinity')"
      label="Affinity"
      :active-count="activeCounts.affinity"
    >
      <SymbolToggleGroup
        v-model:included-value="selectedAffinitySymbolIds"
        v-model:excluded-value="excludedAffinitySymbolIds"
        v-model:match-mode="affinitySymbolMatch"
        :default-open="isSectionOpenByDefault('affinity')"
        :collapsible="layout !== 'bar'"
        label="Affinity"
        :options="state.affinityTypeOptions"
        @reset="state.resetAffinityGroup"
      />
    </FilterSlot>

    <FilterSlot
      v-if="isSectionVisible('devotion')"
      label="Devotion"
      :active-count="activeCounts.devotion"
    >
      <SymbolToggleGroup
        v-model:included-value="selectedDevotionSymbolIds"
        v-model:excluded-value="excludedDevotionSymbolIds"
        v-model:match-mode="devotionSymbolMatch"
        :default-open="isSectionOpenByDefault('devotion')"
        :collapsible="layout !== 'bar'"
        label="Devotion"
        :options="state.devotionTypeOptions"
        @reset="state.resetDevotionGroup"
      />
    </FilterSlot>
    <button
      v-if="layout === 'bar' && (totalActiveCount > 0 || hasActiveState) && onReset"
      type="button"
      class="theme-ghost-button inline-flex min-h-9 items-center gap-1.5 rounded-full px-3 text-sm font-medium"
      @click="onReset"
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
import { computed, type FunctionalComponent } from 'vue';
import { X } from 'lucide-vue-next';
import AppFilterChip from '@/shared/components/app/AppFilterChip.vue';
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
  showCardPool?: boolean;
  visibleSections?: readonly CardFilterSectionKey[];
  defaultOpenSections?: readonly CardFilterSectionKey[];
  /** `column` stacks open sections in a filter aside; `bar` turns each section into a chip with a popover. */
  layout?: 'column' | 'bar';
  /** Clears every filter; offered from the bar once any filter is active. */
  onReset?: () => void;
  /** Filter state the sections cannot count themselves, such as a search query or unresolved route keys. */
  hasActiveState?: boolean;
}>();

const layout = computed(() => props.layout ?? 'column');

// Column sections render as-is; bar sections sit behind a chip that reports their active selections.
const PassThroughSection: FunctionalComponent = (_props, { slots }) => slots.default?.();
PassThroughSection.inheritAttrs = false;
const FilterSlot = computed(() => (layout.value === 'bar' ? AppFilterChip : PassThroughSection));

const showCardPool = computed(() => props.showCardPool ?? true);

const visibleSections = computed(() =>
  props.visibleSections ? new Set(props.visibleSections) : null,
);
const defaultOpenSections = computed(() =>
  props.defaultOpenSections ? new Set(props.defaultOpenSections) : null,
);

const isSectionVisible = (section: CardFilterSectionKey): boolean =>
  visibleSections.value?.has(section) ?? true;
const isSectionOpenByDefault = (section: CardFilterSectionKey, fallback = false): boolean => {
  if (layout.value === 'bar') {
    return true;
  }
  return defaultOpenSections.value?.has(section) ?? fallback;
};

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
const selectedCardFactions = computed({
  get: () => props.state.selectedCardFactions,
  set: props.state.onUpdateSelectedCardFactions,
});
const excludedCardFactions = computed({
  get: () => props.state.excludedCardFactions,
  set: props.state.onUpdateExcludedCardFactions,
});
const cardFactionMatch = computed({
  get: () => props.state.cardFactionMatch,
  set: props.state.onUpdateCardFactionMatch,
});

const selectedManaFamilyIds = computed({
  get: () => props.state.selectedManaFamilyIds,
  set: props.state.onUpdateSelectedManaFamilyIds,
});
const excludedManaFamilyIds = computed({
  get: () => props.state.excludedManaFamilyIds,
  set: props.state.onUpdateExcludedManaFamilyIds,
});
const manaFamilyMatch = computed({
  get: () => props.state.manaFamilyMatch,
  set: props.state.onUpdateManaFamilyMatch,
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

const countRange = (min: string, max: string): number => (min.trim() || max.trim() ? 1 : 0);
const activeCounts = computed<Record<CardFilterSectionKey, number>>(() => {
  const state = props.state;
  return {
    roles: state.selectedCardRoles.length + state.excludedCardRoles.length,
    factions: state.selectedCardFactions.length + state.excludedCardFactions.length,
    mana:
      state.selectedManaFamilyIds.length +
      state.excludedManaFamilyIds.length +
      countRange(state.manaCostMin, state.manaCostMax),
    types: state.selectedTypeIds.length + state.excludedTypeIds.length,
    affinity: state.selectedAffinitySymbolIds.length + state.excludedAffinitySymbolIds.length,
    devotion: state.selectedDevotionSymbolIds.length + state.excludedDevotionSymbolIds.length,
    generic:
      state.selectedOtherSymbolIds.length +
      state.excludedOtherSymbolIds.length +
      countRange(state.attackMin, state.attackMax) +
      countRange(state.healthMin, state.healthMax),
    keywords: state.selectedKeywordIds.length,
    tags: state.selectedTagIds.length,
  };
});
const totalActiveCount = computed(() => {
  let total = 0;
  for (const section of Object.keys(activeCounts.value) as CardFilterSectionKey[]) {
    if (isSectionVisible(section)) {
      total += activeCounts.value[section];
    }
  }
  return total;
});
</script>
