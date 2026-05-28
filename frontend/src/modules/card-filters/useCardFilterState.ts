import { computed, ref } from 'vue';
import type { Ref } from 'vue';
import type { CardFilterCatalog, CardFilterSelectionState } from './cardFilterState';
import {
  buildCardFilterSelectionState,
  buildCardFilterStateFromSelection,
  createEmptyCardFilterSelectionState,
  normalizeCardFilterSelectionState,
  type CardFilterState,
} from './cardFilterState';

export const useCardFilterState = (catalog: Ref<CardFilterCatalog>) => {
  const query = ref('');
  const lifecycleStatus = ref<'active' | 'deprecated' | 'all'>('active');
  const keywordMatch = ref<'any' | 'all'>('any');
  const tagMatch = ref<'any' | 'all'>('any');
  const typeMatch = ref<'any' | 'all'>('any');
  const manaSymbolMatch = ref<'any' | 'all'>('any');
  const affinitySymbolMatch = ref<'any' | 'all'>('any');
  const devotionSymbolMatch = ref<'any' | 'all'>('any');
  const otherSymbolMatch = ref<'any' | 'all'>('any');
  const templateId = ref('');
  const manaCostMin = ref('');
  const manaCostMax = ref('');
  const attackMin = ref('');
  const attackMax = ref('');
  const healthMin = ref('');
  const healthMax = ref('');
  const keywordIds = ref<string[]>([]);
  const tagIds = ref<string[]>([]);
  const manaTypeSymbolIds = ref<string[]>([]);
  const manaTypeSymbolExcludeIds = ref<string[]>([]);
  const affinitySymbolIds = ref<string[]>([]);
  const affinitySymbolExcludeIds = ref<string[]>([]);
  const devotionSymbolIds = ref<string[]>([]);
  const devotionSymbolExcludeIds = ref<string[]>([]);
  const otherSymbolIds = ref<string[]>([]);
  const otherSymbolExcludeIds = ref<string[]>([]);
  const typeIds = ref<string[]>([]);

  const selectionState = computed<CardFilterSelectionState>(() =>
    normalizeCardFilterSelectionState({
      query: query.value,
      lifecycleStatus: lifecycleStatus.value,
      keywordMatch: keywordMatch.value,
      tagMatch: tagMatch.value,
      typeMatch: typeMatch.value,
      manaSymbolMatch: manaSymbolMatch.value,
      affinitySymbolMatch: affinitySymbolMatch.value,
      devotionSymbolMatch: devotionSymbolMatch.value,
      otherSymbolMatch: otherSymbolMatch.value,
      templateId: templateId.value,
      manaCostMin: manaCostMin.value,
      manaCostMax: manaCostMax.value,
      attackMin: attackMin.value,
      attackMax: attackMax.value,
      healthMin: healthMin.value,
      healthMax: healthMax.value,
      keywordIds: keywordIds.value,
      tagIds: tagIds.value,
      manaTypeSymbolIds: manaTypeSymbolIds.value,
      manaTypeSymbolExcludeIds: manaTypeSymbolExcludeIds.value,
      affinitySymbolIds: affinitySymbolIds.value,
      affinitySymbolExcludeIds: affinitySymbolExcludeIds.value,
      devotionSymbolIds: devotionSymbolIds.value,
      devotionSymbolExcludeIds: devotionSymbolExcludeIds.value,
      otherSymbolIds: otherSymbolIds.value,
      otherSymbolExcludeIds: otherSymbolExcludeIds.value,
      typeIds: typeIds.value,
    }),
  );

  const applySelectionState = (state: CardFilterSelectionState): void => {
    const normalized = normalizeCardFilterSelectionState(state);
    query.value = normalized.query;
    lifecycleStatus.value = normalized.lifecycleStatus ?? 'active';
    keywordMatch.value = normalized.keywordMatch;
    tagMatch.value = normalized.tagMatch;
    typeMatch.value = normalized.typeMatch;
    manaSymbolMatch.value = normalized.manaSymbolMatch;
    affinitySymbolMatch.value = normalized.affinitySymbolMatch;
    devotionSymbolMatch.value = normalized.devotionSymbolMatch;
    otherSymbolMatch.value = normalized.otherSymbolMatch;
    templateId.value = normalized.templateId;
    manaCostMin.value = normalized.manaCostMin;
    manaCostMax.value = normalized.manaCostMax;
    attackMin.value = normalized.attackMin;
    attackMax.value = normalized.attackMax;
    healthMin.value = normalized.healthMin;
    healthMax.value = normalized.healthMax;
    keywordIds.value = [...normalized.keywordIds];
    tagIds.value = [...normalized.tagIds];
    manaTypeSymbolIds.value = [...normalized.manaTypeSymbolIds];
    manaTypeSymbolExcludeIds.value = [...normalized.manaTypeSymbolExcludeIds];
    affinitySymbolIds.value = [...normalized.affinitySymbolIds];
    affinitySymbolExcludeIds.value = [...normalized.affinitySymbolExcludeIds];
    devotionSymbolIds.value = [...normalized.devotionSymbolIds];
    devotionSymbolExcludeIds.value = [...normalized.devotionSymbolExcludeIds];
    otherSymbolIds.value = [...normalized.otherSymbolIds];
    otherSymbolExcludeIds.value = [...normalized.otherSymbolExcludeIds];
    typeIds.value = [...normalized.typeIds];
  };

  const applyFilterState = (state: CardFilterState): void => {
    applySelectionState(buildCardFilterSelectionState(state, catalog.value));
  };

  const readFilterState = (): CardFilterState =>
    buildCardFilterStateFromSelection(selectionState.value, catalog.value);

  const reset = (): void => {
    applySelectionState(createEmptyCardFilterSelectionState());
  };

  return {
    query,
    lifecycleStatus,
    keywordMatch,
    tagMatch,
    typeMatch,
    manaSymbolMatch,
    affinitySymbolMatch,
    devotionSymbolMatch,
    otherSymbolMatch,
    templateId,
    manaCostMin,
    manaCostMax,
    attackMin,
    attackMax,
    healthMin,
    healthMax,
    keywordIds,
    tagIds,
    manaTypeSymbolIds,
    manaTypeSymbolExcludeIds,
    affinitySymbolIds,
    affinitySymbolExcludeIds,
    devotionSymbolIds,
    devotionSymbolExcludeIds,
    otherSymbolIds,
    otherSymbolExcludeIds,
    typeIds,
    selectionState,
    applySelectionState,
    applyFilterState,
    readFilterState,
    reset,
  };
};

export type ReturnTypeUseCardFilterState = ReturnType<typeof useCardFilterState>;
