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
  const manaCost = ref('');
  const manaSymbolMatch = ref<'any' | 'all'>('any');
  const affinitySymbolMatch = ref<'any' | 'all'>('any');
  const devotionSymbolMatch = ref<'any' | 'all'>('any');
  const otherSymbolMatch = ref<'any' | 'all'>('any');
  const templateId = ref('');
  const attackMin = ref('');
  const attackMax = ref('');
  const healthMin = ref('');
  const healthMax = ref('');
  const keywordIds = ref<string[]>([]);
  const tagIds = ref<string[]>([]);
  const manaTypeSymbolIds = ref<string[]>([]);
  const affinitySymbolIds = ref<string[]>([]);
  const devotionSymbolIds = ref<string[]>([]);
  const otherSymbolIds = ref<string[]>([]);
  const typeIds = ref<string[]>([]);

  const selectionState = computed<CardFilterSelectionState>(() =>
    normalizeCardFilterSelectionState({
      query: query.value,
      manaCost: manaCost.value,
      manaSymbolMatch: manaSymbolMatch.value,
      affinitySymbolMatch: affinitySymbolMatch.value,
      devotionSymbolMatch: devotionSymbolMatch.value,
      otherSymbolMatch: otherSymbolMatch.value,
      templateId: templateId.value,
      attackMin: attackMin.value,
      attackMax: attackMax.value,
      healthMin: healthMin.value,
      healthMax: healthMax.value,
      keywordIds: keywordIds.value,
      tagIds: tagIds.value,
      manaTypeSymbolIds: manaTypeSymbolIds.value,
      affinitySymbolIds: affinitySymbolIds.value,
      devotionSymbolIds: devotionSymbolIds.value,
      otherSymbolIds: otherSymbolIds.value,
      typeIds: typeIds.value,
    }),
  );

  const applySelectionState = (state: CardFilterSelectionState): void => {
    const normalized = normalizeCardFilterSelectionState(state);
    query.value = normalized.query;
    manaCost.value = normalized.manaCost;
    manaSymbolMatch.value = normalized.manaSymbolMatch;
    affinitySymbolMatch.value = normalized.affinitySymbolMatch;
    devotionSymbolMatch.value = normalized.devotionSymbolMatch;
    otherSymbolMatch.value = normalized.otherSymbolMatch;
    templateId.value = normalized.templateId;
    attackMin.value = normalized.attackMin;
    attackMax.value = normalized.attackMax;
    healthMin.value = normalized.healthMin;
    healthMax.value = normalized.healthMax;
    keywordIds.value = [...normalized.keywordIds];
    tagIds.value = [...normalized.tagIds];
    manaTypeSymbolIds.value = [...normalized.manaTypeSymbolIds];
    affinitySymbolIds.value = [...normalized.affinitySymbolIds];
    devotionSymbolIds.value = [...normalized.devotionSymbolIds];
    otherSymbolIds.value = [...normalized.otherSymbolIds];
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
    manaCost,
    manaSymbolMatch,
    affinitySymbolMatch,
    devotionSymbolMatch,
    otherSymbolMatch,
    templateId,
    attackMin,
    attackMax,
    healthMin,
    healthMax,
    keywordIds,
    tagIds,
    manaTypeSymbolIds,
    affinitySymbolIds,
    devotionSymbolIds,
    otherSymbolIds,
    typeIds,
    selectionState,
    applySelectionState,
    applyFilterState,
    readFilterState,
    reset,
  };
};
