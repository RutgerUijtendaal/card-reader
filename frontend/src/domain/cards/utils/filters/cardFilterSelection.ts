import type { CardFiltersResponse, MetadataOption, SymbolFilterOption } from '@/domain/cards/types';
import {
  normalizeCardFilterSelectionState,
  normalizeCardFilterState,
  type CardFilterSelectionState,
  type CardFilterState,
} from '@/domain/cards/utils/filters/cardFilterState';

export type CardFilterCatalog = {
  keywords: MetadataOption[];
  tags: MetadataOption[];
  types: MetadataOption[];
  manaSymbols: SymbolFilterOption[];
  affinitySymbols: SymbolFilterOption[];
  devotionSymbols: SymbolFilterOption[];
  otherSymbols: SymbolFilterOption[];
};

export const createCardFilterCatalog = (filters: CardFiltersResponse): CardFilterCatalog => ({
  keywords: filters.keywords ?? [],
  tags: filters.tags ?? [],
  types: filters.types ?? [],
  manaSymbols: (filters.symbols ?? []).filter(
    (row) => row.symbol_type === 'mana' && !row.key.startsWith('colorless-mana-'),
  ),
  affinitySymbols: (filters.symbols ?? []).filter((row) => row.symbol_type === 'affinity'),
  devotionSymbols: (filters.symbols ?? []).filter((row) => row.symbol_type === 'devotion'),
  otherSymbols: (filters.symbols ?? []).filter(
    (row) => !['mana', 'devotion', 'affinity'].includes(row.symbol_type),
  ),
});

const resolveIdsFromKeys = (keys: string[], options: MetadataOption[]): string[] => {
  const idByKey = new Map(options.map((option) => [option.key, option.id]));
  return keys.map((key) => idByKey.get(key)).filter((id): id is string => typeof id === 'string');
};

const resolveKeysFromIds = (ids: string[], options: MetadataOption[]): string[] => {
  const keyById = new Map(options.map((option) => [option.id, option.key]));
  return ids.map((id) => keyById.get(id)).filter((key): key is string => typeof key === 'string');
};

export const buildCardFilterSelectionState = (
  state: CardFilterState,
  catalog: CardFilterCatalog,
): CardFilterSelectionState =>
  normalizeCardFilterSelectionState({
    query: state.query,
    lifecycleStatus: state.lifecycleStatus,
    keywordMatch: state.keywordMatch,
    tagMatch: state.tagMatch,
    typeMatch: state.typeMatch,
    manaSymbolMatch: state.manaSymbolMatch,
    affinitySymbolMatch: state.affinitySymbolMatch,
    devotionSymbolMatch: state.devotionSymbolMatch,
    otherSymbolMatch: state.otherSymbolMatch,
    templateId: state.templateId,
    manaCostMin: state.manaCostMin,
    manaCostMax: state.manaCostMax,
    attackMin: state.attackMin,
    attackMax: state.attackMax,
    healthMin: state.healthMin,
    healthMax: state.healthMax,
    keywordIds: resolveIdsFromKeys(state.keywordKeys, catalog.keywords),
    tagIds: resolveIdsFromKeys(state.tagKeys, catalog.tags),
    manaTypeSymbolIds: resolveIdsFromKeys(state.manaSymbolKeys, catalog.manaSymbols),
    manaTypeSymbolExcludeIds: resolveIdsFromKeys(state.manaSymbolExcludeKeys, catalog.manaSymbols),
    affinitySymbolIds: resolveIdsFromKeys(state.affinitySymbolKeys, catalog.affinitySymbols),
    affinitySymbolExcludeIds: resolveIdsFromKeys(state.affinitySymbolExcludeKeys, catalog.affinitySymbols),
    devotionSymbolIds: resolveIdsFromKeys(state.devotionSymbolKeys, catalog.devotionSymbols),
    devotionSymbolExcludeIds: resolveIdsFromKeys(state.devotionSymbolExcludeKeys, catalog.devotionSymbols),
    otherSymbolIds: resolveIdsFromKeys(state.otherSymbolKeys, catalog.otherSymbols),
    otherSymbolExcludeIds: resolveIdsFromKeys(state.otherSymbolExcludeKeys, catalog.otherSymbols),
    typeIds: resolveIdsFromKeys(state.typeKeys, catalog.types),
    typeExcludeIds: resolveIdsFromKeys(state.typeExcludeKeys, catalog.types),
  });

export const buildCardFilterStateFromSelection = (
  state: CardFilterSelectionState,
  catalog: CardFilterCatalog,
): CardFilterState =>
  normalizeCardFilterState({
    query: state.query,
    lifecycleStatus: state.lifecycleStatus,
    keywordMatch: state.keywordMatch,
    tagMatch: state.tagMatch,
    typeMatch: state.typeMatch,
    manaSymbolMatch: state.manaSymbolMatch,
    affinitySymbolMatch: state.affinitySymbolMatch,
    devotionSymbolMatch: state.devotionSymbolMatch,
    otherSymbolMatch: state.otherSymbolMatch,
    templateId: state.templateId,
    manaCostMin: state.manaCostMin,
    manaCostMax: state.manaCostMax,
    attackMin: state.attackMin,
    attackMax: state.attackMax,
    healthMin: state.healthMin,
    healthMax: state.healthMax,
    keywordKeys: resolveKeysFromIds(state.keywordIds, catalog.keywords),
    tagKeys: resolveKeysFromIds(state.tagIds, catalog.tags),
    manaSymbolKeys: resolveKeysFromIds(state.manaTypeSymbolIds, catalog.manaSymbols),
    manaSymbolExcludeKeys: resolveKeysFromIds(state.manaTypeSymbolExcludeIds, catalog.manaSymbols),
    affinitySymbolKeys: resolveKeysFromIds(state.affinitySymbolIds, catalog.affinitySymbols),
    affinitySymbolExcludeKeys: resolveKeysFromIds(state.affinitySymbolExcludeIds, catalog.affinitySymbols),
    devotionSymbolKeys: resolveKeysFromIds(state.devotionSymbolIds, catalog.devotionSymbols),
    devotionSymbolExcludeKeys: resolveKeysFromIds(state.devotionSymbolExcludeIds, catalog.devotionSymbols),
    otherSymbolKeys: resolveKeysFromIds(state.otherSymbolIds, catalog.otherSymbols),
    otherSymbolExcludeKeys: resolveKeysFromIds(state.otherSymbolExcludeIds, catalog.otherSymbols),
    typeKeys: resolveKeysFromIds(state.typeIds, catalog.types),
    typeExcludeKeys: resolveKeysFromIds(state.typeExcludeIds, catalog.types),
  });
