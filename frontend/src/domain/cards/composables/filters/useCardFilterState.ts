import { computed, ref } from 'vue';
import type { Ref } from 'vue';
import type { CardRoleFilter } from '@/domain/cards/cardRoles';
import type { CardPool } from '@/domain/cards/cardPools';
import type { CardFaction } from '@/domain/cards/cardFactions';
import type {
  CardFilterSelectionState,
} from '@/domain/cards/utils/filters/cardFilterState';
import type { CardFilterCatalog } from '@/domain/cards/utils/filters/cardFilterSelection';
import {
  DEFAULT_CARD_LIFECYCLE_FILTER,
  type CardLifecycleFilterValue,
} from '@/domain/cards/utils/filters/cardLifecycle';
import {
  createEmptyCardFilterSelectionState,
  normalizeCardFilterSelectionState,
  type CardFilterState,
} from '@/domain/cards/utils/filters/cardFilterState';
import {
  buildCardFilterSelectionState,
  buildCardFilterStateFromSelection,
} from '@/domain/cards/utils/filters/cardFilterSelection';

export const useCardFilterState = (catalog: Ref<CardFilterCatalog>) => {
  const query = ref('');
  const lifecycleStatus = ref<CardLifecycleFilterValue>(DEFAULT_CARD_LIFECYCLE_FILTER);
  const cardPool = ref<CardPool>('player');
  const cardRoleMatch = ref<'any' | 'all'>('any');
  const cardRoleIds = ref<CardRoleFilter[]>([]);
  const cardRoleExcludeIds = ref<CardRoleFilter[]>([]);
  const cardFactionMatch = ref<'any' | 'all'>('any');
  const cardFactionIds = ref<CardFaction[]>([]);
  const cardFactionExcludeIds = ref<CardFaction[]>([]);
  const keywordMatch = ref<'any' | 'all'>('any');
  const tagMatch = ref<'any' | 'all'>('any');
  const typeMatch = ref<'any' | 'all'>('any');
  const manaFamilyMatch = ref<'any' | 'all'>('any');
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
  const manaFamilyIds = ref<string[]>([]);
  const manaFamilyExcludeIds = ref<string[]>([]);
  const affinitySymbolIds = ref<string[]>([]);
  const affinitySymbolExcludeIds = ref<string[]>([]);
  const devotionSymbolIds = ref<string[]>([]);
  const devotionSymbolExcludeIds = ref<string[]>([]);
  const otherSymbolIds = ref<string[]>([]);
  const otherSymbolExcludeIds = ref<string[]>([]);
  const typeIds = ref<string[]>([]);
  const typeExcludeIds = ref<string[]>([]);

  const selectionState = computed<CardFilterSelectionState>(() =>
    normalizeCardFilterSelectionState({
      query: query.value,
      lifecycleStatus: lifecycleStatus.value,
      cardPool: cardPool.value,
      cardRoleMatch: cardRoleMatch.value,
      cardRoleIds: cardRoleIds.value,
      cardRoleExcludeIds: cardRoleExcludeIds.value,
      cardFactionMatch: cardFactionMatch.value,
      cardFactionIds: cardFactionIds.value,
      cardFactionExcludeIds: cardFactionExcludeIds.value,
      keywordMatch: keywordMatch.value,
      tagMatch: tagMatch.value,
      typeMatch: typeMatch.value,
      manaFamilyMatch: manaFamilyMatch.value,
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
      manaFamilyIds: manaFamilyIds.value,
      manaFamilyExcludeIds: manaFamilyExcludeIds.value,
      affinitySymbolIds: affinitySymbolIds.value,
      affinitySymbolExcludeIds: affinitySymbolExcludeIds.value,
      devotionSymbolIds: devotionSymbolIds.value,
      devotionSymbolExcludeIds: devotionSymbolExcludeIds.value,
      otherSymbolIds: otherSymbolIds.value,
      otherSymbolExcludeIds: otherSymbolExcludeIds.value,
      typeIds: typeIds.value,
      typeExcludeIds: typeExcludeIds.value,
    }),
  );

  const applySelectionState = (state: CardFilterSelectionState): void => {
    const normalized = normalizeCardFilterSelectionState(state);
    query.value = normalized.query;
    lifecycleStatus.value = normalized.lifecycleStatus ?? DEFAULT_CARD_LIFECYCLE_FILTER;
    cardPool.value = normalized.cardPool;
    cardRoleMatch.value = normalized.cardRoleMatch;
    cardRoleIds.value = [...normalized.cardRoleIds];
    cardRoleExcludeIds.value = [...normalized.cardRoleExcludeIds];
    cardFactionMatch.value = normalized.cardFactionMatch ?? 'any';
    cardFactionIds.value = [...(normalized.cardFactionIds ?? [])];
    cardFactionExcludeIds.value = [...(normalized.cardFactionExcludeIds ?? [])];
    keywordMatch.value = normalized.keywordMatch;
    tagMatch.value = normalized.tagMatch;
    typeMatch.value = normalized.typeMatch;
    manaFamilyMatch.value = normalized.manaFamilyMatch;
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
    manaFamilyIds.value = [...normalized.manaFamilyIds];
    manaFamilyExcludeIds.value = [...normalized.manaFamilyExcludeIds];
    affinitySymbolIds.value = [...normalized.affinitySymbolIds];
    affinitySymbolExcludeIds.value = [...normalized.affinitySymbolExcludeIds];
    devotionSymbolIds.value = [...normalized.devotionSymbolIds];
    devotionSymbolExcludeIds.value = [...normalized.devotionSymbolExcludeIds];
    otherSymbolIds.value = [...normalized.otherSymbolIds];
    otherSymbolExcludeIds.value = [...normalized.otherSymbolExcludeIds];
    typeIds.value = [...normalized.typeIds];
    typeExcludeIds.value = [...normalized.typeExcludeIds];
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
    cardPool,
    cardRoleMatch,
    cardRoleIds,
    cardRoleExcludeIds,
    cardFactionMatch,
    cardFactionIds,
    cardFactionExcludeIds,
    keywordMatch,
    tagMatch,
    typeMatch,
    manaFamilyMatch,
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
    manaFamilyIds,
    manaFamilyExcludeIds,
    affinitySymbolIds,
    affinitySymbolExcludeIds,
    devotionSymbolIds,
    devotionSymbolExcludeIds,
    otherSymbolIds,
    otherSymbolExcludeIds,
    typeIds,
    typeExcludeIds,
    selectionState,
    applySelectionState,
    applyFilterState,
    readFilterState,
    reset,
  };
};

export type ReturnTypeUseCardFilterState = ReturnType<typeof useCardFilterState>;
