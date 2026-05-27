import { computed } from 'vue';
import type { ComputedRef, Ref } from 'vue';
import type { CardFiltersResponse } from '@/modules/card-detail/types';
import type { CardFilterCatalog } from '@/modules/card-filters/cardFilterState';
import type { ReturnTypeUseCardFilterState } from '@/modules/card-filters/useCardFilterState';
import type { CardFilterSectionsState, MatchMode } from '@/modules/card-search/cardFilterSectionsState';

const createArrayUpdater =
  (target: { value: string[] }) =>
  (value: string[]): void => {
    target.value = value;
  };

const createStringUpdater =
  (target: { value: string }) =>
  (value: string): void => {
    target.value = value;
  };

const createMatchModeUpdater =
  (target: { value: MatchMode }) =>
  (value: MatchMode): void => {
    target.value = value;
  };

export const useCardFilterSectionsState = (
  filterState: ReturnTypeUseCardFilterState,
  filters: Ref<CardFiltersResponse>,
  filterCatalog: ComputedRef<CardFilterCatalog>,
) => {
  const resetManaGroup = (): void => {
    filterState.manaTypeSymbolIds.value = [];
    filterState.manaTypeSymbolExcludeIds.value = [];
    filterState.manaSymbolMatch.value = 'any';
    filterState.manaCostMin.value = '';
    filterState.manaCostMax.value = '';
  };

  const resetAffinityGroup = (): void => {
    filterState.affinitySymbolIds.value = [];
    filterState.affinitySymbolExcludeIds.value = [];
    filterState.affinitySymbolMatch.value = 'any';
  };

  const resetDevotionGroup = (): void => {
    filterState.devotionSymbolIds.value = [];
    filterState.devotionSymbolExcludeIds.value = [];
    filterState.devotionSymbolMatch.value = 'any';
  };

  const resetGenericGroup = (): void => {
    filterState.otherSymbolIds.value = [];
    filterState.otherSymbolExcludeIds.value = [];
    filterState.otherSymbolMatch.value = 'any';
    filterState.attackMin.value = '';
    filterState.attackMax.value = '';
    filterState.healthMin.value = '';
    filterState.healthMax.value = '';
  };

  const resetKeywordGroup = (): void => {
    filterState.keywordIds.value = [];
    filterState.keywordMatch.value = 'any';
  };

  const resetTagGroup = (): void => {
    filterState.tagIds.value = [];
    filterState.tagMatch.value = 'any';
  };

  const resetTypeGroup = (): void => {
    filterState.typeIds.value = [];
    filterState.typeMatch.value = 'any';
  };

  const filterSectionsState = computed<CardFilterSectionsState>(() => ({
    selectedManaTypeSymbolIds: filterState.manaTypeSymbolIds.value,
    onUpdateSelectedManaTypeSymbolIds: createArrayUpdater(filterState.manaTypeSymbolIds),
    excludedManaTypeSymbolIds: filterState.manaTypeSymbolExcludeIds.value,
    onUpdateExcludedManaTypeSymbolIds: createArrayUpdater(filterState.manaTypeSymbolExcludeIds),
    manaSymbolMatch: filterState.manaSymbolMatch.value,
    onUpdateManaSymbolMatch: createMatchModeUpdater(filterState.manaSymbolMatch),
    manaTypeOptions: filterCatalog.value.manaSymbols,
    manaCostMin: filterState.manaCostMin.value,
    onUpdateManaCostMin: createStringUpdater(filterState.manaCostMin),
    manaCostMax: filterState.manaCostMax.value,
    onUpdateManaCostMax: createStringUpdater(filterState.manaCostMax),
    resetManaGroup,
    selectedTypeIds: filterState.typeIds.value,
    onUpdateSelectedTypeIds: createArrayUpdater(filterState.typeIds),
    typeMatch: filterState.typeMatch.value,
    onUpdateTypeMatch: createMatchModeUpdater(filterState.typeMatch),
    typeOptions: filters.value.types,
    resetTypeGroup,
    selectedAffinitySymbolIds: filterState.affinitySymbolIds.value,
    onUpdateSelectedAffinitySymbolIds: createArrayUpdater(filterState.affinitySymbolIds),
    excludedAffinitySymbolIds: filterState.affinitySymbolExcludeIds.value,
    onUpdateExcludedAffinitySymbolIds: createArrayUpdater(filterState.affinitySymbolExcludeIds),
    affinitySymbolMatch: filterState.affinitySymbolMatch.value,
    onUpdateAffinitySymbolMatch: createMatchModeUpdater(filterState.affinitySymbolMatch),
    affinityTypeOptions: filterCatalog.value.affinitySymbols,
    resetAffinityGroup,
    selectedDevotionSymbolIds: filterState.devotionSymbolIds.value,
    onUpdateSelectedDevotionSymbolIds: createArrayUpdater(filterState.devotionSymbolIds),
    excludedDevotionSymbolIds: filterState.devotionSymbolExcludeIds.value,
    onUpdateExcludedDevotionSymbolIds: createArrayUpdater(filterState.devotionSymbolExcludeIds),
    devotionSymbolMatch: filterState.devotionSymbolMatch.value,
    onUpdateDevotionSymbolMatch: createMatchModeUpdater(filterState.devotionSymbolMatch),
    devotionTypeOptions: filterCatalog.value.devotionSymbols,
    resetDevotionGroup,
    selectedOtherSymbolIds: filterState.otherSymbolIds.value,
    onUpdateSelectedOtherSymbolIds: createArrayUpdater(filterState.otherSymbolIds),
    excludedOtherSymbolIds: filterState.otherSymbolExcludeIds.value,
    onUpdateExcludedOtherSymbolIds: createArrayUpdater(filterState.otherSymbolExcludeIds),
    otherSymbolMatch: filterState.otherSymbolMatch.value,
    onUpdateOtherSymbolMatch: createMatchModeUpdater(filterState.otherSymbolMatch),
    otherSymbolOptions: filterCatalog.value.otherSymbols,
    resetGenericGroup,
    attackMin: filterState.attackMin.value,
    onUpdateAttackMin: createStringUpdater(filterState.attackMin),
    attackMax: filterState.attackMax.value,
    onUpdateAttackMax: createStringUpdater(filterState.attackMax),
    healthMin: filterState.healthMin.value,
    onUpdateHealthMin: createStringUpdater(filterState.healthMin),
    healthMax: filterState.healthMax.value,
    onUpdateHealthMax: createStringUpdater(filterState.healthMax),
    selectedKeywordIds: filterState.keywordIds.value,
    onUpdateSelectedKeywordIds: createArrayUpdater(filterState.keywordIds),
    keywordMatch: filterState.keywordMatch.value,
    onUpdateKeywordMatch: createMatchModeUpdater(filterState.keywordMatch),
    keywordOptions: filters.value.keywords,
    resetKeywordGroup,
    selectedTagIds: filterState.tagIds.value,
    onUpdateSelectedTagIds: createArrayUpdater(filterState.tagIds),
    tagMatch: filterState.tagMatch.value,
    onUpdateTagMatch: createMatchModeUpdater(filterState.tagMatch),
    tagOptions: filters.value.tags,
    resetTagGroup,
  }));

  return {
    filterSectionsState,
    resetManaGroup,
    resetAffinityGroup,
    resetDevotionGroup,
    resetGenericGroup,
    resetKeywordGroup,
    resetTagGroup,
    resetTypeGroup,
  };
};
